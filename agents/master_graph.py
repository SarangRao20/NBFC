"""Master Graph for NBFC — Deterministic Linear Pipeline with MongoDB Persistence

DETERMINISTIC FLOW (No LLM routing overhead):
  1. Load Session → Resume from MongoDB if existing
  2. Intent → Ask what they want (user already authenticated)
  3. Sales → Get loan amount & tenure
  4. Document+Fraud → Process documents, check fraud (parallel)
  5. Underwriting → Make approval/rejection decision
  6. Negotiations → If soft-reject, offer alternatives
  7. Sanction/Rejection → Generate final letter
  8. Advisory → Final guidance & completion

Every phase saves state to MongoDB automatically.
Advisor has full context: current_phase, docs, messages, action_log.
"""

import os
import sys
from typing import Annotated, TypedDict, Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

# Import agent nodes (registration removed since users authenticate via onboarding UI)
from agents.intent_agent import intent_node
from agents.sales_agent import sales_agent_node
from agents.document_agent import document_agent_node
from agents.kyc_agent import verification_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.sanction_agent import sanction_agent_node
from agents.bank_verification_agent import bank_verification_agent_node
from agents.document_query_agent import document_query_agent_node
from agents.emi_engine import emi_engine_node
from agents.repayment_agent import repayment_agent_node
from agents.master_state import MasterState
from agents.master_router import route_next_agent
from agents.session_manager import SessionManager

from api.core.websockets import manager
from langchain_core.messages import HumanMessage, AIMessage


# ─── Node Wrapper (Timing + Observability) ────────────────────────────────────
def node_wrapper(node_func, node_name):
    """Wraps a node function to track timing, previous_agent, and emit trace spans."""
    async def wrapper(state: MasterState):
        import inspect
        from agents.tracer import Span, append_span

        span = Span(
            node=node_name,
            phase=state.get("current_phase", "unknown"),
            intent=state.get("intent"),
            decision=state.get("decision") or None,
        )
        print(f"🚀 [NODE:{node_name}] phase={span.phase} intent={span.intent}")

        try:
            if inspect.iscoroutinefunction(node_func):
                result = await node_func(state)
            else:
                result = node_func(state)

            if result is None:
                result = {}

            if isinstance(result, dict):
                result["previous_agent"] = node_name
                span.end(
                    success=True,
                    decision=result.get("decision") or state.get("decision") or None,
                )
                result["trace_events"] = append_span(state.get("trace_events", []), span)
                print(f"   ✅ [{node_name}] done in {span.duration_ms}ms")

        except Exception as exc:
            span.end(success=False, error=str(exc))
            print(f"   ❌ [{node_name}] failed in {span.duration_ms}ms: {exc}")
            raise

        return result
    return wrapper

# ─── Load Session (at START) ──────────────────────────────────────────────────
async def load_session_node(state: MasterState):
    """Load existing session from MongoDB if resuming."""
    session_id = state.get("session_id", "default")
    
    print(f"\n📂 [LOAD SESSION] Starting for session {session_id}")
    
    try:
        # Try to load from DB
        saved_state = await SessionManager.load_session(session_id)
        if saved_state:
            print(f"📂 Resuming session {session_id}")
            # Merge saved state with current state, preferring saved values
            merged_state = {**state, **saved_state}
            
            # Ensure customer_data has required fields
            customer_data = merged_state.get("customer_data", {})
            if not isinstance(customer_data, dict):
                customer_data = {}
            merged_state["customer_data"] = {
                "name": customer_data.get("name", ""),
                "phone": customer_data.get("phone", ""),
                "email": customer_data.get("email", ""),
                "city": customer_data.get("city", ""),
                "salary": customer_data.get("salary", 0),
                "dob": customer_data.get("dob", ""),
                "credit_score": customer_data.get("credit_score", 0),
                "existing_emi_total": customer_data.get("existing_emi_total", 0),
                "pre_approved_limit": customer_data.get("pre_approved_limit", 100000),
                **customer_data
            }
            
            return {
                "action_log": ["📂 Session resumed from MongoDB"],
                **merged_state
            }
    except Exception as load_err:
        print(f"   ⚠️ Session load error: {load_err}")
        import traceback
        traceback.print_exc()
    
    print(f"🆕 New session {session_id}")
    # Ensure state has required fields for new sessions
    if "customer_data" not in state:
        state["customer_data"] = {}
    if "name" not in state["customer_data"]:
        state["customer_data"]["name"] = ""
    if "email" not in state["customer_data"]:
        state["customer_data"]["email"] = ""
    if "phone" not in state["customer_data"]:
        state["customer_data"]["phone"] = ""
    if "city" not in state["customer_data"]:
        state["customer_data"]["city"] = ""
    if "salary" not in state["customer_data"]:
        state["customer_data"]["salary"] = 0
    if "dob" not in state["customer_data"]:
        state["customer_data"]["dob"] = ""
    if "pre_approved_limit" not in state["customer_data"]:
        state["customer_data"]["pre_approved_limit"] = 100000
    
    return {
        "action_log": ["🆕 New session started"],
        "current_phase": state.get("current_phase") or "registration",
    }


# ─── Deterministic Supervisor Node (NO LLM) ──────────────────────────────────
async def supervisor_node(state: MasterState):
    """Route to next agent based on DETERMINISTIC state rules."""
    session_id = state.get("session_id", "default")
    
    print(f"\n🔀 [SUPERVISOR] Starting for session {session_id}")
    print(f"   Current state keys: {list(state.keys())[:10]}...")
    
    # Build safe defaults as a NEW dict — never mutate state directly in a node
    _cust = state.get("customer_data") if isinstance(state.get("customer_data"), dict) else {}
    customer_data = {
        "name": "", "email": "", "phone": "", "city": "",
        "salary": 0, "dob": "", "credit_score": 0,
        "existing_emi_total": 0, "pre_approved_limit": 100000,
        **_cust,
    }
    _terms = state.get("loan_terms") if isinstance(state.get("loan_terms"), dict) else {}
    loan_terms = {"principal": 0, "tenure": 0, **_terms}
    _docs = state.get("documents") if isinstance(state.get("documents"), dict) else {}
    documents = {"verified": False, **_docs}
    
    # Build a patched view of state for the router without mutating the real state
    patched_state = {**state, "customer_data": customer_data, "loan_terms": loan_terms, "documents": documents}

    await manager.broadcast_thinking(session_id, "Router", True)
    next_agent, reasoning = route_next_agent(patched_state)
    await manager.broadcast_thinking(session_id, "Router", False)

    # Cap action_log at 50 entries to prevent unbounded MongoDB growth
    existing_log = list(state.get("action_log") or [])
    new_entry = f"🔀 {next_agent} — {reasoning}"
    trimmed_log = (existing_log + [new_entry])[-50:]

    # Cap messages at last 40 to prevent unbounded MongoDB growth (keep context window sensible)
    existing_msgs = list(state.get("messages") or [])
    trimmed_msgs = existing_msgs[-40:] if len(existing_msgs) > 40 else existing_msgs

    return {
        "next_agent": next_agent,
        "routing_reasoning": reasoning,
        "customer_data": customer_data,
        "loan_terms": loan_terms,
        "documents": documents,
        "action_log": trimmed_log,
        "messages": trimmed_msgs,
    }


# ─── Supervisor Router (Agent Name → Graph Node) ────────────────────────────
def supervisor_router(state: MasterState) -> str:
    """Map next_agent → graph node with loop-prevention. No fan-out; sequential only."""
    next_agent = state.get("next_agent", "sales_agent")

    valid_nodes = {
        "intent_agent", "sales_agent", "document_agent",
        "verification_agent", "fraud_agent", "underwriting_agent",
        "sanction_agent", "bank_verification_agent",
        "document_query_agent", "emi_engine", "repayment_agent",
    }
    target = next_agent if next_agent in valid_nodes else "sales_agent"

    # Loop prevention: if the last message is already an AI reply, stop.
    msgs = state.get("messages", [])
    previous = state.get("previous_agent")

    if msgs and isinstance(msgs[-1], AIMessage) and previous:
        print(f"🛑 [ROUTER] {previous} already responded. Waiting for user.")
        return "__end__"

    if target == previous:
        print(f"🛑 [ROUTER] {target} already ran. Waiting for user.")
        return "__end__"

    print(f"🔀 [ROUTER] → {target}")
    return target


# ─── Join Node (merge parallel KYC + Fraud results) ─────────────────────────
def join_verification_node(state: MasterState):
    """Aggregate results from parallel KYC and Fraud checks."""
    print("🤝 [JOIN NODE] Merging verification results...")
    return {"action_log": ["🤝 Parallel checks completed and merged."]}

def route_after_intent(state: MasterState) -> str:
    # If the intent is unclear, we stop and wait for the user to answer the clarification text.
    if state.get("intent") == "unclear":
        return END
    return "supervisor"

# ─── Graph Construction ───────────────────────────────────────────────────────
def compile_master_graph():
    workflow = StateGraph(MasterState)

    # ── Register nodes (Wrapped) ─────────────────────────────────────────────
    workflow.add_node("load_session",           node_wrapper(load_session_node, "load_session"))
    workflow.add_node("supervisor",             supervisor_node)
    workflow.add_node("intent_agent",           node_wrapper(intent_node, "intent_agent"))
    workflow.add_node("sales_agent",            node_wrapper(sales_agent_node, "sales_agent"))
    workflow.add_node("document_agent",         node_wrapper(document_agent_node, "document_agent"))
    workflow.add_node("verification_agent",     node_wrapper(verification_agent_node, "verification_agent"))
    workflow.add_node("fraud_agent",            node_wrapper(fraud_agent_node, "fraud_agent"))
    workflow.add_node("join_verification",      node_wrapper(join_verification_node, "join_verification"))
    workflow.add_node("underwriting_agent",     node_wrapper(underwriting_agent_node, "underwriting_agent"))
    workflow.add_node("sanction_agent",         node_wrapper(sanction_agent_node, "sanction_agent"))
    workflow.add_node("bank_verification_agent", node_wrapper(bank_verification_agent_node, "bank_verification_agent"))
    workflow.add_node("document_query_agent",   node_wrapper(document_query_agent_node, "document_query_agent"))
    workflow.add_node("emi_engine",             node_wrapper(emi_engine_node, "emi_engine"))
    workflow.add_node("repayment_agent",        node_wrapper(repayment_agent_node, "repayment_agent"))

    # ── Entry: Load session, then conditionally EMI engine, then supervisor ───
    workflow.add_edge(START, "load_session")
    workflow.add_conditional_edges(
        "load_session",
        lambda s: "emi_engine" if (
            s.get("loan_terms", {}).get("principal", 0) > 0 and
            s.get("loan_terms", {}).get("next_emi_date")
        ) else "supervisor",
        {"emi_engine": "emi_engine", "supervisor": "supervisor"}
    )
    workflow.add_edge("emi_engine", "supervisor")

    # ── Dynamic routing from supervisor ──────────────────────────────────────
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "intent_agent":             "intent_agent",
            "sales_agent":              "sales_agent",
            "document_agent":           "document_agent",
            "verification_agent":       "verification_agent",
            "fraud_agent":              "fraud_agent",
            "underwriting_agent":       "underwriting_agent",
            "sanction_agent":           "sanction_agent",
            "bank_verification_agent":  "bank_verification_agent",
            "document_query_agent":     "document_query_agent",
            "emi_engine":               "emi_engine",
            "repayment_agent":          "repayment_agent",
            "__end__":                  END
        }
    )

    # ── ALL nodes - Chain back to supervisor to continue processing ──────────
    # (Router handles END logic based on state change/human messages)
    workflow.add_edge("intent_agent",             "supervisor")
    workflow.add_edge("sales_agent",              "supervisor")
    workflow.add_edge("document_agent",           "supervisor")
    workflow.add_edge("document_query_agent",     "supervisor")
    workflow.add_edge("repayment_agent",          "supervisor")
    workflow.add_edge("underwriting_agent",       "supervisor")
    workflow.add_edge("sanction_agent",           "supervisor")
    workflow.add_edge("bank_verification_agent",  "supervisor")

    # Verification nodes merge at join before continuing
    workflow.add_edge("verification_agent", "join_verification")
    workflow.add_edge("fraud_agent",        "join_verification")
    workflow.add_edge("join_verification",  "supervisor")

    return workflow.compile()


if __name__ == "__main__":
    graph = compile_master_graph()
    print("✅ Master Graph compiled successfully!")

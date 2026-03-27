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
from typing import Annotated, TypedDict, Sequence, Optional, Any, cast
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END, START

# Import agent nodes (registration removed since users authenticate via onboarding UI)
from agents.intent_agent import intent_node
from agents.sales_agent import sales_agent_node
from agents.document_agent import document_agent_node
from agents.kyc_agent import verification_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.sanction_agent import sanction_agent_node
from agents.document_query_agent import document_query_agent_node
from agents.emi_engine import emi_engine_node
from agents.repayment_agent import repayment_agent_node
from agents.master_state import MasterState
from agents.master_router import route_next_agent
from agents.session_manager import SessionManager
from agents.subgraphs import disbursement_subgraph

from api.core.websockets import manager


from api.core.websockets import manager
from langchain_core.messages import HumanMessage, AIMessage


# ─── Node Wrapper (Auto-track previous_agent) ────────────────────────────────
def node_wrapper(node_func, node_name):
    """Wraps a node function to automatically update 'previous_agent' in state."""
    async def wrapper(state: MasterState):
        print(f"🚀 [NODE] Starting: {node_name}")
        
        # Call original node
        # Check if it's async or sync
        import inspect
        if inspect.iscoroutinefunction(node_func):
            result = await node_func(state)
        else:
            result = node_func(state)
            
        # Ensure result is a dict and set previous_agent
        if result is None:
            result = {}
        
        # Result might be a dict to update state
        if isinstance(result, dict):
            # Special case for Load Session which returns current_phase
            result["previous_agent"] = node_name
            
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
        "current_phase": "registration",
        **state
    }


# ─── Deterministic Supervisor Node (NO LLM) ──────────────────────────────────
async def supervisor_node(state: MasterState):
    """Route to next agent based on DETERMINISTIC state rules."""
    session_id = state.get("session_id", "default")
    
    print(f"\n🔀 [SUPERVISOR] Starting for session {session_id}")
    print(f"   Current state keys: {list(state.keys())[:10]}...")
    
    # SAFETY: Ensure state has all required fields (defensive against incomplete state)
    try:
        if not isinstance(state.get("customer_data"), dict):
            print(f"   ⚠️ customer_data is not dict, resetting")
            state["customer_data"] = {}
        
        required_customer_fields = ["name", "email", "phone", "city", "salary", "dob", "credit_score", "existing_emi_total", "pre_approved_limit"]
        for field in required_customer_fields:
            if field not in state["customer_data"]:
                print(f"   ➕ Adding missing customer_data.{field}")
                if field == "salary" or field == "credit_score" or field == "existing_emi_total":
                    state["customer_data"][field] = 0
                elif field == "pre_approved_limit":
                    state["customer_data"][field] = 100000
                else:
                    state["customer_data"][field] = ""
        
        if not isinstance(state.get("loan_terms"), dict):
            state["loan_terms"] = {}
        for field in ["principal", "tenure"]:
            if field not in state["loan_terms"]:
                state["loan_terms"][field] = 0
        
        if not isinstance(state.get("documents"), dict):
            state["documents"] = {}
        if "verified" not in state["documents"]:
            state["documents"]["verified"] = False
        
        print(f"   ✅ State safety check passed")
    except Exception as safety_err:
        print(f"   ❌ Safety initialization failed: {safety_err}")
        import traceback
        traceback.print_exc()
        raise
    
    # Broadcast thinking indicator
    await manager.broadcast_thinking(session_id, "Router", True)
    
    print("🔀 [DETERMINISTIC ROUTER] Analyzing state...")
    
    # Get next agent via rule-based router
    next_agent, reasoning = route_next_agent(state)
    
    print(f"  → Next Agent: {next_agent}")
    print(f"  → Reason: {reasoning}")
    
    await manager.broadcast_thinking(session_id, "Router", False)
    
    return {
        "next_agent": next_agent,
        "routing_reasoning": reasoning,
        "action_log": [f"🔀 Router Decision: {next_agent} — {reasoning}"],
    }


# ─── Supervisor Router (Agent Name → Graph Node) ────────────────────────────
def supervisor_router(state: MasterState):
    """Map agent name to graph node with loop prevention and parallel execution."""
    next_agent = state.get("next_agent", "sales_agent")
    
    # ── Parallel execution for verification ──────────────────────────────────
    documents_verified = state.get("documents", {}).get("uploaded", False)
    kyc_done = state.get("kyc_status") == "verified"
    fraud_checked = state.get("fraud_score", -1) != -1
    
    # If documents are uploaded but verification is pending, run both
    if documents_verified and (not kyc_done or not fraud_checked):
        # Only do this if we aren't ALREADY running them to avoid loops
        prev = state.get("previous_agent")
        if prev not in ["verification_agent", "fraud_agent", "join_verification"]:
            targets = []
            if not kyc_done:
                targets.append("verification_agent")
            if not fraud_checked:
                targets.append("fraud_agent")
            if targets:
                print(f"🏎️ [ROUTER] Running Parallel: {targets}")
                return targets

    # ── Standard Agent Mapping ──────────────────────────────────────────────
    mapping = {
        "intent_agent": "intent_agent",
        "sales_agent": "sales_agent",
        "document_agent": "document_agent",
        "verification_agent": "verification_agent",
        "fraud_agent": "fraud_agent",
        "underwriting_agent": "underwriting_agent",
        "sanction_agent": "sanction_agent",
        "document_query_agent": "document_query_agent",
        "emi_engine": "emi_engine",
        "repayment_agent": "repayment_agent",
    }
    
    target = mapping.get(next_agent, "sales_agent")
    
    # ── Loop Prevention ──────────────────────────────────────────────────────
    # If any agent already ran and produced a message, STOP.
    # We check if the last message is an AIMessage and if we have a previous_agent.
    # This prevents Supervisor -> Agent A -> Supervisor -> Agent B chains in one turn.
    msgs = state.get("messages", [])
    previous = state.get("previous_agent")
    
    if msgs and isinstance(msgs[-1], AIMessage) and previous:
        print(f"🛑 [ROUTER] Agent {previous} already spoke. Waiting for user...")
        return END

    if target == previous:
        # Fallback safety if the above didn't catch it
        print(f"🛑 [ROUTER] Agent {target} already ran. Waiting for user...")
        return END
            
    print(f"🔀 [ROUTER] Routing to: {target}")
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
    workflow.add_node("document_query_agent",   node_wrapper(document_query_agent_node, "document_query_agent"))
    workflow.add_node("emi_engine",             node_wrapper(emi_engine_node, "emi_engine"))
    workflow.add_node("repayment_agent",        node_wrapper(repayment_agent_node, "repayment_agent"))
    # 🟢 Add the new Disbursement Subgraph as a single node
    workflow.add_node("disbursement_process", disbursement_subgraph)

    # ── Entry: Load session first, then engine, then supervisor ──────────────
    workflow.add_edge(START, "load_session")
    workflow.add_edge("load_session", "emi_engine")
    workflow.add_edge("emi_engine", "supervisor")

    # ── Dynamic routing from supervisor ──────────────────────────────────────
    workflow.add_conditional_edges(
        "supervisor", 
        supervisor_router,
        {
            "intent_agent": "intent_agent",
            "sales_agent": "sales_agent",
            "document_agent": "document_agent",
            "verification_agent": "verification_agent",
            "fraud_agent": "fraud_agent",
            "underwriting_agent": "underwriting_agent",
            "sanction_agent": "sanction_agent",
            "document_query_agent": "document_query_agent",
            "emi_engine": "emi_engine",
            "repayment_agent": "repayment_agent",
            "disbursement_process": "disbursement_process",
            END: END
        }
    )

    # ── CHAT nodes — always END (pause, wait for next user message) ──────────
    workflow.add_conditional_edges("intent_agent", route_after_intent)
    workflow.add_edge("sales_agent",        END)
    workflow.add_edge("document_query_agent", END)
    workflow.add_edge("repayment_agent",    END)

    workflow.add_edge("disbursement_process", END)

    # ── AUTOMATIC processor nodes — Chain back to supervisor to continue ─────
    workflow.add_edge("document_agent",     END) 
    
    # Parallel verification join still goes back to supervisor
    workflow.add_edge("verification_agent", "join_verification")
    workflow.add_edge("fraud_agent",        "join_verification")
    workflow.add_edge("join_verification",  "supervisor")

    workflow.add_edge("underwriting_agent", "supervisor")
    
    # ── Sanction chains back to supervisor to trigger disbursement_process ──
    workflow.add_edge("sanction_agent",     "supervisor")

    return workflow.compile()


if __name__ == "__main__":
    graph = compile_master_graph()
    print("✅ Master Graph compiled successfully!")

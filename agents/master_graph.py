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
from agents.advisor_agent import advisor_agent_node
from agents.persuasion_agent import persuasion_agent_node
from agents.emi_agent import emi_agent_node
from agents.document_query_agent import document_query_agent_node
from agents.emi_engine import emi_engine_node
from agents.master_state import MasterState
from agents.master_router import route_next_agent
from agents.session_manager import SessionManager

from api.core.websockets import manager

from api.core.websockets import manager


# ─── Load Session (at START) ──────────────────────────────────────────────────
async def load_session_node(state: MasterState):
    """Load existing session from MongoDB if resuming."""
    session_id = state.get("session_id", "default")
    
    print(f"\n📂 [LOAD SESSION] Starting for session {session_id}")
    
    try:
        # Try to load from DB
        saved_state = SessionManager.load_session(session_id)
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
    """Map agent name to graph node."""
    next_agent = state.get("next_agent", "advisor_agent")
    
    # Parallel optimization: KYC + Fraud together if both pending
    documents_verified = state.get("documents", {}).get("verified", False)
    kyc_done = state.get("kyc_status") == "verified"
    fraud_checked = state.get("fraud_score", -1) != -1
    
    if documents_verified and (not kyc_done or not fraud_checked):
        targets = []
        if not kyc_done:
            targets.append("verification_agent")
        if not fraud_checked:
            targets.append("fraud_agent")
        if targets:
            print(f"🏎️ [ROUTER] Running KYC + Fraud in parallel")
            return targets
    
    # Standard mapping (registration removed)
    mapping = {
        "intent_agent": "intent_agent",
        "sales_agent": "sales_agent",
        "document_agent": "document_agent",
        "verification_agent": "verification_agent",
        "fraud_agent": "fraud_agent",
        "underwriting_agent": "underwriting_agent",
        "persuasion_agent": "persuasion_agent",
        "sanction_agent": "sanction_agent",
        "advisor_agent": "advisor_agent",
        "emi_agent": "emi_agent",
        "document_query_agent": "document_query_agent",
        "emi_engine": "emi_engine",
    }
    
    target = mapping.get(next_agent, "advisor_agent")
    print(f"🔀 [ROUTER] Routing to: {target}")
    return target


# ─── Join Node (merge parallel KYC + Fraud results) ─────────────────────────
def join_verification_node(state: MasterState):
    """Aggregate results from parallel KYC and Fraud checks."""
    print("🤝 [JOIN NODE] Merging verification results...")
    return {"action_log": ["🤝 Parallel checks completed and merged."]}

# ─── Advisor Context Node (prepare full context before advisor) ─────────────
async def advisor_context_node(state: MasterState):
    """Prepare comprehensive context for advisor agent."""
    session_id = state.get("session_id", "default")
    
    # Load all documents uploaded for this session
    uploaded_docs = SessionManager.get_session_documents(session_id)
    
    # Prepare advisor briefing
    advisor_context = {
        "current_phase": state.get("current_phase", "unknown"),
        "customer_data": state.get("customer_data", {}),
        "loan_terms": state.get("loan_terms", {}),
        "kyc_status": state.get("kyc_status", "pending"),
        "fraud_score": state.get("fraud_score", -1),
        "decision": state.get("decision", ""),
        "risk_level": state.get("risk_level", "unknown"),
        "documents_uploaded": uploaded_docs,
        "action_log": state.get("action_log", []),
        "message_count": len(state.get("messages", [])),
    }
    
    print(f"📋 [ADVISOR CONTEXT] Session {session_id}:")
    print(f"   Phase: {advisor_context['current_phase']}")
    print(f"   Decision: {advisor_context['decision'] or 'PENDING'}")
    print(f"   Documents: {len(uploaded_docs)} uploaded")
    print(f"   Actions: {len(advisor_context['action_log'])} events logged")
    
    return {
        "advisor_context": advisor_context,
        "action_log": ["📋 Advisor context loaded with full session history"]
    }

def route_after_intent(state: MasterState) -> str:
    # If the intent is unclear, we stop and wait for the user to answer the clarification text.
    if state.get("intent") == "unclear":
        return END
    return "supervisor"

# ─── Graph Construction ───────────────────────────────────────────────────────
def compile_master_graph():
    workflow = StateGraph(MasterState)

    # ── Register nodes ──────────────────────────────────────────────────────
    workflow.add_node("load_session",           load_session_node)
    workflow.add_node("supervisor",             supervisor_node)
    workflow.add_node("intent_agent",           intent_node)
    workflow.add_node("sales_agent",            sales_agent_node)
    workflow.add_node("document_agent",         document_agent_node)
    workflow.add_node("verification_agent",     verification_agent_node)
    workflow.add_node("fraud_agent",            fraud_agent_node)
    workflow.add_node("join_verification",      join_verification_node)
    workflow.add_node("underwriting_agent",     underwriting_agent_node)
    workflow.add_node("sanction_agent",         sanction_agent_node)
    workflow.add_node("advisor_context",        advisor_context_node)
    workflow.add_node("advisor_agent",          advisor_agent_node)
    workflow.add_node("persuasion_agent",       persuasion_agent_node)
    workflow.add_node("emi_agent",              emi_agent_node)
    workflow.add_node("document_query_agent",   document_query_agent_node)
    workflow.add_node("emi_engine",             emi_engine_node)

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
            "advisor_agent": "advisor_context",
            "sanction_agent": "sanction_agent",
            "persuasion_agent": "persuasion_agent",
            "emi_agent": "emi_agent",
            "document_query_agent": "document_query_agent",
            "emi_engine": "emi_engine",
        }
    )

    # ── CHAT nodes — always END (pause, wait for next user message) ──────────
    workflow.add_conditional_edges("intent_agent", route_after_intent)
    workflow.add_edge("sales_agent",        END)
    workflow.add_edge("persuasion_agent",   END)
    workflow.add_edge("document_query_agent", END)
    workflow.add_edge("emi_agent",          END) # Stop and wait for user after showing EMI

    # ── AUTOMATIC processor nodes — Chain back to supervisor to continue ─────
    workflow.add_edge("document_agent",     END) 
    
    # Verification & Fraud run in parallel and join
    workflow.add_edge("verification_agent", "join_verification")
    workflow.add_edge("fraud_agent",        "join_verification")
    workflow.add_edge("join_verification",  "supervisor")

    workflow.add_edge("underwriting_agent", "supervisor")
    
    # ── Advisor context → advisor agent → end ──────────────────────────────
    workflow.add_edge("advisor_context",    "advisor_agent")
    workflow.add_edge("advisor_agent",      END)

    # ── Sanction chains into advisor context for final message ───────────────
    workflow.add_edge("sanction_agent",     "advisor_context")

    return workflow.compile()


if __name__ == "__main__":
    graph = compile_master_graph()
    print("✅ Master Graph compiled successfully!")

"""Master Graph for NBFC — Orchestrates the entire loan pipeline.

Architecture (Hub-and-Spoke with careful termination):
  - START → registration_extraction → supervisor → [route]
  - Nodes that need USER INPUT (chat nodes): always → END  (pauses for next message)
  - Nodes that are AUTOMATIC PROCESSORS: chain forward, then → END
  - supervisor_router decides which agent runs based on current state
"""

import os
import sys
from typing import Annotated, TypedDict, Sequence, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages

# Import agent nodes
from agents.registration import registration_chat_node, registration_extraction_node
from agents.intent_agent import intent_node
from agents.sales_agent import sales_agent_node
from agents.document_agent import document_agent_node
from agents.kyc_agent import verification_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.sanction_agent import sanction_agent_node
from agents.advisor_agent import advisor_agent_node
from agents.master_state import MasterState

import json
import re
from config import get_master_llm
from langchain_core.messages import SystemMessage, HumanMessage

MASTER_ROUTER_PROMPT = """You are the Master Router (Supervisor Brain) of an autonomous NBFC Loan Processing system.
You operate within a state-driven, hub-and-spoke architecture.

Your ONLY responsibility is to route execution to the correct agent based on:
1. Current GraphState
2. Latest user input

You are a deterministic routing engine.
You DO NOT:
- Generate conversational responses
- Perform calculations (EMI, DTI, etc.)
- Modify system state
- Skip workflow stages

=== CURRENT SYSTEM STATE (GraphState) ===
{state_json}

=== CORE EXECUTION MODEL ===
The system follows a cyclical state loop:
Supervisor → Agent → State Update → Supervisor

Your job is to detect missing or incomplete state fields and route accordingly.
ALWAYS prioritize state completeness over user intent.

=== MANDATORY WORKFLOW PIPELINE ===
You MUST enforce this strict order:
1. Sales Ingestion (loan intent capture)
2. KYC + Document Processing
3. Fraud Analysis
4. Underwriting Decision
5. Decision Handling (Approval / Soft Reject / Hard Reject)

You MUST NOT skip or reorder stages.

=== ROUTING DECISION MATRIX ===

1.  **registration_agent**
    -   Route if: `is_authenticated == false` OR customer profile is missing critical data (Phone, Name).
    -   Goal: OTP verification and profile enrichment.

2.  **intent_agent**
    -   Route if: `is_authenticated == true` AND `intent == "none"` AND customer profile is complete.
    -   Goal: Classified user request.

3.  **sales_agent**
    -   Route if: `intent == "loan"` AND (`loan_details.requested_amount == 0` OR `loan_details.tenure_months == 0`).
    -   Goal: Converge on principal and tenure.

4.  **kyc_agent** (mapped to `document_agent` or `verification_agent`)
    -   Route if: `intent == "kyc"` OR (`intent == "loan"` AND `verification_status.kyc_complete == false`).
    -   Goal: Document extraction then verification.

5.  **fraud_agent**
    -   Route if: `verification_status.fraud_score == -1` AND KYC is complete.
    -   Goal: Risk assessment.

6.  **underwriting_engine**
    -   Route if: `underwriting.decision_status == ""` AND Fraud/KYC are complete.
    -   Goal: Approval/Rejection logic.

7.  **sales_closer_agent** (mapped to `persuasion_agent`)
    -   Route if: `underwriting.decision_status == "soft_reject"`.
    -   Goal: Move user to accept alternative offer.

8.  **sanction_pdf_agent**
    -   Route if: `underwriting.decision_status == "approve"` AND `sanction_pdf == null`.
    -   Goal: Generate the PDF.

9.  **final_advisor_agent**
    -   Route if: `intent == "advice"` OR `intent == "sign"` OR All above are complete.
    -   Goal: Post-approval support / General advice.

=== RESPONSE FORMAT ===
You MUST return ONLY a valid JSON object:
{{
  "next_agent": "agent_name",
  "reasoning": "Brief explanation of why this agent was chosen based on state."
}}

Agent Names: `registration_agent`, `intent_agent`, `sales_agent`, `kyc_agent`, `fraud_agent`, `underwriting_engine`, `sales_closer_agent`, `sanction_pdf_agent`, `final_advisor_agent`.
"""


# ─── State ───────────────────────────────────────────────────────────────────
# MasterState imported from agents.master_state


# ─── Supervisor ──────────────────────────────────────────────────────────────
from api.core.websockets import manager

# ─── Supervisor ──────────────────────────────────────────────────────────────
async def supervisor_node(state: MasterState):
    """Brain node — Determines the next step using the Master Router LLM."""
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "Supervisor Brain", True)
    
    print("🧠 [SUPERVISOR BRAIN] Analyzing state for routing...")
    
    # Map MasterState to the Brain's expected schema
    brain_state = {
        "loan_details": {
            "requested_amount": state.get("loan_terms", {}).get("principal", 0),
            "tenure_months": state.get("loan_terms", {}).get("tenure", 0)
        },
        "verification_status": {
            "kyc_complete": state.get("kyc_status") == "verified",
            "documents_uploaded": state.get("documents", {}).get("verified", False),
            "fraud_score": state.get("fraud_score", -1)
        },
        "underwriting": {
            "decision_status": state.get("decision", "")
        },
        "sign_status": {
            "is_signed": state.get("is_signed", False)
        },
        "meta": {
            "intent": state.get("intent", "none"),
            "is_authenticated": state.get("is_authenticated", False)
        }
    }

    # If not authenticated, force registration (don't even bother LLM)
    if not state.get("is_authenticated"):
        await manager.broadcast_thinking(session_id, "Supervisor Brain", False)
        return {"next_agent": "registration_agent", "action_log": ["🔐 Routing to Registration Agent"]}

    # Extract latest user message for better context
    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    llm = get_master_llm()
    
    try:
        res = await llm.ainvoke([
            SystemMessage(content=MASTER_ROUTER_PROMPT.format(state_json=json.dumps(brain_state, indent=2))),
            HumanMessage(content=f"User Message: {user_msg}\n\nDetermine the next agent.")
        ])
        
        content = res.content
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
        else:
            # Try raw JSON if no markdown blocks
            data = json.loads(content)
            
        next_agent = data.get("next_agent", "intent_agent" if state.get("intent") == "none" else "sales_agent")
        reasoning = data.get("reasoning", "No reasoning provided.")
        
        print(f"  → Brain Decision: {next_agent}")
        print(f"  → Reasoning: {reasoning}")
        
        await manager.broadcast_thinking(session_id, "Supervisor Brain", False)
        return {
            "next_agent": next_agent,
            "routing_reasoning": reasoning,
            "action_log": [f"🧠 Brain Decision: {next_agent}"]
        }
        
    except Exception as e:
        print(f"  ⚠️ Brain Routing Failed: {e}")
        await manager.broadcast_thinking(session_id, "Supervisor Brain", False)
        return {
            "next_agent": "intent_agent" if state.get("intent") == "none" else "final_advisor_agent",
            "action_log": [f"⚠️ Brain routing error: {str(e)[:50]}"]
        }


def supervisor_router(state: MasterState):
    """Routes based on the LLM's decision stored in next_agent."""
    brain_decision = state.get("next_agent", "final_advisor_agent")
    
    # 🏎️ Parallel Processing Optimization:
    # If the decision is kyc_agent or fraud_agent, and one is already done but the other isn't,
    # or if BOTH need to be done (documents are verified), run them in parallel.
    docs_uploaded = state.get("documents", {}).get("verified", False)
    kyc_done = state.get("kyc_status") == "verified"
    fraud_checked = state.get("fraud_score", -1) != -1

    if docs_uploaded and (not kyc_done or not fraud_checked):
        if brain_decision in ("kyc_agent", "fraud_agent"):
            print("🏎️ [ROUTER] Parallel Verification Triggered (KYC + Fraud)")
            targets = []
            if not kyc_done: targets.append("verification_agent")
            if not fraud_checked: targets.append("fraud_agent")
            return targets

    # Standard mapping
    mapping = {
        "registration_agent": "registration_agent",
        "intent_agent": "intent_agent",
        "sales_agent": "sales_agent",
        "kyc_agent": "document_agent" if not docs_uploaded else "verification_agent",
        "fraud_agent": "fraud_agent",
        "underwriting_engine": "underwriting_agent",
        "sales_closer_agent": "persuasion_agent",
        "sanction_pdf_agent": "sanction_agent",
        "final_advisor_agent": "advisor_agent"
    }
    
    target = mapping.get(brain_decision, "intent_agent" if state.get("intent") == "none" else "sales_agent")
    print(f"🔀 [ROUTER] Routing to: {target}")
    return target


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

    # ── Register nodes ──────────────────────────────────────────────────────
    workflow.add_node("supervisor",             supervisor_node)
    workflow.add_node("registration_extraction",registration_extraction_node)
    workflow.add_node("registration_agent",     registration_chat_node)
    workflow.add_node("intent_agent",           intent_node)
    workflow.add_node("sales_agent",            sales_agent_node)
    workflow.add_node("document_agent",         document_agent_node)
    workflow.add_node("verification_agent",     verification_agent_node)
    workflow.add_node("fraud_agent",            fraud_agent_node)
    workflow.add_node("join_verification",      join_verification_node)
    workflow.add_node("underwriting_agent",     underwriting_agent_node)
    workflow.add_node("sanction_agent",         sanction_agent_node)
    workflow.add_node("advisor_agent",          advisor_agent_node)
    workflow.add_node("persuasion_agent",       persuasion_agent_node)

    # ── Entry: always extract first, then supervisor decides ─────────────────
    workflow.add_edge(START, "registration_extraction")
    workflow.add_edge("registration_extraction", "supervisor")

    # ── Dynamic routing from supervisor ──────────────────────────────────────
    workflow.add_conditional_edges(
        "supervisor", 
        supervisor_router,
        {
            "registration_agent": "registration_agent",
            "intent_agent": "intent_agent",
            "sales_agent": "sales_agent",
            "document_agent": "document_agent",
            "verification_agent": "verification_agent",
            "fraud_agent": "fraud_agent",
            "underwriting_agent": "underwriting_agent",
            "advisor_agent": "advisor_agent",
            "sanction_agent": "sanction_agent",
            "persuasion_agent": "persuasion_agent"
        }
    )

    # ── CHAT nodes — always END (pause, wait for next user message) ──────────
    workflow.add_edge("registration_agent", END)
    workflow.add_conditional_edges("intent_agent", route_after_intent)
    workflow.add_edge("sales_agent",        END)
    workflow.add_edge("persuasion_agent",   END)

    # ── AUTOMATIC processor nodes — Chain back to supervisor to continue ─────
    workflow.add_edge("document_agent",     END) 
    
    # Verification & Fraud run in parallel and join
    workflow.add_edge("verification_agent", "join_verification")
    workflow.add_edge("fraud_agent",        "join_verification")
    workflow.add_edge("join_verification",  "supervisor")

    workflow.add_edge("underwriting_agent", "supervisor")
    workflow.add_edge("advisor_agent",      END)

    # ── Sanction chains into advisor for final message ───────────────────────
    workflow.add_edge("sanction_agent",     "advisor_agent")

    return workflow.compile()


if __name__ == "__main__":
    graph = compile_master_graph()
    print("✅ Master Graph compiled successfully!")

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
from agents.emi_agent import emi_agent_node
from agents.document_agent import document_agent_node
from agents.kyc_agent import verification_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.persuasion_agent import persuasion_agent_node
from agents.sanction_agent import sanction_agent_node
from agents.advisor_agent import advisor_agent_node


# ─── State ───────────────────────────────────────────────────────────────────
class MasterState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_agent: Optional[str]
    is_authenticated: bool
    customer_data: dict
    intent: str               # "loan" | "kyc" | "advice" | "none" | "unclear"
    loan_terms: dict          # {principal, rate, tenure, emi, type}
    documents: dict           # {verified: bool, ...}
    kyc_status: bool
    fraud_score: int
    decision: str             # "approve" | "soft_reject" | "hard_reject"
    sanction_pdf: Optional[str]
    is_signed: bool           # True once user accepts & e-signs the sanction letter
    current_phase: str        # tracks the active phase in the workflow
    action_log: list          # Human-readable step log for the UI ["✅ OTP Verified", ...]


# ─── Supervisor ──────────────────────────────────────────────────────────────
async def supervisor_node(state: MasterState):
    """Pure pass-through hub — no logic, just triggers router. Resets action log."""
    print("🤖 [SUPERVISOR] Evaluating state...")
    return {"action_log": []}   # Fresh log each turn


def supervisor_router(state: MasterState) -> str:
    """ONE decision per invocation. Routes to the single correct agent/END."""
    is_auth      = state.get("is_authenticated", False)
    customer     = state.get("customer_data", {}) or {}
    intent       = state.get("intent", "none")
    terms        = state.get("loan_terms", {}) or {}
    docs         = state.get("documents", {}) or {}
    decision     = state.get("decision", "")
    is_signed    = state.get("is_signed", False)

    # ── Phase 0: Registration ──────────────────────────────────────────────
    if not is_auth or not customer.get("name"):
        return "registration_agent"   # -> END (chat node, waits for user)

    # ── Phase 0.5: Intent Discovery ────────────────────────────────────────
    if intent in ("none", ""):
        return "intent_agent"         # -> END (will ask user what they want)

    # Unclear intent: we need the intent agent to classify the new message
    if intent == "unclear":
        return "intent_agent"

    # ── Phase 1: KYC intent ───────────────────────────────────────────────
    if intent == "kyc":
        return "document_agent"

    # ── Phase 1.5: Sign intent ───────────────────────────────────────────
    if intent == "sign":
        return "advisor_agent"  # Will process signature and say thanks

    # ── Phase 2: Advice intent ────────────────────────────────────────────
    if intent == "advice":
        return "advisor_agent"

    # ── Phase 3: Loan intent ──────────────────────────────────────────────
    if intent in ("loan", "loan_confirmed"):
        # 3.0. Final: Signed & Sealed (Priority)
        if is_signed:
            return "advisor_agent"       # -> END

        # 3a. Need to discover loan reason & amount OR wait for confirmation
        if not terms.get("principal") or intent == "loan":
            return "sales_agent"       # -> END

        # 3b. Need EMI computed (automatic)
        if not terms.get("emi"):
            return "emi_agent"         # -> END (auto, then done for this turn)

        # 3c. Need document verification (prompts user to upload)
        if not docs.get("verified"):
            return "document_agent"    # -> END

        # 3d. KYC cross-check (automatic but needs docs)
        if not state.get("kyc_status"):
            return "verification_agent"  # -> END

        # 3e. Fraud analysis (automatic)
        if state.get("fraud_score", -1) < 0:
            return "fraud_agent"         # -> END

        # 3f. Underwriting decision (automatic)
        if not decision:
            return "underwriting_agent"  # -> END

        # 3g. Soft reject → persuasion (chat)
        if decision == "soft_reject":
            return "persuasion_agent"    # -> END

        # 3h. Sanction letter generation (automatic) → advisor sends it
        if decision == "approve" and not state.get("sanction_pdf"):
            return "sanction_agent"      # -> advisor_agent -> END

        # 3i. Final: Signed & Sealed (handled above)

        # 3j. Default: advisor wraps up
        return "advisor_agent"

    # Catch-all
    return "advisor_agent"


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
    workflow.add_node("emi_agent",              emi_agent_node)
    workflow.add_node("document_agent",         document_agent_node)
    workflow.add_node("verification_agent",     verification_agent_node)
    workflow.add_node("fraud_agent",            fraud_agent_node)
    workflow.add_node("underwriting_agent",     underwriting_agent_node)
    workflow.add_node("sanction_agent",         sanction_agent_node)
    workflow.add_node("advisor_agent",          advisor_agent_node)
    workflow.add_node("persuasion_agent",       persuasion_agent_node)

    # ── Entry: always extract first, then supervisor decides ─────────────────
    workflow.add_edge(START, "registration_extraction")
    workflow.add_edge("registration_extraction", "supervisor")

    # ── Dynamic routing from supervisor ──────────────────────────────────────
    workflow.add_conditional_edges("supervisor", supervisor_router)

    # ── CHAT nodes — always END (pause, wait for next user message) ──────────
    workflow.add_edge("registration_agent", END)
    workflow.add_conditional_edges("intent_agent", route_after_intent)
    workflow.add_edge("sales_agent",        END)
    workflow.add_edge("persuasion_agent",   END)

    # ── AUTOMATIC processor nodes — Chain back to supervisor to continue ─────
    workflow.add_edge("emi_agent",          "supervisor")
    workflow.add_edge("document_agent",     END) # Still needs to wait for upload
    workflow.add_edge("verification_agent", "supervisor")
    workflow.add_edge("fraud_agent",        "supervisor")
    workflow.add_edge("underwriting_agent", "supervisor")
    workflow.add_edge("advisor_agent",      END)

    # ── Sanction chains into advisor for final message ───────────────────────
    workflow.add_edge("sanction_agent",     "advisor_agent")

    return workflow.compile()


if __name__ == "__main__":
    graph = compile_master_graph()
    print("✅ Master Graph compiled successfully!")

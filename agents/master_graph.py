"""Master Graph — 9-Agent LangGraph Pipeline with Supervisor Hub-and-Spoke routing.

Architecture:
  START → Supervisor → [Sales → EMI] → Supervisor → [Document → Verification] 
        → Supervisor → [Fraud → Underwriting] → Supervisor → [Sanction | Advisor] → END

The Supervisor dynamically routes based on what data is missing in the shared MasterState.
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Literal
from langgraph.graph import StateGraph, END, START
from agents.master_state import MasterState
from langchain_core.messages import AIMessage

# Import all agent nodes
from agents.emi_agent import emi_agent_node
from agents.document_agent import document_agent_node
from agents.kyc_agent import verification_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.advisor_agent import advisor_agent_node
from agents.sanction_agent import sanction_agent_node
from agents.persuasion_agent import persuasion_agent_node


# ═══════════════════════════════════════════════════════════════════════════════
#  SUPERVISOR NODE — The Master Brain
# ═══════════════════════════════════════════════════════════════════════════════
def supervisor_node(state: MasterState) -> dict:
    """Determines the next agent based on what's missing in the pipeline state."""
    print("🚦 [SUPERVISOR] Routing decision...")

    terms = state.get("loan_terms", {})
    docs = state.get("documents", {})
    decision = state.get("decision", "")

    # Phase 1: Need loan terms from Sales
    if not terms.get("principal"):
        route = "sales_agent"

    # Phase 2: Need EMI calculation
    elif not terms.get("emi"):
        route = "emi_agent"

    # Phase 3: Need document upload & OCR
    elif not docs.get("verified"):
        route = "document_agent"

    # Phase 4: Need KYC cross-check
    elif not state.get("kyc_status"):
        route = "verification_agent"

    # Phase 5: Need fraud analysis
    elif state.get("fraud_score", -1) < 0:
        route = "fraud_agent"

    # Phase 6: Need underwriting decision
    elif not decision:
        route = "underwriting_agent"

    # Phase 7: Soft reject → Persuasion Loop (per workflow diagram)
    elif decision == "soft_reject":
        route = "persuasion_agent"

    # Phase 8: Generate sanction (approved only)
    elif decision == "approve" and not state.get("sanction_pdf"):
        route = "sanction_agent"

    # Phase 9: Final advice (both approved and rejected)
    else:
        route = "advisor_agent"

    print(f"  → Next: {route}")
    return {"next_agent": route}


# ═══════════════════════════════════════════════════════════════════════════════
#  SALES NODE (Wrapper — the real logic is in sales_agent.py)
# ═══════════════════════════════════════════════════════════════════════════════
def sales_wrapper_node(state: MasterState) -> dict:
    """Sales agent is interactive (chat-driven), so this is a pass-through.
    
    The actual Sales logic runs in the Streamlit UI layer via sales_chat_response().
    This node just marks that Sales has been activated.
    """
    print("🗣️ [SALES AGENT] Active — waiting for user input via chat...")
    return {"next_agent": "await_user_sales"}


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTER — Dynamic conditional edge function
# ═══════════════════════════════════════════════════════════════════════════════
AGENT_ROUTES = [
    "sales_agent", "emi_agent", "document_agent", "verification_agent",
    "fraud_agent", "underwriting_agent", "advisor_agent", "sanction_agent",
    "persuasion_agent", "__end__"
]

def supervisor_router(state: MasterState) -> str:
    """Routes from Supervisor to the correct worker node."""
    route = state.get("next_agent", "__end__")

    # Shortcut: if decision is reject, go directly to advisor
    if state.get("decision") == "reject" and route not in ("advisor_agent",):
        return "advisor_agent"

    # Advisor is the terminal agent
    if route == "advisor_agent":
        return "advisor_agent"

    if route in AGENT_ROUTES:
        return route

    return "__end__"


# ═══════════════════════════════════════════════════════════════════════════════
#  COMPILE THE MASTER GRAPH
# ═══════════════════════════════════════════════════════════════════════════════
def compile_master_graph():
    """Builds and compiles the full 10-agent StateGraph (9 original + Persuasion Loop)."""
    workflow = StateGraph(MasterState)

    # Register all nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("sales_agent", sales_wrapper_node)
    workflow.add_node("emi_agent", emi_agent_node)
    workflow.add_node("document_agent", document_agent_node)
    workflow.add_node("verification_agent", verification_agent_node)
    workflow.add_node("fraud_agent", fraud_agent_node)
    workflow.add_node("underwriting_agent", underwriting_agent_node)
    workflow.add_node("advisor_agent", advisor_agent_node)
    workflow.add_node("sanction_agent", sanction_agent_node)
    workflow.add_node("persuasion_agent", persuasion_agent_node)

    # Entry point
    workflow.add_edge(START, "supervisor")

    # Hub-and-spoke: every worker returns to Supervisor for re-routing
    workflow.add_edge("sales_agent", "supervisor")
    workflow.add_edge("emi_agent", "supervisor")
    workflow.add_edge("document_agent", "supervisor")
    workflow.add_edge("verification_agent", "supervisor")
    workflow.add_edge("fraud_agent", "supervisor")
    workflow.add_edge("underwriting_agent", "supervisor")
    workflow.add_edge("sanction_agent", "advisor_agent")
    workflow.add_edge("advisor_agent", END)

    # Persuasion Loop: returns to Supervisor for re-routing
    # If user accepts → decision reset to "" → Supervisor routes to underwriting_agent
    # If user declines → decision set to "reject" → Supervisor routes to advisor_agent
    workflow.add_edge("persuasion_agent", "supervisor")

    # Dynamic routing from Supervisor
    workflow.add_conditional_edges("supervisor", supervisor_router)

    return workflow.compile()


if __name__ == "__main__":
    graph = compile_master_graph()
    print("✅ Master Graph compiled successfully!")
    print(f"  Nodes: {list(graph.nodes.keys())}")

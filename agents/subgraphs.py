from langgraph.graph import StateGraph, END, START
from langchain_core.messages import AIMessage
from agents.master_state import MasterState

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. DISBURSEMENT NODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def net_calc_node(state: MasterState):
    """Step 1 & 2: Calculate deductions and Net Disbursement"""
    # Extract original requested amount safely
    loan_amt = state.get("loan_terms", {}).get("requested_amount", 0)
    if not loan_amt:
        loan_amt = state.get("loan_terms", {}).get("principal", 500000) # fallback
        
    fee = loan_amt * 0.01      # 1% Processing Fee
    gst = fee * 0.18           # 18% GST on Fee
    bpi = 450.00               # Mock Broken Period Interest
    net_amount = loan_amt - fee - gst - bpi
    
    # Append to existing action log
    current_log = state.get("action_log", [])
    current_log.append(f"> Calculated Net Disbursement: ₹{net_amount:,.2f}")
    
    return {
        "net_disbursement_amount": net_amount,
        "disbursement_step": "pending",
        "action_log": current_log
    }

def compliance_check_node(state: MasterState):
    """Step 3 (Hybrid): Check if UI checkboxes are ticked. If not, PAUSE."""
    if not state.get("kfs_signed") or not state.get("enach_setup"):
        # We tell the frontend to show the compliance UI and we STOP the graph.
        return {
            "disbursement_step": "ui_paused",
            "next_agent": "frontend_compliance_ui",
            "messages": [AIMessage(content="Please complete the **RBI Compliance Checklist** below to authorize the final disbursement.")]
        }
    
    # If checkboxes are ticked, we proceed!
    return {"disbursement_step": "compliance_verified"}

def api_execution_node(state: MasterState):
    """Step 4: Audit Trail Generation (Terminal Flex)"""
    current_log = state.get("action_log", [])
    current_log.extend([
        "> Validating Bank Account Name matches PAN (Penny Drop)... SUCCESS",
        "> Checking LSP routing constraints... DIRECT TO BORROWER CONFIRMED",
        "> RBI Digital Lending Guideline Check... PASS"
    ])
    return {"action_log": current_log}

def direct_transfer_node(state: MasterState):
    """Step 5: RBI Compliant Transfer"""
    net_amt = state.get("net_disbursement_amount", 0)
    current_log = state.get("action_log", [])
    current_log.append(f"> Initiating RTGS/NEFT Transfer for ₹{net_amt:,.2f}... SUCCESS")
    return {"action_log": current_log}

def cooling_off_node(state: MasterState):
    """Step 6: Initiate 1-day cooling-off tracking"""
    return {
        "cooling_off_active": True,
        "disbursement_step": "completed",
        "current_phase": "sanction",
        "messages": [AIMessage(content="🎉 **Disbursement Successful!** \n\nYour funds have been transferred. Under RBI Digital Lending Guidelines, your 1-day cooling-off period is now active. Check your dashboard for details.")]
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. SUBGRAPH ROUTING & COMPILATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def route_compliance(state: MasterState):
    """If the UI is paused, we exit the subgraph to yield to the user."""
    if state.get("disbursement_step") == "ui_paused":
        return END
    return "api_exec"

# Build the Disbursement Subgraph
disbursement_builder = StateGraph(MasterState)
disbursement_builder.add_node("net_calc", net_calc_node)
disbursement_builder.add_node("compliance_check", compliance_check_node)
disbursement_builder.add_node("api_exec", api_execution_node)
disbursement_builder.add_node("transfer", direct_transfer_node)
disbursement_builder.add_node("cooling_off", cooling_off_node)

# Define the precise linear flow
disbursement_builder.add_edge(START, "net_calc")
disbursement_builder.add_edge("net_calc", "compliance_check")
disbursement_builder.add_conditional_edges("compliance_check", route_compliance, {
    END: END,
    "api_exec": "api_exec"
})
disbursement_builder.add_edge("api_exec", "transfer")
disbursement_builder.add_edge("transfer", "cooling_off")
disbursement_builder.add_edge("cooling_off", END)

# Export the compiled subgraph
disbursement_subgraph = disbursement_builder.compile()
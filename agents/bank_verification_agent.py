"""Bank Verification Agent — Handles Penny Drop and eNACH mandate setup.

This agent simulates standard Indian banking verification workflows:
1. Penny Drop: Validating that the provided bank account name matches the KYC name.
2. eNACH Mandate: Simulating the user setting up an auto-debit mandate for their EMI.
"""

from langchain_core.messages import AIMessage
from agents.session_manager import SessionManager

async def bank_verification_agent_node(state: dict) -> dict:
    print("🏦 [BANK VERIFICATION AGENT] Executing Penny Drop & eNACH Setup...")
    
    penny_drop = state.get("penny_drop_status", "pending")
    enach = state.get("enach_status", "pending")
    customer = state.get("customer_data", {})
    bank_name = customer.get("bank_name", "Mock Bank")
    account_no = customer.get("bank_account_number", "XXXX1234")
    
    updates = {}
    
    if penny_drop != "verified":
        # Simulate Penny Drop API call
        print(f"💸 [PENNY DROP] Depositing ₹1 to {bank_name} A/C {account_no}...")
        
        msg = (f"🏦 **Bank Account Verification (Penny Drop)**\n\n"
               f"We are initiating a ₹1 test deposit to your {bank_name} account ending in **{account_no[-4:] if len(account_no) > 4 else account_no}** to verify the beneficiary name.\n\n"
               f"Status: **VERIFIED ✅**\n\n"
               f"Now, let's set up your Auto-Debit (eNACH) mandate so your EMI is deducted automatically on the due date.")
        
        updates["penny_drop_status"] = "verified"
        updates["messages"] = [AIMessage(content=msg)]
        updates["current_phase"] = "bank_verification"
        
        # We stop here to let the user see the verification message and "approve" the mandate
        updates["options"] = ["✅ Setup eNACH Mandate (Auto-Debit)"]
        
    elif enach != "active":
        # Simulate eNACH setup completion
        print(f"🔄 [eNACH] Mandate registered for {bank_name}...")
        
        msg = (f"🔄 **eNACH Mandate Registered Successfully!**\n\n"
               f"Your auto-debit mandate has been approved by {bank_name}. EMIs will be automatically deducted every month.\n\n"
               f"Your loan is now fully processed and queued for final disbursement!")
        
        updates["enach_status"] = "active"
        updates["messages"] = [AIMessage(content=msg)]
        
        # Move to disbursement phase
        updates["current_phase"] = "disbursement"
        updates["disbursement_step"] = "processing"
        
    # Save session
    session_id = state.get("session_id", "default")
    try:
        await SessionManager.save_session(session_id, updates)
    except Exception as e:
        print(f"⚠️ Failed to save session: {e}")
        
    return updates

"""EMI Engine — Handles dynamic credit scoring, payment simulation, and EMI reminders."""

import os, sys, json
from datetime import datetime, timedelta
from langchain_core.messages import AIMessage
from api.core.websockets import manager
from agents.session_manager import SessionManager

async def emi_engine_node(state: dict) -> dict:
    """
    Simulation engine for EMI payments and Credit Score dynamics.
    Runs after session load to check for due payments.
    """
    session_id = state.get("session_id", "default")
    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    
    if not customer or not terms:
        return {}

    print(f"🔢 [EMI ENGINE] Checking status for {customer.get('name')}...")
    
    log = list(state.get("action_log") or [])
    updates = {}
    
    # 1. Check for 'Pending Payment' Simulation
    # In this mock, we simulate that an EMI is due if the user has an active loan
    # and hasn't paid in the last 30 days.
    
    next_emi_str = terms.get("next_emi_date")
    if next_emi_str:
        next_emi_date = datetime.strptime(next_emi_str, "%Y-%m-%d")
        today = datetime.now()
        
        # Reminder Logic: Within 3 days of due date
        days_to_due = (next_emi_date - today).days
        if 0 <= days_to_due <= 3:
            reminder_msg = f"🔔 **EMI Reminder**: Your payment of ₹{terms.get('emi', 0):,.2f} is due in {days_to_due} days ({next_emi_str})."
            await manager.broadcast_to_session(session_id, {
                "type": "NOTIFICATION",
                "priority": "high",
                "message": reminder_msg
            })
            log.append(f"🔔 EMI Reminder sent for {next_emi_str}")

        # Overdue Logic: If today is past due date and not paid
        if today > next_emi_date:
            days_overdue = (today - next_emi_date).days
            if days_overdue > 0:
                print(f"  ⚠️ Loan is {days_overdue} days overdue!")
                
                # Dynamic Credit Score Decrease
                old_score = customer.get("credit_score", 700)
                # Lose 5 points per day overdue, capped at 100
                penalty = min(days_overdue * 5, 100)
                new_score = max(old_score - penalty, 300)
                
                if new_score != old_score:
                    customer["credit_score"] = new_score
                    log.append(f"📉 Credit Score decreased to {new_score} due to late payment.")
                    
                    await manager.broadcast_to_session(session_id, {
                        "type": "NOTIFICATION",
                        "priority": "critical",
                        "message": f"🚨 **Credit Score Impact**: Your score dropped to **{new_score}** due to {days_overdue} days delay in EMI."
                    })

    # 2. Payment Simulation (triggered by user message 'pay my emi' - handled here for simplicity)
    user_msg = ""
    for m in reversed(state.get("messages", [])):
        from langchain_core.messages import HumanMessage
        if isinstance(m, HumanMessage):
            user_msg = m.content.lower()
            break
            
    if "pay" in user_msg and "emi" in user_msg and terms.get("emi", 0) > 0:
        print("  💳 [PAYMENT] Simulating EMI payment...")
        
        # Update Terms
        payments_made = terms.get("payments_made", 0) + 1
        terms["payments_made"] = payments_made
        terms["last_payment_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Calculate Next EMI Date (plus 30 days)
        last_due = datetime.strptime(terms.get("next_emi_date"), "%Y-%m-%d")
        next_due = last_due + timedelta(days=30)
        terms["next_emi_date"] = next_due.strftime("%Y-%m-%d")
        
        # Dynamic Credit Score Increase
        old_score = customer.get("credit_score", 700)
        new_score = min(old_score + 10, 850) # Increase by 10 for on-time payment
        customer["credit_score"] = new_score
        
        log.append(f"💳 EMI Payment successful. Total payments: {payments_made}")
        log.append(f"📈 Credit Score increased to {new_score}!")
        
        updates["messages"] = [AIMessage(content=(
            f"✅ **Payment Successful!**\n\n"
            f"Thank you for your payment of ₹{terms.get('emi', 0):,.2f}.\n"
            f"- Next Due Date: **{terms['next_emi_date']}**\n"
            f"- Your new Credit Score: **{new_score}** (↑ 10 pts)\n\n"
            f"Consistent payments help you qualify for lower rates in the future!"
        ))]

    # 3. Final Reimbursal/Tenure Completion Increase
    if terms.get("payments_made") == terms.get("tenure") and terms.get("tenure", 0) > 0:
        if not terms.get("is_closed"):
            terms["is_closed"] = True
            customer["credit_score"] = min(customer.get("credit_score", 700) + 50, 900)
            log.append("🏆 Loan fully repaid! Credit Score boosted by 50 points.")
            updates["messages"] = [AIMessage(content="🎉 **Congratulations!** Your loan has been fully repaid. Your credit score has received a significant boost!")]

    return {
        "customer_data": customer,
        "loan_terms": terms,
        "action_log": log,
        **updates
    }

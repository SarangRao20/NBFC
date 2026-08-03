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
    if next_emi_str and isinstance(next_emi_str, str):
        try:
            next_emi_date = datetime.strptime(next_emi_str, "%Y-%m-%d")
        except ValueError:
            next_emi_str = None
        
        if next_emi_str:
            today = datetime.now()

            # Reminder Logic: Within 3 days of due date
            days_to_due = (next_emi_date - today).days
            if 0 <= days_to_due <= 3:
                emi_value = (terms.get('emi') or 0)
                reminder_msg = f"🔔 **EMI Reminder**: Your payment of ₹{emi_value:,.2f} is due in {days_to_due} days ({next_emi_str})."
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

    # 2. Final Reimbursal/Tenure Completion Increase
    if terms.get("payments_made") == terms.get("tenure") and terms.get("tenure", 0) > 0:
        if not terms.get("is_closed"):
            terms["is_closed"] = True
            
            # Dynamic Credit Score & Limit Increase
            old_score = customer.get("credit_score", 700)
            score_boost = 50
            new_score = min(old_score + score_boost, 900)
            customer["credit_score"] = new_score
            
            old_limit = customer.get("pre_approved_limit", 25000)
            # Increase limit by 50% upon successful repayment
            limit_boost = int(old_limit * 0.5)
            new_limit = old_limit + limit_boost
            customer["pre_approved_limit"] = new_limit
            
            log.append(f"🏆 Loan fully repaid! Credit Score boosted to {new_score} and Limit increased to ₹{new_limit:,}.")
            
            updates["messages"] = [AIMessage(content=(
                f"🎉 **Congratulations!** Your loan has been fully repaid.\n\n"
                f"Because of your consistent repayment:\n"
                f"- Your Credit Score increased to **{new_score}** (↑ {score_boost})\n"
                f"- Your Pre-approved Limit is now **₹{new_limit:,}** (↑ ₹{limit_boost:,})\n\n"
                f"We're excited to support your next big goal!"
            ))]
            
            # ── SYNC CLOSURE TO DATABASE ────────────────────────────────────
            try:
                from db.database import loan_applications_collection
                await loan_applications_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": "Closed",
                        "is_closed": True,
                        "closed_at": datetime.now().isoformat()
                    }}
                )
                print(f"🔒 Loan in session {session_id} marked as Closed in DB")
            except Exception as e:
                print(f"⚠️ Failed to sync loan closure to DB: {e}")

    return {
        "customer_data": customer,
        "loan_terms": terms,
        "action_log": log,
        **updates
    }

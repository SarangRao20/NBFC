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
        next_emi_date = datetime.strptime(next_emi_str, "%Y-%m-%d")
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

    # 2. Payment Request Handling (triggered by user message 'pay my emi')
    # Delegate to Razorpay service for real payment processing
    user_msg = ""
    for m in reversed(state.get("messages", [])):
        from langchain_core.messages import HumanMessage
        if isinstance(m, HumanMessage):
            user_msg = m.content.lower()
            break
            
    is_pay_request = ("pay" in user_msg and "emi" in user_msg) or ("confirm" in user_msg and "payment" in user_msg)
    if is_pay_request and terms.get("emi", 0) > 0:
        print("  💳 [PAYMENT] Delegating to Razorpay service...")
        
        # Import Razorpay service for order creation
        try:
            from api.services.payment_service import create_emi_order
            order_result = await create_emi_order(session_id)
            
            if order_result and order_result.get("success"):
                order_id = order_result.get("order_id")
                amount = order_result.get("amount")
                key_id = order_result.get("key_id")
                mock_mode = order_result.get("mock", False)
                
                if mock_mode:
                    # Mock mode - simulate payment for development
                    print(f"  ⚠️ Razorpay mock mode - simulating payment for order {order_id}")
                    
                    # Update Terms (same as before for mock mode)
                    new_payments_made = terms.get("payments_made", 0) + 1
                    tenure = terms.get("tenure", 0)
                    emi = terms.get("emi", 0)
                    
                    terms["payments_made"] = new_payments_made
                    terms["last_payment_date"] = datetime.now().strftime("%Y-%m-%d")
                    terms["remaining_balance"] = round(max(0, (tenure - new_payments_made) * emi), 2)
                    
                    # Calculate Next EMI Date
                    next_emi_str = terms.get("next_emi_date")
                    if next_emi_str and isinstance(next_emi_str, str):
                        try:
                            curr_date = datetime.strptime(next_emi_str, "%Y-%m-%d")
                            if curr_date.month == 12:
                                next_date = curr_date.replace(year=curr_date.year + 1, month=1)
                            else:
                                next_date = curr_date.replace(month=curr_date.month + 1)
                            terms["next_emi_date"] = next_date.strftime("%Y-%m-%d")
                        except:
                            terms["next_emi_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    else:
                        terms["next_emi_date"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    
                    # Dynamic Credit Score Increase
                    old_score = customer.get("credit_score", 700)
                    new_score = min(old_score + 10, 850)
                    customer["credit_score"] = new_score
                    
                    log.append(f"💳 EMI Payment successful (mock). Total payments: {new_payments_made}")
                    log.append(f"📈 Credit Score increased to {new_score}!")
                    
                    # Sync to Database
                    try:
                        from db.database import loan_applications_collection
                        await loan_applications_collection.update_one(
                            {"session_id": session_id},
                            {"$set": {
                                "payments_made": new_payments_made,
                                "remaining_balance": terms.get("remaining_balance"),
                                "next_emi_date": terms["next_emi_date"],
                                "last_payment_date": terms["last_payment_date"]
                            }}
                        )
                    except Exception as e:
                        print(f"⚠️ Failed to sync payment to DB: {e}")
                    
                    updates["messages"] = [AIMessage(content=(
                        f"✅ **Payment Successful!** (Mock Mode)\n\n"
                        f"Thank you for your payment of ₹{(terms.get('emi') or 0):,.2f}.\n"
                        f"- Next Due Date: **{terms['next_emi_date']}**\n"
                        f"- Your new Credit Score: **{new_score}** (↑ 10 pts)\n\n"
                        f"Consistent payments help you qualify for lower rates in the future!"
                    ))]
                else:
                    # Real Razorpay mode - provide checkout instructions
                    log.append(f"💳 Razorpay order created: {order_id} for ₹{amount:,.2f}")
                    
                    updates["messages"] = [AIMessage(content=(
                        f"💳 **Payment Initiated**\n\n"
                        f"A payment order has been created for ₹{amount:,.2f}.\n\n"
                        f"**Please complete the payment using the Razorpay checkout widget** "
                        f"that will appear in your dashboard.\n\n"
                        f"Order ID: `{order_id}`\n"
                        f"Once you complete the payment, your EMI will be automatically processed."
                    ))]
            else:
                # Order creation failed
                error_msg = order_result.get("message", "Unknown error") if order_result else "Failed to create payment order"
                log.append(f"❌ Payment order creation failed: {error_msg}")
                
                updates["messages"] = [AIMessage(content=(
                    f"❌ **Payment Failed**\n\n"
                    f"Unable to create payment order: {error_msg}\n\n"
                    f"Please try again or contact support."
                ))]
                
        except Exception as e:
            print(f"❌ Razorpay service error: {e}")
            log.append(f"❌ Payment service error: {str(e)}")
            
            updates["messages"] = [AIMessage(content=(
                f"❌ **Payment Service Error**\n\n"
                f"Unable to process payment request: {str(e)}\n\n"
                f"Please try again later."
            ))]

    # 3. Final Reimbursal/Tenure Completion Increase
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

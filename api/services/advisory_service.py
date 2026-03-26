"""Advisory Service — post-decision financial advice + smart loan table analysis + NL responses."""

from api.core.state_manager import get_session, update_session, advance_phase
from db.database import loan_applications_collection
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


async def generate_advisory(session_id: str) -> dict:
    """Step 17: Advisory Agent — personalized advice based on decision outcome."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    decision = state.get("decision", "unknown")
    dti = state.get("dti_ratio", 0)
    terms = state.get("loan_terms", {})
    fraud_score = state.get("fraud_score", 0.0)
    reasons = state.get("reasons", [])

    salary = customer.get("salary", 0)
    score = customer.get("credit_score", 0)
    name = customer.get("name", "Customer")
    existing_emi = customer.get("existing_emi_total", 0)
    emi = terms.get("emi", 0)

    next_steps = []
    cross_sell = ""

    if decision == "approve":
        advisory_message = (
            f"Congratulations, {name}! Your loan of ₹{(terms.get('principal') or 0):,} has been approved. "
            f"EMI of ₹{(emi or 0):,.2f} will be debited on the 5th of every month. "
            f"Total repayment: ₹{((emi or 0) * (terms.get('tenure') or 0)):,.2f} over {terms.get('tenure', 0)} months."
        )
        next_steps = [
            "Complete KYC documentation within 30 days",
            "Set up auto-debit for EMI payments",
            "Download your sanction letter from the portal",
        ]
        # Cross-sell based on profile
        if salary > 60000:
            cross_sell = "Consider starting a SIP of ₹5,000/month alongside your loan for wealth building."
        elif dti < 0.30:
            cross_sell = "Your low EMI burden qualifies you for a FinServe FD at 8% p.a."

    elif decision in ("reject", "soft_reject"):
        if fraud_score >= 0.7:
            advisory_message = (
                f"{name}, our compliance team requires manual verification for your application. "
                f"Please visit the nearest FinServe branch with original documents."
            )
            next_steps = [
                "Visit nearest branch with original ID and income documents",
                "Reference number will be shared via SMS",
                "Resolution typically takes 5-7 business days",
            ]
        elif score < 700:
            advisory_message = (
                f"{name}, your CIBIL score of {score} needs to reach 700+ for approval. "
                f"Here's a 90-day improvement plan."
            )
            next_steps = [
                "Pay all EMIs on/before due dates — even 1-day delays affect CIBIL",
                "Reduce credit card utilization below 30%",
                "Do NOT apply for other loans in the next 3 months",
                "Check CIBIL report for errors at mycibil.com",
                "Consider a FinServe Secured Credit Card to rebuild credit",
            ]
            cross_sell = "A FD-backed credit card can help rebuild your score safely."
        else:
            # DTI rejection
            total_emi = existing_emi + emi
            advisory_message = (
                f"{name}, your total EMI burden of ₹{total_emi:,} is {dti*100:.0f}% of income, "
                f"above our 50% ceiling. Options: reduce loan amount, extend tenure, or clear an existing loan."
            )
            next_steps = [
                "Consider reducing the loan amount",
                "Extend tenure to lower monthly EMI",
                "Clear one existing loan to free up DTI capacity",
                "Reapply after 3 months with improved debt profile",
            ]
    else:
        advisory_message = f"Thank you for using FinServe, {name}. Contact us for any assistance."
        next_steps = ["Reach out to customer support for further queries."]

    await update_session(session_id, {"advisory_message": advisory_message})
    await advance_phase(session_id, "advisory_complete")

    return {
        "decision": decision,
        "advisory_message": advisory_message,
        "cross_sell_suggestion": cross_sell,
        "next_steps": next_steps,
        "message": "Advisory generated. Session can now be ended."
    }


# ─── SMART LOAN QUERY & NATURAL LANGUAGE ANALYSIS ────────────────────────────

async def get_loans_smart(
    phone: str,
    intent: Optional[str] = None,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Smart loan query with field filtering and intent-based responses.
    
    Args:
        phone: Customer phone number
        intent: Query intent ('next_emi', 'loan_details', 'all')
        fields: Specific fields to return (overrides intent)
    
    Returns: Structured loan data + optional natural language summary
    """
    try:
        loans = list(loan_applications_collection.find({"phone": phone}))
        
        if not loans:
            return {
                "success": False,
                "message": "No loans found for this customer.",
                "loans": []
            }
        
        # Determine fields to return
        field_map = {
            "next_emi": ["loan_id", "amount", "emi", "next_emi_due_date", "remaining_emis"],
            "loan_details": ["loan_id", "amount", "status", "interest_rate", "tenure", "emi", "next_emi_due_date", "loan_end_date"],
            "payment_status": ["loan_id", "amount", "emi", "next_emi_due_date", "loan_end_date", "remaining_emis"],
            "all": None
        }
        
        selected_fields = fields or (field_map.get(intent) if intent else field_map.get("loan_details"))
        
        # Enrich and filter loans
        enriched_loans = []
        for idx, loan in enumerate(loans, 1):
            enriched = _enrich_loan(loan, selected_fields, idx)
            enriched_loans.append(enriched)
        
        return {
            "success": True,
            "count": len(enriched_loans),
            "loans": enriched_loans,
            "fields_returned": selected_fields if selected_fields else "all"
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error fetching loans: {str(e)}",
            "loans": []
        }


def _enrich_loan(loan: Dict[str, Any], fields: Optional[List[str]], idx: int) -> Dict[str, Any]:
    """Enrich loan with EMI calculations and field filtering."""
    
    created_at = datetime.fromisoformat(loan.get("created_at", datetime.utcnow().isoformat()))
    first_emi_due = loan.get("first_emi_due_date")
    tenure = loan.get("tenure", 0)
    emi = loan.get("emi", 0)
    
    # Parse first_emi_due_date
    if first_emi_due:
        if isinstance(first_emi_due, str):
            next_emi_due_date = datetime.fromisoformat(first_emi_due)
        else:
            next_emi_due_date = first_emi_due
    else:
        next_emi_due_date = created_at + timedelta(days=30)
    
    # Calculate remaining EMIs
    remaining_emis = tenure
    if "emi_schedule" in loan and loan["emi_schedule"]:
        remaining_emis = len([e for e in loan["emi_schedule"] if e.get("status") == "pending"])
    
    # Calculate loan end date
    loan_end_date = next_emi_due_date + timedelta(days=30 * (remaining_emis - 1))
    
    # Build enriched record
    enriched = {
        "loan_id": loan.get("session_id", f"LOAN_{idx}"),
        "amount": loan.get("amount", 0),
        "status": loan.get("status", "unknown"),
        "interest_rate": loan.get("interest_rate", 0),
        "tenure": tenure,
        "emi": emi,
        "next_emi_due_date": next_emi_due_date.date().isoformat() if next_emi_due_date else None,
        "loan_end_date": loan_end_date.date().isoformat(),
        "remaining_emis": remaining_emis,
        "created_at": created_at.date().isoformat(),
    }
    
    # Filter fields if specified
    if fields:
        enriched = {k: v for k, v in enriched.items() if k in fields}
    
    return enriched


async def generate_advisory_message(
    phone: str,
    intent: str = "general",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate natural language advisory by analyzing loan tables.
    
    Args:
        phone: Customer phone
        intent: Message type ('next_emi', 'status', 'approval', 'general')
        context: Additional context (loan terms, decision, etc.)
    
    Returns: Natural language advisory message
    """
    try:
        result = await get_loans_smart(phone)
        
        if not result["success"] or not result["loans"]:
            return "Welcome! I don't see active loans for your account. How can I help?"
        
        loans = result["loans"]
        
        if intent == "next_emi":
            return _message_next_emi(loans)
        elif intent == "status":
            return _message_loan_status(loans)
        elif intent == "approval":
            return _message_approval(loans, context or {})
        else:
            return _message_general(loans)
    
    except Exception as e:
        return f"I'm having trouble accessing your information. Please try again. (Error: {str(e)})"


def _message_next_emi(loans: List[Dict[str, Any]]) -> str:
    """Generate next EMI due message from table data."""
    if not loans:
        return "No active loans found."
    
    loan = loans[0]
    emi = loan.get("emi", 0)
    next_due = loan.get("next_emi_due_date")
    remaining = loan.get("remaining_emis", 0)
    
    return f"""💳 **Your EMI Status**

Your next EMI payment:
• **Amount:** ₹{emi:,.0f}
• **Due Date:** {next_due}
• **Remaining EMIs:** {remaining}

You can pay anytime through our payment portal. Click below to make a payment! 🚀"""


def _message_loan_status(loans: List[Dict[str, Any]]) -> str:
    """Generate loan status overview from table data."""
    if not loans:
        return "No loans found."
    
    status_lines = []
    for idx, loan in enumerate(loans, 1):
        lid = loan.get("loan_id", f"Loan {idx}")
        status = loan.get("status", "unknown")
        amount = loan.get("amount", 0)
        next_due = loan.get("next_emi_due_date")
        remaining = loan.get("remaining_emis", 0)
        
        emoji = "✅" if status == "Approved" else "⏳" if status == "Pending" else "❌"
        status_lines.append(
            f"{emoji} **{lid}:** {status}\n   Amount: ₹{amount:,} | Next EMI: {next_due} | {remaining} EMIs left"
        )
    
    return "📊 **Your Loans Overview**\n\n" + "\n".join(status_lines)


def _message_approval(loans: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
    """Generate approval celebration message from table data."""
    customer_name = context.get("name", "Customer")
    principal = context.get("amount", loans[0].get("amount", 0) if loans else 0)
    emi = context.get("emi", loans[0].get("emi", 0) if loans else 0)
    tenure = context.get("tenure", loans[0].get("tenure", 0) if loans else 0)
    next_due = loans[0].get("next_emi_due_date") if loans else "Soon"
    
    return f"""🎉 **Congratulations {customer_name}!**

Your loan of **₹{principal:,.0f}** has been approved! 🚀

💰 **Loan Details:**
• Monthly EMI: ₹{emi:,.0f}
• Tenure: {tenure} months
• First EMI Due: {next_due}

✅ **What's Next:**
1. Review your sanction letter (email)
2. Complete digital signing
3. Our team will guide on docs
4. Disbursement in 24-48 hrs

Need help? message us! 🤝"""


def _message_general(loans: List[Dict[str, Any]]) -> str:
    """Generate general overview from table data."""
    if not loans:
        return "Welcome! How can I help?"
    
    total_emi = sum(loan.get("emi", 0) for loan in loans)
    total_remaining = sum(loan.get("remaining_emis", 0) for loan in loans)
    
    return f"""📋 **Your Loan Summary**

You have {len(loans)} active loan(s):
• **Total Monthly Payment:** ₹{total_emi:,.0f}
• **Total EMIs Remaining:** {total_remaining}

What would you like to do?
• Check next EMI due date
• View detailed loan status
• Make an EMI payment
• Get financial advice

Just ask! 🤝"""


# ─── LOAN EXPLANATION (PHASE 5 INTEGRATION) ────────────────────────────────

async def explain_selected_loan(session_id: str, lender_name: str, interest_rate: float, rank_info: Optional[str] = None) -> str:
    """
    ✅ NEW (Phase 6): Explain why the selected loan is a good choice and what it means.
    
    Args:
        session_id: Session ID to fetch loan details
        lender_name: Name of selected lender
        interest_rate: Selected loan interest rate
        rank_info: Optional rank/badge info (e.g., "🥇 Best Option", "🥈 Top Alternative")
    
    Returns: Formatted explanation message
    """
    try:
        state = await get_session(session_id)
        if not state:
            return f"Great! You've selected {lender_name}. Let's proceed to the next step."
        
        terms = state.get("loan_terms", {})
        customer = state.get("customer_data", {})
        comparison_result = state.get("comparison_result", {})
        
        principal = terms.get("principal", 0)
        tenure = terms.get("tenure", 12)
        salary = customer.get("salary", 0)
        
        # Calculate monthly EMI for explanation
        monthly_rate = interest_rate / 12 / 100
        num_payments = tenure
        emi = (principal * monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        
        # Build explanation
        badge = f"({rank_info}) " if rank_info else ""
        emi_percentage = (emi / salary * 100) if salary > 0 else 0
        total_cost = emi * tenure
        total_interest = total_cost - principal
        
        explanation = f"""💡 **Why {lender_name}? {badge}**

**Loan Summary:**
• **Lender:** {lender_name}
• **Amount:** ₹{principal:,.0f}
• **Interest Rate:** {interest_rate:.2f}% per annum
• **Tenure:** {tenure} months

**Your Monthly Commitment:**
• **EMI:** ₹{emi:,.0f}/month ({emi_percentage:.1f}% of your income)
• **Total Interest:** ₹{total_interest:,.0f}
• **Total Repayment:** ₹{total_cost:,.0f}

**Why This Loan?**"""
        
        # Add comparison reasoning if available
        if comparison_result:
            eligible_count = comparison_result.get("eligible_count", 0)
            explanation += f"\n✅ Selected from {eligible_count} eligible offers"
            
            recommendation_reason = comparison_result.get("recommendation_reason", "")
            if recommendation_reason:
                explanation += f"\n📊 {recommendation_reason}"
        
        explanation += f"\n\n**Next Steps:**\n1. Review your documents\n2. Proceed to verification\n3. Sanction letter generation\n4. E-sign & dibursement\n\n🚀 Ready to move forward?"
        
        return explanation
        
    except Exception as e:
        return f"✅ You've selected {lender_name} at {interest_rate:.2f}% p.a. Let's proceed to document verification."

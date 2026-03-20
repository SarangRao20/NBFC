"""Advisory Service — post-decision financial advice (Step 17)."""

from api.core.state_manager import get_session, update_session, advance_phase


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
            f"Congratulations, {name}! Your loan of ₹{terms.get('principal', 0):,} has been approved. "
            f"EMI of ₹{emi:,.2f} will be debited on the 5th of every month. "
            f"Total repayment: ₹{emi * terms.get('tenure', 0):,.2f} over {terms.get('tenure', 0)} months."
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

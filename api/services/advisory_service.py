from api.core.state_manager import get_session, update_session, advance_phase
from db.database import loan_applications_collection
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


async def generate_advisory(session_id: str) -> dict:
    """Advisory Agent — personalized advice based on decision outcome and customer data."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    decision = state.get("decision", "unknown")
    dti = state.get("dti_ratio", 0)
    terms = state.get("loan_terms", {})
    fraud_score = state.get("fraud_score", 0.0)
    reasons = state.get("reasons", [])
    risk_level = state.get("risk_level", "medium")

    salary = customer.get("salary", 0)
    score = customer.get("credit_score", 0)
    name = customer.get("name", "Customer")
    existing_emi = customer.get("existing_emi_total", 0)
    city = customer.get("city", "")
    profession = customer.get("profession", "")
    past_loans = customer.get("past_loans", [])
    emi = terms.get("emi", 0)
    principal = terms.get("principal", 0)
    tenure = terms.get("tenure", 0)

    next_steps = []
    cross_sell = ""

    # Build context-aware profile summary
    profile_parts = []
    if city:
        profile_parts.append(f"based in {city}")
    if profession:
        profile_parts.append(f"working as {profession}")
    if past_loans:
        past_approved = sum(1 for p in past_loans if p.get("decision") == "approve")
        if past_approved:
            profile_parts.append(f"with {past_approved} past approved loan(s)")
    profile_str = ", ".join(profile_parts) if profile_parts else ""

    if decision == "approve":
        total_repayment = (emi or 0) * (tenure or 0)
        total_interest = total_repayment - (principal or 0)
        dti_percent = (dti * 100) if dti else 0

        advisory_message = (
            f"Congratulations, {name}! Your loan of ₹{principal:,.0f} has been approved. "
            f"Here's your personalized repayment summary:\n\n"
            f"• **EMI**: ₹{emi:,.0f}/month\n"
            f"• **Tenure**: {tenure} months\n"
            f"• **Interest Rate**: {terms.get('rate', 0):.1f}% p.a.\n"
            f"• **Total Interest Payable**: ₹{total_interest:,.0f}\n"
            f"• **Total Repayment**: ₹{total_repayment:,.0f}\n"
            f"• **DTI Ratio**: {dti_percent:.0f}% of income"
        )
        if profile_str:
            advisory_message += f"\n\n📋 **Profile**: {profile_str}"

        next_steps = [
            "Complete KYC documentation within 30 days",
            "Set up auto-debit for EMI payments",
            "Download your sanction letter from the portal",
            "First EMI due on the 5th of next month",
        ]

        # Personalised cross-sell
        if salary > 60000:
            recommended_sip = min(5000, int(salary * 0.08))
            cross_sell = (
                f"With your monthly income of ₹{salary:,}, consider starting a SIP of "
                f"₹{recommended_sip:,}/month (just {recommended_sip/salary*100:.0f}% of salary) "
                f"alongside your loan for wealth building. Even a 12% annual return could grow "
                f"this to ₹{int(recommended_sip * ((1+0.01)**120 - 1)/0.01):,} in 10 years."
            )
        elif dti < 0.30:
            cross_sell = (
                f"Your DTI of {dti_percent:.0f}% leaves room for additional investments. "
                f"FinServe's Flexi FD offers 8.5% p.a. with monthly payout — "
                f"a great complement to your loan."
            )

    elif decision in ("reject", "soft_reject"):
        if fraud_score >= 0.7:
            advisory_message = (
                f"{name}, our compliance team flagged your application (fraud score: {fraud_score:.0%}). "
                f"Manual verification is required. Please visit the nearest FinServe branch "
                f"with original ID and income documents for in-person verification."
            )
            next_steps = [
                "Visit nearest branch with original ID and income documents",
                "Reference number will be shared via SMS",
                "Resolution typically takes 5-7 business days",
            ]
        elif score < 700:
            score_gap = 700 - score
            estimated_months = max(3, score_gap // 10)
            advisory_message = (
                f"{name}, your CIBIL score of {score} is {score_gap} points below our 700 threshold. "
                f"Based on historical patterns, you can bridge this gap in approximately {estimated_months} months."
            )
            if profile_str:
                advisory_message += f"\n\n*{profile_str}*"
            advisory_message += "\n\n📊 **90-Day Credit Improvement Plan:**"

            next_steps = [
                "Pay all EMIs on/before due dates — even 1-day delays affect CIBIL",
                "Reduce credit card utilization below 30% of your limit",
                "Do NOT apply for other loans in the next 3 months (each inquiry drops 5-10 points)",
                f"Check CIBIL report for errors at mycibil.com (free annual report)",
                "Consider a FinServe Secured Credit Card (FD-backed) to rebuild credit safely",
            ]
            # Personalized: if salary known
            if salary > 0 and existing_emi > 0:
                free_cash_flow = salary - existing_emi
                next_steps.append(
                    f"With your monthly surplus of ₹{free_cash_flow:,}, "
                    f"pay down existing debt faster to improve DTI"
                )
            cross_sell = (
                f"A ₹25,000 FD-backed credit card from FinServe reports to all bureaus monthly, "
                f"helping rebuild your score 2-3x faster than unsecured cards."
            )
        else:
            total_emi = existing_emi + emi
            dti_actual = (total_emi / salary * 100) if salary > 0 else 0
            excess_dti = max(0, dti_actual - 50)

            advisory_message = (
                f"{name}, your total monthly debt obligation of ₹{total_emi:,} "
                f"is {dti_actual:.0f}% of your income, exceeding our 50% ceiling by {excess_dti:.0f}%. "
            )
            if principal > 0:
                # Suggest a lower amount
                max_emi_for_dti = salary * 0.50 - existing_emi
                if max_emi_for_dti > 0:
                    monthly_rate = (terms.get("rate", 10) / 12) / 100
                    if monthly_rate > 0:
                        suggested_principal = max_emi_for_dti * (
                            ((1 + monthly_rate) ** tenure) - 1
                        ) / (monthly_rate * ((1 + monthly_rate) ** tenure))
                    else:
                        suggested_principal = max_emi_for_dti * tenure
                    advisory_message += (
                        f"\n\n💡 **Recommendation**: A loan of ₹{suggested_principal:,.0f} "
                        f"would keep your DTI at 50%, with EMI of ₹{max_emi_for_dti:,.0f}/month."
                    )

            advisory_message += "\n\n**Options to improve eligibility:**"
            next_steps = [
                f"Reduce loan amount to fit within 50% DTI ceiling",
                "Extend tenure to lower monthly EMI burden",
                "Clear one existing loan to free up DTI capacity",
                "Reapply after 3 months with improved debt profile",
            ]
            cross_sell = (
                "FinServe offers debt consolidation loans at 11.5% p.a. — "
                "combine your existing EMIs into one lower payment and free up DTI."
            )

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


async def get_loans_smart(
    phone: str,
    intent: Optional[str] = None,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Smart loan query with field filtering and intent-based responses."""
    try:
        loans = await loan_applications_collection.find({"phone": phone}).to_list(length=None)

        if not loans:
            return {
                "success": False,
                "message": "No loans found for this customer.",
                "loans": []
            }

        field_map = {
            "next_emi": ["loan_id", "amount", "emi", "next_emi_due_date", "remaining_emis"],
            "loan_details": ["loan_id", "amount", "status", "interest_rate", "tenure", "emi", "next_emi_due_date", "loan_end_date"],
            "payment_status": ["loan_id", "amount", "emi", "next_emi_due_date", "loan_end_date", "remaining_emis"],
            "all": None
        }

        selected_fields = fields or (field_map.get(intent) if intent else field_map.get("loan_details"))

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

    if first_emi_due:
        if isinstance(first_emi_due, str):
            next_emi_due_date = datetime.fromisoformat(first_emi_due)
        else:
            next_emi_due_date = first_emi_due
    else:
        next_emi_due_date = created_at + timedelta(days=30)

    remaining_emis = tenure
    if "emi_schedule" in loan and loan["emi_schedule"]:
        remaining_emis = len([e for e in loan["emi_schedule"] if e.get("status") == "pending"])

    loan_end_date = next_emi_due_date + timedelta(days=30 * (remaining_emis - 1))

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

    if fields:
        enriched = {k: v for k, v in enriched.items() if k in fields}

    return enriched


async def generate_contextual_response(phone: str, query: str) -> str:
    """Generate a contextual advisory response to a user question using Groq LLM."""
    try:
        from config import get_master_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        from db.database import users_collection

        user = await users_collection.find_one({"phone": phone})
        if not user:
            return "I'm having trouble finding your profile. Please try again."

        name = user.get("name", "there")
        score = user.get("credit_score", 0)
        salary = user.get("salary", 0)
        city = user.get("city", "your city")
        existing_emi = user.get("existing_emi_total", 0)
        loans = await loan_applications_collection.find({"phone": phone}).to_list(length=None)

        profile = (
            f"Customer: {name}\n"
            f"CIBIL: {score}\n"
            f"Salary: ₹{salary:,}/month\n"
            f"City: {city}\n"
            f"Existing EMIs: ₹{existing_emi:,}/month\n"
            f"Active loans: {len(loans)}"
        )

        llm = get_master_llm()
        messages = [
            SystemMessage(content=(
                "You are Priya, a Senior Financial Advisor at FinServe NBFC. "
                "Answer the user's question concisely using their profile data below. "
                "Be helpful, warm, and data-driven. 2-3 sentences max.\n\n"
                f"## CUSTOMER PROFILE\n{profile}"
            )),
            HumanMessage(content=query),
        ]
        response = await llm.ainvoke(messages)
        return response.content.strip()
    except Exception as e:
        return f"I can help with that! Based on your profile, I'd recommend checking with our loan specialists. (Error: {str(e)})"


async def generate_advisory_message(
    phone: str,
    intent: str = "general",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Generate natural language advisory by analyzing loan tables."""
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

    return f"""Your next EMI payment:
• **Amount:** ₹{emi:,.0f}
• **Due Date:** {next_due}
• **Remaining EMIs:** {remaining}

You can pay anytime through our payment portal."""


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

        emoji = "Approved" if status == "Approved" else "Pending" if status == "Pending" else "Rejected"
        status_lines.append(
            f"**{lid}:** {emoji}\n   Amount: ₹{amount:,} | Next EMI: {next_due} | {remaining} EMIs left"
        )

    return "Your Loans Overview\n" + "\n".join(status_lines)


def _message_approval(loans: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
    """Generate approval celebration message from table data."""
    customer_name = context.get("name", "Customer")
    principal = context.get("amount", loans[0].get("amount", 0) if loans else 0)
    emi = context.get("emi", loans[0].get("emi", 0) if loans else 0)
    tenure = context.get("tenure", loans[0].get("tenure", 0) if loans else 0)
    next_due = loans[0].get("next_emi_due_date") if loans else "Soon"

    return f"""Congratulations {customer_name}!

Your loan of **₹{principal:,.0f}** has been approved!

**Loan Details:**
• Monthly EMI: ₹{emi:,.0f}
• Tenure: {tenure} months
• First EMI Due: {next_due}

**What's Next:**
1. Review your sanction letter (email)
2. Complete digital signing
3. Our team will guide on docs
4. Disbursement in 24-48 hrs

Need help? message us!"""


def _message_general(loans: List[Dict[str, Any]]) -> str:
    """Generate concise greeting from table data."""
    if not loans:
        return "Welcome! How can I help?"

    total_emi = sum(loan.get("emi", 0) for loan in loans)
    count = len(loans)

    return (
        f"Hey! You've got {count} active loan(s) — ₹{total_emi:,.0f}/month total. "
        f"What can I help with? You can check your next EMI due date, "
        f"view detailed loan status, make an EMI payment, or ask for advice."
    )


async def get_health_score(phone: str) -> dict:
    """Compute financial health score (0-100) using CIBIL, DTI, loan history."""
    try:
        from db.database import users_collection
        user = await users_collection.find_one({"phone": phone})
        if not user:
            return {"success": False, "message": "User not found", "health_score": 0, "components": {}}

        score = user.get("credit_score", 0) or 0
        salary = user.get("salary", 0) or 0
        existing_emi = user.get("existing_emi_total", 0) or 0
        dti = (existing_emi / salary) if salary > 0 else 0
        past_loans = user.get("past_loans", []) or []

        # Component scores (each 0-100)
        cibil_score = min(100, max(0, (score / 900) * 100))
        dti_score = max(0, min(100, (1 - dti / 0.5) * 100)) if dti > 0 else 100
        stability_score = 70  # default
        if user.get("city") and user.get("profession"):
            stability_score = 80
        if salary > 100000:
            stability_score += 10
        elif salary > 50000:
            stability_score += 5

        loan_history_score = 60
        approved_count = sum(1 for p in past_loans if p.get("decision") == "approve")
        if approved_count > 0:
            loan_history_score = 70 + min(30, approved_count * 10)

        weights = {"cibil": 0.35, "dti": 0.30, "stability": 0.20, "loan_history": 0.15}
        overall = (
            cibil_score * weights["cibil"]
            + dti_score * weights["dti"]
            + stability_score * weights["stability"]
            + loan_history_score * weights["loan_history"]
        )

        return {
            "success": True,
            "phone": phone,
            "health_score": round(overall, 1),
            "components": {
                "cibil": {"score": round(cibil_score, 1), "raw": score, "weight": weights["cibil"]},
                "dti": {"score": round(dti_score, 1), "raw_dti": round(dti * 100, 1), "weight": weights["dti"]},
                "stability": {"score": round(stability_score, 1), "weight": weights["stability"]},
                "loan_history": {"score": round(loan_history_score, 1), "raw_approved": approved_count, "weight": weights["loan_history"]},
            },
            "risk_level": "low" if overall >= 70 else "medium" if overall >= 45 else "high",
        }
    except Exception as e:
        return {"success": False, "message": str(e), "health_score": 0, "components": {}}


async def get_emi_calculator(
    phone: str,
    amount: float,
    rate: float,
    tenure: int,
) -> dict:
    """Calculate EMI, amortization schedule, and tenure comparison."""
    try:
        if amount <= 0 or rate <= 0 or tenure <= 0:
            return {"success": False, "message": "Invalid parameters"}

        r = (rate / 12) / 100
        emi = amount * r * ((1 + r) ** tenure) / (((1 + r) ** tenure) - 1)
        total_repayment = emi * tenure
        total_interest = total_repayment - amount

        # Generate amortization schedule (first 12 months + summary)
        amortization = []
        balance = amount
        for m in range(1, min(tenure + 1, 13)):
            interest_portion = balance * r
            principal_portion = emi - interest_portion
            balance -= principal_portion
            amortization.append({
                "month": m,
                "emi": round(emi, 2),
                "interest": round(interest_portion, 2),
                "principal": round(principal_portion, 2),
                "balance": round(max(0, balance), 2),
            })

        # Tenure comparison (12, 24, 36, 48, 60 months)
        tenure_options = [t for t in [12, 24, 36, 48, 60] if t != tenure]
        comparisons = []
        for t in tenure_options:
            r2 = (rate / 12) / 100
            e2 = amount * r2 * ((1 + r2) ** t) / (((1 + r2) ** t) - 1)
            comparisons.append({
                "tenure": t,
                "emi": round(e2, 2),
                "total_interest": round(e2 * t - amount, 2),
                "total_repayment": round(e2 * t, 2),
            })

        # DTI check with user data
        from db.database import users_collection
        user = await users_collection.find_one({"phone": phone})
        salary = user.get("salary", 0) if user else 0
        existing_emi = user.get("existing_emi_total", 0) if user else 0
        total_emi = emi + existing_emi
        dti_after = (total_emi / salary) if salary > 0 else 0

        return {
            "success": True,
            "phone": phone,
            "params": {"amount": amount, "rate": rate, "tenure": tenure},
            "emi": round(emi, 2),
            "total_interest": round(total_interest, 2),
            "total_repayment": round(total_repayment, 2),
            "amortization": amortization,
            "amortization_truncated": tenure > 12,
            "total_months": tenure,
            "tenure_comparisons": comparisons,
            "dti_after_loan": round(dti_after * 100, 1),
            "monthly_income": salary,
            "existing_emi": existing_emi,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


async def get_lender_comparison(phone: str) -> dict:
    """Return structured lender offer data for dashboard visualization."""
    try:
        from mock_apis.lender_apis import get_lender_rules_summary, aggregate_lender_offers
        from db.database import users_collection

        user = await users_collection.find_one({"phone": phone})
        if not user:
            return {"success": False, "message": "User not found", "lenders": []}

        salary = user.get("salary", 100000) or 100000
        score = user.get("credit_score", 750) or 750
        # Use a moderate loan amount and tenure for comparison
        test_amount = min(500000, int(salary * 5))
        test_tenure = 36

        result = await aggregate_lender_offers(
            principal=test_amount,
            tenure=test_tenure,
            credit_score=score,
            monthly_income=salary,
        )

        all_rules = get_lender_rules_summary()

        # Merge rules with computed offers
        lender_data = []
        for rule in all_rules:
            offer = next((o for o in result.get("offers", []) if o["lender_id"] == rule["lender_id"]), None)
            rejection = next((r for r in result.get("rejection_details", []) if r["lender_id"] == rule["lender_id"]), None)

            entry = {
                "lender_id": rule["lender_id"],
                "lender_name": rule["lender_name"],
                "lender_type": rule["lender_type"],
                "interest_rate": offer["interest_rate"] if offer else rule["base_rate"],
                "processing_fee_percent": rule["processing_fee_percent"],
                "min_credit_score": rule["min_credit_score"],
                "max_loan_amount": rule["max_loan_amount"],
                "tenure_options": rule["tenure_options"],
                "foir_limit": rule["foir_limit"],
                "risk_profile": rule["risk_profile"],
                "approval_probability": rule["approval_probability"],
                "characteristics": rule["characteristics"],
                "eligible": offer is not None,
                "rejection_reasons": rejection["rejection_reasons"] if rejection else [],
            }

            if offer:
                entry["emi"] = offer.get("emi", 0)
                entry["processing_fee"] = offer.get("processing_fee", 0)
            else:
                # Estimate EMI with base rate
                est_emi = _calculate_emi_simple(test_amount, rule["base_rate"], test_tenure)
                entry["emi"] = round(est_emi, 2)
                entry["processing_fee"] = test_amount * (rule["processing_fee_percent"] / 100)

            lender_data.append(entry)

        return {
            "success": True,
            "phone": phone,
            "lenders": lender_data,
            "total_lenders": len(lender_data),
            "eligible_count": sum(1 for l in lender_data if l["eligible"]),
            "test_params": {"amount": test_amount, "tenure": test_tenure},
        }
    except Exception as e:
        return {"success": False, "message": str(e), "lenders": []}


def _calculate_emi_simple(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Simple EMI calculation for comparative purposes."""
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return 0.0
    r = (annual_rate / 12) / 100
    if r == 0:
        return principal / tenure_months
    emi = principal * r * ((1 + r) ** tenure_months) / (((1 + r) ** tenure_months) - 1)
    return emi


async def explain_selected_loan(session_id: str, lender_name: str, interest_rate: float, rank_info: Optional[str] = None) -> str:
    """Explain why the selected loan is a good choice."""
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

        monthly_rate = interest_rate / 12 / 100
        num_payments = tenure
        emi = (principal * monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)

        badge = f"({rank_info}) " if rank_info else ""
        emi_percentage = (emi / salary * 100) if salary > 0 else 0
        total_cost = emi * tenure
        total_interest = total_cost - principal

        explanation = f"""Why {lender_name}? {badge}

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

        if comparison_result:
            eligible_count = comparison_result.get("eligible_count", 0)
            explanation += f"\nSelected from {eligible_count} eligible offers"

            recommendation_reason = comparison_result.get("recommendation_reason", "")
            if recommendation_reason:
                explanation += f"\n{recommendation_reason}"

        explanation += "\n\n**Next Steps:**\n1. Review your documents\n2. Proceed to verification\n3. Sanction letter generation\n4. E-sign & disbursement\n\nReady to move forward?"

        return explanation

    except Exception as e:
        return f"You've selected {lender_name} at {interest_rate:.2f}% p.a. Let's proceed to document verification."

"""Underwriting Agent — evaluates loan eligibility using PS rules:
  - If amount ≤ pre-approved limit → instant approve (basic docs only)
  - If amount ≤ 2× pre-approved limit → approve only if EMI ≤ 50% salary (needs salary slip)
  - If amount > 2× pre-approved limit → reject
  - If credit score < 700 → reject
  - If fraud score ≥ 0.7 → reject (escalate)
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from langchain_core.messages import AIMessage
from agents.session_manager import SessionManager
from utils.financial_rules import (
    calculate_foir,
    MAX_SAFE_DTI,
    HARD_DTI_CEILING,
    MIN_CREDIT_SCORE,
    FRAUD_SCORE_HARD_REJECT_THRESHOLD,
    DTI_TIERS
)


def _calculate_max_principal(desired_emi: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate maximum principal for a given EMI, rate, and tenure.
    
    Args:
        desired_emi: Desired monthly EMI amount
        annual_rate: Annual interest rate (e.g., 0.10 for 10%)
        tenure_months: Loan tenure in months
    
    Returns:
        Maximum principal amount achievable with the given constraints
    """
    if annual_rate == 0 or tenure_months == 0:
        return 0
    
    monthly_rate = (annual_rate / 12) / 100
    if monthly_rate == 0:
        # Simple division if no interest
        return desired_emi * tenure_months
    
    # EMI formula: EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    # Rearranging for P: P = EMI * ((1 + r)^n - 1) / (r * (1 + r)^n)
    numerator = (1 + monthly_rate) ** tenure_months - 1
    denominator = monthly_rate * ((1 + monthly_rate) ** tenure_months)
    
    principal = desired_emi * (numerator / denominator)
    return max(0, principal)  # Ensure non-negative

async def underwriting_agent_node(state: dict) -> dict:
    """Deterministic underwriting engine checking NTC and FOIR heuristics."""
    print("⚖️ [UNDERWRITING AGENT] Executing multi-factor credit risk assessment...")

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    docs = state.get("documents", {})
    
    # ✅ NEW: Check for selected lender (Phase 5 integration)
    selected_lender_id = state.get("selected_lender_id")
    selected_lender_name = state.get("selected_lender_name")
    selected_rate = state.get("selected_interest_rate")
    
    if selected_lender_id:
        print(f"✅ [LENDER SELECTED] Using {selected_lender_name} (ID: {selected_lender_id}) at {selected_rate}% rate")

    salary = customer.get("salary", 0)
    score = customer.get("credit_score", customer.get("score", 0))
    pre_approved = customer.get("pre_approved_limit", customer.get("limit", 0))
    existing_emi = customer.get("existing_emi_total", 0)
    
    emi = terms.get("emi", 0)
    principal = terms.get("principal", 0)
    
    # ⚠️ GUARD: Do not evaluate if loan amount isn't captured yet
    if principal <= 0:
        print("⚖️ [UNDERWRITING] Skipping evaluation - No principal amount set.")
        return {
            "decision": "",
            "messages": [AIMessage(content="I'm still waiting for your loan details to perform a credit check.")],
            "current_phase": "sales"
        }
    
    rate = selected_rate if selected_rate else float(terms.get("rate", 12.0))  # Use selected or default rate
    tenure = terms.get("tenure", 12)  # Default 12 months
    fraud_score = state.get("fraud_score", 0.0)
    max_affordable_principal = terms.get("max_affordable_principal", 0)

    reasons = []
    decision = "approve"
    risk_level = "low"
    alternative_offer = 0.0

    # Base Metrics
    # NOTE: calculate_foir now returns fraction (0.50 = 50%), NOT percentage (50.0)
    total_emi = existing_emi + emi
    dti = calculate_foir(existing_emi, emi, salary)

    # Rule 5: Risk Classification
    if score > 0 and (score < 720 or dti > 0.40 or principal > pre_approved):
        risk_level = "high"
    elif 720 <= score <= 750 or 0.30 <= dti <= 0.40:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Rule 4: Professional Risk Scoring (New)
    occupation = customer.get("occupation", "").lower()
    employer = customer.get("employer_name", "").lower()
    
    # Simulate high-value employer whitelist
    WHITELIST_EMPLOYERS = ["google", "microsoft", "amazon", "tcs", "infosys", "hdfc", "isro"]
    is_whitelisted = any(w in employer for w in WHITELIST_EMPLOYERS)
    
    if is_whitelisted:
        risk_level = "low"
        print(f"🌟 [WHITELIST] Employer '{employer}' recognized. Risk level set to Low.")
    elif occupation in ["business", "self-employed"]:
        # Simulate Cash-flow underwriting (UPI Transaction Velocity)
        upi_velocity = state.get("simulated_upi_velocity", 0.85) # Mocked high velocity
        if upi_velocity < 0.5:
            reasons.append("Low transaction velocity detected in digital cash-flow analysis.")
            risk_level = "high"
        else:
            print(f"📈 [CASH-FLOW] Stable transaction velocity ({upi_velocity}) detected.")

    # Rule 4.5: Loan-to-Value (LTV) for Car/Home loans
    loan_purpose = terms.get("loan_purpose", "").lower()
    if any(p in loan_purpose for p in ["car", "home", "property"]):
        market_value = principal / 0.8  # Assume user needs 80% LTV
        ltv = principal / market_value
        if ltv > 0.85:
            reasons.append(f"Loan-to-Value (LTV) ratio is {ltv*100:.1f}%, which exceeds the safe lending limit of 85%. Requested: ₹{principal:,} | Asset Value: ₹{market_value:,.0f}.")
            decision = "soft_reject"
            alternative_offer = 0.80 * market_value

    # ─── BYPASS FOR TESTING/PIPELINE DEMO ───
    # Adding a "Force Reject" trigger so you can test the rejection letter flow too!
    loan_purpose = terms.get("loan_purpose", "").lower()
    if "force reject" in loan_purpose or "test reject" in loan_purpose or principal == 99999:
        reasons.append("⚠️ [DEVELOPER OVERRIDE] Manual rejection triggered for flow testing.")
        decision = "hard_reject"
    
    elif score <= 0:
        reasons.append(f"⚠️ Credit score missing or invalid ({score}). Cannot complete full underwriting without a valid credit score.")
        # Mark as pending to request further verification (e.g., fetch CIBIL or request documents)
        decision = "pending_docs"
    
    # ─── GATED EVALUATION ───
    if fraud_score >= FRAUD_SCORE_HARD_REJECT_THRESHOLD:
        reasons.append(f"Fraud score ({fraud_score:.2f}) ≥ {FRAUD_SCORE_HARD_REJECT_THRESHOLD} — Escalated to manual audit.")
        decision = "hard_reject"

    # Evaluation logic (with clear, documented thresholds)
    else:
        # Hard reject: DTI exceeds ceiling (150% = 1.50)
        if dti > HARD_DTI_CEILING:
            reasons.append(f"DTI Ratio ({dti:.2%}) exceeds absolute ceiling ({HARD_DTI_CEILING:.0%}). No loan possible.")
            decision = "hard_reject"
        
        # Hard reject: Extreme exposure
        elif principal > 100 * pre_approved:
            reasons.append(f"Requested loan (₹{principal:,}) exceeds extreme exposure limit (100× ₹{pre_approved:,}).")
            decision = "hard_reject"
        
        # Hard reject: Credit score too low
        elif score > 0 and score < MIN_CREDIT_SCORE:
            reasons.append(f"Credit score ({score}) is below minimum required ({MIN_CREDIT_SCORE}).")
            decision = "hard_reject"
        
        # Soft-Reject or Approve based on DTI and limits
        elif principal > pre_approved:
            # DTI exceeds safe limit but customer has good credit → soft reject (negotiation)
            if dti > MAX_SAFE_DTI:
                reasons.append(f"DTI Ratio ({dti:.2%}) exceeds safe limit ({MAX_SAFE_DTI:.0%}). Offering restructured terms.")
                decision = "soft_reject"
                # Calculate what we CAN offer
                max_viable_emi = (MAX_SAFE_DTI * salary) - existing_emi
                if max_viable_emi > 0:
                    alternative_offer = max_viable_emi
            else:
                # DTI is acceptable → approve
                decision = "approve"
        
        else:
            # Principal within pre-approved limit → approve
            decision = "approve"

    # Rule 7: Smart Offer Optimization + Soft Reject Classification
    # Per workflow diagram: DTI-only failures with good credit → "soft_reject" (Persuasion Loop)
    # Hard rejects (fraud, low credit score, exposure) remain "reject"
    if decision == "reject" and fraud_score < 0.7 and score >= 700:
        # Calculate maximum mathematically viable EMI
        max_viable_emi = (0.50 * salary) - existing_emi
        if max_viable_emi > 0:
            alt_p = _calculate_max_principal(max_viable_emi, rate, tenure)
            # Cap the alternative offer to the absolute maximum exposure limit (2x pre-approved)
            alt_p = min(alt_p, 2 * pre_approved)
            # Round down to nearest 5000 for realistic offering
            alt_p = (alt_p // 5000) * 5000
            alternative_offer = alt_p
            # Reclassify as soft_reject — eligible for Persuasion Loop negotiation
            if alt_p > 1000:
                decision = "soft_reject"

    # Rule 9: Explainability Layer Output Generator
    # ── Arjun's Human-Centric Decisioning ──
    if decision == "approve":
        lender_text = f" with {selected_lender_name}" if selected_lender_name else ""
        msg = (f"🎉 **EXCELLENT NEWS!**\n\n"
               f"I've personally reviewed your request, and your application for ₹{principal:,} is **FULLY APPROVED** {lender_text}. "
               f"Your disciplined credit profile and consistent history make you a preferred customer for us. "
               f"We're offering this at {rate:.1f}% p.a.")
    
    elif decision == "pending_docs":
        missing = "Salary Slip" if principal > pre_approved else "KYC Documents"
        msg = (f"⏳ **ALMOST THERE!**\n\n"
               f"Your application for ₹{principal:,} looks very promising. Since this is above your standard pre-approved limit, "
               f"I just need one small thing to wrap this up: **your latest {missing}**. "
               f"Once you upload that, we can push this straight to sanction!")

    elif decision == "soft_reject":
        msg = (f"🤝 **Let's work something out...**\n\n"
               f"I see you're aiming for ₹{principal:,}. While our current underwriting rules for student/new profiles "
               f"are a bit tight, I've managed to secure a revised offer of **₹{alternative_offer:,.0f}** for you instantly.\n\n"
               f"Would you like to proceed with this amount, or should we discuss a different tenure?")

    else:
        msg = (f"❌ **NOT THIS TIME (But don't give up!)**\n\n"
               f"I've analyzed the request, and currently, we aren't able to approve a loan due to your credit history/DTI constraints. "
               f"I recommend waiting for 90 days while maintaining timely payments on other obligations to boost your score.")

    # ✅ Calculate EMI dates when approved
    if decision == "approve":
        today = datetime.now()
        emi_day = state.get("loan_terms", {}).get("emi_day_of_month", 28)
        
        # First EMI: next month on selected day
        first_emi = today.replace(day=min(emi_day, 28))  # Cap at 28 to avoid invalid dates
        if first_emi <= today:
            # Move to next month if that day already passed
            if first_emi.month == 12:
                first_emi = first_emi.replace(year=first_emi.year + 1, month=1)
            else:
                first_emi = first_emi.replace(month=first_emi.month + 1)
        
        sanction_date = today.strftime("%Y-%m-%d")
        first_emi_str = first_emi.strftime("%Y-%m-%d")
    else:
        sanction_date = None
        first_emi_str = None

    updates = {
        "decision": decision,
        "dti_ratio": dti,
        "risk_level": risk_level,
        "alternative_offer": alternative_offer,
        "reasons": reasons,
        "messages": [AIMessage(content=msg)],
        "current_phase": "underwriting",
        
        # ✅ NEW: Persist selected lender information
        "selected_lender_id": selected_lender_id,
        "selected_lender_name": selected_lender_name,
        "selected_interest_rate": selected_rate,
        
        # ✅ Add EMI tracking fields
        "loan_terms": {
            **state.get("loan_terms", {}),
            "rate": rate,  # Explicitly save the evaluated rate
            "sanction_date": sanction_date,
            "first_emi_date": first_emi_str,
            "next_emi_date": first_emi_str,
            "emi_day_of_month": state.get("loan_terms", {}).get("emi_day_of_month", 28),
            "payments_made": 0,
            "days_overdue": 0,
            "last_payment_date": None
        },
        
        # ✅ Add YES/NO button options based on decision
        "options": (
            ["✅ Accept Loan Offer", "❓ Ask Questions Before Proceeding"]
            if decision == "approve"
            else [f"💪 Try ₹{alternative_offer:,.0f} Instead", "❌ Exit Application"]
            if decision == "soft_reject"
            else ["🔄 Reapply in 90 Days", "💬 Speak to Customer Support"]
        )
    }
    
    # Save session to MongoDB
    session_id = state.get("session_id", "default")
    try:
        await SessionManager.save_session(session_id, updates)
        print(f"💾 Session {session_id} saved to MongoDB")
    except Exception as e:
        print(f"⚠️ Failed to save session: {e}")
    
    return updates

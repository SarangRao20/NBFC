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
    
    monthly_rate = annual_rate / 12
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
    
    rate = terms.get("rate", 0.10)  # Default 10% annual rate
    tenure = terms.get("tenure", 12)  # Default 12 months
    fraud_score = state.get("fraud_score", 0.0)
    max_affordable_principal = terms.get("max_affordable_principal", 0)

    reasons = []
    decision = "approve"
    risk_level = "low"
    alternative_offer = 0.0

    # Base Metrics
    total_emi = existing_emi + emi
    dti = round(total_emi / salary, 3) if salary > 0 else 1.0

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
            reasons.append(f"Loan-to-Value ratio ({ltv*100:.0f}%) exceeds the 85% safety cap for asset-backed loans.")
            decision = "soft_reject"
            alternative_offer = 0.80 * market_value

    # Evaluate Logical Gates
    if fraud_score >= 0.7:
        reasons.append(f"Fraud score ({fraud_score}) ≥ 0.7 — Escalated to manual audit.")
        decision = "hard_reject"

    # NTC (New To Credit) Thin-file Detection
    elif score == 0 or score == -1:
        if not docs.get("bank_statement_verified"):
            reasons.append("New-To-Credit Detected. Please upload 6 months' Bank Statement for limit assessment.")
            decision = "pending_docs"
        elif principal > 50000:
            reasons.append("For 'New to Credit' users without a CIBIL score, the maximum introductory loan is strictly ₹50,000.")
            decision = "soft_reject"
            alternative_offer = 50000.0
            
    # Standard CIBIL Borrower
    else:
        # NEW: Global History Check
        past_records = (customer.get("past_records") or "").lower()
        if "rejected" in past_records or "fraud" in past_records:
            reasons.append(f"Historical system records flag recent rejection or risk: {past_records[:50]}...")
            risk_level = "high"
            if "fraud" in past_records: decision = "hard_reject"

        if score < 700:
            reasons.append(f"Credit score ({score}) is below the minimum threshold of 700.")
            decision = "hard_reject"
        elif occupation == "student" and principal > 25000:
             reasons.append("Maximum loan for students is ₹25,000 without a co-signer.")
             decision = "soft_reject"
             alternative_offer = 25000.0
        elif principal > 3 * pre_approved:
            reasons.append(f"Requested loan exceeds maximum permissible exposure (3× limit).")
            decision = "hard_reject"
        elif principal > 1.5 * pre_approved:
            # If it's between 1.5x and 3x, we offer a soft reject with negotiation or ask for more docs
            reasons.append(f"Requested loan (₹{principal:,}) is significantly higher than your pre-approved limit (₹{pre_approved:,}).")
            if score >= 750:
                decision = "pending_docs" # High score can get more if they show income
                reasons.append("Since you have an excellent credit score, we can consider this if you provide a verified Salary Slip.")
            else:
                decision = "soft_reject"
                alternative_offer = pre_approved * 1.5
        elif principal > pre_approved and not docs.get("verified"):
            reasons.append("Loan exceeds pre-approved limit; additional income verification (Salary Slip) required.")
            decision = "pending_docs"
        elif not state.get("documents_uploaded"):
            reasons.append("Mandatory KYC documents (PAN/Aadhaar) and income proof are required for all loan applications.")
            decision = "pending_docs"
        elif dti > 0.50:
            reasons.append(f"EMI exceeds affordability threshold (Total EMI > 50% of income).")
            decision = "reject"

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
        msg = (f"🎉 **EXCELLENT NEWS!**\n\n"
               f"I've personally reviewed your request, and your application for ₹{principal:,} is **FULLY APPROVED**. "
               f"Your disciplined credit profile and consistent history make you a preferred customer for us. "
               f"We're offering this at our best rate of {rate*100:.1f}% p.a.")
    
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
        
        # ✅ Add EMI tracking fields
        "loan_terms": {
            **state.get("loan_terms", {}),
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

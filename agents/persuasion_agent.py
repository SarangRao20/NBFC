"""Persuasion Agent — Sales Closer mode for soft-rejected loan applications.

Triggered when Decision Engine returns 'soft_reject' (DTI too high but credit is good).
Workflow per diagram:
  1. Analyze Reason for Rejection
  2. Suggest Fix: Reduce Amount or Increase Tenure
  3. User Accepts Modified Offer?
     → Yes: Recalculate Loan Terms → loop back to Decision Engine
     → No:  Route to Advisory Agent
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from config import get_master_llm
from utils.financial_rules import calculate_emi

# Maximum negotiation rounds before auto-routing to Advisory
MAX_NEGOTIATION_ROUNDS = 3


CLOSER_SYSTEM_PROMPT = """You are Arjun in CLOSER MODE — a skilled loan negotiation specialist at FinServe NBFC.

The customer's original loan application was SOFT REJECTED because their EMI-to-income ratio exceeds 50%.
However, their credit score qualifies them for a modified offer. Your job is to negotiate revised loan terms.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## REJECTION CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Customer: {name}
Original Request: ₹{original_principal:,} for {original_tenure} months
Original EMI: ₹{original_emi:,.2f}
Current DTI: {dti_pct:.1f}% (threshold: 50%)
Credit Score: {credit_score} ✓ (qualifies)
Monthly Salary: ₹{salary:,}
Existing EMIs: ₹{existing_emi:,}/month
Maximum Approvable Amount: ₹{max_amount:,}
Rejection Reasons: {reasons}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## YOUR NEGOTIATION STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ACKNOWLEDGE the rejection diplomatically — never blame the customer
2. PRESENT the modified offer clearly with exact numbers:
   - Option A: Reduce loan amount to ₹{max_amount:,} (same tenure)
   - Option B: Increase tenure to reduce EMI (calculate for 36/48/60 months)
   - Option C: Combination of both
3. CALCULATE and show the new EMI for each option
4. ASK clearly: "Would you like to proceed with any of these options?"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## RESPONSE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Be warm and solution-oriented, never pushy
- Always show exact ₹ amounts and EMI calculations
- If the user says NO / declines / not interested → respond with understanding and end
- If the user says YES to a modified amount/tenure → output JSON block below
- Negotiation round: {round_number} of {max_rounds}

## JSON OUTPUT (when user accepts modified terms)
When the customer CONFIRMS revised terms, end your reply with EXACTLY:
```json
{{"action": "accept", "revised_amount": <number>, "revised_tenure": <months>, "revised_rate": {rate}}}
```

If the customer DECLINES all options:
```json
{{"action": "decline"}}
```
"""


def _calculate_options(salary, existing_emi, rate, original_principal, original_tenure):
    """Generate viable restructured loan options."""
    max_emi = (0.50 * salary) - existing_emi
    if max_emi <= 0:
        return [], 0

    options = []

    # Option A: Same tenure, lower amount
    r_monthly = (rate / 12) / 100
    n = original_tenure
    if r_monthly > 0 and n > 0:
        max_principal_same_tenure = max_emi * (((1 + r_monthly) ** n) - 1) / (r_monthly * ((1 + r_monthly) ** n))
        max_principal_same_tenure = round(max_principal_same_tenure, -3)  # Round to nearest 1000
        if max_principal_same_tenure > 0:
            new_emi = calculate_emi(max_principal_same_tenure, rate, n)
            options.append({
                "label": f"Reduce to ₹{max_principal_same_tenure:,.0f} ({n} months)",
                "amount": max_principal_same_tenure,
                "tenure": n,
                "emi": new_emi
            })

    # Option B & C: Extended tenures
    for extended_tenure in [36, 48, 60]:
        if extended_tenure <= original_tenure:
            continue
        emi_extended = calculate_emi(original_principal, rate, extended_tenure)
        if emi_extended > 0 and (existing_emi + emi_extended) / salary <= 0.50:
            options.append({
                "label": f"Full ₹{original_principal:,.0f} ({extended_tenure} months)",
                "amount": original_principal,
                "tenure": extended_tenure,
                "emi": emi_extended
            })

    return options, round(max_principal_same_tenure if options else 0)


async def persuasion_agent_node(state: dict) -> dict:
    """Persuasion Loop: negotiate revised loan terms after soft rejection."""
    print("🤝 [PERSUASION AGENT] Entering negotiation mode...")

    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    reasons = state.get("reasons", [])

    salary = customer.get("salary", 0)
    existing_emi = customer.get("existing_emi_total", 0)
    score = customer.get("credit_score", customer.get("score", 0))
    rate = terms.get("rate", 12.0)
    principal = terms.get("principal", 0)
    tenure = terms.get("tenure", 12)
    dti = state.get("dti_ratio", 0)

    # Track negotiation rounds
    negotiation_round = state.get("negotiation_round", 0) + 1

    # Max rounds exceeded → auto-route to advisory
    if negotiation_round > MAX_NEGOTIATION_ROUNDS:
        print(f"  ⏰ Max negotiation rounds ({MAX_NEGOTIATION_ROUNDS}) reached. Routing to Advisory.")
        return {
            "decision": "reject",
            "negotiation_round": negotiation_round,
            "messages": [AIMessage(content=(
                f"⏳ We've explored {MAX_NEGOTIATION_ROUNDS} options together. "
                f"Our Advisory team will now help you with next steps and financial guidance."
            ))]
        }

    # Calculate viable options
    options, max_amount = _calculate_options(salary, existing_emi, rate, principal, tenure)

    if not options:
        # No viable restructuring possible → hard reject
        return {
            "decision": "reject",
            "negotiation_round": negotiation_round,
            "messages": [AIMessage(content=(
                "Unfortunately, based on your current income and obligations, "
                "we're unable to structure a viable loan offer at this time. "
                "Our Advisory team will provide personalized guidance to improve your eligibility."
            ))]
        }

    # Build the negotiation prompt
    llm = get_master_llm()
    sys_content = CLOSER_SYSTEM_PROMPT.format(
        name=customer.get("name", "Customer"),
        original_principal=principal,
        original_tenure=tenure,
        original_emi=terms.get("emi", 0),
        dti_pct=dti * 100,
        credit_score=score,
        salary=salary,
        existing_emi=existing_emi,
        max_amount=max_amount,
        reasons="; ".join(reasons) if reasons else "EMI exceeds affordability threshold",
        round_number=negotiation_round,
        max_rounds=MAX_NEGOTIATION_ROUNDS,
        rate=rate
    )

    # Present options summary
    options_text = "\n".join(
        f"  **Option {chr(65+i)}**: {opt['label']} → EMI: ₹{opt['emi']:,.2f}/month"
        for i, opt in enumerate(options)
    )

    msg = (
        f"🤝 **Loan Restructuring Options** (Round {negotiation_round}/{MAX_NEGOTIATION_ROUNDS})\n\n"
        f"Your original request of ₹{principal:,} exceeds our affordability threshold, "
        f"but your excellent credit score ({score}) qualifies you for these alternatives:\n\n"
        f"{options_text}\n\n"
        f"Would you like to proceed with any of these options?"
    )

    return {
        "negotiation_round": negotiation_round,
        "persuasion_options": options,
        "messages": [AIMessage(content=msg)]
    }


def process_persuasion_response(user_response: str, state: dict) -> dict:
    """Process user's response to the persuasion offer.

    Called from the Streamlit UI layer (like sales_chat_response).
    Returns updated state fields based on user's choice.
    """
    import json, re

    response_lower = user_response.strip().lower()
    
    print(f"🤝 [PERSUASION RESPONSE] User said: '{user_response}'")

    # Check for decline keywords - expanded and more strict
    DECLINE_KEYWORDS = {
        "no", "nope", "nah", "decline", "not interested", "cancel",
        "forget it", "leave it", "nahi", "mat karo", "no thanks",
        "don't want", "don't like", "not good", "reject", "refuse",
        "disagree", "won't", "will not", "can't", "cannot"
    }

    # First check for explicit decline - this should take priority
    if response_lower in DECLINE_KEYWORDS or any(kw in response_lower for kw in DECLINE_KEYWORDS):
        print(f"  ❌ User explicitly declined the offer")
        return {
            "action": "decline",
            "decision": "reject",
            "persuasion_status": "declined",
            "messages": [AIMessage(content=(
                "Understood! No worries at all. Our Advisory team will now provide "
                "personalized financial guidance to help you in the future. 🙏"
            ))]
        }

    # Check for acceptance with specific option
    options = state.get("persuasion_options", [])
    terms = state.get("loan_terms", {})

    # Try to detect which option they chose (Option A, B, C or by amount)
    for i, opt in enumerate(options):
        option_letter = chr(65 + i).lower()
        if f"option {option_letter}" in response_lower or f"option{option_letter}" in response_lower:
            print(f"  ✅ User accepted Option {option_letter.upper()}")
            new_emi = calculate_emi(opt["amount"], terms.get("rate", 12), opt["tenure"])
            return {
                "action": "accept",
                "loan_terms": {
                    **terms,
                    "principal": opt["amount"],
                    "tenure": opt["tenure"],
                    "emi": new_emi
                },
                # Reset decision so underwriting re-evaluates
                "decision": "",
                "persuasion_status": "accepted",
                "messages": [AIMessage(content=(
                    f"✅ Great choice! Revised terms accepted:\n"
                    f"- Amount: ₹{opt['amount']:,.0f}\n"
                    f"- Tenure: {opt['tenure']} months\n"
                    f"- New EMI: ₹{new_emi:,.2f}/month\n\n"
                    f"Re-submitting to our Decision Engine for final approval..."
                ))]
            }

    # Check for amount-based acceptance
    amount_match = re.search(r'₹?\s?(\d+(?:,\d+)*(?:\.\d+)?)', response_lower)
    if amount_match and options:
        requested_amount = int(amount_match.group(1).replace(',', ''))
        print(f"  🔍 User mentioned amount: ₹{requested_amount}")
        
        # Find closest matching option
        for opt in options:
            if abs(opt["amount"] - requested_amount) < 5000:  # Within 5k tolerance
                new_emi = calculate_emi(opt["amount"], terms.get("rate", 12), opt["tenure"])
                return {
                    "action": "accept",
                    "loan_terms": {
                        **terms,
                        "principal": opt["amount"],
                        "tenure": opt["tenure"],
                        "emi": new_emi
                    },
                    "decision": "",
                    "persuasion_status": "accepted",
                    "messages": [AIMessage(content=(
                        f"✅ Great choice! Revised terms accepted:\n"
                        f"- Amount: ₹{opt['amount']:,.0f}\n"
                        f"- Tenure: {opt['tenure']} months\n"
                        f"- New EMI: ₹{new_emi:,.2f}/month\n\n"
                        f"Re-submitting for final approval..."
                    ))]
                }

    # Generic acceptance (take first viable option) - but be more strict
    ACCEPT_KEYWORDS = {
        "yes", "ok", "okay", "sure", "proceed", "accept", "haan",
        "go ahead", "let's do it", "sounds good", "yep", "yeah"
    }
    
    # Only accept if there's a clear acceptance keyword AND no decline keywords
    is_clear_acceptance = (
        (response_lower in ACCEPT_KEYWORDS or any(kw in response_lower for kw in ACCEPT_KEYWORDS)) and
        not any(kw in response_lower for kw in DECLINE_KEYWORDS)
    )
    
    if is_clear_acceptance and options:
        opt = options[0]  # Default to first (most conservative) option
        new_emi = calculate_emi(opt["amount"], terms.get("rate", 12), opt["tenure"])
        print(f"  ✅ User gave clear acceptance, selected first option")
        return {
            "action": "accept",
            "loan_terms": {
                **terms,
                "principal": opt["amount"],
                "tenure": opt["tenure"],
                "emi": new_emi
            },
            "decision": "",
            "persuasion_status": "accepted",
            "messages": [AIMessage(content=(
                f"✅ Revised terms accepted:\n"
                f"- Amount: ₹{opt['amount']:,.0f}\n"
                f"- Tenure: {opt['tenure']} months\n"
                f"- New EMI: ₹{new_emi:,.2f}/month\n\n"
                f"Re-submitting for final approval..."
            ))]
        }

    # If we get here, the response is unclear - ask for clarification
    print(f"  ❓ Response unclear, asking for clarification")
    return {
        "action": "unclear",
        "persuasion_status": "unclear",
        "messages": [AIMessage(content=(
            "I want to make sure I get this right! Could you please specify:\n"
            "- **'Option A'** / **'Option B'** etc. to select a specific plan\n"
            "- **'Yes'** to accept our recommended option\n"
            "- **'No'** if you'd prefer not to proceed\n\n"
            "Your options are:\n" + "\n".join(
                f"• Option {chr(65+i)}: {opt['label']} → EMI: ₹{opt['emi']:,.2f}/month"
                for i, opt in enumerate(options[:3])  # Show max 3 options
            ) if options else "No options available."
        ))]
    }

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


CLOSER_SYSTEM_PROMPT = """ You are in **CLOSER MODE** — a Senior Loan Negotiation Specialist at FinServe NBFC (India).
SYSTEM ROLE: You handle cases where the original loan request resulted in a **Soft Reject** due to exceeding safe Debt-to-Income (DTI) limits.

Your objective:
- Recover the deal using safe, pre-approved alternatives
- Guide the user toward an acceptable option
- Capture a clear decision (accept / decline)

You DO NOT:
- Perform calculations
- Modify system values
- Generate new offers

You ONLY present pre-approved options and capture user choice.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM STATE & REJECTION CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Customer Name: {name}

Original Request:
₹{original_principal:,} over {original_tenure} months

Calculated DTI:
{dti_pct:.1f}% (Policy Maximum: 50%)

Rejection Reason:
{reasons}

Authorized Counter-Offers (STRICT — DO NOT MODIFY):

Option A (Lower Amount):
₹{safe_max_amount:,} over {original_tenure} months  
EMI: ₹{option_a_emi:,.2f}

Option B (Extended Tenure):
₹{original_principal:,} over {extended_tenure} months  
EMI: ₹{option_b_emi:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEGOTIATION STRATEGY (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DIPLOMATIC OPENING
- Acknowledge constraint without blame
- Position this as optimization, not rejection

Example framing:
"To keep your monthly commitments comfortable, we've adjusted the structure slightly."

---

2. PRESENT OPTIONS CLEARLY
- Show BOTH Option A and Option B
- Use exact numbers only
- Keep explanation simple and comparison-driven

---

3. GUIDE DECISION
- Ask user to choose:
  - "Option A"
  - "Option B"
- OR allow them to decline

Example:
"Which option works better for you?"

---

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DECISION INTERPRETATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Treat as ACCEPT if user:
- Explicitly says "Option A" or "Option B"
- OR confirms with phrases like:
  - "I'll take this"
  - "Go with second option"
  - "Yes, proceed with lower EMI"

Map:
- Option A → reduced amount
- Option B → extended tenure

---

Treat as DECLINE if:
- User rejects both options
- Says "not interested", "cancel", "no"
- OR max negotiation rounds reached

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOOP CONTROL (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current round: {round_number}  
Max allowed: {max_rounds}

Rules:
- If round < max_rounds:
  → Continue negotiation
- If round >= max_rounds:
  → Force graceful exit (decline)

NEVER loop endlessly.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT GUARDRAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NO calculations (EMI already provided)
- NO new offers
- NO blaming user
- NO financial advice beyond loan structuring
- NO deviation from given numbers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE FORMAT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your response MUST have two parts:

1. Conversational message (first)
- Persuasive but respectful
- Clear options
- Short and structured

2. JSON block (LAST line ONLY)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON OUTPUT CONTRACT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IF USER ACCEPTS:

```json
{{
  "action": "accept",
  "revised_amount": <number>,
  "revised_tenure": <months>,
  "revised_emi": <number>
}}

Mapping:

Option A → use {{safe_max_amount}}, {{original_tenure}}, {{option_a_emi}}
Option B → use {{original_principal}}, {{extended_tenure}}, {{option_b_emi}}

IF USER DECLINES OR MAX ROUNDS REACHED:

{{
  "action": "decline",
  "revised_amount": null,
  "revised_tenure": null,
  "revised_emi": null
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

JSON MUST be valid
JSON MUST be last in response
NO text after JSON
DO NOT emit JSON until decision is clear
DO NOT omit fields

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL BEHAVIOR SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are:

A structured negotiation agent
A deal recovery specialist
A deterministic decision capture system

You are NOT:

A chatbot
A calculator
A financial advisor

Act with clarity, control, and precision.
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
    
    log = list(state.get("action_log") or [])
    log.append("🤝 Arjun: Analyzing restructuring options for soft-reject...")

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
        log.append(f"⏰ Max negotiation rounds ({MAX_NEGOTIATION_ROUNDS}) reached.")
        return {
            "decision": "reject",
            "negotiation_round": negotiation_round,
            "messages": [AIMessage(content=(
                f"⏳ We've explored {MAX_NEGOTIATION_ROUNDS} options together. "
                f"Our Advisory team will now help you with next steps and financial guidance."
            ))],
            "action_log": log,
            "options": ["Talk to Advisor", "Exit"]
        }

    # Calculate viable options
    options, max_amount = _calculate_options(salary, existing_emi, rate, principal, tenure)
    log.append(f"📊 Calculated {len(options)} viable restructuring plans.")

    if not options:
        # No viable restructuring possible → hard reject
        log.append("❌ No viable restructuring possible for this profile.")
        return {
            "decision": "reject",
            "negotiation_round": negotiation_round,
            "messages": [AIMessage(content=(
                "Unfortunately, based on your current income and obligations, "
                "we're unable to structure a viable loan offer at this time. "
                "Our Advisory team will provide personalized guidance to improve your eligibility."
            ))],
            "action_log": log,
            "options": ["View Recovery Plan", "Talk to Advisor"]
        }

    # Build the options text and buttons
    options_text = "\n".join(
        f"  **Option {chr(65+i)}**: {opt['label']} → EMI: ₹{opt['emi']:,.2f}/month"
        for i, opt in enumerate(options)
    )
    
    opts_buttons = [f"Accept Option {chr(65+i)}" for i in range(len(options))]
    opts_buttons.append("Decline All")

    # ENHANCEMENT: Generate personalized LLM dialogue instead of hardcoded message
    try:
        from config import get_master_llm
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = get_master_llm()
        context_prompt = f"""
        Customer: {customer.get("name", "Valued Customer")}
        Original Request: ₹{principal:,} for {tenure} months
        Credit Score: {score}
        Current DTI: {dti*100:.1f}%
        Monthly Salary: ₹{salary:,}
        
        Restructuring Options:
{options_text}
        
        Generate a warm, persuasive negotiation message that:
        1. Acknowledges the original request respectfully
        2. Explains why restructuring is beneficial
        3. Presents the two options clearly
        4. Asks which option they prefer
        
        Keep it professionally friendly and solution-oriented. No calculations needed.
        """
        
        llm_response = await llm.ainvoke([
            SystemMessage(content=CLOSER_SYSTEM_PROMPT.format(
                name=customer.get("name", "Valued Customer"),
                original_principal=principal,
                original_tenure=tenure,
                dti_pct=dti*100,
                reasons="; ".join(reasons) if reasons else "DTI exceeds 50%",
                safe_max_amount=options[0]["amount"] if options else principal,
                option_a_emi=options[0]["emi"] if options else 0,
                extended_tenure=options[1]["tenure"] if len(options) > 1 else tenure + 12,
                option_b_emi=options[1]["emi"] if len(options) > 1 else 0,
                round_number=negotiation_round,
                max_rounds=MAX_NEGOTIATION_ROUNDS
            )),
            HumanMessage(content=context_prompt)
        ])
        
        msg = llm_response.content
        log.append("💬 Generated personalized negotiation dialogue via LLM")
        
    except Exception as e:
        # Fallback to hardcoded message if LLM fails
        print(f"⚠️ LLM dialogue generation failed: {e}, using fallback")
        log.append(f"⚠️ LLM failed, using fallback message")
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
        "messages": [AIMessage(content=msg)],
        "action_log": log,
        "options": opts_buttons
    }


def process_persuasion_response(user_response: str, state: dict) -> dict:
    """Process user's response to the persuasion offer."""
    import json, re

    response_lower = user_response.strip().lower()
    log = list(state.get("action_log") or [])
    
    print(f"🤝 [PERSUASION RESPONSE] User said: '{user_response}'")

    # Check for decline keywords
    DECLINE_KEYWORDS = {
        "no", "nope", "nah", "decline", "not interested", "cancel",
        "forget it", "leave it", "nahi", "mat karo", "no thanks",
        "don't want", "don't like", "not good", "reject", "refuse",
        "disagree", "won't", "will not", "can't", "cannot"
    }

    if response_lower in DECLINE_KEYWORDS or any(kw in response_lower for kw in DECLINE_KEYWORDS):
        log.append("❌ User declined restructured offer.")
        return {
            "action": "decline",
            "decision": "reject",
            "persuasion_status": "declined",
            "action_log": log,
            "messages": [AIMessage(content=(
                "Understood! No worries at all. Our Advisory team will now provide "
                "personalized financial guidance to help you in the future. 🙏"
            ))]
        }

    options = state.get("persuasion_options", [])
    terms = state.get("loan_terms", {})

    # Try to detect which option they chose
    for i, opt in enumerate(options):
        option_letter = chr(65 + i).lower()
        if f"option {option_letter}" in response_lower or f"option{option_letter}" in response_lower:
            log.append(f"✅ User accepted Option {option_letter.upper()}.")
            new_emi = calculate_emi(opt["amount"], terms.get("rate", 12), opt["tenure"])
            return {
                "action": "accept",
                "loan_terms": {
                    **terms,
                    "principal": opt["amount"],
                    "tenure": opt["tenure"],
                    "emi": new_emi
                },
                "decision": "", # Reset for re-evaluation
                "persuasion_status": "accepted",
                "action_log": log,
                "messages": [AIMessage(content=(
                    f"✅ Great choice! Revised terms accepted:\n"
                    f"- Amount: ₹{opt['amount']:,.0f}\n"
                    f"- Tenure: {opt['tenure']} months\n"
                    f"- New EMI: ₹{new_emi:,.2f}/month\n\n"
                    f"Re-submitting to our Decision Engine for final approval..."
                ))]
            }

    # Default to clarify
    log.append("❓ Clarification requested for restructuring choice.")
    return {
        "action": "unclear",
        "persuasion_status": "unclear",
        "action_log": log,
        "messages": [AIMessage(content=(
            "I want to make sure I get this right! Could you please specify which option you'd like to proceed with?"
        ))]
    }

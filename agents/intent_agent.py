"""Intent Agent — Classifies user requests to route to the correct workflow.

This agent acts as a dispatcher after the user is authenticated.
It determines if the user wants:
1. 'loan': Apply for a new loan or check loan status.
2. 'advice': Get financial advice or CIBIL tips.
3. 'kyc': Update or verify documents.
4. 'none': General greeting/unknown.
"""

import json
import re
from config import get_extraction_llm
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

INTENT_SYSTEM_PROMPT = """You are Arjun, the Senior Financial Advisor. 
Briefly look at the user message and categorize their INTENT.

1. 'loan': Wants a loan, asking for rates, or pre-approved limit for a loan.
2. 'advice': Needs tips on credit score, CIBIL, investments, or how to improve their profile.
3. 'kyc': Uploading docs, PAN, Aadhaar, salary slips, or updating paperwork.
4. 'sign': Explicitly accepting the sanction letter, e-signing, or confirming the loan offer.
5. 'none': Just a hello, greeting, or unclear question.

OUTPUT FORMAT:
Return EXACTLY a JSON block:
```json
{{ "intent": "one of the above", "reason": "short explanation" }}
```
"""

def intent_node(state: dict):
    """Classifies user intent to set the next workflow."""
    print("🎯 [INTENT AGENT] Analyzing user intent...")
    log = list(state.get("action_log") or [])
    log.append("🎯 Routed to Intent Classification Agent")
    llm = get_extraction_llm()

    # Get the latest user message
    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break
    
    if not user_msg or len(user_msg.split()) < 2:
        # If it's just a number (like OTP) or a 1-word greeting, label as unclear to prompt the user appropriately
        intent = 'unclear'
    else:
        intent = 'unclear'
        try:
            # Avoid structured output; use manual parsing for robustness
            res = llm.invoke([
                SystemMessage(content=INTENT_SYSTEM_PROMPT),
                HumanMessage(content=f"User Message: {user_msg}")
            ])
            content = res.content
            
            # Regex to find JSON block
            json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                intent = data.get("intent", "unclear")
                log.append(f"✅ Intent classified: '{intent}' — {data.get('reason', '')}")
                print(f"  → Classified as: {intent} ({data.get('reason')})")
            else:
                # Simple keyword check as last resort
                lower = content.lower()
                if "loan" in lower: intent = "loan"
                elif "advice" in lower: intent = "advice"
                elif "kyc" in lower: intent = "kyc"
                elif "sign" in lower or "accept" in lower: intent = "sign"
                log.append(f"✅ Intent (keyword fallback): '{intent}'")
                print(f"  → Classified as: {intent} (Fallback)")
                
        except Exception as e:
            print(f"  ⚠️ Intent classification failed: {e}")
            log.append(f"⚠️ Intent classification error: {str(e)[:60]}")
            intent = 'unclear'

    if intent == 'unclear' or intent not in ['loan', 'advice', 'kyc', 'sign']:
        msg = "I'm here to help! I can assist you with a **new loan**, give you **expert financial advice**, or help you with your **KYC documents**. Which one would you like to explore first?"
        return {"intent": "unclear", "messages": [AIMessage(content=msg)], "action_log": log, "current_phase": "intent_discovery"}

    phase_map = {"loan": "loan_application", "advice": "advice", "kyc": "kyc_verification", "sign": "loan_approval"}
    return {"intent": intent, "action_log": log, "current_phase": phase_map.get(intent, "intent_discovery")}

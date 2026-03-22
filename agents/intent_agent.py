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

INTENT_SYSTEM_PROMPT = """You are Arjun, the Senior Strategy Dispatcher at FinServe NBFC. Your job is to classify the user's latest message into one of five strict categories to ensure they talk to the right specialist.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## INTENT CATEGORIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. **'loan'**: The user wants to borrow money, start a new application, check their pre-approved limit, or mentions "borrow", "apply", "fees", "tuition", "IIT", or "loan please".
2. **'advice'**: The user is asking "Is this rate good?", "How can I improve my CIBIL?", "What is my DTI?", or looking for general financial tips.
3. **'kyc'**: The user is uploading or asking about PAN, Aadhaar, Salary Slips, or "how to upload documents".
4. **'sign'**: The user says "I am ready to sign", "e-sign", "accept the offer", or "confirm the loan".
5. **'none'**: General greetings ("Hi", "Hello") or completely unrelated chat.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## DISPATCH RULES (ANTI-HALLUCINATION):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- If the user asks for a loan AND advice in the same message, prioritize **'loan'** (Sales).
- If the user is just saying "Yes" to a specific term confirmed earlier, use **'loan'**.
- If the user says "Yes" to signing an approved offer, use **'sign'**.

OUTPUT FORMAT:
Return EXACTLY a JSON block:
```json
{{ "intent": "one of the above", "reason": "short explanation" }}
```
"""


async def intent_node(state: dict):
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
            res = await llm.ainvoke([
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

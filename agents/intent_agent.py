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
1. **'loan'**: The user wants to borrow money, start a new application, check their pre-approved limit, or mentions "borrow", "apply", "fees", "tuition", "IIT", "loan please", or "Apply for Loan".
2. **'advice'**: The user is asking "Should I take a loan?", "Is this a good investment?", "How can I improve my CIBIL?", "What is my DTI?", or looking for advisor guidance.
3. **'kyc'**: The user is uploading or asking about PAN, Aadhaar, Salary Slips, or "how to upload documents".
4. **'sign'**: The user says "I am ready to sign", "e-sign", "accept the offer", or "confirm the loan".
5. **'payment'**: The user wants to make an EMI payment, check their **loan status**, see **remaining balance**, or track **repayment progress**. (e.g., "how much is left?", "pay my emi", "status of my loan").
6. **'none'**: General greetings ("Hi", "Hello") or completely unrelated chat.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## DISPATCH RULES (ANTI-HALLUCINATION):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- If the user asks "Should I", "What do you think", "Is it good/bad", or "Why", prioritize **'advice'**.
- If the user is clearly ready to provide terms (amount, tenure) or says "Apply", use **'loan'**.
- If the user is just saying "Yes" to a specific term confirmed earlier, use **'loan'**.
- If the user says "Yes" to signing an approved offer, use **'sign'**.

OUTPUT FORMAT:
Return EXACTLY a JSON block:
```json
{{ "intent": "one of the above", "reason": "short explanation", "requested_amount": "number or 0", "salary": "number or 0" }}
```

If the user is correcting something or talking about their finances (salary, budget), use 'advice'.
"""


async def intent_node(state: dict):
    """Classifies user intent to set the next workflow with intelligent extraction."""
    print("🎯 [INTENT AGENT] Analyzing user intent with LLM...")
    log = list(state.get("action_log") or [])
    log.append("🎯 Routed to Intelligent Intent Agent")
    llm = get_extraction_llm()

    # Get context window for classification (last 3 messages)
    history = []
    for m in state.get("messages", [])[-3:]:
        role = "User" if isinstance(m, HumanMessage) else "Assistant"
        history.append(f"{role}: {m.content if hasattr(m, 'content') else str(m)}")
    context_text = "\n".join(history)
    
    # Get the latest user message for extraction
    user_msg = ""
    for m in reversed(state.get("messages", [])):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break
    
    intent = "unclear"
    extracted_amount = 0
    extracted_salary = 0
    
    # Intelligent LLM Classification & Extraction
    try:
        PROMPT = INTENT_SYSTEM_PROMPT + "\n\nEXTRACTOR RULE: Extract 'requested_amount' and 'salary' if mentioned. Return 0 for missing values."
        
        res = await llm.ainvoke([
            SystemMessage(content=PROMPT),
            HumanMessage(content=f"RECENT CONTEXT:\n{context_text}\n\nLatest User Message: {user_msg}")
        ])
        content = res.content
        
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            intent = data.get("intent", "unclear")
            raw_amt = data.get("requested_amount", 0)
            raw_salary = data.get("salary", 0)
            
            # Helper to parse amounts
            def parse_amt(val):
                if isinstance(val, str):
                    s = val.lower().replace("₹", "").replace(",", "").strip()
                    if "lakh" in s or "lac" in s:
                        nums = re.findall(r"[\d.]+", s)
                        return float(nums[0]) * 100000 if nums else 0
                    elif "k" in s:
                        nums = re.findall(r"[\d.]+", s)
                        return float(nums[0]) * 1000 if nums else 0
                    else:
                        nums = re.findall(r"[\d.]+", s)
                        return float(nums[0]) if nums else 0
                try:
                    return float(val or 0)
                except: return 0

            extracted_amount = parse_amt(raw_amt)
            extracted_salary = parse_amt(raw_salary)

            log.append(f"✅ Intent: '{intent}' — {data.get('reason', '')}")
            if extracted_amount > 0:
                log.append(f"💰 Extracted Loan: ₹{extracted_amount:,.0f}")
            if extracted_salary > 0:
                log.append(f"💼 Extracted Salary: ₹{extracted_salary:,.0f}")
        else:
            # Fallback
            lower = content.lower()
            if "loan" in lower or "borrow" in lower: intent = "loan"
            elif "advice" in lower: intent = "advice"
            elif "kyc" in lower: intent = "kyc"
            elif "sign" in lower: intent = "sign"
            elif "pay" in lower or "payment" in lower or "repay" in lower: intent = "payment"
            
    except Exception as e:
        print(f"  ⚠️ Intent Error: {e}")
        intent = "unclear"

    if intent == 'unclear' or intent not in ['loan', 'advice', 'kyc', 'sign', 'payment']:
        cust = state.get("customer_data", {}) or {}
        name = cust.get("name", "").strip()
        
        # Check if they have past loans to acknowledge
        past_loans = cust.get("past_loans", [])
        if past_loans and not state.get("messages"):
             greeting_prompt = f"Greet the user {name if name else ''} warmly. Acknowledge that they are a valued returning customer. Mention you see their history and can help with new loans, payments, or just advice. Keep it human and warm."
        else:
             greeting_prompt = f"Greet the user {name if name else ''} warmly. Mention you can help with loans, advice, KYC, or payments. Keep it human and ask what's on their mind. Limit to 2 sentences."
        
        res = await llm.ainvoke([SystemMessage(content=greeting_prompt)])
        msg = res.content

        return {
            "intent": "unclear",
            "messages": [AIMessage(content=msg)],
            "action_log": log,
            "current_phase": "intent_discovery",
            "options": ["Apply for Loan", "Check Loan History", "Financial Advice"]
        }

    phase_map = {
        "loan": "loan_application", 
        "advice": "advice", 
        "kyc": "kyc_verification", 
        "sign": "loan_approval",
        "payment": "payment"
    }
    updates = {"intent": intent, "action_log": log, "current_phase": phase_map.get(intent)}
    
    # ─── Data Sync — Update profile if salary extracted ───
    customer_data = dict(state.get("customer_data", {}))
    if extracted_salary > 0:
        customer_data["salary"] = extracted_salary
        updates["customer_data"] = customer_data
        log.append(f"📝 Profile updated with new salary: ₹{extracted_salary:,.0f}")

    if intent == "loan":
        # Reset Logic for Re-application
        if state.get("decision") or state.get("sanction_pdf"):
            log.append("🔄 Resetting stale application state for new request.")
            updates.update({
                "decision": "", "is_signed": False, "sanction_pdf": "",
                "kyc_status": "pending", "fraud_score": -1, "documents_uploaded": False
            })
        
        if extracted_amount > 0:
            # Prime terms
            updates["loan_terms"] = {"principal": extracted_amount, "tenure": 0}

    if intent != "loan":
        updates["pending_question"] = None

    return updates

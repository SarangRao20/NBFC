"""Sales Agent — conversational sales flow to determine loan type, amount, and tenure."""

import json
import re
from typing import Optional

from config import get_master_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from mock_apis.loan_products import LOAN_PRODUCTS

# ─── System prompt ──────────────────────────────────────────────────────────────
SALES_SYSTEM_PROMPT = """You are an expert NBFC Sales Agent for FinServe NBFC.  
Your job is to understand the customer's needs and recommend the best loan product.

## Available Loan Products
{products_info}

## Your Responsibilities
1. Greet the customer warmly.
2. Recommend a suitable loan type (personal / student / business / home).
3. Help them decide on a loan amount and tenure.
4. Calculate and present EMI estimates.
5. Once confirmed, output a JSON summary.

## IMPORTANT — Confirmation & Output
When the customer has CONFIRMED their choices, you MUST end your reply with a JSON block:
```json
{{"loan_type": "<type>", "loan_amount": <number>, "tenure": <months>, "interest_rate": <rate>, "confirmed": true}}
```
"""

def _build_products_info() -> str:
    lines = []
    for key, p in LOAN_PRODUCTS.items():
        lines.append(f"### {p['name']} ({key})\n- Amount: ₹{p['min_amount']:,} – ₹{p['max_amount']:,}\n- Base Rate: {p['base_rate']}% p.a.\n")
    return "\n".join(lines)

def _extract_json_from_response(text: str) -> Optional[dict]:
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try: return json.loads(json_match.group(1))
        except: pass
    return None

def sales_chat_response(user_message: str, chat_history: list[dict]) -> dict:
    """Process a single chat turn."""
    llm = get_master_llm()
    system = SystemMessage(content=SALES_SYSTEM_PROMPT.format(products_info=_build_products_info()))

    messages = [system]
    for msg in chat_history:
        role = HumanMessage if msg["role"] == "user" else AIMessage
        messages.append(role(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    reply = response.content
    extracted = _extract_json_from_response(reply)

    return {"reply": reply, "extracted": extracted}
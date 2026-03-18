"""Sales Agent — conversational sales flow to determine loan type, amount, and tenure.

Works in two modes:
  1. **Streamlit / chat mode** — `sales_chat_response()` takes a message + history and returns
     an assistant reply along with any extracted structured data.
  2. **CLI mode** — `sales_agent_node()` is a LangGraph node that runs the full conversation
     interactively via stdin/stdout.
"""

import json
import re
from typing import Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from state import LoanState
from mock_apis.loan_products import LOAN_PRODUCTS, calculate_emi, check_eligibility

# ─── LLM ────────────────────────────────────────────────────────────────────────
llm = ChatOllama(model="llama3:8b", temperature=0.7)

# ─── System prompt ──────────────────────────────────────────────────────────────
SALES_SYSTEM_PROMPT = """You are an expert NBFC Sales Agent for FinServe NBFC.  
Your job is to understand the customer's needs and recommend the best loan product.

## Available Loan Products
{products_info}

## Your Responsibilities
1. Greet the customer warmly and ask what they need a loan for.
2. Based on their purpose, recommend a suitable loan type (personal / student / business / home).
3. Help them decide on a loan amount within the allowed range.
4. Help them choose a comfortable tenure (repayment period in months).
5. Calculate and present EMI estimates to help them decide.
6. Once the customer confirms their choice, output a JSON summary.

## Conversation Rules
- Be friendly, professional, and empathetic.
- Provide clear explanations of loan features and terms.
- If the customer is unsure, suggest options based on their situation.
- Always quote amounts in Indian Rupees (₹).
- Keep responses concise — 2-4 sentences max unless explaining EMI details.

## IMPORTANT — Confirmation & Output
When the customer has CONFIRMED their loan type, amount, and tenure, you MUST end your
reply with a JSON block on its own line (no other text on that line):

```json
{{"loan_type": "<type>", "loan_amount": <number>, "tenure": <months>, "interest_rate": <rate>, "confirmed": true}}
```

Do NOT output this JSON until the customer explicitly confirms. Until then, just converse
normally.
"""


def _build_products_info() -> str:
    """Build a human-readable product catalog for the system prompt."""
    lines = []
    for key, p in LOAN_PRODUCTS.items():
        lines.append(
            f"### {p['name']} ({key})\n"
            f"- Amount: ₹{p['min_amount']:,} – ₹{p['max_amount']:,}\n"
            f"- Tenure: {p['min_tenure']} – {p['max_tenure']} months\n"
            f"- Base Rate: {p['base_rate']}% p.a.\n"
            f"- Min Income: ₹{p['min_income']:,}/month\n"
            f"- {p['description']}\n"
            f"- Features: {', '.join(p['features'])}\n"
        )
    return "\n".join(lines)


def _extract_json_from_response(text: str) -> Optional[dict]:
    """Try to extract a JSON block from the LLM response."""
    # Look for ```json ... ``` blocks
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Fallback: look for raw JSON objects
    json_match = re.search(r'\{[^{}]*"confirmed"\s*:\s*true[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


# ─── Streamlit / Chat mode ──────────────────────────────────────────────────────

def sales_chat_response(user_message: str, chat_history: list[dict]) -> dict:
    """Process a single chat turn and return the assistant's reply + extracted data.

    Args:
        user_message: The latest message from the user.
        chat_history: List of {"role": "user"|"assistant", "content": "..."} dicts
                      (does NOT include the current user_message yet).

    Returns:
        {
            "reply": str,               # assistant's response text
            "extracted": dict | None,    # structured loan data if confirmed, else None
        }
    """
    system = SystemMessage(content=SALES_SYSTEM_PROMPT.format(products_info=_build_products_info()))

    messages = [system]
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    reply = response.content
    extracted = _extract_json_from_response(reply)

    return {"reply": reply, "extracted": extracted}


# ─── CLI / LangGraph node mode ──────────────────────────────────────────────────

def sales_agent_node(state: LoanState) -> dict:
    """LangGraph node — runs an interactive sales conversation in the terminal."""
    print("\n" + "═" * 50)
    print("  💼 SALES AGENT")
    print("  Let me help you find the perfect loan product")
    print("═" * 50)

    chat_history: list[dict] = state.get("chat_history", [])

    # Initial greeting if no history
    if not chat_history:
        greeting = (
            "Hello! 👋 Welcome to FinServe NBFC. I'm your sales advisor.\n"
            "I'd love to help you find the right loan. Could you tell me "
            "what you need the loan for?"
        )
        print(f"\n  🤖 Sales Agent: {greeting}")
        chat_history.append({"role": "assistant", "content": greeting})

    extracted = None
    while extracted is None or not extracted.get("confirmed"):
        user_input = input("\n  You: ").strip()
        if not user_input:
            continue

        result = sales_chat_response(user_input, chat_history)
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": result["reply"]})

        print(f"\n  🤖 Sales Agent: {result['reply']}")
        extracted = result.get("extracted")

    # Build state updates
    updates = {
        "current_agent": "sales",
        "chat_history": chat_history,
        "loan_type": extracted.get("loan_type", "personal"),
        "loan_amount": float(extracted.get("loan_amount", 0)),
        "tenure": int(extracted.get("tenure", 0)),
        "interest_rate": float(extracted.get("interest_rate", 0)),
    }

    print("\n" + "═" * 50)
    print("  ✅ SALES AGENT COMPLETE")
    print(f"  Loan Type:     {updates['loan_type']}")
    print(f"  Amount:        ₹{updates['loan_amount']:,.0f}")
    print(f"  Tenure:        {updates['tenure']} months")
    print(f"  Interest Rate: {updates['interest_rate']}% p.a.")
    print("═" * 50)

    return updates
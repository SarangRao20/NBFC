"""Advisor Agent — personalized financial tips based on loan decision outcome.

Provides:
  - Credit improvement tips (if rejected due to low score)
  - Lower amount suggestions (if FOIR too high)
  - Cross-sell recommendations (if approved — Gold Loan, FD, Insurance)
  - Past loan info & due date reminders
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_master_llm
from langchain_core.messages import AIMessage, SystemMessage


def advisor_agent_node(state: dict) -> dict:
    """LLM-powered financial advisor that tailors advice based on the pipeline outcome."""
    print("💡 [ADVISOR AGENT] Generating personalized advice...")

    llm = get_master_llm()
    customer = state.get("customer_data", {})
    decision = state.get("decision", "unknown")
    dti = state.get("dti_ratio", 0)
    terms = state.get("loan_terms", {})
    fraud = state.get("fraud_score", 0)

    context = f"""
Customer Profile:
- Name: {customer.get('name', 'N/A')}
- City: {customer.get('city', 'N/A')}
- Monthly Salary: ₹{customer.get('salary', 0):,}
- Credit Score: {customer.get('score', 'N/A')}
- Pre-approved Limit: ₹{customer.get('limit', 0):,}
- Current Loans: {customer.get('current_loans', 'None')}

Loan Application Result:
- Decision: {decision.upper()}
- Requested Amount: ₹{terms.get('principal', 0):,}
- EMI: ₹{terms.get('emi', 0):,.2f}
- DTI Ratio: {dti*100:.1f}%
- Fraud Score: {fraud}
"""

    system = SystemMessage(content=f"""You are a senior Financial Advisor at FinServe NBFC.
Based on the customer's loan application outcome, provide 3-4 short, actionable tips.

Rules:
- If APPROVED: Congratulate them, mention EMI dates (15th of every month), suggest cross-sell (Gold Loan, FD).
- If REJECTED due to low credit score: Give 3 specific tips to improve their CIBIL score.
- If REJECTED due to high DTI: Suggest a lower loan amount that would fit within 50% FOIR.
- If REJECTED due to fraud: Politely inform them that manual verification is needed.
- If they have existing loans, mention upcoming due dates.
- Keep it warm, concise, and professional. Use bullet points.

{context}""")

    response = llm.invoke([system])
    return {"messages": [response]}

"""Fraud Detection Agent — computes a 0-1 fraud score based on signal mismatches."""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage


def fraud_agent_node(state: dict) -> dict:
    """Rule-based fraud detection across 5 signals (no LLM needed)."""
    print("🚨 [FRAUD AGENT] Analyzing signals...")

    customer = state.get("customer_data", {})
    docs = state.get("documents", {})
    terms = state.get("loan_terms", {})

    score = 0.0
    signals = []

    # Signal 1: Name mismatch between registration & document OCR
    reg_name = (customer.get("name") or "").lower().strip()
    doc_name = (docs.get("name_extracted") or reg_name).lower().strip()
    if reg_name and doc_name and reg_name not in doc_name and doc_name not in reg_name:
        score += 0.35
        signals.append(f"⚠️ Name mismatch: Registration='{reg_name}' vs Document='{doc_name}'")

    # Signal 2: Income inflation (claimed vs OCR extracted salary)
    claimed_salary = customer.get("salary", 0)
    extracted_salary = docs.get("salary_extracted", claimed_salary)
    if extracted_salary > 0 and claimed_salary > (extracted_salary * 1.15):
        score += 0.25
        signals.append(f"⚠️ Salary inflation: Claimed ₹{claimed_salary:,} vs Document ₹{extracted_salary:,}")

    # Signal 3: Low document OCR confidence (blurry/tampered)
    confidence = docs.get("confidence", 1.0)
    if confidence < 0.60:
        score += 0.15
        signals.append(f"⚠️ Low document quality: OCR confidence {confidence:.0%}")

    # Signal 4: Risk flags from CRM (pre-existing fraud markers)
    risk_flags = customer.get("risk_flags", [])
    if risk_flags:
        score += 0.20
        signals.append(f"⚠️ CRM risk flags: {', '.join(risk_flags)}")

    # Signal 5: Abnormal loan amount (requesting > 5x monthly salary)
    principal = terms.get("principal", 0)
    if claimed_salary > 0 and principal > (claimed_salary * 60):  # 5 years salary
        score += 0.05
        signals.append(f"⚠️ Abnormally high loan request relative to income")

    score = min(round(score, 2), 1.0)

    # Build response
    if score >= 0.7:
        level = "🔴 HIGH RISK — Escalating to Manual Audit"
    elif score >= 0.4:
        level = "🟡 MEDIUM RISK — Additional verification recommended"
    else:
        level = "🟢 LOW RISK — Cleared"

    signal_text = "\n".join(signals) if signals else "No fraud signals detected."
    msg = f"🛡️ **Fraud Analysis Complete**\nFraud Score: **{score}** / 1.0 → {level}\n\n{signal_text}"

    return {"fraud_score": score, "messages": [AIMessage(content=msg)]}

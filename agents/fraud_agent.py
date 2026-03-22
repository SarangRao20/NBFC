"""Fraud Detection Agent — computes a 0-1 fraud risk score based on cross-signal analysis.

Rule-based (no LLM) for speed and auditability.
Each signal is independently scored and summed.
If score >= 0.7, escalates to manual audit.
"""

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage


# ─── Signal weights ────────────────────────────────────────────────────────────
SIGNAL_WEIGHTS = {
    "name_mismatch":       0.30,   # Registration vs OCR name doesn't match
    "income_inflation":    0.25,   # Claimed income > 15% above document salary
    "low_ocr_confidence":  0.15,   # OCR confidence < 60% (possible tamper/blur)
    "tampered_document":   0.35,   # Vision model explicitly flagged tampering
    "crm_risk_flag":       0.20,   # CRM has pre-existing fraud/risk markers
    "abnormal_loan_ratio": 0.10,   # Loan request > 5× annual salary (60 months)
    "multiple_signals":    0.10,   # Bonus if 3+ signals triggered (coordinated fraud)
}


def _token_name_match(name1: str, name2: str) -> bool:
    """Returns True if names are compatible (token overlap check — handles middle names)."""
    if not name1 or not name2:
        return True  # Can't verify → don't penalize
    t1 = set(name1.lower().split())
    t2 = set(name2.lower().split())
    shorter = t1 if len(t1) <= len(t2) else t2
    longer  = t2 if len(t1) <= len(t2) else t1
    return shorter.issubset(longer)


def fraud_agent_node(state: dict) -> dict:
    """Rule-based fraud detection with 6 independently scored signals."""
    print("🚨 [FRAUD AGENT] Analyzing fraud signals...")

    customer = state.get("customer_data", {})
    docs = state.get("documents", {})
    terms = state.get("loan_terms", {})

    score = 0.0
    signals = []
    signals_triggered = 0

    # ── Signal 1: Name mismatch (registration vs OCR) ─────────────────────────
    reg_name = (customer.get("name") or "").strip()
    doc_name = (docs.get("name_extracted") or "").strip()
    if reg_name and doc_name:
        if not _token_name_match(reg_name, doc_name):
            score += SIGNAL_WEIGHTS["name_mismatch"]
            signals_triggered += 1
            signals.append(
                f"⚠️ **Name Mismatch** (+{SIGNAL_WEIGHTS['name_mismatch']:.0%} risk)\n"
                f"   CRM: '{reg_name}' ≠ Document: '{doc_name}'\n"
                f"   Action: Require in-person ID verification"
            )

    # ── Signal 2: Income inflation (claimed vs OCR salary) ────────────────────
    claimed = customer.get("salary", 0)
    extracted = docs.get("salary_extracted", 0)
    if extracted > 0 and claimed > (extracted * 1.20):
        inflation_pct = (claimed - extracted) / extracted * 100
        score += SIGNAL_WEIGHTS["income_inflation"]
        signals_triggered += 1
        signals.append(
            f"⚠️ **Income Inflation** (+{SIGNAL_WEIGHTS['income_inflation']:.0%} risk)\n"
            f"   Claimed: ₹{claimed:,}/month vs Document: ₹{extracted:,}/month "
            f"({inflation_pct:.0f}% overstatement)\n"
            f"   Action: Request last 3 months bank statement"
        )

    # ── Signal 3: Tampered document flagged by Vision ─────────────────────────
    if docs.get("tampered"):
        score += SIGNAL_WEIGHTS["tampered_document"]
        signals_triggered += 1
        reason = docs.get("tamper_reason", "Unknown anomaly detected")
        signals.append(
            f"🚨 **Document Tampering Detected** (+{SIGNAL_WEIGHTS['tampered_document']:.0%} risk)\n"
            f"   Reason: {reason}\n"
            f"   Action: MANDATORY — Escalate to physical document verification"
        )

    # ── Signal 4: Low OCR confidence (blurry/incomplete scan) ────────────────
    confidence = docs.get("confidence", 1.0)
    if confidence < 0.60:
        score += SIGNAL_WEIGHTS["low_ocr_confidence"]
        signals_triggered += 1
        signals.append(
            f"⚠️ **Poor Document Quality** (+{SIGNAL_WEIGHTS['low_ocr_confidence']:.0%} risk)\n"
            f"   OCR confidence: {confidence:.0%} (threshold: 60%)\n"
            f"   Action: Request re-upload in better lighting"
        )

    # ── Signal 5: CRM risk flags ──────────────────────────────────────────────
    risk_flags = customer.get("risk_flags", [])
    if risk_flags:
        score += SIGNAL_WEIGHTS["crm_risk_flag"]
        signals_triggered += 1
        signals.append(
            f"🚨 **CRM Risk Flags Active** (+{SIGNAL_WEIGHTS['crm_risk_flag']:.0%} risk)\n"
            f"   Flags: {', '.join(risk_flags)}\n"
            f"   Action: Cross-check with fraud blacklist database"
        )

    # ── Signal 6: Abnormal loan-to-income ratio ───────────────────────────────
    principal = terms.get("principal", 0)
    if claimed > 0 and principal > (claimed * 60):  # > 5 years salary
        ratio = principal / claimed
        score += SIGNAL_WEIGHTS["abnormal_loan_ratio"]
        signals_triggered += 1
        signals.append(
            f"⚠️ **Abnormal Loan-to-Income Ratio** (+{SIGNAL_WEIGHTS['abnormal_loan_ratio']:.0%} risk)\n"
            f"   Requested ₹{principal:,} = {ratio:.1f}× monthly salary (threshold: 60×)\n"
            f"   Action: Enhanced income verification required"
        )

    # ── Bonus: Multiple coordinated signals ───────────────────────────────────
    if signals_triggered >= 3:
        score += SIGNAL_WEIGHTS["multiple_signals"]
        signals.append(
            f"🚨 **Coordinated Risk Pattern** (+{SIGNAL_WEIGHTS['multiple_signals']:.0%} risk)\n"
            f"   {signals_triggered} independent signals triggered simultaneously\n"
            f"   Action: MANDATORY manual audit before any disbursement"
        )

    score = min(round(score, 2), 1.0)

    # ── Risk classification ───────────────────────────────────────────────────
    if score >= 0.70:
        level = "🔴 HIGH RISK — Escalating to Manual Audit"
        escalation = "\n\n**⚡ ESCALATION TRIGGERED**: This application requires mandatory human review. Disbursement is BLOCKED until cleared by the Risk team."
    elif score >= 0.40:
        level = "🟡 MEDIUM RISK — Additional Verification Recommended"
        escalation = "\n\n**Note**: Standard processing can continue, but please re-verify the flagged documents before disbursement."
    elif score >= 0.20:
        level = "🟠 LOW-MEDIUM RISK — Minor Anomalies Noted"
        escalation = "\n\nStandard processing can proceed. Flagged items are logged for audit."
    else:
        level = "🟢 LOW RISK — Cleared for Processing"
        escalation = ""

    signal_text = "\n\n".join(signals) if signals else "✅ No fraud signals detected across all 6 checks."

    msg = (
        f"🛡️ **Fraud Analysis Complete**\n\n"
        f"**Risk Score**: {score:.2f} / 1.0 → {level}\n"
        f"**Signals Triggered**: {signals_triggered} / 6\n\n"
        f"{'─' * 40}\n\n"
        f"{signal_text}"
        f"{escalation}"
    )

    return {
        "fraud_score": score,
        "fraud_signals": signals_triggered,
        "messages": [AIMessage(content=msg)],
        "current_phase": "underwriting"
    }

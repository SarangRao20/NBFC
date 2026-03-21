"""Fraud Service — 6-signal rule-based fraud detection (Step 10)."""

from api.core.state_manager import get_session, update_session, advance_phase

SIGNAL_WEIGHTS = {
    "name_mismatch":       0.30,
    "income_inflation":    0.25,
    "low_ocr_confidence":  0.15,
    "tampered_document":   0.35,
    "crm_risk_flag":       0.20,
    "abnormal_loan_ratio": 0.10,
    "multiple_signals":    0.10,
}


def _token_name_match(name1: str, name2: str) -> bool:
    if not name1 or not name2:
        return True
    t1 = set(name1.lower().split())
    t2 = set(name2.lower().split())
    shorter = t1 if len(t1) <= len(t2) else t2
    longer = t2 if len(t1) <= len(t2) else t1
    return shorter.issubset(longer)


async def fraud_check(session_id: str) -> dict:
    """Step 10: Compute 6-signal fraud score."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    docs = state.get("documents", {})
    terms = state.get("loan_terms", {})

    score = 0.0
    signals = []
    triggered = 0

    # Signal 1: Name mismatch
    reg_name = (customer.get("name") or "").strip()
    doc_name = (docs.get("name_extracted") or "").strip()
    name_mismatch = bool(reg_name and doc_name and not _token_name_match(reg_name, doc_name))
    if name_mismatch:
        score += SIGNAL_WEIGHTS["name_mismatch"]
        triggered += 1
    signals.append({
        "signal_name": "Name Mismatch",
        "weight": SIGNAL_WEIGHTS["name_mismatch"],
        "triggered": name_mismatch,
        "detail": f"CRM='{reg_name}' vs Doc='{doc_name}'" if name_mismatch else ""
    })

    # Signal 2: Income inflation
    claimed = customer.get("salary", 0)
    extracted = docs.get("salary_extracted", 0)
    income_inflated = bool(extracted > 0 and claimed > (extracted * 1.20))
    if income_inflated:
        score += SIGNAL_WEIGHTS["income_inflation"]
        triggered += 1
    signals.append({
        "signal_name": "Income Inflation",
        "weight": SIGNAL_WEIGHTS["income_inflation"],
        "triggered": income_inflated,
        "detail": f"Claimed: ₹{claimed:,} vs Extracted: ₹{extracted:,}" if income_inflated else ""
    })

    # Signal 3: Tampered document
    tampered = bool(docs.get("tampered", False))
    if tampered:
        score += SIGNAL_WEIGHTS["tampered_document"]
        triggered += 1
    signals.append({
        "signal_name": "Document Tampering",
        "weight": SIGNAL_WEIGHTS["tampered_document"],
        "triggered": tampered,
        "detail": docs.get("tamper_reason", "") if tampered else ""
    })

    # Signal 4: Low OCR confidence
    confidence = float(docs.get("confidence", 1.0))
    low_conf = bool(confidence < 0.60)
    if low_conf:
        score += SIGNAL_WEIGHTS["low_ocr_confidence"]
        triggered += 1
    signals.append({
        "signal_name": "Low OCR Confidence",
        "weight": SIGNAL_WEIGHTS["low_ocr_confidence"],
        "triggered": low_conf,
        "detail": f"Confidence: {confidence:.0%}" if low_conf else ""
    })

    # Signal 5: CRM risk flags
    risk_flags = customer.get("risk_flags", [])
    has_flags = bool(len(risk_flags) > 0)
    if has_flags:
        score += SIGNAL_WEIGHTS["crm_risk_flag"]
        triggered += 1
    signals.append({
        "signal_name": "CRM Risk Flags",
        "weight": SIGNAL_WEIGHTS["crm_risk_flag"],
        "triggered": has_flags,
        "detail": ", ".join(risk_flags) if has_flags else ""
    })

    # Signal 6: Abnormal loan-to-income ratio
    principal = terms.get("principal", 0)
    abnormal = bool(claimed > 0 and principal > (claimed * 60))
    if abnormal:
        score += SIGNAL_WEIGHTS["abnormal_loan_ratio"]
        triggered += 1
    signals.append({
        "signal_name": "Abnormal Loan-to-Income",
        "weight": SIGNAL_WEIGHTS["abnormal_loan_ratio"],
        "triggered": abnormal,
        "detail": f"₹{principal:,} = {principal/claimed:.1f}× salary" if abnormal else ""
    })

    # Bonus: Multiple signals
    if triggered >= 3:
        score += SIGNAL_WEIGHTS["multiple_signals"]

    score = min(round(score, 2), 1.0)

    # Risk level
    if score >= 0.70:
        risk_level = "HIGH"
        escalation = True
    elif score >= 0.40:
        risk_level = "MEDIUM"
        escalation = False
    else:
        risk_level = "LOW"
        escalation = False

    await update_session(session_id, {
        "fraud_score": score,
        "fraud_signals": triggered,
        "fraud_details": [s["signal_name"] for s in signals if s["triggered"]],
    })
    await advance_phase(session_id, "fraud_checked")

    return {
        "fraud_score": score,
        "risk_level": risk_level,
        "signals_triggered": triggered,
        "signals": signals,
        "escalation_required": escalation,
        "message": f"Fraud score: {score:.2f}/1.0 — {risk_level} RISK. {triggered}/6 signals triggered."
    }

"""KYC Service — cross-check customer vs document data (Step 9)."""

from api.core.state_manager import get_session, update_session, advance_phase


async def kyc_verify(session_id: str) -> dict:
    """Step 9: KYC Verification — name cross-check, tamper flag, document status."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = state.get("customer_data", {})
    docs = state.get("documents", {})

    reg_name = (customer.get("name") or "").strip().lower()
    doc_name = (docs.get("name_extracted") or "").strip().lower()
    doc_verified = docs.get("verified", False)

    issues = []

    if not doc_verified:
        issues.append("Document has not been verified yet.")

    # Token overlap name match
    if reg_name and doc_name:
        reg_tokens = set(reg_name.split())
        doc_tokens = set(doc_name.split())
        shorter = reg_tokens if len(reg_tokens) <= len(doc_tokens) else doc_tokens
        longer = doc_tokens if len(reg_tokens) <= len(doc_tokens) else reg_tokens
        if not shorter.issubset(longer):
            issues.append(
                f"Name mismatch: CRM='{customer.get('name')}' vs Document='{docs.get('name_extracted')}'"
            )

    if docs.get("tampered"):
        issues.append("Document flagged as potentially tampered by OCR analysis.")

    kyc_status = "failed" if issues else "verified"
    await update_session(session_id, {"kyc_status": kyc_status, "kyc_issues": issues})
    await advance_phase(session_id, "kyc_verified")

    if issues:
        return {
            "kyc_status": "failed",
            "issues": issues,
            "message": "KYC verification failed. Please re-upload correct documents."
        }

    return {
        "kyc_status": "verified",
        "issues": [],
        "message": f"KYC verified successfully for {customer.get('name', 'N/A')}."
    }

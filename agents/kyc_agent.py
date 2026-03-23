"""KYC Verification Agent — cross-checks customer data against CRM records."""

import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage


from api.core.websockets import manager

async def verification_agent_node(state: dict) -> dict:
    """Verifies KYC: checks that document-extracted name matches CRM records."""
    session_id = state.get("session_id", "default")
    await manager.broadcast_thinking(session_id, "KYC Agent", True)
    
    print("✅ [VERIFICATION AGENT] Cross-checking CRM...")
    
    log = list(state.get("action_log") or [])
    log.append("✅ Verification Agent: Cross-checking CRM and Document data...")

    customer = state.get("customer_data", {})
    docs = state.get("documents", {})

    reg_name = (customer.get("name") or "").strip().lower()
    doc_name = (docs.get("name_extracted") or "").strip().lower()
    doc_verified = docs.get("verified", False)

    issues = []

    if not doc_verified:
        issues.append("Document has not been verified yet.")
        log.append("⚠️ Document verification pending.")

    if reg_name and doc_name:
        # Token overlap: all tokens from shorter name must exist in longer name's tokens
        reg_tokens = set(reg_name.split())
        doc_tokens = set(doc_name.split())
        shorter = reg_tokens if len(reg_tokens) <= len(doc_tokens) else doc_tokens
        longer = doc_tokens if len(reg_tokens) <= len(doc_tokens) else reg_tokens
        if not shorter.issubset(longer):
            issues.append(f"Name mismatch: CRM='{customer.get('name')}' vs Document='{docs.get('name_extracted')}'")
            log.append(f"❌ Name mismatch detected: {customer.get('name')} vs {docs.get('name_extracted')}")
        else:
            log.append("✅ Identity Name Match confirmed.")

    if docs.get("tampered"):
        issues.append("Document flagged as potentially tampered by OCR analysis.")
        log.append("🚨 TAMPER ALERT: Forensic scan flagged anomalies.")

    # 3-Layer Document Type Verification
    terms = state.get("loan_terms", {})
    principal = terms.get("principal", 0)
    pre_approved = customer.get("pre_approved_limit", 0)
    if not pre_approved or pre_approved <= 0:
        pre_approved = 150000

    doc_type = docs.get("document_type", "").lower()

    if principal > pre_approved:
        if "salary slip" not in doc_type:
            issues.append(f"High-value loan requested (₹{principal:,} > Limit ₹{pre_approved:,}). A Salary Slip is mandatory, but received '{docs.get('document_type')}'.")
            log.append(f"⚠️ Mandatory Salary Slip missing for ₹{principal:,} loan.")
    else:
        if "pan" not in doc_type and "aadhaar" not in doc_type:
            issues.append(f"Identity verification required for regular loans. Please upload PAN Card or Aadhaar Card. Received '{docs.get('document_type')}'.")
            log.append("⚠️ Identity document missing.")

    if issues:
        issue_text = "\n".join(f"  • {i}" for i in issues)
        msg = f"⚠️ **KYC Verification Issues Found:**\n{issue_text}\n\nPlease re-upload correct documents."
        log.append("❌ KYC verification failed.")
        await manager.broadcast_thinking(session_id, "KYC Agent", False)
        return {
            "kyc_status": "failed", 
            "messages": [AIMessage(content=msg)],
            "action_log": log,
            "options": ["Re-upload Document", "Need help?", "Exit"],
            "current_phase": "kyc_verification"
        }

    # Update permanent customer profile with verified info
    updated_customer = {**customer}
    if docs.get("address_extracted"):
        updated_customer["address"] = docs["address_extracted"]
    if docs.get("dob_extracted"):
        updated_customer["dob"] = docs["dob_extracted"]
    if docs.get("document_number"):
        updated_customer["id_number"] = docs["document_number"]

    msg = (
        f"✅ **KYC Verified Successfully!**\n"
        f"- Name: {customer.get('name', 'N/A')} ✓\n"
        f"- Document Type: {docs.get('document_type', 'N/A')} ✓\n"
        f"- Profile Updated: Address & ID verified ✓\n"
        f"- OCR Confidence: {docs.get('confidence', 0):.0%} ✓"
    )
    log.append("✅ KYC verification successful. All checks passed.")
    await manager.broadcast_thinking(session_id, "KYC Agent", False)
    return {
        "kyc_status": "verified", 
        "customer_data": updated_customer,
        "messages": [AIMessage(content=msg)],
        "action_log": log,
        "options": ["Proceed to Fraud Screening", "About My Privacy", "Exit"],
        "current_phase": "fraud_check"
    }

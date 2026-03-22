"""KYC Verification Agent — cross-checks customer data against CRM records."""

import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage


def verification_agent_node(state: dict) -> dict:
    """Verifies KYC: checks that document-extracted name matches CRM records."""
    print("✅ [VERIFICATION AGENT] Cross-checking CRM...")

    customer = state.get("customer_data", {})
    docs = state.get("documents", {})

    reg_name = (customer.get("name") or "").strip().lower()
    doc_name = (docs.get("name_extracted") or "").strip().lower()
    doc_verified = docs.get("verified", False)

    issues = []

    if not doc_verified:
        issues.append("Document has not been verified yet.")

    if reg_name and doc_name:
        # Token overlap: all tokens from shorter name must exist in longer name's tokens
        reg_tokens = set(reg_name.split())
        doc_tokens = set(doc_name.split())
        shorter = reg_tokens if len(reg_tokens) <= len(doc_tokens) else doc_tokens
        longer = doc_tokens if len(reg_tokens) <= len(doc_tokens) else reg_tokens
        if not shorter.issubset(longer):
            issues.append(f"Name mismatch: CRM='{customer.get('name')}' vs Document='{docs.get('name_extracted')}'")

    if docs.get("tampered"):
        issues.append("Document flagged as potentially tampered by OCR analysis.")

    if issues:
        issue_text = "\n".join(f"  • {i}" for i in issues)
        msg = f"⚠️ **KYC Verification Issues Found:**\n{issue_text}\n\nPlease re-upload correct documents."
        return {"kyc_status": "failed", "messages": [AIMessage(content=msg)]}

    msg = (
        f"✅ **KYC Verified Successfully!**\n"
        f"- Name: {customer.get('name', 'N/A')} ✓\n"
        f"- Document Type: {docs.get('document_type', 'N/A')} ✓\n"
        f"- OCR Confidence: {docs.get('confidence', 0):.0%} ✓"
    )
    return {"kyc_status": "verified", "messages": [AIMessage(content=msg)]}

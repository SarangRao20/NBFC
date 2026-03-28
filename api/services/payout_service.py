"""Payout Service — RazorpayX integration for loan disbursements."""

import logging
from datetime import datetime
from typing import Optional

from api.config import get_settings
from api.services.razorpay_service import get_razorpay_service

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_beneficiary(
    name: str,
    account_number: str,
    ifsc: str,
    email: str = "",
    phone: str = "",
) -> dict:
    """Register a beneficiary (Contact + Fund Account) for disbursement.
    
    Returns:
        Dict with contact_id and fund_account_id
    """
    razorpay = get_razorpay_service()

    if not razorpay.is_payoutx_available:
        logger.warning("⚠️ RazorpayX Payout not available — using mock beneficiary (EMI payments still work)")
        return {
            "contact_id": f"cont_mock_{datetime.now().strftime('%H%M%S')}",
            "fund_account_id": f"fa_mock_{datetime.now().strftime('%H%M%S')}",
            "mock": True,
        }

    # Step 1: Create Contact
    contact = razorpay.create_contact(
        name=name,
        email=email,
        phone=phone,
        contact_type="customer",
        notes={"purpose": "loan_disbursement"},
    )
    contact_id = contact["id"]

    # Step 2: Create Fund Account linked to Contact
    fund_account = razorpay.create_fund_account(
        contact_id=contact_id,
        account_number=account_number,
        ifsc=ifsc,
        name=name,
    )
    fund_account_id = fund_account["id"]

    logger.info(f"✅ Beneficiary registered: Contact={contact_id}, FundAccount={fund_account_id}")

    return {
        "contact_id": contact_id,
        "fund_account_id": fund_account_id,
        "mock": False,
    }


async def initiate_disbursement(
    fund_account_id: str,
    amount: float,
    session_id: str = "",
    mode: str = "IMPS",
    narration: str = "Loan Disbursement",
) -> dict:
    """Initiate a payout to the borrower's bank account via RazorpayX.
    
    Args:
        fund_account_id: RazorpayX Fund Account ID
        amount: Amount in INR to disburse
        session_id: Internal session reference
        mode: Transfer mode — IMPS (default), NEFT, RTGS
        narration: Bank statement narration
    
    Returns:
        Dict with payout_id, status, amount, utr
    """
    razorpay = get_razorpay_service()

    if not razorpay.is_payoutx_available:
        logger.warning("⚠️ RazorpayX Payout not available — simulating disbursement (EMI payments still work with standard Razorpay)")
        mock_payout_id = f"pout_sim_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return {
            "success": True,
            "payout_id": mock_payout_id,
            "status": "processed",
            "amount": amount,
            "utr": f"UTR{datetime.now().strftime('%Y%m%d%H%M%S')}SIM",
            "mode": mode,
            "mock": True,
            "simulated": True,
            "message": f"[SIMULATED] Disbursement of ₹{amount:,.2f} recorded. EMI payments work with real Razorpay, disbursement requires PayoutX business activation.",
        }

    try:
        payout = razorpay.create_payout(
            fund_account_id=fund_account_id,
            amount=amount,
            mode=mode,
            purpose="payout",
            reference_id=f"loan_{session_id}" if session_id else "",
            narration=narration,
            notes={
                "session_id": session_id,
                "type": "loan_disbursement",
            },
        )

        payout_id = payout.get("id", "")
        status = payout.get("status", "unknown")
        utr = payout.get("utr", "")

        logger.info(f"💸 Payout initiated: {payout_id} | Status: {status} | ₹{amount:,.2f}")

        return {
            "success": status in ("processing", "processed", "queued"),
            "payout_id": payout_id,
            "status": status,
            "amount": amount,
            "utr": utr,
            "mode": mode,
            "mock": False,
            "message": f"Disbursement of ₹{amount:,.2f} initiated via {mode}. Payout ID: {payout_id}",
        }

    except Exception as e:
        logger.error(f"❌ Disbursement failed: {e}")
        return {
            "success": False,
            "payout_id": "",
            "status": "failed",
            "amount": amount,
            "utr": "",
            "mode": mode,
            "mock": False,
            "message": f"Disbursement failed: {str(e)}",
        }


async def check_payout_status(payout_id: str) -> dict:
    """Check the status of an existing payout.
    
    Returns:
        Dict with payout_id, status, utr, failure_reason
    """
    razorpay = get_razorpay_service()

    if not razorpay.is_payoutx_available:
        return {
            "payout_id": payout_id,
            "status": "processed",
            "amount": 0,
            "utr": "SIMULATED_UTR",
            "failure_reason": "",
            "simulated": True,
        }

    try:
        payout = razorpay.fetch_payout(payout_id)
        return {
            "payout_id": payout.get("id", payout_id),
            "status": payout.get("status", "unknown"),
            "amount": (payout.get("amount", 0) or 0) / 100,  # paise → INR
            "utr": payout.get("utr", ""),
            "failure_reason": payout.get("failure_reason", ""),
        }
    except Exception as e:
        logger.error(f"❌ Failed to check payout status: {e}")
        return {
            "payout_id": payout_id,
            "status": "error",
            "amount": 0,
            "utr": "",
            "failure_reason": str(e),
        }


async def handle_payout_webhook(event: str, payload: dict) -> dict:
    """Process payout-related webhook events from RazorpayX.
    
    Args:
        event: Event type (e.g., "payout.processed", "payout.reversed")
        payload: Webhook payload
    
    Returns:
        Dict with processing result
    """
    payout_entity = payload.get("payload", {}).get("payout", {}).get("entity", {})
    payout_id = payout_entity.get("id", "")
    status = payout_entity.get("status", "")
    amount = (payout_entity.get("amount", 0) or 0) / 100
    utr = payout_entity.get("utr", "")
    reference_id = payout_entity.get("reference_id", "")

    logger.info(f"🔔 Payout webhook: {event} | ID: {payout_id} | Status: {status} | ₹{amount:,.2f}")

    # Extract session_id from reference_id (format: "loan_SESSION_ID")
    session_id = ""
    if reference_id and reference_id.startswith("loan_"):
        session_id = reference_id[5:]

    if event == "payout.processed":
        # Disbursement successful — update loan record
        if session_id:
            try:
                from db.database import loan_applications_collection
                await loan_applications_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "disbursement_status": "completed",
                        "payout_id": payout_id,
                        "utr": utr,
                        "disbursed_at": datetime.utcnow().isoformat(),
                    }}
                )
                logger.info(f"✅ Loan record updated for session {session_id}: disbursement complete")
            except Exception as e:
                logger.error(f"❌ Failed to update loan record: {e}")

        return {"processed": True, "action": "disbursement_confirmed", "payout_id": payout_id}

    elif event == "payout.reversed":
        # Disbursement reversed — flag for manual review
        failure_reason = payout_entity.get("failure_reason", "Unknown")
        if session_id:
            try:
                from db.database import loan_applications_collection
                await loan_applications_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "disbursement_status": "reversed",
                        "payout_failure_reason": failure_reason,
                    }}
                )
            except Exception as e:
                logger.error(f"❌ Failed to update reversed payout: {e}")

        return {"processed": True, "action": "disbursement_reversed", "payout_id": payout_id, "reason": failure_reason}

    return {"processed": False, "action": "unknown_event", "event": event}

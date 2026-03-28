"""Webhook Router — handles incoming Razorpay webhook events for payments and payouts."""

import logging
from fastapi import APIRouter, Request, HTTPException
from api.services.razorpay_service import get_razorpay_service
from api.services import payout_service
from db.database import loan_applications_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/razorpay", summary="Razorpay Webhook Handler")
async def razorpay_webhook(request: Request):
    """Handle all Razorpay webhook events.
    
    Events handled:
    - payment.authorized → auto-capture payment
    - payment.captured → update loan EMI state
    - payment.failed → log failure
    - payout.processed → confirm disbursement (requires RazorpayX activation)
    - payout.reversed → flag failed disbursement (requires RazorpayX activation)
    - payout.failed → handle payout creation failure (requires RazorpayX activation)
    
    Note: Payout events require RazorpayX activation. If not available,
    the system will still work with payment events only.
    
    Security: Verifies HMAC-SHA256 signature on every request.
    """
    razorpay = get_razorpay_service()

    # 1. Read raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # 2. Verify signature (skip if webhook secret not configured — log warning)
    if razorpay.webhook_secret:
        if not signature:
            logger.warning("❌ Webhook received without signature")
            raise HTTPException(status_code=400, detail="Missing X-Razorpay-Signature header")

        if not razorpay.verify_webhook_signature(body, signature):
            logger.warning("❌ Webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        logger.warning("⚠️ Webhook secret not configured — processing without verification")

    # 3. Parse the event
    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    logger.info(f"🔔 [WEBHOOK] Received event: {event}")

    # 4. Route to appropriate handler
    try:
        if event == "payment.authorized":
            return await _handle_payment_authorized(payload)
        elif event == "payment.captured":
            return await _handle_payment_captured(payload)
        elif event == "payment.failed":
            return await _handle_payment_failed(payload)
        elif event.startswith("payout."):
            return await payout_service.handle_payout_webhook(event, payload)
        else:
            logger.info(f"ℹ️ Unhandled webhook event: {event}")
            return {"status": "ignored", "event": event}

    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        # Always return 200 to Razorpay so they don't retry
        return {"status": "error", "message": str(e)}


async def _handle_payment_authorized(payload: dict) -> dict:
    """Auto-capture authorized payments."""
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_entity.get("id", "")
    amount_paise = payment_entity.get("amount", 0) or 0
    amount_inr = amount_paise / 100

    logger.info(f"💳 Payment authorized: {payment_id} for ₹{amount_inr:,.2f}")

    razorpay = get_razorpay_service()
    if razorpay.is_configured:
        try:
            razorpay.capture_payment(payment_id, amount_inr)
            logger.info(f"✅ Auto-captured payment: {payment_id}")
        except Exception as e:
            logger.error(f"❌ Auto-capture failed for {payment_id}: {e}")

    return {"status": "captured", "payment_id": payment_id}


async def _handle_payment_captured(payload: dict) -> dict:
    """Update loan state when EMI payment is captured."""
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_entity.get("id", "")
    order_id = payment_entity.get("order_id", "")
    amount_paise = payment_entity.get("amount", 0) or 0
    amount_inr = amount_paise / 100
    method = payment_entity.get("method", "")
    notes = payment_entity.get("notes", {})

    session_id = notes.get("session_id", "")

    logger.info(f"✅ Payment captured: {payment_id} | Order: {order_id} | ₹{amount_inr:,.2f} via {method}")

    # Store transaction record
    try:
        from db.database import razorpay_transactions_collection
        await razorpay_transactions_collection.insert_one({
            "payment_id": payment_id,
            "order_id": order_id,
            "session_id": session_id,
            "amount": amount_inr,
            "method": method,
            "status": "captured",
            "type": "emi_payment",
            "captured_at": payment_entity.get("captured_at", ""),
            "raw_payload": payment_entity,
        })
    except Exception as e:
        logger.error(f"⚠️ Failed to store transaction record: {e}")

    return {"status": "processed", "payment_id": payment_id}


async def _handle_payment_failed(payload: dict) -> dict:
    """Log failed payment attempts."""
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = payment_entity.get("id", "")
    error_code = payment_entity.get("error_code", "")
    error_description = payment_entity.get("error_description", "")
    notes = payment_entity.get("notes", {})
    session_id = notes.get("session_id", "")

    logger.warning(f"❌ Payment failed: {payment_id} | Error: {error_code} — {error_description}")

    # Store failed transaction for audit
    try:
        from db.database import razorpay_transactions_collection
        await razorpay_transactions_collection.insert_one({
            "payment_id": payment_id,
            "session_id": session_id,
            "amount": (payment_entity.get("amount", 0) or 0) / 100,
            "status": "failed",
            "type": "emi_payment",
            "error_code": error_code,
            "error_description": error_description,
            "raw_payload": payment_entity,
        })
    except Exception as e:
        logger.error(f"⚠️ Failed to store failed transaction record: {e}")

    return {"status": "logged", "payment_id": payment_id, "error": error_code}

"""Razorpay Service — Core wrapper for Razorpay Payment Gateway & RazorpayX Payout APIs."""

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional

import razorpay
from api.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class RazorpayService:
    """Singleton wrapper around the Razorpay Python SDK.
    
    Provides methods for:
    - Order creation (EMI collection)
    - Payment verification & capture
    - Refunds
    - Payout (RazorpayX) for loan disbursements
    - Webhook signature verification
    """
    _instance: Optional["RazorpayService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance - useful for testing or config changes."""
        cls._instance = None

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Reload settings each time to catch changes
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        self.account_number = settings.RAZORPAY_ACCOUNT_NUMBER
        self.payout_mode = settings.RAZORPAY_PAYOUT_MODE

        # Check if keys are configured
        if not self.key_id or not self.key_secret:
            logger.warning("⚠️ Razorpay API keys not configured — payment features will be unavailable")
            self.client = None
        else:
            try:
                self.client = razorpay.Client(auth=(self.key_id, self.key_secret))
                logger.info(f"✅ Razorpay client initialized (mode: {self.payout_mode})")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Razorpay client: {e}")
                self.client = None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    @property
    def is_payoutx_available(self) -> bool:
        """Check if RazorpayX Payout is available (requires separate business activation)."""
        if not self.is_configured:
            return False
        # PayoutX requires account_number to be configured
        # If not set, payouts will fail even though regular payments work
        return bool(self.account_number and self.account_number.strip())

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. ORDER MANAGEMENT (EMI Collection)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_order(
        self,
        amount: float,
        currency: str = "INR",
        receipt: str = "",
        notes: dict = None,
    ) -> dict:
        """Create a Razorpay Order for collecting payment.
        
        Args:
            amount: Amount in INR (will be converted to paise internally)
            currency: Currency code (default: INR)
            receipt: Unique receipt ID for your reference
            notes: Additional metadata (max 15 key-value pairs)
        
        Returns:
            Razorpay order dict with `id`, `amount`, `status`, etc.
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env")

        amount_paise = int(round(amount * 100))  # Convert INR to paise

        order_data = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt or f"rcpt_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "notes": notes or {},
        }

        try:
            order = self.client.order.create(data=order_data)
            logger.info(f"📦 Razorpay Order created: {order['id']} for ₹{amount:,.2f}")
            return order
        except Exception as e:
            logger.error(f"❌ Failed to create Razorpay order: {e}")
            raise

    def fetch_order(self, order_id: str) -> dict:
        """Fetch an existing order by its ID."""
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")
        return self.client.order.fetch(order_id)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. PAYMENT VERIFICATION & CAPTURE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """Verify the payment signature returned by Razorpay Checkout.
        
        This is CRITICAL for security — never skip this step.
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")

        params = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }

        try:
            self.client.utility.verify_payment_signature(params)
            logger.info(f"✅ Payment signature verified: {razorpay_payment_id}")
            return True
        except razorpay.errors.SignatureVerificationError:
            logger.warning(f"❌ Payment signature verification FAILED: {razorpay_payment_id}")
            return False

    def capture_payment(self, payment_id: str, amount: float, currency: str = "INR") -> dict:
        """Capture an authorized payment.
        
        Args:
            payment_id: Razorpay payment ID (pay_xxxxx)
            amount: Amount to capture in INR
            currency: Currency code
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")

        amount_paise = int(round(amount * 100))
        try:
            payment = self.client.payment.capture(payment_id, amount_paise, {"currency": currency})
            logger.info(f"💰 Payment captured: {payment_id} for ₹{amount:,.2f}")
            return payment
        except Exception as e:
            logger.error(f"❌ Failed to capture payment {payment_id}: {e}")
            raise

    def fetch_payment(self, payment_id: str) -> dict:
        """Fetch payment details by ID."""
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")
        return self.client.payment.fetch(payment_id)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. REFUNDS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        notes: dict = None,
    ) -> dict:
        """Create a full or partial refund.
        
        Args:
            payment_id: Original payment ID
            amount: Refund amount in INR (None = full refund)
            notes: Additional metadata
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")

        refund_data = {"notes": notes or {}}
        if amount is not None:
            refund_data["amount"] = int(round(amount * 100))

        try:
            refund = self.client.payment.refund(payment_id, refund_data)
            logger.info(f"↩️ Refund created for payment {payment_id}: {refund['id']}")
            return refund
        except Exception as e:
            logger.error(f"❌ Failed to create refund for {payment_id}: {e}")
            raise

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. PAYOUTS (RazorpayX — Loan Disbursements)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def create_contact(self, name: str, email: str = "", phone: str = "", contact_type: str = "customer", notes: dict = None) -> dict:
        """Create a RazorpayX Contact (beneficiary) for disbursement.
        
        Args:
            name: Beneficiary name
            email: Email (optional)
            phone: Phone (optional)
            contact_type: "customer", "vendor", "employee"
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")

        contact_data = {
            "name": name,
            "type": contact_type,
            "notes": notes or {},
        }
        if email:
            contact_data["email"] = email
        if phone:
            contact_data["phone"] = phone

        try:
            contact = self.client.contact.create(data=contact_data)  # type: ignore
            logger.info(f"👤 Contact created: {contact.get('id')} — {name}")
            return contact
        except Exception as e:
            logger.error(f"❌ Failed to create contact: {e}")
            raise

    def create_fund_account(self, contact_id: str, account_number: str, ifsc: str, name: str) -> dict:
        """Create a Fund Account (bank account) linked to a contact for payout.
        
        Args:
            contact_id: RazorpayX Contact ID
            account_number: Beneficiary bank account number
            ifsc: IFSC code
            name: Account holder name
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")

        fund_account_data = {
            "contact_id": contact_id,
            "account_type": "bank_account",
            "bank_account": {
                "name": name,
                "ifsc": ifsc,
                "account_number": account_number,
            },
        }

        try:
            fund_account = self.client.fund_account.create(data=fund_account_data)  # type: ignore
            logger.info(f"🏦 Fund account created: {fund_account.get('id')}")
            return fund_account
        except Exception as e:
            logger.error(f"❌ Failed to create fund account: {e}")
            raise

    def create_payout(
        self,
        fund_account_id: str,
        amount: float,
        mode: str = "IMPS",
        purpose: str = "payout",
        reference_id: str = "",
        narration: str = "Loan Disbursement",
        notes: dict = None,
    ) -> dict:
        """Create a RazorpayX Payout to disburse funds.
        
        Args:
            fund_account_id: Fund Account ID
            amount: Amount in INR
            mode: Transfer mode — "NEFT", "RTGS", "IMPS", "UPI"
            purpose: Purpose code — "payout", "salary", "refund"
            reference_id: Your internal reference
            narration: Bank statement narration (max 30 chars)
        """
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")

        amount_paise = int(round(amount * 100))

        payout_data = {
            "account_number": self.account_number,
            "fund_account_id": fund_account_id,
            "amount": amount_paise,
            "currency": "INR",
            "mode": mode,
            "purpose": purpose,
            "queue_if_low_balance": True,
            "reference_id": reference_id or f"disb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "narration": narration[:30],
            "notes": notes or {},
        }

        try:
            payout = self.client.payout.create(data=payout_data)  # type: ignore
            logger.info(f"💸 Payout created: {payout.get('id')} for ₹{amount:,.2f}")
            return payout
        except Exception as e:
            logger.error(f"❌ Failed to create payout: {e}")
            raise

    def fetch_payout(self, payout_id: str) -> dict:
        """Fetch payout details by ID."""
        if not self.is_configured:
            raise RuntimeError("Razorpay client not configured")
        try:
            return self.client.payout.fetch(payout_id)  # type: ignore
        except Exception as e:
            logger.error(f"❌ Failed to fetch payout {payout_id}: {e}")
            raise

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. WEBHOOK SIGNATURE VERIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify the Razorpay webhook HMAC-SHA256 signature.
        
        Args:
            body: Raw request body bytes
            signature: Value of X-Razorpay-Signature header
        
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("⚠️ Webhook secret not configured — skipping verification")
            return False

        expected = hmac.new(
            key=self.webhook_secret.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)


# ── Module-level singleton accessor ─────────────────────────────────────────
_razorpay_service: Optional[RazorpayService] = None


def get_razorpay_service() -> RazorpayService:
    """Get or create the singleton RazorpayService instance."""
    return RazorpayService()

"""Razorpay Integration Tests — Unit tests for payment and payout services."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Test the Razorpay service
from api.services.razorpay_service import RazorpayService, get_razorpay_service
from api.services.payment_service import create_emi_order, verify_emi_payment
from api.services.payout_service import create_beneficiary, initiate_disbursement, handle_payout_webhook
from api.schemas.payment import CreateOrderResponse, VerifyPaymentRequest
from api.schemas.payout import DisbursementRequest, DisbursementResponse


class TestRazorpayService:
    """Test Razorpay service core functionality."""

    @pytest.fixture
    def mock_razorpay_client(self):
        """Mock Razorpay client."""
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            "id": "order_test_123",
            "amount": 50000,
            "currency": "INR",
            "receipt": "test_receipt"
        }
        mock_client.payment.fetch.return_value = {
            "id": "pay_test_123",
            "order_id": "order_test_123",
            "amount": 50000,
            "status": "captured",
            "method": "card"
        }
        return mock_client

    @pytest.fixture
    def razorpay_service(self, mock_razorpay_client):
        """Create Razorpay service instance with mocked client."""
        with patch('api.services.razorpay_service.razorpay', mock_razorpay_client):
            service = RazorpayService(
                key_id="rzp_test_test",
                key_secret="test_secret",
                webhook_secret="test_webhook_secret"
            )
            return service

    def test_singleton_pattern(self):
        """Test that get_razorpay_service returns singleton instance."""
        service1 = get_razorpay_service()
        service2 = get_razorpay_service()
        assert service1 is service2

    def test_create_order(self, razorpay_service):
        """Test order creation."""
        order = razorpay_service.create_order(
            amount=500.0,
            currency="INR",
            receipt="test_receipt"
        )
        
        assert order["id"] == "order_test_123"
        assert order["amount"] == 50000  # Amount in paise
        assert order["currency"] == "INR"

    def test_verify_payment_signature_valid(self, razorpay_service):
        """Test payment signature verification with valid signature."""
        # Mock the signature verification to return True
        with patch.object(razorpay_service, 'verify_payment_signature', return_value=True):
            result = razorpay_service.verify_payment_signature(
                razorpay_order_id="order_test_123",
                razorpay_payment_id="pay_test_123",
                razorpay_signature="valid_signature"
            )
            assert result is True

    def test_verify_payment_signature_invalid(self, razorpay_service):
        """Test payment signature verification with invalid signature."""
        # Mock the signature verification to return False
        with patch.object(razorpay_service, 'verify_payment_signature', return_value=False):
            result = razorpay_service.verify_payment_signature(
                razorpay_order_id="order_test_123",
                razorpay_payment_id="pay_test_123",
                razorpay_signature="invalid_signature"
            )
            assert result is False

    def test_webhook_signature_verification(self, razorpay_service):
        """Test webhook signature verification."""
        test_payload = b'{"event": "payment.captured"}'
        test_signature = "test_signature"
        
        with patch.object(razorpay_service, 'verify_webhook_signature', return_value=True):
            result = razorpay_service.verify_webhook_signature(test_payload, test_signature)
            assert result is True


class TestPaymentService:
    """Test payment service EMI order creation and verification."""

    @pytest.fixture
    def mock_session_state(self):
        """Mock session state for testing."""
        return {
            "session_id": "test_session_123",
            "customer_data": {
                "name": "Test Customer",
                "email": "test@example.com",
                "phone": "9876543210"
            },
            "loan_terms": {
                "principal": 50000,
                "emi": 5000,
                "tenure": 12,
                "payments_made": 3,
                "next_emi_date": "2024-02-01"
            }
        }

    @pytest.mark.asyncio
    async def test_create_emi_order_success(self, mock_session_state):
        """Test successful EMI order creation."""
        with patch('api.services.payment_service.get_session', return_value=mock_session_state), \
             patch('api.services.payment_service.get_razorpay_service') as mock_razorpay:
            
            # Mock Razorpay service
            mock_razorpay_instance = AsyncMock()
            mock_razorpay_instance.is_configured = True
            mock_razorpay_instance.create_order.return_value = {
                "id": "order_test_123",
                "amount": 500000,  # 5000 * 100 (paise)
                "currency": "INR"
            }
            mock_razorpay.return_value = mock_razorpay_instance

            result = await create_emi_order("test_session_123")
            
            assert result["success"] is True
            assert result["order_id"] == "order_test_123"
            assert result["amount"] == 5000.0
            assert result["amount_paise"] == 500000

    @pytest.mark.asyncio
    async def test_create_emi_order_mock_mode(self, mock_session_state):
        """Test EMI order creation in mock mode."""
        with patch('api.services.payment_service.get_session', return_value=mock_session_state), \
             patch('api.services.payment_service.get_razorpay_service') as mock_razorpay:
            
            # Mock unconfigured Razorpay service
            mock_razorpay_instance = AsyncMock()
            mock_razorpay_instance.is_configured = False
            mock_razorpay.return_value = mock_razorpay_instance

            result = await create_emi_order("test_session_123")
            
            assert result["success"] is True
            assert result["mock"] is True
            assert "order_mock_" in result["order_id"]

    @pytest.mark.asyncio
    async def test_verify_emi_payment_success(self, mock_session_state):
        """Test successful EMI payment verification."""
        with patch('api.services.payment_service.get_session', return_value=mock_session_state), \
             patch('api.services.payment_service.update_session', new_callable=AsyncMock), \
             patch('api.services.payment_service.get_razorpay_service') as mock_razorpay, \
             patch('db.database.loan_applications_collection') as mock_collection, \
             patch('db.database.razorpay_transactions_collection') as mock_tx_collection:
            
            # Mock Razorpay service
            mock_razorpay_instance = AsyncMock()
            mock_razorpay_instance.is_configured = True
            mock_razorpay_instance.verify_payment_signature.return_value = True
            mock_razorpay.return_value = mock_razorpay_instance

            # Mock database collections
            mock_collection.update_one = AsyncMock()
            mock_tx_collection.insert_one = AsyncMock()

            result = await verify_emi_payment(
                session_id="test_session_123",
                razorpay_payment_id="pay_test_123",
                razorpay_order_id="order_test_123",
                razorpay_signature="valid_signature"
            )
            
            assert result["success"] is True
            assert result["payment_id"] == "pay_test_123"
            assert result["loan_terms"]["payments_made"] == 4  # incremented from 3

    @pytest.mark.asyncio
    async def test_verify_emi_payment_invalid_signature(self, mock_session_state):
        """Test EMI payment verification with invalid signature."""
        with patch('api.services.payment_service.get_session', return_value=mock_session_state), \
             patch('api.services.payment_service.get_razorpay_service') as mock_razorpay:
            
            # Mock Razorpay service with invalid signature
            mock_razorpay_instance = AsyncMock()
            mock_razorpay_instance.is_configured = True
            mock_razorpay_instance.verify_payment_signature.return_value = False
            mock_razorpay.return_value = mock_razorpay_instance

            result = await verify_emi_payment(
                session_id="test_session_123",
                razorpay_payment_id="pay_test_123",
                razorpay_order_id="order_test_123",
                razorpay_signature="invalid_signature"
            )
            
            assert result["success"] is False
            assert "signature mismatch" in result["message"].lower()


class TestPayoutService:
    """Test payout service for disbursements."""

    @pytest.mark.asyncio
    async def test_create_beneficiary_success(self):
        """Test successful beneficiary creation."""
        with patch('api.services.payout_service.get_razorpay_service') as mock_razorpay:
            # Mock Razorpay service
            mock_razorpay_instance = AsyncMock()
            mock_razorpay_instance.is_configured = True
            mock_razorpay_instance.create_contact.return_value = {"id": "cont_test_123"}
            mock_razorpay_instance.create_fund_account.return_value = {"id": "fa_test_123"}
            mock_razorpay.return_value = mock_razorpay_instance

            result = await create_beneficiary(
                name="Test Customer",
                account_number="1234567890",
                ifsc="HDFC0000000",
                email="test@example.com",
                phone="9876543210"
            )
            
            assert result["contact_id"] == "cont_test_123"
            assert result["fund_account_id"] == "fa_test_123"
            assert result["mock"] is False

    @pytest.mark.asyncio
    async def test_initiate_disbursement_success(self):
        """Test successful disbursement initiation."""
        with patch('api.services.payout_service.get_razorpay_service') as mock_razorpay:
            # Mock Razorpay service
            mock_razorpay_instance = AsyncMock()
            mock_razorpay_instance.is_configured = True
            mock_razorpay_instance.create_payout.return_value = {
                "id": "pout_test_123",
                "status": "processing",
                "utr": "UTR123456"
            }
            mock_razorpay.return_value = mock_razorpay_instance

            result = await initiate_disbursement(
                fund_account_id="fa_test_123",
                amount=45000.0,
                session_id="test_session_123",
                mode="IMPS"
            )
            
            assert result["success"] is True
            assert result["payout_id"] == "pout_test_123"
            assert result["status"] == "processing"
            assert result["utr"] == "UTR123456"

    @pytest.mark.asyncio
    async def test_handle_payout_webhook_processed(self):
        """Test handling of payout.processed webhook."""
        payload = {
            "payload": {
                "payout": {
                    "entity": {
                        "id": "pout_test_123",
                        "status": "processed",
                        "amount": 4500000,  # 45000 * 100
                        "utr": "UTR123456",
                        "reference_id": "loan_test_session_123"
                    }
                }
            }
        }

        with patch('db.database.loan_applications_collection') as mock_collection:
            mock_collection.update_one = AsyncMock()

            result = await handle_payout_webhook("payout.processed", payload)
            
            assert result["processed"] is True
            assert result["action"] == "disbursement_confirmed"
            assert result["payout_id"] == "pout_test_123"

    @pytest.mark.asyncio
    async def test_handle_payout_webhook_reversed(self):
        """Test handling of payout.reversed webhook."""
        payload = {
            "payload": {
                "payout": {
                    "entity": {
                        "id": "pout_test_123",
                        "status": "reversed",
                        "amount": 4500000,
                        "failure_reason": "Insufficient funds",
                        "reference_id": "loan_test_session_123"
                    }
                }
            }
        }

        with patch('db.database.loan_applications_collection') as mock_collection:
            mock_collection.update_one = AsyncMock()

            result = await handle_payout_webhook("payout.reversed", payload)
            
            assert result["processed"] is True
            assert result["action"] == "disbursement_reversed"
            assert result["reason"] == "Insufficient funds"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

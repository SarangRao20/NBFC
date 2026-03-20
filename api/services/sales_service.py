"""Sales Service — customer identification and loan capture (Steps 2, 3)."""

import json
import os
from api.core.state_manager import get_session, update_session, advance_phase
from mock_apis.loan_products import LOAN_PRODUCTS


def _normalize_phone(phone: str) -> str:
    """Strip +91/91 prefix and spaces to get clean 10-digit number."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    return phone[-10:]


def _lookup_customer_by_phone(phone: str) -> dict | None:
    """CRM lookup by phone number."""
    phone = _normalize_phone(phone)
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if c["phone"] == phone:
                    return c
    except Exception:
        pass
    return None


def _lookup_customer_by_email(email: str, password: str) -> dict | None:
    """CRM lookup by email + password."""
    email = email.strip().lower()
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if c.get("email", "").lower() == email and c.get("password", "") == password:
                    return c
    except Exception:
        pass
    return None


def _calculate_emi(principal: float, rate_pa: float, tenure: int) -> float:
    """Standard EMI formula: P × R × (1+R)^N / ((1+R)^N - 1)."""
    if principal <= 0 or tenure <= 0 or rate_pa <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    emi = principal * r * ((1 + r) ** tenure) / (((1 + r) ** tenure) - 1)
    return round(emi, 2)


def _get_rate_for_product(loan_type: str) -> float:
    """Look up base rate from loan products catalog."""
    product = LOAN_PRODUCTS.get(loan_type)
    if product:
        return product.get("base_rate", 12.0)
    return 12.0


async def identify_customer(session_id: str, phone: str, email: str = None, password: str = None) -> dict:
    """Step 2: Identify Existing vs New User via DB lookup."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = None

    # Try phone-based lookup first
    clean_phone = _normalize_phone(phone)
    customer = _lookup_customer_by_phone(clean_phone)

    # Fallback to email-based lookup
    if not customer and email and password:
        customer = _lookup_customer_by_email(email, password)

    if customer:
        update_session(session_id, {
            "customer_id": customer.get("id", clean_phone),
            "is_existing_customer": True,
            "customer_data": {
                "name": customer.get("name", ""),
                "phone": clean_phone,
                "email": customer.get("email", ""),
                "city": customer.get("city", ""),
                "salary": customer.get("salary", 0),
                "credit_score": customer.get("credit_score", 0),
                "pre_approved_limit": customer.get("pre_approved_limit", 0),
                "existing_emi_total": customer.get("existing_emi_total", 0),
                "current_loans": customer.get("current_loans", []),
                "risk_flags": customer.get("risk_flags", []),
            }
        })
        await advance_phase(session_id, "customer_identified")
        return {
            "is_existing_customer": True,
            "customer_data": {
                "name": customer.get("name", ""),
                "phone": clean_phone,
                "city": customer.get("city", ""),
                "salary": customer.get("salary", 0),
                "credit_score": customer.get("credit_score", 0),
                "pre_approved_limit": customer.get("pre_approved_limit", 0),
                "existing_emi_total": customer.get("existing_emi_total", 0),
                "current_loans": customer.get("current_loans", []),
            },
            "message": f"Welcome back, {customer.get('name', 'Customer')}!"
        }
    else:
        # New customer — create minimal profile
        await update_session(session_id, {
            "customer_id": clean_phone,
            "is_existing_customer": False,
            "customer_data": {
                "name": "",
                "phone": clean_phone,
                "email": email or "",
                "city": "",
                "salary": 0,
                "credit_score": 700,
                "pre_approved_limit": 100000,
                "existing_emi_total": 0,
                "current_loans": [],
                "risk_flags": [],
            }
        })
        await advance_phase(session_id, "customer_identified")
        return {
            "is_existing_customer": False,
            "customer_data": None,
            "message": "New customer. Profile created with default values. Proceed to capture loan requirement."
        }


async def capture_loan_requirement(session_id: str, loan_type: str, loan_amount: float, tenure_months: int) -> dict:
    """Step 3: Capture Loan Requirement → compute EMI → State Update: Profile & Intent."""
    state = await get_session(session_id)
    if not state:
        return None

    rate = _get_rate_for_product(loan_type)
    emi = _calculate_emi(loan_amount, rate, tenure_months)
    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - loan_amount, 2)

    loan_terms = {
        "loan_type": loan_type,
        "principal": loan_amount,
        "rate": rate,
        "tenure": tenure_months,
        "emi": emi,
    }

    await update_session(session_id, {"loan_terms": loan_terms})
    await advance_phase(session_id, "loan_captured")

    return {
        "loan_terms": loan_terms,
        "emi": emi,
        "total_interest": total_interest,
        "total_repayment": total_payment,
        "message": f"Loan captured: ₹{loan_amount:,.0f} at {rate}% for {tenure_months} months. EMI: ₹{emi:,.2f}/month."
    }

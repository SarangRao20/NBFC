"""Mock IMPS Disbursement Service — Simulates real-time fund transfer via IMPS."""

import asyncio
import uuid
from datetime import datetime, timedelta
from api.core.state_manager import get_session, update_session
from mock_apis.bank_details_api import get_bank_details


async def initiate_imps_transfer(session_id: str) -> dict:
    session = await get_session(session_id)
    if not session:
        return {"success": False, "error": "Session not found"}

    state = session
    terms = state.get("loan_terms", {}) or {}
    customer = state.get("customer_data", {}) or {}

    if state.get("disbursement_status") == "completed":
        return {
            "success": False,
            "error": "Loan already disbursed",
            "disbursement_id": state.get("disbursement_id"),
        }

    if not state.get("is_signed"):
        return {"success": False, "error": "Loan not signed yet"}

    principal = terms.get("principal", 0) or 0
    net_amount = state.get("net_disbursement_amount", 0) or 0
    if net_amount <= 0 and principal > 0:
        net_amount = principal - (principal * 0.035)
    disbursement_id = f"IMPS-{uuid.uuid4().hex[:12].upper()}"

    bank_account = customer.get("bank_account_number", "")
    ifsc = customer.get("ifsc_code", "")
    bank_name = customer.get("bank_name", "")

    if not bank_account or not ifsc:
        bank_lookup = get_bank_details(bank_name or "HDFC Bank")
        if bank_lookup.get("found"):
            bank_account = bank_lookup["account_number"]
            ifsc = bank_lookup["ifsc"]
            bank_name = bank_lookup["bank_name"]

    await asyncio.sleep(3)

    today = datetime.now().strftime("%Y-%m-%d")
    first_emi = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    completion_update = {
        "disbursement_step": "completed",
        "disbursement_status": "completed",
        "disbursement_id": disbursement_id,
        "disbursement_date": today,
        "current_phase": "disbursed",
        "loan_terms": {
            **terms,
            "disbursement_date": today,
            "first_emi_date": first_emi,
            "next_emi_date": first_emi,
            "sanction_date": terms.get("sanction_date", today),
            "payments_made": 0,
            "emi_day_of_month": int(datetime.now().strftime("%d")),
        },
        "customer_data": {
            **customer,
            "bank_account_number": bank_account,
            "ifsc_code": ifsc,
            "bank_name": bank_name,
        },
    }
    await update_session(session_id, completion_update)

    # Persist active loan to customer record in MongoDB
    try:
        from db.database import users_collection
        phone = customer.get("phone")
        if phone:
            active_loan_doc = {
                "session_id": session_id,
                "disbursement_id": disbursement_id,
                "amount": terms.get("principal", 500000),
                "tenure": terms.get("tenure", 36),
                "emi": terms.get("emi", 16250),
                "rate": terms.get("rate", 10.5),
                "lender": terms.get("lender_name", "ICICI Bank"),
                "status": "ACTIVE",
                "disbursed_at": today,
                "first_emi_date": first_emi,
                "paid_emis": 0,
                "remaining_emis": terms.get("tenure", 36)
            }
            await users_collection.update_one(
                {"phone": phone},
                {
                    "$push": {"current_loans": active_loan_doc},
                    "$set": {"active_facility": active_loan_doc}
                },
                upsert=True
            )
            print(f"✅ Disbursed loan persisted to MongoDB for phone {phone}")
    except Exception as dberr:
        print(f"⚠️ Failed to persist disbursed loan to MongoDB: {dberr}")

    return {
        "success": True,
        "disbursement_id": disbursement_id,
        "amount": net_amount,
        "bank_account": bank_account,
        "ifsc": ifsc,
        "bank_name": bank_name,
        "date": today,
        "first_emi_date": first_emi,
    }

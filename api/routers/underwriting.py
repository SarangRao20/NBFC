"""Underwriting Router — Step 11 (Decision Engine)."""

from fastapi import APIRouter
from api.schemas.underwriting import UnderwritingResponse
from api.services import underwriting_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Underwriting / Decision Engine"])


@router.post("/{session_id}/underwrite", response_model=UnderwritingResponse,
             summary="Step 11: Underwriting Agent — Full Decision Engine")
async def underwrite(session_id: str):
    """Evaluates loan eligibility via the decision tree:
    1. Credit Score >= 700?
    2. Check Loan Limit (Low/Medium/High exposure)
    3. Calculate DTI ratio
    4. Decision: approve / soft_reject / reject / pending_docs

    soft_reject triggers the Persuasion Loop (Steps 12-15).
    reject routes to Advisory (Step 17).
    approve routes to Sanction (Step 16).
    """
    result = await underwriting_service.underwrite(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.get("/{session_id}/offers", summary="Fetch Real-Time Institutional Lender Offers")
async def get_lender_offers(session_id: str):
    """Fetch eligible lender offers for session based on credit score & income."""
    from api.core.state_manager import get_session, update_session
    from mock_apis.lender_apis import aggregate_lender_offers

    state = await get_session(session_id)
    if not state:
        raise SessionNotFoundError(session_id)

    customer = state.get("customer_data", {}) or {}
    terms = state.get("loan_terms", {}) or {}

    principal = terms.get("principal", 500000) or 500000
    tenure = terms.get("tenure", 36) or 36
    score = customer.get("credit_score", 785) or 785
    salary = customer.get("salary", 75000) or 75000

    aggregated = await aggregate_lender_offers(principal, tenure, score, salary)
    offers = aggregated.get("offers", [])

    await update_session(session_id, {"eligible_offers": offers})

    return {
        "success": True,
        "offers": offers,
        "total_offers": len(offers),
        "request_params": {
            "principal": principal,
            "tenure": tenure,
            "credit_score": score,
            "salary": salary
        }
    }


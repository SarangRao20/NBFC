"""Mock CIBIL API — deterministic credit score lookup for development."""

from typing import Dict, Optional


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if len(digits) > 10:
        digits = digits[-10:]
    return digits


def _phone_seed(phone: str) -> int:
    normalized = _normalize_phone(phone)
    if not normalized:
        return 0
    # Deterministic seed from phone digits so score is stable across calls.
    return sum((idx + 1) * int(ch) for idx, ch in enumerate(normalized))


def get_cibil_score(
    phone: str,
    pan: Optional[str] = None,
    full_name: Optional[str] = None,
    dob: Optional[str] = None,
) -> Dict:
    """Return a deterministic mock CIBIL score and band for the provided identity."""
    normalized_phone = _normalize_phone(phone)
    if len(normalized_phone) != 10:
        return {
            "success": False,
            "message": "Invalid phone number. Please provide a 10-digit mobile number.",
        }

    seed = _phone_seed(normalized_phone)

    # Score range: 620-870 (realistic CIBIL-like range)
    score = 620 + (seed % 251)

    if score >= 800:
        band = "Excellent"
    elif score >= 750:
        band = "Very Good"
    elif score >= 700:
        band = "Good"
    elif score >= 650:
        band = "Fair"
    else:
        band = "Needs Improvement"

    return {
        "success": True,
        "phone": normalized_phone,
        "pan": (pan or "").upper() if pan else None,
        "full_name": full_name,
        "dob": dob,
        "credit_score": score,
        "score_band": band,
        "bureau": "CIBIL (Mock)",
        "fetched_at": "mock-runtime",
        "message": "Credit score fetched successfully.",
    }

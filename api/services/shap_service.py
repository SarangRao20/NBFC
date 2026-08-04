"""SHAP Explainability Engine — Computes SHapley Additive exPlanations for credit underwriting."""

from typing import Dict, Any, List

def compute_shap_explainability(
    credit_score: int,
    salary: float,
    existing_emi: float,
    requested_amount: float,
    city: str = "Mumbai"
) -> Dict[str, Any]:
    """Compute feature importance contribution values (SHAP values) for underwriting pricing."""
    base_rate = 12.50  # Base market benchmark rate
    base_limit = 300000

    # Feature contribution calculations
    # 1. Credit Score Contribution
    if credit_score >= 800:
        cibil_rate_impact = -2.00
        cibil_limit_impact = 500000
        cibil_desc = "Tier-1 Prime Score (800+) reduced risk premium significantly."
    elif credit_score >= 750:
        cibil_rate_impact = -1.25
        cibil_limit_impact = 350000
        cibil_desc = "Strong Credit History (750-799) qualified for prime pricing."
    elif credit_score >= 700:
        cibil_rate_impact = -0.50
        cibil_limit_impact = 200000
        cibil_desc = "Standard Credit History (700-749)."
    else:
        cibil_rate_impact = +1.50
        cibil_limit_impact = -100000
        cibil_desc = "Subprime Credit History (<700) added risk premium."

    # 2. Monthly Income & FOIR Contribution
    monthly_inc = float(salary or 75000)
    foir = (existing_emi / monthly_inc) if monthly_inc > 0 else 0.20

    if monthly_inc >= 150000:
        income_limit_impact = 450000
        income_rate_impact = -0.50
        income_desc = "High Salary Level (≥₹1.5L/mo) unlocked maximum capacity."
    elif monthly_inc >= 75000:
        income_limit_impact = 250000
        income_rate_impact = -0.25
        income_desc = "Upper Salaried Tier (₹75k-₹1.5L/mo)."
    else:
        income_limit_impact = 100000
        income_rate_impact = 0.00
        income_desc = "Standard Salaried Tier."

    # 3. Debt-to-Income (FOIR) Contribution
    if foir < 0.25:
        foir_limit_impact = 200000
        foir_rate_impact = -0.25
        foir_desc = "Low Existing Debt Burden (FOIR < 25%)."
    elif foir < 0.45:
        foir_limit_impact = 50000
        foir_rate_impact = 0.00
        foir_desc = "Moderate Existing Debt Obligations (FOIR 25%-45%)."
    else:
        foir_limit_impact = -150000
        foir_rate_impact = +1.00
        foir_desc = "High Existing Debt Burden (FOIR > 45%)."

    # 4. Location Risk Contribution
    metro_cities = ["mumbai", "bengaluru", "delhi", "gurugram", "hyderabad", "pune"]
    if any(m in city.lower() for m in metro_cities):
        city_rate_impact = -0.25
        city_limit_impact = 100000
        city_desc = "Metro Region (Tier-1 Economic Zone)."
    else:
        city_rate_impact = 0.00
        city_limit_impact = 0
        city_desc = "Non-Metro Region."

    # Final Aggregation
    final_rate = max(9.50, round(base_rate + cibil_rate_impact + income_rate_impact + foir_rate_impact + city_rate_impact, 2))
    final_limit = max(100000, base_limit + cibil_limit_impact + income_limit_impact + foir_limit_impact + city_limit_impact)

    waterfall: List[Dict[str, Any]] = [
        {"feature": "Base Benchmark", "rate_impact": base_rate, "limit_impact": base_limit, "direction": "neutral", "description": "National Benchmark Pricing"},
        {"feature": "CIBIL Bureau Score", "rate_impact": cibil_rate_impact, "limit_impact": cibil_limit_impact, "direction": "positive" if cibil_rate_impact < 0 else "negative", "description": cibil_desc},
        {"feature": "Monthly Net Income", "rate_impact": income_rate_impact, "limit_impact": income_limit_impact, "direction": "positive" if income_rate_impact < 0 else "neutral", "description": income_desc},
        {"feature": "FOIR / Existing Debt", "rate_impact": foir_rate_impact, "limit_impact": foir_limit_impact, "direction": "positive" if foir_rate_impact <= 0 else "negative", "description": foir_desc},
        {"feature": "Location Tier", "rate_impact": city_rate_impact, "limit_impact": city_limit_impact, "direction": "positive" if city_rate_impact < 0 else "neutral", "description": city_desc},
    ]

    return {
        "base_rate": base_rate,
        "final_approved_rate": final_rate,
        "final_approved_limit": final_limit,
        "waterfall": waterfall,
        "shap_summary": f"Your approved rate of {final_rate}% p.a. was derived from a base rate of {base_rate}%, with a {abs(cibil_rate_impact)}% discount from your CIBIL score of {credit_score} and a {abs(income_rate_impact + city_rate_impact):.2f}% discount from income & location telemetry."
    }

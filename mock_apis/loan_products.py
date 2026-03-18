"""Mock Loan Products — provides product details, eligibility, and rate calculations."""

LOAN_PRODUCTS = {
    "personal": {
        "name": "Personal Loan",
        "min_amount": 50000,
        "max_amount": 2500000,
        "min_tenure": 6,
        "max_tenure": 60,
        "base_rate": 12.0,
        "min_income": 20000,
        "description": "Unsecured personal loan for any purpose — weddings, travel, medical emergencies, or debt consolidation.",
        "features": [
            "No collateral required",
            "Quick disbursal within 24 hours",
            "Flexible repayment tenure",
            "Minimal documentation",
        ],
    },
    "student": {
        "name": "Student / Education Loan",
        "min_amount": 100000,
        "max_amount": 5000000,
        "min_tenure": 12,
        "max_tenure": 120,
        "base_rate": 8.5,
        "min_income": 0,
        "description": "Education loan for tuition, hostel fees, and study material at recognised institutions.",
        "features": [
            "Lower interest rates for merit students",
            "Moratorium period until course completion + 6 months",
            "ABC ID integration for instant verification",
            "Co-applicant (parent/guardian) accepted",
        ],
    },
    "business": {
        "name": "Business Loan",
        "min_amount": 200000,
        "max_amount": 10000000,
        "min_tenure": 12,
        "max_tenure": 84,
        "base_rate": 14.0,
        "min_income": 40000,
        "description": "Working capital and business expansion loans for MSMEs and self-employed professionals.",
        "features": [
            "Collateral-free up to ₹50 lakh",
            "Overdraft facility available",
            "GST-linked assessment for faster approval",
            "Top-up loans after 6 months",
        ],
    },
    "home": {
        "name": "Home Loan",
        "min_amount": 500000,
        "max_amount": 50000000,
        "min_tenure": 60,
        "max_tenure": 360,
        "base_rate": 8.0,
        "min_income": 30000,
        "description": "Home purchase, construction, and renovation loans at attractive rates.",
        "features": [
            "Tax benefits under Section 80C & 24(b)",
            "Balance-transfer facility",
            "Step-up EMI option for young professionals",
            "Joint application with spouse for higher eligibility",
        ],
    },
}


def get_product_info(loan_type: str) -> dict:
    """Return product info for a given loan type."""
    product = LOAN_PRODUCTS.get(loan_type.lower())
    if product:
        return {"found": True, **product}
    return {"found": False, "error": f"Unknown loan type: {loan_type}"}


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> dict:
    """Calculate EMI using the standard reducing-balance formula."""
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return {"error": "All values must be positive."}

    monthly_rate = annual_rate / (12 * 100)
    emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (
        ((1 + monthly_rate) ** tenure_months) - 1
    )
    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return {
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "principal": principal,
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
    }


def check_eligibility(loan_type: str, amount: float, monthly_income: float) -> dict:
    """Basic eligibility check based on product limits and income."""
    product = LOAN_PRODUCTS.get(loan_type.lower())
    if not product:
        return {"eligible": False, "reason": "Unknown loan type."}

    issues = []
    if amount < product["min_amount"]:
        issues.append(f"Minimum loan amount is ₹{product['min_amount']:,.0f}.")
    if amount > product["max_amount"]:
        issues.append(f"Maximum loan amount is ₹{product['max_amount']:,.0f}.")
    if monthly_income < product["min_income"]:
        issues.append(f"Minimum monthly income required is ₹{product['min_income']:,.0f}.")

    if issues:
        return {"eligible": False, "reason": " ".join(issues)}
    return {"eligible": True, "reason": "Preliminary eligibility check passed."}

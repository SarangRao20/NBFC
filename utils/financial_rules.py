"""Financial Rules & Deterministic Underwriting policies for NBFC.

These rules precisely calculate Eligibility, DTI, FOIR, and Fraud Scores based on real-world Indian NBFC practices.
"""

def calculate_emi(principal: float, rate_pa: float, tenure_months: int) -> float:
    """Standard EMI calculation formula: P * R * (1+R)^N / ((1+R)^N - 1)"""
    if principal <= 0 or tenure_months <= 0 or rate_pa <= 0:
        return 0.0
    
    monthly_rate = (rate_pa / 12) / 100
    emi = principal * monthly_rate * ((1 + monthly_rate)**tenure_months) / (((1 + monthly_rate)**tenure_months) - 1)
    return round(emi, 2)


def evaluate_underwriting_rules(salary: float, existing_emis: float, requested_emi: float, credit_score: int) -> dict:
    """
    Evaluates Fixed Obligation to Income Ratio (FOIR/DTI) and Base Credit Score.
    No, not everyone gets a loan!
    """
    reasons = []
    
    # 1. Credit Score Threshold checks
    if credit_score < 700:
        reasons.append(f"Credit Score ({credit_score}) is below the NBFC minimum criteria of 700.")
        
    # 2. Strict Income Checks (FOIR)
    # Total monthly debt cannot exceed 50% of Monthly Salary
    total_outgoing_debt = existing_emis + requested_emi
    
    if salary <= 0:
        dti_ratio = 1.0 # 100% debt (No salary)
    else:
        dti_ratio = total_outgoing_debt / salary

    if dti_ratio > 0.50:
        reasons.append(
            f"DTI/FOIR is {dti_ratio*100:.1f}%. Total monthly EMIs (₹{total_outgoing_debt}) exceed 50% of the User's salary (₹{salary})."
        )
        
    decision = "reject" if reasons else "approve"
        
    return {
        "decision": decision,
        "dti_ratio": round(dti_ratio, 3),
        "rejection_reasons": reasons
    }


def compute_fraud_score(claimed_salary: float, ocr_extracted_salary: float, claimed_name: str, ocr_name: str, doc_confidence: float) -> float:
    """
    Computes a mock fraud score (0.0 to 1.0) based on mismatched applicant variables.
    0.0 = Safest, 1.0 = Absolute Fraud
    """
    score = 0.0
    
    # Signal 1: Name Mismatch (Highest Weight)
    if claimed_name.lower().strip() not in ocr_name.lower().strip() and ocr_name.lower().strip() not in claimed_name.lower().strip():
        score += 0.40 # Heavy penalty: Applying under false identity!
        
    # Signal 2: Income Inflation
    # If the user lied about their salary in the chat by more than 10%
    if claimed_salary > (ocr_extracted_salary * 1.10):
        score += 0.30
        
    # Signal 3: Document Quality
    if doc_confidence < 0.60:
        score += 0.15 # Suspiciously blurry or edited document
        
    # Signal 4: Low Salary but extremely high loan request (Done in DTI mostly, but signals intent)
    
    return min(score, 1.0)

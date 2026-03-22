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


def compute_fraud_score(claimed_salary: float, ocr_extracted_salary: float, claimed_name: str, ocr_name: str, doc_confidence: float) -> dict:
    """
    Computes a fraud score (0.0 to 1.0) and risk level based on mismatched applicant variables.
    """
    score = 0.0
    signals_triggered = 0
    
    # Clean strings for comparison
    c_name = claimed_name.lower().strip()
    o_name = ocr_name.lower().strip()
    
    # Signal 1: Name Mismatch
    if c_name not in o_name and o_name not in c_name:
        score += 0.40
        signals_triggered += 1
        
    # Signal 2: Income Inflation (>10%)
    if ocr_extracted_salary > 0:
        if claimed_salary > (ocr_extracted_salary * 1.10):
            score += 0.30
            signals_triggered += 1
    elif claimed_salary > 0:
        # If OCR salary is 0 or missing and claimed is not, consider it inflated/mismatch
        score += 0.30
        signals_triggered += 1
        
    # Signal 3: Document Quality
    if doc_confidence < 0.60:
        score += 0.15
        signals_triggered += 1
        
    # Bonus if 2 or more signals triggered
    if signals_triggered >= 2:
        score += 0.10
        
    # Cap score at 1.0
    fraud_score = min(score, 1.0)
    
    # Determine fraud level
    if fraud_score >= 0.7:
        fraud_level = "high"
    elif fraud_score >= 0.3:
        fraud_level = "medium"
    else:
        fraud_level = "low"
        
    return {
        "fraud_score": round(fraud_score, 3),
        "fraud_level": fraud_level
    }


def evaluate_underwriting(
    salary: float,
    existing_emis: float,
    requested_loan_amount: float,
    tenure: int,
    interest_rate: float,
    credit_score: int,
    fraud_score: float,
    doc_confidence: float,
    doc_status: str,
    employment_years: float,
    loan_type: str
) -> dict:
    """
    Evaluates underwriting rules to return a comprehensive decision.
    """
    reasons = []
    
    # EMI Calculation
    requested_emi = calculate_emi(requested_loan_amount, interest_rate, tenure)
    
    # FOIR (Dynamic)
    if salary < 30000:
        max_foir = 0.40
    elif salary <= 100000:
        max_foir = 0.50
    else:
        max_foir = 0.60
        
    total_outgoing_debt = existing_emis + requested_emi
    dti_ratio = total_outgoing_debt / salary if salary > 0 else 1.0
    foir_exceeded = dti_ratio > max_foir
    
    # Financial Health Score (0-10)
    # Credit Score (40% weight): Map 600-800 to 0-10
    cs_normalized = max(0.0, min(10.0, float((credit_score - 600) / 20)))
    # FOIR (30% weight): Map 0-max_foir to 10-0
    foir_normalized = max(0.0, min(10.0, float(10.0 - (dti_ratio / max_foir * 10.0))))
    # Fraud Score (30% weight): Map 0-1 to 10-0
    fraud_normalized = max(0.0, min(10.0, float(10.0 - (fraud_score * 10.0))))
    financial_health_score = round((cs_normalized * 0.4) + (foir_normalized * 0.3) + (fraud_normalized * 0.3), 2)
    
    # Risk Classification modifiers
    risk_score = financial_health_score
    
    lp = loan_type.lower()
    if lp in ["education", "home"]:
        risk_score += 1.0  # Reduces risk
    elif lp == "luxury":
        risk_score -= 1.0  # Increases risk
        
    if employment_years >= 3.0:
        risk_score += 1.0
    elif employment_years < 1.0:
        risk_score -= 1.0
        
    if risk_score >= 7.5:
        risk_level = "low"
    elif risk_score >= 5.0:
        risk_level = "medium"
    elif risk_score >= 3.0:
        risk_level = "high"
    else:
        risk_level = "very_high"
        
    # Document Issue Check
    # Prompt says "Return 'pending' ONLY IF: doc_confidence < 0.75, missing required fields, partial name mismatch, salary mismatch within 20%, doc_status == 'suspicious'"
    # We will trigger pending if doc_confidence is low or doc_status matches known bad values.
    # Note: If the document had a name mismatch or salary mismatch, the caller might pass "partial name mismatch" or "salary mismatch within 20%" in doc_status.
    suspicious_statuses = [
        "suspicious", "missing", "missing required fields", 
        "partial name mismatch", "salary mismatch within 20%",
        "invalid"
    ]
    doc_issue = False
    if doc_confidence < 0.75:
        doc_issue = True
        reasons.append("Document confidence is below 0.75.")
    if doc_status.lower() in suspicious_statuses:
        doc_issue = True
        reasons.append(f"Document issue flagged: {doc_status}.")
        
    # Decision Logic
    decision = "approve"
    recommended_offer = None
    pending_expiry_hours = None
    
    if fraud_score >= 0.7:
        decision = "reject"
        reasons.append(f"Fraud score ({fraud_score}) is high. Automatic rejection.")
        risk_level = "very_high"  # Force very_high risk
    elif credit_score < 650:
        decision = "reject"
        reasons.append(f"Credit score ({credit_score}) is below the minimum required (650).")
        risk_level = "very_high"
    elif doc_issue:
        decision = "pending"
        pending_expiry_hours = 48
        reasons.append("Please upload correct documents within 48 hours")
    elif foir_exceeded:
        decision = "optimize"
        reasons.append(f"FOIR exceeded: {dti_ratio*100:.1f}% > {max_foir*100:.1f}%.")
    else:
        if 0.3 <= fraud_score < 0.7:
            reasons.append("Application marked as suspicious due to moderate fraud score.")
            
    # Loan Optimization
    if decision == "optimize":
        # We need to reduce EMI to fit FOIR, so calculate max permitted EMI
        max_allowed_emi = (salary * max_foir) - existing_emis
        if max_allowed_emi <= 0:
            decision = "reject"
            reasons.append("Existing EMIs exceed maximum allowed FOIR. No loan possible.")
            risk_level = "very_high"
        else:
            monthly_rate = (interest_rate / 12) / 100
            # P = EMI * ((1+R)^N - 1) / (R * (1+R)^N)
            if monthly_rate > 0:
                optimal_loan_amount = max_allowed_emi * (((1 + monthly_rate)**tenure) - 1) / (monthly_rate * ((1 + monthly_rate)**tenure))
            else:
                optimal_loan_amount = max_allowed_emi * tenure
                
            recommended_offer = {
                "recommended_loan_amount": round(optimal_loan_amount, 2),
                "recommended_tenure": tenure,
                "recommended_emi": round(max_allowed_emi, 2)
            }
            decision = "approve"
            reasons.append(f"Offered optimized loan amount of ₹{round(optimal_loan_amount, 2)} to meet FOIR requirements.")
            
    # Construct final result
    result = {
        "decision": decision,
        "risk_level": risk_level,
        "emi": requested_emi,
        "dti_ratio": round(float(dti_ratio), 3),
        "fraud_score": float(fraud_score),
        "financial_health_score": float(financial_health_score),
        "reasons": reasons
    }
    
    if recommended_offer:
        result["recommended_offer"] = recommended_offer
        
    if pending_expiry_hours is not None:
        result["pending_expiry_hours"] = pending_expiry_hours
        
    return result

"""
Mock Lender APIs — Simulates loan offers from multiple lenders.
This module fetches loan offers from different lender mock data sources.
"""

import json
import os
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def _load_lenders_data() -> Dict:
    """Load lenders data from JSON file."""
    lenders_path = os.path.join(os.path.dirname(__file__), "lenders.json")
    with open(lenders_path, "r") as f:
        return json.load(f)


def _calculate_interest_rate(base_rate: float, credit_score: int) -> float:
    """
    Calculate actual interest rate based on credit score.
    Lower credit score = higher rate (risk-based pricing).
    """
    if credit_score >= 800:
        adjustment = -0.5  # Excellent credit gets discount
    elif credit_score >= 750:
        adjustment = 0.0  # No adjustment
    elif credit_score >= 700:
        adjustment = 0.5  # Slight increase
    elif credit_score >= 650:
        adjustment = 1.5  # Moderate increase
    else:
        adjustment = 2.5  # Higher risk premium
    
    return max(base_rate + adjustment, base_rate)  # Never below base rate


def fetch_lender_offer(
    lender_id: str,
    loan_amount: float,
    tenure_months: int,
    credit_score: int,
    monthly_salary: float,
) -> Optional[Dict]:
    """Generic fetch function for any lender."""
    lenders = _load_lenders_data()
    lender = next((l for l in lenders["lenders"] if l["lender_id"] == lender_id), None)
    
    if not lender:
        print(f"🔍 [LENDER DEBUG] Lender {lender_id} not found")
        return None
        
    print(f"🔍 [LENDER DEBUG] Checking {lender['lender_name']}: amount={loan_amount}, tenure={tenure_months}, score={credit_score}, salary={monthly_salary}")
    
    # Eligibility check
    if credit_score < lender["min_credit_score"]:
        print(f"🔍 [LENDER DEBUG] REJECTED: Credit score {credit_score} < min {lender['min_credit_score']}")
        return None  # Not eligible
    
    if loan_amount > lender["max_loan_amount"] or loan_amount < lender["min_loan_amount"]:
        print(f"🔍 [LENDER DEBUG] REJECTED: Loan amount {loan_amount} not in range [{lender['min_loan_amount']}, {lender['max_loan_amount']}]")
        return None
    
    if tenure_months not in lender["tenure_options"]:
        print(f"🔍 [LENDER DEBUG] REJECTED: Tenure {tenure_months} not in options {lender['tenure_options']}")
        # Allow slight flexibility in tenure for mock purposes if it's close? 
        # No, let's stick to defined options for consistency.
        return None
    
    # Calculate FOIR (Fixed Obligation to Income Ratio)
    emi = _calculate_emi(loan_amount, _calculate_interest_rate(lender["base_rate"], credit_score), tenure_months)
    monthly_foir = emi / monthly_salary if monthly_salary > 0 else 1.0
    
    print(f"🔍 [LENDER DEBUG] EMI={emi}, FOIR={monthly_foir}, limit={lender['foir_limit']}")
    
    if monthly_foir > lender["foir_limit"]:
        print(f"🔍 [LENDER DEBUG] REJECTED: FOIR {monthly_foir} > limit {lender['foir_limit']}")
        return None
    
    print(f"🔍 [LENDER DEBUG] APPROVED: {lender['lender_name']}")
    return {
        "lender_id": lender["lender_id"],
        "lender_name": lender["lender_name"],
        "lender_type": lender["lender_type"],
        "interest_rate": _calculate_interest_rate(lender["base_rate"], credit_score),
        "processing_fee": loan_amount * (lender["processing_fee_percent"] / 100),
        "max_loan_amount": lender["max_loan_amount"],
        "tenure_options": lender["tenure_options"],
        "risk_profile": lender["risk_profile"],
        "approval_probability": lender["approval_probability"],
        "settlement_days": lender["settlement_days"],
        "characteristics": lender["characteristics"],
        "reg_details": lender.get("reg_details", {}),
    }

# Legacy wrappers for backward compatibility if any other agents use them
def fetch_bank_a_offer(a, b, c, d): return fetch_lender_offer("hdfc_bank", a, b, c, d)
def fetch_bank_b_offer(a, b, c, d): return fetch_lender_offer("icici_bank", a, b, c, d)
def fetch_nbfc_x_offer(a, b, c, d): return fetch_lender_offer("bajaj_finserv", a, b, c, d)
def fetch_fintech_y_offer(a, b, c, d): return fetch_lender_offer("muthoot_finance", a, b, c, d)
def fetch_credit_union_z_offer(a, b, c, d): return fetch_lender_offer("saraswat_bank", a, b, c, d)


def _calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Calculate EMI using the standard reducing-balance formula."""
    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return 0.0
    
    monthly_rate = annual_rate / (12 * 100)
    if monthly_rate == 0:
        return principal / tenure_months
    
    try:
        emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (
            ((1 + monthly_rate) ** tenure_months) - 1
        )
        return round(emi, 2)
    except OverflowError:
        return 0.0


async def aggregate_lender_offers(
    principal: float,
    tenure: int,
    credit_score: int,
    monthly_income: float,
    use_parallel: bool = True,
) -> Dict:
    """Fetch offers from all lenders and return aggregated results."""
    # Map back to internal names if needed
    loan_amount = principal
    tenure_months = tenure
    monthly_salary = monthly_income
    start_time = time.time()
    
    lenders_data = _load_lenders_data()
    lender_ids = [l["lender_id"] for l in lenders_data["lenders"]]
    
    offers = []
    
    if use_parallel:
        with ThreadPoolExecutor(max_workers=len(lender_ids)) as executor:
            future_to_lender = {
                executor.submit(
                    fetch_lender_offer,
                    lid,
                    loan_amount,
                    tenure_months,
                    credit_score,
                    monthly_salary
                ): lid
                for lid in lender_ids
            }
            
            for future in as_completed(future_to_lender):
                try:
                    offer = future.result()
                    if offer:
                        offers.append(offer)
                except Exception:
                    pass
    else:
        for lid in lender_ids:
            offer = fetch_lender_offer(lid, loan_amount, tenure_months, credit_score, monthly_salary)
            if offer:
                offers.append(offer)
    
    fetch_time_ms = round((time.time() - start_time) * 1000, 2)
    
    # Find best offer (lowest interest rate)
    best_offer = min(offers, key=lambda x: x["interest_rate"]) if offers else None
    
    # Proactive Eligibility: Suggest alternative if no offers
    max_eligible_amount = 0
    if not offers:
        all_lenders = lenders_data["lenders"]
        for l in all_lenders:
            if credit_score >= l["min_credit_score"]:
                # Calculate max principal based on FOIR limit
                max_emi = monthly_salary * l["foir_limit"]
                # Use base rate + 1.5 as a conservative estimate for rate
                est_rate = l["base_rate"] + 1.5
                est_principal = _calculate_max_principal_internal(max_emi, est_rate, tenure_months)
                # Cap by lender's max amount
                est_principal = min(est_principal, l["max_loan_amount"])
                if est_principal > max_eligible_amount:
                    max_eligible_amount = int(est_principal // 1000) * 1000

    return {
        "offers": offers,
        "total_offers": len(offers),
        "selected_lender_id": best_offer["lender_id"] if best_offer else None,
        "selected_lender_name": best_offer["lender_name"] if best_offer else None,
        "selected_interest_rate": best_offer["interest_rate"] if best_offer else None,
        "max_eligible_amount": max_eligible_amount,
        "applied_on": datetime.now().isoformat(),
        "fetch_time_ms": fetch_time_ms,
        "request_params": {
            "loan_amount": loan_amount,
            "tenure_months": tenure_months,
            "credit_score": credit_score,
            "monthly_salary": monthly_salary,
        },
    }

def _calculate_max_principal_internal(desired_emi: float, annual_rate: float, tenure_months: int) -> float:
    if annual_rate == 0 or tenure_months <= 0: return 0
    r = (annual_rate / 12) / 100
    if r == 0: return desired_emi * tenure_months
    return desired_emi * ((1 + r) ** tenure_months - 1) / (r * (1 + r) ** tenure_months)

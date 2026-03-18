"""Automated Evaluation Suite for the 9-Agent NBFC Pipeline.

Tests all edge cases from the problem statement:
  1. Happy path (approve)
  2. Credit score < 700 → reject
  3. EMI > 50% salary → reject  
  4. Loan > 2x limit → reject
  5. Fraud detection (name mismatch)
  6. Document not uploaded → pending
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.emi_agent import emi_agent_node
from agents.fraud_agent import fraud_agent_node
from agents.underwriting import underwriting_agent_node
from agents.kyc_agent import verification_agent_node


def test_emi_calculation():
    """Test: EMI math is correct for known values."""
    state = {"loan_terms": {"principal": 200000, "rate": 12.0, "tenure": 36}}
    result = emi_agent_node(state)
    emi = result["loan_terms"]["emi"]
    assert 6600 < emi < 6700, f"EMI should be ~6642, got {emi}"
    print("✅ PASS: EMI calculation correct")


def test_fraud_clean():
    """Test: Clean customer has low fraud score."""
    state = {
        "customer_data": {"name": "Sarang Rao", "salary": 45000, "risk_flags": []},
        "documents": {"name_extracted": "Sarang Rao", "salary_extracted": 45000, "confidence": 0.95},
        "loan_terms": {"principal": 150000}
    }
    result = fraud_agent_node(state)
    assert result["fraud_score"] < 0.3, f"Clean customer should have low fraud, got {result['fraud_score']}"
    print("✅ PASS: Clean customer — low fraud score")


def test_fraud_name_mismatch():
    """Test: Name mismatch triggers high fraud score."""
    state = {
        "customer_data": {"name": "Sarang Rao", "salary": 45000, "risk_flags": []},
        "documents": {"name_extracted": "Ramesh Kumar", "salary_extracted": 45000, "confidence": 0.95},
        "loan_terms": {"principal": 150000}
    }
    result = fraud_agent_node(state)
    assert result["fraud_score"] >= 0.35, f"Name mismatch should trigger fraud, got {result['fraud_score']}"
    print("✅ PASS: Name mismatch detected — fraud score elevated")


def test_fraud_salary_inflation():
    """Test: Claiming higher salary than document shows."""
    state = {
        "customer_data": {"name": "Test User", "salary": 100000, "risk_flags": []},
        "documents": {"name_extracted": "Test User", "salary_extracted": 45000, "confidence": 0.95},
        "loan_terms": {"principal": 150000}
    }
    result = fraud_agent_node(state)
    assert result["fraud_score"] >= 0.25, f"Salary inflation should flag fraud, got {result['fraud_score']}"
    print("✅ PASS: Salary inflation detected")


def test_fraud_crm_flags():
    """Test: CRM risk flags increase fraud score (Vikram Singh case)."""
    state = {
        "customer_data": {"name": "Vikram Singh", "salary": 22000, "risk_flags": ["FRAUD_SUSPICION"]},
        "documents": {"name_extracted": "Vikram Singh", "salary_extracted": 22000, "confidence": 0.50},
        "loan_terms": {"principal": 50000}
    }
    result = fraud_agent_node(state)
    assert result["fraud_score"] >= 0.35, f"CRM flags should elevate fraud, got {result['fraud_score']}"
    print("✅ PASS: CRM risk flags detected")


def test_underwriting_approve():
    """Test: Loan within pre-approved limit → instant approve."""
    state = {
        "customer_data": {"name": "Sarang Rao", "salary": 45000, "credit_score": 750, "pre_approved_limit": 150000, "existing_emi_total": 0},
        "loan_terms": {"principal": 100000, "emi": 3300},
        "documents": {"verified": True},
        "fraud_score": 0.1
    }
    result = underwriting_agent_node(state)
    assert result["decision"] == "approve", f"Should approve, got {result['decision']}"
    print("✅ PASS: Loan within limit — approved")


def test_underwriting_reject_low_score():
    """Test: Credit score < 700 → reject (Raj Patel case)."""
    state = {
        "customer_data": {"name": "Raj Patel", "salary": 28000, "credit_score": 620, "pre_approved_limit": 75000, "existing_emi_total": 5000},
        "loan_terms": {"principal": 50000, "emi": 1700},
        "documents": {"verified": True},
        "fraud_score": 0.1
    }
    result = underwriting_agent_node(state)
    assert result["decision"] == "reject", f"Score 620 should reject, got {result['decision']}"
    print("✅ PASS: Low credit score — rejected")


def test_underwriting_reject_over_2x():
    """Test: Loan > 2x pre-approved limit → reject."""
    state = {
        "customer_data": {"name": "Test", "salary": 45000, "credit_score": 750, "pre_approved_limit": 100000, "existing_emi_total": 0},
        "loan_terms": {"principal": 250000, "emi": 8000},
        "documents": {"verified": True},
        "fraud_score": 0.05
    }
    result = underwriting_agent_node(state)
    assert result["decision"] == "reject", f"Over 2x limit should reject, got {result['decision']}"
    print("✅ PASS: Over 2x limit — rejected")


def test_underwriting_reject_high_foir():
    """Test: EMI > 50% salary (FOIR breach) → reject."""
    state = {
        "customer_data": {"name": "Test", "salary": 15000, "credit_score": 750, "pre_approved_limit": 100000, "existing_emi_total": 3000},
        "loan_terms": {"principal": 180000, "emi": 6000},
        "documents": {"verified": True},
        "fraud_score": 0.05
    }
    result = underwriting_agent_node(state)
    # Total EMI = 3000+6000 = 9000, salary=15000, FOIR=60% > 50%
    assert result["decision"] == "reject", f"FOIR 60% should reject, got {result['decision']}"
    print("✅ PASS: High FOIR — rejected")


def test_underwriting_pending_docs():
    """Test: Loan between 1x-2x limit without docs → pending."""
    state = {
        "customer_data": {"name": "Test", "salary": 45000, "credit_score": 750, "pre_approved_limit": 100000, "existing_emi_total": 0},
        "loan_terms": {"principal": 180000, "emi": 6000},
        "documents": {"verified": False},
        "fraud_score": 0.05
    }
    result = underwriting_agent_node(state)
    assert result["decision"] == "pending_docs", f"Should need docs, got {result['decision']}"
    print("✅ PASS: Extended range without docs — pending")


def test_kyc_name_match():
    """Test: Matching names → KYC passes."""
    state = {
        "customer_data": {"name": "Sarang Rao"},
        "documents": {"name_extracted": "Sarang Rao", "verified": True, "tampered": False}
    }
    result = verification_agent_node(state)
    assert result["kyc_status"] == "verified", f"Should verify, got {result['kyc_status']}"
    print("✅ PASS: KYC name match — verified")


def test_kyc_name_mismatch():
    """Test: Mismatched names → KYC fails."""
    state = {
        "customer_data": {"name": "Sarang Rao"},
        "documents": {"name_extracted": "Ramesh Kumar", "verified": True, "tampered": False}
    }
    result = verification_agent_node(state)
    assert result["kyc_status"] == "failed", f"Should fail, got {result['kyc_status']}"
    print("✅ PASS: KYC name mismatch — failed")


# ─── Run All Tests ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  🧪 NBFC 9-AGENT PIPELINE — EVALUATION SUITE")
    print("=" * 60)

    tests = [
        test_emi_calculation,
        test_fraud_clean,
        test_fraud_name_mismatch,
        test_fraud_salary_inflation,
        test_fraud_crm_flags,
        test_underwriting_approve,
        test_underwriting_reject_low_score,
        test_underwriting_reject_over_2x,
        test_underwriting_reject_high_foir,
        test_underwriting_pending_docs,
        test_kyc_name_match,
        test_kyc_name_mismatch,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {test.__name__} — {e}")
            failed += 1
        except Exception as e:
            print(f"💥 ERROR: {test.__name__} — {e}")
            failed += 1

    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)

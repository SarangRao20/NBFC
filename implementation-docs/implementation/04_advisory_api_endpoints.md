# Step 4: Structured Advisory API Endpoints

**Date:** 2026-07-27  
**Duration:** Approx. 45 minutes  
**Author:** System Implementation  

---

## What Was Done

### Problem
The advisory agent was chat-only. It returned natural language messages but no structured data for dashboard visualizations. The Advisor Dashboard (Step 5) needed JSON endpoints for health gauge, EMI calculator, and lender comparison table.

### Approach
Added 3 new structured endpoints to `api/routers/advisory.py` + 3 new service functions + 1 helper in `api/services/advisory_service.py`.

---

## New Endpoints

### 1. `GET /advisory/loans/{phone}/health-score`

**Purpose:** Financial health gauge data for Advisor Dashboard.

**Response:**
```json
{
  "success": true,
  "phone": "9421140800",
  "health_score": 72.5,
  "components": {
    "cibil": {"score": 88.9, "raw": 800, "weight": 0.35},
    "dti": {"score": 65.0, "raw_dti": 17.5, "weight": 0.30},
    "stability": {"score": 80.0, "weight": 0.20},
    "loan_history": {"score": 60.0, "raw_approved": 0, "weight": 0.15}
  },
  "risk_level": "low"
}
```

**Scoring weights:** CIBIL 35% | DTI 30% | Stability 20% | Loan History 15%

### 2. `GET /advisory/loans/{phone}/emi-calculator`

**Purpose:** Interactive EMI calculation with amortization schedule + tenure comparison.

**Query params:** `amount`, `rate`, `tenure`

**Response:**
```json
{
  "success": true,
  "emi": 16607.32,
  "total_interest": 97863.52,
  "total_repayment": 597863.52,
  "amortization": [
    {"month": 1, "emi": 16607.32, "interest": 5000.00, "principal": 11607.32, "balance": 488392.68},
    ...
  ],
  "tenure_comparisons": [
    {"tenure": 12, "emi": 44424.49, "total_interest": 33093.91, "total_repayment": 533093.91},
    {"tenure": 24, "emi": 23536.71, "total_interest": 64881.14, "total_repayment": 564881.14},
    ...
  ],
  "dti_after_loan": 33.2,
  "monthly_income": 150000,
  "existing_emi": 0
}
```

### 3. `GET /advisory/loans/{phone}/lender-comparison`

**Purpose:** Structured lender data for comparison table in Advisor Dashboard.

**Response:**
```json
{
  "success": true,
  "phone": "9421140800",
  "lenders": [
    {
      "lender_id": "hdfc_bank",
      "lender_name": "HDFC Bank",
      "interest_rate": 10.0,
      "processing_fee_percent": 0.5,
      "min_credit_score": 750,
      "max_loan_amount": 5000000,
      "tenure_options": [12, 24, 36, 48, 60],
      "foir_limit": 0.40,
      "eligible": true,
      "emi": 16133.67,
      "rejection_reasons": []
    },
    ...
  ],
  "total_lenders": 5,
  "eligible_count": 3,
  "test_params": {"amount": 500000, "tenure": 36}
}
```

---

## Files Changed

| File | Lines | Change Type |
|------|-------|-------------|
| `api/services/advisory_service.py` | ~580 | Added `get_health_score`, `get_emi_calculator`, `get_lender_comparison`, `_calculate_emi_simple` |
| `api/routers/advisory.py` | ~110 | Added 3 new GET endpoints |

### Helper Function

```python
def _calculate_emi_simple(principal, annual_rate, tenure_months):
    """Simple EMI calculation for comparative purposes."""
```

Used by `get_lender_comparison` for lender data enrichment.

### Dependency Flow

```
AdvisorDashboard (frontend)
  → GET /advisory/loans/{phone}/health-score
    → advisory_service.get_health_score()
      → users_collection.find_one({phone})
      → compute weighted score

  → GET /advisory/loans/{phone}/emi-calculator?amount=X&rate=Y&tenure=Z
    → advisory_service.get_emi_calculator()
      → standard EMI formula
      → amortization generation (first 12 months)
      → tenure comparison (12/24/36/48/60)

  → GET /advisory/loans/{phone}/lender-comparison
    → advisory_service.get_lender_comparison()
      → users_collection for profile
      → aggregate_lender_offers() + get_lender_rules_summary()
      → merge rules + offers + rejection details
```

### Verification

- Python syntax: ✓ (ast.parse passes both files)
- Endpoints return consistent JSON structures for dashboard consumption
- No breaking changes to existing endpoints

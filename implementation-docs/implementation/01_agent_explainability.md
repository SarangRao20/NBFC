# Step 1: Agent Explainability (Backend)

**Date:** 2026-07-27  
**Duration:** Approx. 1 hour  
**Author:** System Implementation  

---

## What Was Done

### Problem
The sales agent (`sales_agent.py`) silently adjusted loan amounts/tenures when no lenders matched the user's request. The explanation was generic: *"I can't offer ₹X for Y months"* — with zero detail about **which specific lender rule** caused the rejection. Users couldn't understand why their request was impossible, eroding trust.

### Approach

Three backend files were modified end-to-end:

### 1. `mock_apis/lender_apis.py`

**Change 1: Rejection reasons in `fetch_lender_offer`**
- Previously: Returned `None` on first failure, losing all diagnostic info
- Now: Collects **all** rejection reasons before returning (credit score, amount range, tenure, FOIR)
- Each reason is a human-readable string like *"Credit score 650 is below minimum requirement of 700"*

**Change 2: New `get_lender_rules_summary()` function**
- Returns every lender's complete eligibility rules from `lenders.json`
- Fields: min_credit_score, min/max loan amount, tenure_options, foir_limit, base_rate, interest_rate_range, risk_profile, approval_probability, characteristics
- Used by frontend to show "View Lender Rules" modal

**Change 3: `aggregate_lender_offers` restructured**
- Previously: Only returned successful offers (silently discarded rejections)
- Now: Returns `rejection_details` (per-lender rejection reasons) and `all_lender_rules` (complete rule set for display)
- Returns `max_eligible_amount` and `best_tenure` for alternative suggestions

**New response structure:**
```python
{
    "offers": [...],  # Successful offers (unchanged)
    "rejection_details": [  # NEW
        {"lender_id": "hdfc_bank", "lender_name": "HDFC Bank", "rejection_reasons": ["Credit score...", "Tenure..."]},
        ...
    ],
    "all_lender_rules": [  # NEW
        {"lender_id": "hdfc_bank", "lender_name": "HDFC Bank", "min_credit_score": 750, ...},
        ...
    ],
    "max_eligible_amount": 500000,
    "best_tenure": 48,
    ...
}
```

### 2. `agents/sales_agent.py`

**Change 1: Store rejection data in state**
- Before: `updates["eligible_offers"] = offers` only
- Now: Also stores `updates["rejection_details"]`, `updates["all_lender_rules"]`, `updates["show_rules_button"]`

**Change 2: Explainable "no offers" branch (line ~851)**
- **With max_eligible_amount:** Explains WHY (lists top 3 rejection reasons from lenders), then offers adjusted amount. Adds `show_rules_button: True` + tip to tap "View Lender Rules"
- **Without any offer:** Lists every lender's rejection reason with lender name. Shows structured explanation like:
  > *"Here's why none can offer ₹X for Y months:  
  > • HDFC Bank: Credit score 650 below minimum 750...  
  > • ICICI Bank: Tenure not supported..."*
- Includes `show_rules_button: True` for all rejection cases

### 3. `api/services/sales_service.py`

**Change 1: Forward new fields in chat response**
- Added `rejection_details`, `all_lender_rules`, `show_rules_button` to `chat_with_agent()` response payload
- Frontend now receives these alongside `eligible_offers`, `loan_terms`, etc.

### 4. `frontend/src/types.ts`

- Added `RejectionDetail` and `LenderRule` interfaces
- Added `show_rules_button`, `rejection_details`, `all_lender_rules`, `viewAdvisor` to `AppState`

### 5. `frontend/src/App.tsx`

- Added new fields to `INITIAL_APP_STATE`
- `handleSendMessage`: Captures `show_rules_button`, `rejection_details`, `all_lender_rules` from chat response
- `PHASE_UPDATE` handler: Syncs new fields from backend state
- `loadSession`: Loads new fields from stored state
- Post-chat state sync: Captures new fields after `getSession` call

---

## Files Changed

| File | Lines | Change Type |
|------|-------|-------------|
| `mock_apis/lender_apis.py` | ~214 | Restructured: rejection_details, get_lender_rules_summary, all_lender_rules |
| `agents/sales_agent.py` | ~969 | Explainable rejection branch, stores new fields in state |
| `api/services/sales_service.py` | ~458 | Forwards new fields in chat response |
| `frontend/src/types.ts` | ~97 | New interfaces: RejectionDetail, LenderRule; new AppState fields |
| `frontend/src/App.tsx` | ~950 | Captures + syncs new fields across chat, PHASE_UPDATE, loadSession |

---

## Data Flow

```
User types "I want ₹50L for 5 years"
  → sales_agent.py calls aggregate_lender_offers()
    → lender_apis.py checks 5 lenders, each with full rejection gathering
    → Returns: offers=[], rejection_details=[5 items], all_lender_rules=[5 items]
  → sales_agent.py detects 0 offers
    → Builds explainable reply with rejection reasons per lender
    → Stores: rejection_details, all_lender_rules, show_rules_button=true in state
  → sales_service.py.chat_with_agent() returns response with new fields
  → App.tsx updates appState with rejection_details, all_lender_rules, show_rules_button
  → (Future) RulesModal/ContextPanel read these fields to display "View Lender Rules" button
```

---

## Pending Frontend Work

The `show_rules_button` and `rejection_details` are now in AppState but not yet rendered in the UI. They will be consumed by:
- **ContextPanel.tsx** (Step 2) — display lender comparison + rules applied
- **RulesModal.tsx** (Step 3) — show all lender constraints when button clicked

## Verification

- Python syntax: ✓ (ast.parse passes all 3 files)
- TypeScript: ✓ (tsc --noEmit passes)
- Logic: rejection_details now flows from lender_apis → sales_agent → sales_service → frontend App.tsx

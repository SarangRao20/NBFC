# Step 3: Rules Modal (Lender Eligibility Popup)

**Date:** 2026-07-27  
**Duration:** Approx. 30 minutes  
**Author:** System Implementation  

---

## What Was Done

### Problem
Users received rejections or adjustments without understanding **which lender rules** caused them. The lending criteria (min credit score, FOIR limits, tenure ranges) were invisible — a black box.

### Approach
Created `RulesModal.tsx` — a full-screen centered modal overlay that shows every lender's eligibility rules with **visual pass/fail indicators** for the user's specific profile.

### Component Structure

```
┌───────────────────────────────────────────┐
│ Lender Eligibility Rules            [✕]   │
│ Your profile vs each lender's criteria    │
├───────────────────────────────────────────┤
│ ┌─ Your Profile Summary ─────────────────┐│
│ │ ℹ Green = pass, Red = fail            ││
│ │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  ││
│ │ │Score │ │Salary│ │Amnt │ │Tenure│  ││
│ │ │  750 │ │150K  │ │5.0L │ │ 36m  │  ││
│ │ └──────┘ └──────┘ └──────┘ └──────┘  ││
│ └────────────────────────────────────────┘│
│                                           │
│ ┌─ HDFC Bank (bank) ──── [Not Eligible] ─┐│
│ │ ✓ Score ≥ 750  ✓ ₹1L–50L              ││
│ │ ✗ Tenure: 12/24/36/48/60m            ││
│ │ Interest: 9.5% – 11.5% | Fee: 0.5%   ││
│ │ Credit score 650 below min 750        ││
│ └────────────────────────────────────────┘│
│                                           │
│ ┌─ Bajaj Finserv (nbfc) ──── [Eligible] ┐│
│ │ ✓ Score ≥ 650  ✓ ₹50K–30L            ││
│ │ ✓ Tenure: 12/24/36/48/60m            ││
│ │ Interest: 13.5% – 16% | Fee: 1.5%     ││
│ └────────────────────────────────────────┘│
└───────────────────────────────────────────┘
```

### Key Design Decisions

1. **Overlay modal** — Full-screen dark backdrop with centered content card
2. **Profile summary bar** — Shows user's current data (score, salary, amount, tenure) for reference
3. **Visual pass/fail** — Green checkmark ✓ for criteria met, Red warning ✗ for criteria failed
4. **Eligible/Not Eligible badge** — Each lender card shows an overall eligibility status
5. **Rejection text** — When `rejection_details` exist, shows the specific reason per lender
6. **Lender characteristics** — Shows the description text from `lenders.json`
7. **Click-outside-to-close** — Clicking the backdrop closes the modal
8. **Animated entry** — Spring animation with scale + fade

### File Created

| File | Lines | Description |
|------|-------|-------------|
| `frontend/src/components/RulesModal.tsx` | ~195 | Full-screen modal with lender rules + pass/fail indicators |

### Props Interface

```typescript
interface Props {
  appState: AppState;
  isOpen: boolean;
  onClose: () => void;
}
```

### Data Sources

| Section | Data Source |
|---------|-------------|
| Lender rules | `appState.all_lender_rules` |
| Rejection reasons | `appState.rejection_details` (matched by lender_id) |
| User profile | `appState.creditScore`, `.salary`, `.requestedAmount`, `.tenure` |

### Verification

- TypeScript: ✓ (tsc --noEmit passes)
- No external dependencies beyond existing imports
- Modal lifecycle managed by parent via `isOpen`/`onClose` props

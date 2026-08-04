# Step 2: Context Panel (Right Sidebar)

**Date:** 2026-07-27  
**Duration:** Approx. 30 minutes  
**Author:** System Implementation  

---

## What Was Done

### Problem
The UI had only 2 columns (Dashboard left, Chat center). Users had to memorize loan terms, lender offers, and document status from chat messages — no persistent right-side reference panel. This caused context-switching and poor UX during loan applications.

### Approach

Created a new `ContextPanel.tsx` component — a collapsible right sidebar (320px) that slides in/out with animated transitions.

### Component Structure

```
┌─────────────────────────────────┐
│ Loan Context            [✕]    │  ← Header with toggle close
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ 📄 Loan Terms              │ │  ← Principal, Rate, EMI, Tenure
│ │ Principal    ₹5,00,000      │ │     Total Interest, Next EMI date
│ │ Rate         12.0%          │ │
│ │ Tenure       36 months      │ │
│ │ Monthly EMI  ₹16,607        │ │
│ │ Total Int.   ₹97,852        │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 🏢 Lender Offers           │ │  ← Each offer: name, rate, EMI
│ │ ┌─────────────────────┐    │ │     approval %, Select button
│ │ │ HDFC Bank   12.0%   │    │ │
│ │ │ EMI: ₹16,607/mo     │    │ │
│ │ │ [Select]            │    │ │
│ │ └─────────────────────┘    │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ 🛡️ Rules Applied    [View All]│  ← Rejection reasons per lender
│ │ ⚠ HDFC Bank                │ │     or full lending criteria
│ │   Credit score below min... │ │
│ └─────────────────────────────┘ │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ ✅ Document Status         │ │  ← PAN: Verified/Pending
│ │ PAN:        ✓ Verified     │ │     Income: Verified/Pending
│ │ Income:     ○ Pending      │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### Key Design Decisions

1. **Collapsible with toggle button**: When closed, a small floating button (fixed right) shows. When open, the panel slides in from right with smooth animation.
2. **Four card sections**: Loan Terms, Lender Offers, Rules Applied, Document Status — each independently rendered (shows only when data exists).
3. **Empty states**: Each section hides when no data is available. Panel shows just what's relevant.
4. **Dark theme consistent**: `bg-slate-900`, `border-slate-800/50`, white/5 backgrounds, emerald accents.
5. **"View All Rules" button**: Links to RulesModal (Step 3) — shown when rejection_details present or all_lender_rules available.

### File Created

| File | Lines | Description |
|------|-------|-------------|
| `frontend/src/components/ContextPanel.tsx` | ~220 | Collapsible right sidebar with 4 data sections |

### Props Interface

```typescript
interface Props {
  appState: AppState;
  isOpen: boolean;
  onToggle: () => void;
  onSelectLender?: (lenderId: string) => void;
  onViewRules?: () => void;
}
```

### Data Sources

| Section | Data from AppState | Condition |
|---------|-------------------|-----------|
| Loan Terms | `appState.loan_terms` | Shows only when `principal > 0` |
| Lender Offers | `appState.eligible_offers` | Shows only when offers exist |
| Rules Applied | `appState.rejection_details` + `appState.show_rules_button` | Shows when rejection present or button flag set |
| Lending Criteria (fallback) | `appState.all_lender_rules` | Shows when no rejection data but rules available |
| Document Status | `appState.documents` | Always visible (shows verified/pending) |

### Verification

- TypeScript: ✓ (tsc --noEmit passes)
- All components match existing dark theme patterns
- Integration with App.tsx is pending Step 6 (layout refactor)

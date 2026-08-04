# Step 5: Advisor Dashboard (Full-Page View)

**Date:** 2026-07-27  
**Duration:** Approx. 1.5 hours  
**Author:** System Implementation  

---

## What Was Done

### Problem
Advisory features were text-only in chat. Users couldn't visually explore their financial profile, compare lenders, or interact with an EMI calculator. No data-rich dashboard existed.

### Approach
Created `AdvisorDashboard.tsx` — a full-page conditional view (no router, controlled by `appState.viewAdvisor`) with 6 sections: health gauge, DTI gauge, EMI calculator, lender comparison table, personalized plan, and inline chat.

---

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│ ← Back to Chat    Financial Wellness Dashboard              │
├──────────────────────────────────────────────────────────────┤
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐│
│ │  Health Gauge │  │  DTI Gauge   │  │  EMI Calculator      ││
│ │     ╭───╮    │  │  33.2%       │  │  Amount [====●=====]  ││
│ │     │72 │    │  │  ████████░░  │  │  Rate   [====●=====]  ││
│ │   low risk   │  │  ✅ Healthy  │  │  Tenure [====●=====]  ││
│ │  cibil: 89   │  │  Income: 150K│  │  EMI: ₹16,607/mo     ││
│ │  dti: 65     │  │  Existing: 0 │  │  Interest: ₹97,863   ││
│ └──────────────┘  └──────────────┘  └──────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  Lender Comparison                         3/5 eligible      │
│ ┌─────────┬──────┬────────┬──────┬────────┬────────────┐    │
│ │ Lender  │ Rate │ EMI    │ Fee  │ Score  │ Status     │    │
│ ├─────────┼──────┼────────┼──────┼────────┼────────────┤    │
│ │ HDFC    │ 10%  │ ₹16k  │ 0.5% │ ≥ 750  │ ✅ Eligible│    │
│ │ Bajaj   │ 14%  │ ₹17k  │ 1.5% │ ≥ 650  │ ✅ Eligible│    │
│ │ Muthoot │ 13%  │ ₹17k  │ 1.0% │ ≥ 600  │ ❌ Not Eli │    │
│ └─────────┴──────┴────────┴──────┴────────┴────────────┘    │
├──────────────────────────────────────────────────────────────┤
│ ┌─ 90-Day Credit Plan ──────┐ ┌─ Tenure Comparison ───────┐│
│ │ ✅ Pay EMIs on time       │ │ ┌─────────────────────┐  ││
│ │ ✅ Reduce utilization     │ │ │ 12m  ₹44k/mo 33k   │  ││
│ │ ✅ Don't apply new loans  │ │ │ 24m  ₹23k/mo 65k   │  ││
│ └───────────────────────────┘ │ │ 36m  ₹16k/mo 98k ◄ │  ││
│                               │ │ 48m  ₹13k/mo 130k  │  ││
│                               │ │ 60m  ₹11k/mo 163k  │  ││
│                               │ └─────────────────────┘  ││
│                               └──────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│  Ask Your Advisor                                            │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Ask anything about loans, EMI, or financial planning│     │
│  │ ┌───────────────────────────────────────────┐ [→] │     │
│  │ │ Type your question...                     │     │     │
│  │ └───────────────────────────────────────────┘     │     │
│  └────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

---

## Components Built

### 1. CircularGauge (SVG)
- SVG-based animated circular gauge for financial health score
- Color bands: green (≥70), amber (45-69), red (<45)
- Animates on mount with `framer-motion` stroke-dashoffset
- Shows score number + risk level label

### 2. DtiGauge (Bar)
- Horizontal bar showing DTI ratio relative to 50% threshold
- Color bands: green (≤30%), amber (30-50%), red (>50%)
- Shows threshold marker line at 50%
- Status message: "Healthy DTI" / "Monitor DTI" / "High DTI"

### 3. EMI Calculator
- Three sliders: Amount (₹50K–₹50L), Rate (5–20%), Tenure (6–84 months)
- Real-time recalculation with 300ms debounce
- Shows: Monthly EMI, Total Interest, Total Repayment
- Fetches data from `GET /advisory/loans/{phone}/emi-calculator`

### 4. Lender Comparison Table
- Full-width table with all lenders
- Columns: Lender name, Rate, EMI, Processing Fee, Min Credit Score, Eligibility Status
- Eligible badge (green) vs Not Eligible badge (red with tooltip)
- Summary: "X/Y eligible" counter

### 5. 90-Day Credit Plan
- Conditional content based on underwriting status
- Rejected → shows 5-step credit improvement plan
- Approved/Pending → shows general wellness plan
- Each step with checkmark icon

### 6. Tenure Comparison
- Shows EMI + total interest for 12/24/36/48/60 month tenures
- Highlights the currently selected tenure
- Data from the same EMI calculator endpoint

### 7. Inline Chat
- Mini chat interface for Q&A with advisor
- Messages displayed with user/advisor styling
- Calls `GET /advisory/loans/{phone}/message?intent=general`
- Scrolls to bottom on new messages

---

## File Created

| File | Lines | Description |
|------|-------|-------------|
| `frontend/src/components/AdvisorDashboard.tsx` | ~420 | Full-page advisor dashboard with all 7 components |

### Props

```typescript
interface Props {
  appState: AppState;
  onBack: () => void;
}
```

### Data Flow

```
Mount → fetch health-score & lender-comparison in parallel
       → health-data flows to CircularGauge
       → lender data flows to comparison table

Slider change → debounced fetch to emi-calculator (300ms)
              → emi data flows to DTI gauge + EMI display + tenure comparison

Chat submit → fetch message intent=general → append to chat stack
```

### Key Design Decisions

1. **All-in-one file** — No sub-components extracted (keeps it simple for a single-page view)
2. **Debounced EMI calc** — 300ms debounce prevents API spam during slider drag
3. **Phone from localStorage fallback** — If not in appState, tries localStorage
4. **Empty states** — Each section shows appropriate placeholder when data isn't available
5. **Consistent theme** — Dark slate/gradient backgrounds, emerald accents, glassmorphism cards
6. **No React Router** — Controlled via `appState.viewAdvisor` boolean

### Verification

- TypeScript: ✓ (tsc --noEmit passes)
- All 3 advisory endpoints integrated
- Responsive grid (1 column mobile, 3 column desktop for row 1)

# Project Audit — FinServe NBFC Agentic Loan Origination

**Date:** 2026-07-27  
**Author:** System Implementation  
**Status:** Baseline document before Phase 1 changes

---

## Project Overview

A multi-agent LangGraph loan origination platform built with:
- **Backend:** FastAPI + LangGraph multi-agent architecture (Groq LLM, llama-3.1-8b)
- **Frontend:** React 19 + Vite + Tailwind CSS + Framer Motion
- **Database:** MongoDB Atlas (prod), with mock fallback for development
- **Auth:** JWT-based + OAuth (Google/GitHub)
- **Payment:** Razorpay simulation (HMAC-SHA256 verification)

## Agent Pipeline

```
intent_agent → sales_agent → document_agent → underwriting → sanction → advisory
```

## Current Architecture

### Directory Structure

```
nbfc-agentic-flow/
├── agents/               # LangGraph agent definitions
│   ├── master_state.py   # State schema
│   ├── master_router.py  # Deterministic routing between agents
│   ├── master_graph.py   # LangGraph workflow graph
│   ├── intent_agent.py   # Intent classification (LLM)
│   ├── sales_agent.py    # Sales/Advisor agent (912 lines)
│   ├── document_agent.py # Document OCR/tampering verification
│   ├── underwriting_agent.py
│   └── advisory_agent.py
├── api/
│   ├── core/
│   │   ├── state_manager.py  # Session CRUD (MongoDB)
│   │   └── websockets.py     # Real-time event broadcast
│   ├── routers/              # FastAPI routers
│   │   ├── session.py
│   │   ├── auth.py
│   │   ├── payment.py
│   │   └── advisory.py
│   └── services/
│       ├── advisory_service.py  # Personalized advisory (434 lines)
│       ├── payment_service.py   # Razorpay + EMI processing
│       └── sales_service.py     # Graph invocation + session
├── mock_apis/
│   ├── lender_apis.py    # Lender aggregation (214 lines)
│   └── lenders.json      # 5 lender definitions
├── db/
│   ├── database.py       # MongoDB Atlas connection
│   └── mock_database.py  # Mock DB fallback (with upsert fix)
├── frontend/
│   └── src/
│       ├── App.tsx       # Main orchestration (935 lines)
│       ├── components/
│       │   ├── ChatPane.tsx       # Chat UI (559 lines)
│       │   ├── DashboardPane.tsx  # Left sidebar (313 lines)
│       │   ├── Login.tsx          # OAuth login
│       │   ├── AuthWrapper.tsx    # Auth flow
│       │   └── ... (15 more)
│       └── api/
│           └── client.ts  # API client (207 lines)
├── start.sh              # Dev startup script
├── .env                  # API keys (GROQ, MongoDB Atlas, etc.)
└── main.py               # FastAPI entry
```

## Compleated Work (Phase 0)

### Backend Bug Fixes
1. **sales_agent.py** — Removed 800+ lines duplicate code block (1790→909 lines)
2. **master_state.py** — Removed duplicate `sanction_pdf` and `is_signed` keys
3. **master_router.py** — Fixed `documents.uploaded` → `documents_uploaded` field check
4. **master_graph.py** — Fixed `load_session_node`: `current_phase` no longer overwritten by `**state`
5. **mock_database.py** — Added `upsert=True` to `update_one` and `replace_one`
6. **config.py (api/)** — Added missing `USE_DTI_SCORE` to Settings class
7. **state_manager.py** — Added `sanitized["_id"] = session_id` + `upsert=True` to all 3 `replace_one` calls

### Frontend Bug Fixes
1. **ChatPane.tsx** — Eligible offers cleared on lender selection via `setAppState`
2. **DashboardPane.tsx** — Fixed `onSelectLender` — local stub shadowing prop fixed
3. **MetricCard.tsx** — Updated for dark sidebar theme
4. **client.ts** — BASE_URL changed from render URL to localhost:8000; added Razorpay methods

### Feature Work
1. **Lender Aggregation** — When no lenders match requested tenure, uses max lender tenure
2. **OAuth Login** — Google/GitHub buttons wired to `/auth/oauth/{provider}`
3. **Advisory Service** — Rewritten for personalized data-driven advice
4. **Razorpay** — Full simulation (order creation, HMAC-SHA256 verification, 3 endpoints)
5. **Infrastructure** — `start.sh`, `.env`, Inter font, dark theme baseline

## Known Issues & Loopholes

### 1. Agent Silently Adjusts User Requests (CRITICAL)
**File:** `agents/sales_agent.py` ~line 851-873  
**Problem:** When no lenders match loan terms, the agent silently changes the amount/tenure and asks "Would you like to proceed with this adjusted amount?" without explaining WHY the original request was invalid.  
**Impact:** Users lose trust — they don't understand which lending rule triggered the adjustment.

### 2. No Structured Rejection Reasons from Lenders
**File:** `mock_apis/lender_apis.py`  
**Problem:** When a lender rejects, `fetch_lender_offer` returns `None` with no info about WHY. The aggregate function loses all diagnostic data.  
**Impact:** Can't show users which rules they passed/failed per lender.

### 3. Single-Column Chat Layout (Bad UX)
**File:** `frontend/src/App.tsx`  
**Problem:** Only 2-column (Dashboard + Chat). No dedicated space for loan terms, lender comparison, or document status during conversation.  
**Impact:** Users must memorize info mentioned in chat or switch context repeatedly.

### 4. No Formal Lender Rules Display
**File:** Not implemented  
**Problem:** Users can't see lender eligibility rules (min credit score, FOIR limit, tenure ranges, loan amount bounds) anywhere in the UI.  
**Impact:** Rejections feel like black-box decisions.

### 5. Advisory Agent is Chat-Only
**Files:** `api/routers/advisory.py`, `api/services/advisory_service.py`  
**Problem:** Advisor only returns chat messages. No structured endpoints for dashboard visualizations like health score, EMI calculator, or lender comparison.  
**Impact:** Can't build data-rich advisor dashboard.

### 6. No Advisor Dashboard UI
**File:** Not implemented  
**Problem:** Advisory features are text-only in chat. No financial health gauge, DTI gauge, EMI calculator widget, or personalized plan view.  
**Impact:** Users can't visually explore their financial profile.

### 7. No Explainable Rejection Flow
**File:** Not implemented  
**Problem:** When underwriting rejects or soft-rejects, there's no button to "View Lender Rules" or explanation of which specific rules caused the rejection (CIBIL < 700? DTI > 50%? Amount > max?).  
**Impact:** Rejection feels arbitrary.

### 8. Session History May Not Persist Across Browser Restarts
**File:** `frontend/src/App.tsx` ~line 66-92  
**Problem:** The `resumeSession` flow relies on `localStorage` session_id + `/auth/verify` endpoint. Chat history is loaded from backend but only on explicit session load. Race conditions possible on full page reload.  
**Impact:** User may lose chat context after browser restart.

## Next Phase Plan (Phase 1)

### Step 1: Agent Explainability (Backend)
- Add structured rejection reasons per lender
- Add all_lender_rules to aggregation response  
- Add show_rules_button flag when adjustment/rejection happens
- Refactor sales_agent.py to explain BEFORE adjusting

### Step 2: Context Panel (Frontend)
- New ContextPanel.tsx component (right sidebar, collapsible)
- Loan Terms, Lender Comparison, Rules Applied, Document Status

### Step 3: Rules Modal (Frontend)
- New RulesModal.tsx component
- All lender constraints with visual pass/fail indicators

### Step 4: Advisory API Endpoints (Backend)
- health-score, emi-calculator, lender-comparison endpoints

### Step 5: Advisor Dashboard (Frontend)
- Full-page view with health gauge, DTI gauge, EMI calculator, comparison table

### Step 6: 3-Column Layout Refactor (Frontend)
- App.tsx restructured, ContextPanel togglable from ChatPane header

### Step 7: Types, API Client, Polish
- New TypeScript interfaces, API methods, final wiring

## Technical Details

### Key Dependencies
- Python 3.11+ (not 3.12+ — langgraph compatibility)
- Node 18+
- MongoDB Atlas (prod) or local MongoDB (dev)
- Groq API key for LLM (llama-3.1-8b)
- Gemini API key (fallback)

### Ports
- Frontend: 5173 (Vite)
- Backend: 8000 (uvicorn)
- API Docs: 8000/docs

### Running
```bash
./start.sh
# or separately:
cd frontend && npx vite --host 0.0.0.0 --port 5173
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables
Key vars in `.env`:
- `GROQ_API_KEY` — LLM provider
- `MONGO_URI` — MongoDB Atlas connection string
- `JWT_SECRET` — JWT signing secret
- `GEMINI_API_KEY` — LLM fallback

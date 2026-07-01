
<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-0.104-red" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-blue" alt="React 19">
  <img src="https://img.shields.io/badge/MongoDB-Atlas-green" alt="MongoDB Atlas">
  <img src="https://img.shields.io/badge/LangGraph-%E2%9C%93-purple" alt="LangGraph">
</p>

<h1 align="center">FinServe NBFC</h1>
<p align="center"><strong>AI-powered loan origination platform with a multi-agent pipeline, real-time decisioning, and a multi-lender marketplace.</strong></p>

<br>

> **NBFC** = Non-Banking Financial Company. This platform handles the full loan lifecycle — from a customer saying *"I need ₹5 lakh"* to funds being disbursed — using a deterministic chain of LLM-powered agents, rule-based underwriting, and document forensics.

---

## The Problem

Applying for a loan at an Indian NBFC is a fragmented, high-friction process:

- **Manual underwriting** takes 3–7 days and requires constant back-and-forth
- **Paper documents** get lost, re-uploaded, or flagged incorrectly
- **No transparency** — applicants wait in the dark after submitting
- **Multiple lenders** means filling the same form 5 times
- **Fraud checks** happen late in the pipeline, wasting processing effort

This project collapses that 7-day process into a **single conversational session** with real-time feedback and automated decisioning.

---

## How It Works (30-Second View)

```mermaid
sequenceDiagram
    participant C as Customer
    participant A as Chat UI
    participant P as Pipeline (LangGraph)
    participant U as Underwriting
    participant L as Lender Marketplace

    C->>A: "I need a loan"
    A->>P: New session
    P->>P: Intent classification
    P->>P: Sales conversation (amount, tenure, purpose)
    P->>L: Fetch offers from 5+ lenders (parallel)
    L-->>P: Best rates & terms
    P->>C: "Here are your options from HDFC, Bajaj..."
    C->>P: Upload PAN, salary slip
    P->>P: OCR + Forensics (Gemini Vision)
    P->>P: KYC + Fraud (parallel)
    P->>U: Rule-based credit decision
    U-->>P: Approved / Soft-reject / Hard-reject
    P->>C: Generate sanction/rejection PDF
    C->>P: E-sign
    P->>C: Loan disbursed 🎉
```

---

## Features

| Layer | Capability | How |
|-------|-----------|-----|
| **Conversational Sales** | Two AI personas: *Arjun* (loan specialist) and *Priya* (financial advisor) | LangChain + LLM with structured JSON extraction |
| **Intent Detection** | Classifies user intent before routing (loan, advice, KYC, payment) | LLM + regex fallback, zero hallucination for confirmations |
| **Document Forensics** | OCR + tamper detection on PAN, Aadhaar, salary slips, bank statements | Gemini 2.5 Flash Vision |
| **KYC Verification** | Cross-checks document name against CRM, validates document type per loan tier | Rule-based token overlap |
| **Fraud Screening** | 6-signal risk scoring (name mismatch, income inflation, tampering, etc.) | Deterministic, no LLM overhead |
| **Underwriting** | DTI/FOIR, credit score, employer whitelist, LTV checks, force-reject overrides | Pure rules — transparent and auditable |
| **Multi-Lender Marketplace** | Fetches offers from multiple lenders in parallel, presents best option | `ThreadPoolExecutor` + eligibility scoring |
| **Soft-Reject Negotiation** | Offers restructured terms when the original request exceeds limits | Alternative EMI/amount calculation |
| **Sanction Letter PDF** | Generates legally-formatted PDF sanction/rejection letters | ReportLab |
| **EMI Engine** | Tracks payment history, dynamically adjusts credit score (up for on-time, down for overdue) | In-memory + DB persistence |
| **Real-Time UI** | WebSocket-pushed agent thinking indicators, loan status, notifications | FastAPI WebSocket + React |
| **Admin Dashboard** | Portfolio analytics, lender management, performance metrics | React + Recharts |
| **CRM Sync** | Automatically syncs customer data back to Users collection on every session save | Motor upsert |

---

## Architecture

```mermaid
graph TB
    subgraph Frontend["React Frontend"]
        CP[ChatPane]
        DP[DashboardPane]
        LC[LoanComparisonPane]
        AD[AdminDashboard]
    end

    subgraph API["FastAPI Backend"]
        R[Routers: session, sales, kyc, fraud, underwriting, sanction, admin]
        WS[WebSocket Manager]
    end

    subgraph Agents["LangGraph Agent Pipeline"]
        direction TB
        LS[Load Session]
        IE[Intent Agent]
        SA[Sales Agent<br/>Arjun / Priya]
        DA[Document Agent<br/>Gemini Vision]
        KA[KYC Agent]
        FA[Fraud Agent<br/>6-signal scoring]
        UA[Underwriting Agent<br/>Rule-based]
        SANC[Sanction Agent<br/>PDF generation]
        EMI[EMI Engine]
        RA[Repayment Agent]
    end

    subgraph Data["Data Layer"]
        MG[MongoDB Atlas]
        RD[Redis Cache]
        GS[GridFS]
        MJ[Mock DB<br/>JSON files]
    end

    subgraph External["Mock External APIs"]
        LB[Lender APIs<br/>HDFC, ICICI, Bajaj…]
        CB[CIBIL API]
        DL[DigiLocker API]
        BK[Bank Details API]
        OT[OTP Service]
    end

    subgraph LLM["LLM Providers"]
        G[Gemini<br/>1.5 Flash / 2.5 Flash]
        GQ[Groq<br/>Llama 3.1 8B]
        OR[OpenRouter<br/>Llama 3.3 70B]
    end

    Frontend <--> API
    API --> Agents
    API --> WS
    Agents <--> Data
    Agents --> External
    Agents --> LLM
    External --> LB

    style Frontend fill:#e1f5fe
    style API fill:#fff3e0
    style Agents fill:#f3e5f5
    style Data fill:#e8f5e9
    style External fill:#fce4ec
    style LLM fill:#fff8e1
```

### Data Flow

```mermaid
flowchart LR
    A[Customer types message] --> B[Load Session<br/>MongoDB]
    B --> C[EMI Engine<br/>Check dues]
    C --> D[Supervisor<br/>Deterministic Router]
    D --> E{Intent Agent}
    E -->|loan| F[Sales Agent<br/>Collect terms]
    E -->|advice| F
    E -->|payment| G[Repayment Agent]
    F --> H[Document Agent<br/>OCR + Forensics]
    H --> I[KYC & Fraud<br/>IN PARALLEL]
    I --> J[Join Node]
    J --> K[Underwriting]
    K -->|approve| L[Sanction Letter<br/>PDF]
    K -->|soft_reject| F[Negotiation]
    K -->|hard_reject| L
    L --> M[Advisor Mode<br/>Priya]
    M --> D

    style A fill:#e3f2fd
    style D fill:#fff3e0,stroke:#f57c00
    style K fill:#fce4ec,stroke:#c62828
    style L fill:#e8f5e9,stroke:#2e7d32
```

---

## Repository Structure

```
NBFC/
├── agents/                    # LangGraph agent nodes
│   ├── master_graph.py        # Pipeline graph definition (edges + nodes)
│   ├── master_router.py       # Deterministic rule-based router (NO LLM)
│   ├── master_state.py        # TypedDict schema for full pipeline state
│   ├── session_manager.py     # MongoDB session persistence + CRM sync
│   ├── intent_agent.py        # LLM classifies: loan / advice / kyc / payment
│   ├── sales_agent.py         # Dual persona: Arjun (sales) / Priya (advisor)
│   ├── document_agent.py      # Gemini Vision OCR + forensic extraction
│   ├── document_query_agent.py # Answers "what documents do I need?"
│   ├── kyc_agent.py            # Cross-checks document name vs CRM
│   ├── fraud_agent.py          # 6-signal deterministic fraud scoring
│   ├── underwriting.py         # DTI, credit score, LTV, employer rules
│   ├── sanction_agent.py       # PDF generation via ReportLab
│   ├── emi_engine.py           # Payment simulation + dynamic credit scoring
│   └── repayment_agent.py      # Guides users through EMI payment
│
├── api/                       # FastAPI backend
│   ├── main.py                # App entry, CORS, error handlers, WebSocket
│   ├── config.py              # Pydantic Settings (env-based)
│   ├── routers/               # 12 domain routers
│   │   ├── session.py         # Session CRUD
│   │   ├── sales.py           # Chat endpoint
│   │   ├── documents.py       # Upload endpoint
│   │   ├── kyc.py / fraud.py / underwriting.py
│   │   ├── sanction.py / advisory.py / payment.py
│   │   └── admin.py           # Portfolio analytics
│   ├── schemas/               # Pydantic request/response models
│   └── core/                  # Shared infra
│       ├── websockets.py      # ConnectionManager per session
│       ├── redis_cache.py     # LLM response cache
│       ├── email_service.py   # SMTP notifications
│       └── validation.py      # Robust JSON parser from LLM output
│
├── frontend/                  # React + Vite + Tailwind
│   ├── src/
│   │   ├── App.tsx            # Main chat + dashboard layout
│   │   ├── components/
│   │   │   ├── ChatPane.tsx        # Conversational UI
│   │   │   ├── DashboardPane.tsx   # Loan status cards
│   │   │   ├── LoanComparisonPane.tsx  # Multi-lender offers
│   │   │   ├── AdminAnalytics.tsx  # Portfolio KPIs
│   │   │   └── ... (19 components)
│   │   ├── api/
│   │   │   ├── client.ts          # REST API client
│   │   │   └── websocket.ts       # WebSocket client
│   │   └── types.ts
│   └── package.json
│
├── db/                        # Database layer
│   ├── database.py            # Motor client + collection init + auto-fallback
│   ├── mock_database.py       # JSON file-based mock for dev
│   ├── gridfs_service.py      # Document file storage
│   └── schemas.py             # LoanComparison, LenderOffer, etc.
│
├── mock_apis/                 # Simulated external services
│   ├── lenders.json           # 7+ lender definitions with rates, limits
│   ├── customers.json         # Pre-seeded customer profiles
│   ├── lender_apis.py         # Parallel offer fetch + FOIR eligibility
│   ├── loan_products.py       # Personal, Student, Business, Home loans
│   ├── cibil_api.py           # Credit score simulation
│   ├── digilocker_api.py      # Document verification mock
│   ├── bank_details_api.py    # Account validation
│   └── otp_service.py         # Twilio simulation
│
├── utils/                     # Shared helpers
│   ├── financial_rules.py     # EMI calc, FOIR, pricing rate, fraud score
│   ├── eligibility_checker.py # Product-level eligibility
│   ├── loan_ranker.py         # Multi-lender ranking engine
│   └── pdf_generator.py       # Alternative PDF generation
│
├── tests/
├── config.py                  # LLM fallback chain (Groq → Gemini → OpenRouter)
├── requirements.txt
└── .env.example
```

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Agent Framework** | [LangGraph](https://github.com/langchain-ai/langgraph) | State graph with deterministic routing; no LLM wasted on routing decisions |
| **LLM Providers** | Groq (Llama 3.1 8B) → Gemini (1.5 Flash) → OpenRouter (Llama 3.3 70B) | Automatic fallback chain; starts with cheapest/fastest |
| **Vision** | Gemini 2.5 Flash | Multimodal OCR + tamper detection |
| **Backend** | FastAPI + Uvicorn | Async, auto-docs, WebSocket-native |
| **Frontend** | React 19 + Vite + Tailwind | Fast dev loop, modern CSS utilities |
| **Database** | MongoDB Atlas (Motor) + mock JSON fallback | Document model fits loan data; Motor for async |
| **Cache** | Redis / Memurai | LLM response caching, session TTL |
| **PDF** | ReportLab | Server-side sanction/rejection letters |
| **Real-time** | WebSocket | Agent "thinking" indicators, notifications |

### Why a Deterministic Router Instead of an LLM Supervisor?

The `master_router.py` uses pure rule-based logic (no LLM call) to decide which agent runs next. This was a deliberate design choice:

- **Predictability**: The pipeline is fully deterministic. You can trace exactly why the system moved from KYC to Underwriting.
- **Cost**: Every LLM call costs money and adds latency. The router costs $0.
- **Debuggability**: When a test fails, the route decision is in the action log with a human-readable reasoning string.
- **Parallel execution**: KYC and Fraud agents execute simultaneously because the router knows they're independent.

```python
# Example routing logic (simplified)
if intent == "loan" and not loan_confirmed:
    return "sales_agent", "Gathering loan requirements"
if intent == "loan" and documents_uploaded and kyc == "pending":
    return "verification_agent", "Proceeding to KYC"
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB Atlas account (or local MongoDB)
- At least one LLM API key (Groq is fastest and free)

### Installation

```bash
# 1. Clone
git clone https://github.com/SarangRao20/NBFC.git
cd NBFC

# 2. Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Environment
cp .env.example .env
# Edit .env — at minimum add GROQ_API_KEY or GEMINI_API_KEY

# 4. Frontend
cd frontend && npm install && cd ..
```

### Running

```bash
# Terminal 1 — Backend
python main.py
# → http://localhost:8000 (API)
# → http://localhost:8000/docs (Swagger)

# Terminal 2 — Frontend
cd frontend && npm run dev
# → http://localhost:5173
```

**Without any LLM key**: The system falls back gracefully. The sales agent returns static responses, but the full pipeline (intent → documents → KYC → fraud → underwriting → sanction) still works for testing.

**Without MongoDB**: Set `MONGO_URI=mock` in `.env`. Everything runs on local JSON files.

---

## Configuration

Key environment variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `GROQ_API_KEY` | — | Fastest provider; recommended for dev |
| `GEMINI_API_KEY` | — | Required for document Vision OCR |
| `MONGO_URI` | `mock` | Set to MongoDB Atlas URI for persistence |
| `DISABLE_OTP` | `false` | Set to `true` for dev (uses `123456`) |
| `APP_ENV` | `development` | Set to `production` for deployment |
| `MIN_CREDIT_SCORE` | `700` | Underwriting threshold |
| `MAX_DTI_RATIO` | `0.50` | 50% max debt-to-income |

Full list in `.env.example`.

---

## API & WebSocket Reference

### REST Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/session/start` | Create new loan session |
| `POST` | `/session/{id}/chat` | Send message (triggers pipeline) |
| `POST` | `/upload` | Upload document (PAN, salary slip) |
| `GET` | `/loan/offers` | Fetch multi-lender offers |
| `GET` | `/session/{id}/state` | Get current pipeline state |
| `POST` | `/auth/login` | Customer auth |
| `GET` | `/admin/analytics` | Portfolio metrics |

Full OpenAPI spec at `http://localhost:8000/docs`.

### WebSocket Events

```
ws://localhost:8000/ws/{session_id}

Server → Client:
  { "type": "AGENT_THINKING", "agent": "Arjun", "thinking": true }
  { "type": "NOTIFICATION", "priority": "high", "message": "..." }
  { "type": "AGENT_MESSAGE", "agent": "...", "content": "..." }
```

---

## Example Workflow

```mermaid
sequenceDiagram
    participant User
    participant NBFC
    participant Lender

    User->>NBFC: "Hi, I need a loan"
    NBFC->>NBFC: Intent Agent → "loan"
    NBFC-->>User: "What's the goal for this loan?"
    User->>NBFC: "I want ₹12 lakh for my business"
    NBFC->>NBFC: Sales Agent extracts amount, purpose
    NBFC->>Lender: Fetch offers from 6 lenders (parallel)
    Lender-->>NBFC: 4 offers returned
    NBFC-->>User: "Here are offers from HDFC (13.5%), Bajaj (14%), ICICI (13%)..."
    User->>NBFC: "HDFC looks good"
    NBFC->>NBFC: Selected lender saved
    NBFC-->>User: "Please upload PAN and salary slip"
    User->>NBFC: Uploads documents
    NBFC->>NBFC: Document Agent (Gemini Vision OCR)
    NBFC->>NBFC: KYC + Fraud (parallel)
    NBFC->>NBFC: Underwriting → Approved
    NBFC-->>User: "🎉 Approved! Rate: 13.5%, EMI: ₹38,412"
    NBFC->>NBFC: Generate sanction letter PDF
    NBFC-->>User: "Please e-sign to disburse"
    User->>NBFC: E-signs
    NBFC-->>User: "Loan disbursed! First EMI due Nov 5"
    Note over User,NBFC: Total time: ~4 minutes
```

---

## Underwriting Rules (Deterministic)

The underwriting engine (`agents/underwriting.py` + `utils/financial_rules.py`) uses clear, documented thresholds:

```mermaid
flowchart TD
    A[Applicant] --> B{Credit Score?}
    B -->|< 650| R[Hard Reject]
    B -->|≥ 650| C{Fraud Score?}
    C -->|≥ 0.70| R
    C -->|< 0.70| D{Amount vs<br/>Pre-approved?}
    D -->|≤ limit| E{DTI ≤ 50%?}
    D -->|> limit| F{DTI ≤ 50%?}
    E -->|Yes| G[Approve]
    E -->|No| H[Soft Reject<br/>→ Offer restructured]
    F -->|Yes| G
    F -->|No| I{DTI > 150%?}
    I -->|Yes| R
    I -->|No| H
```

Additional rules:
- Employer whitelist (Google, Microsoft, TCS, etc.) → automatic low risk
- Secured loans (home/car) → LTV check (< 85%)
- Developer override: set `loan_purpose` to `"force reject"` or `principal=99999` to test rejection flow
- Existing EMI burden is tracked and updated dynamically after disbursement

---

## Multi-Lender Marketplace

When a customer confirms loan terms, the system queries all registered lenders in parallel:

```python
with ThreadPoolExecutor(max_workers=len(lender_ids)) as executor:
    futures = {executor.submit(fetch_lender_offer, ...): lid for lid in lender_ids}
```

Each lender (defined in `mock_apis/lenders.json`) has its own:
- Min/max loan amount & tenure
- Base rate + credit-score-based adjustment
- FOIR limit (max EMI/salary ratio)
- Risk profile and approval probability

The best offer (lowest rate) is pre-selected, but the user sees all options and can pick.

---

## Performance & Limitations

### What It Does Well

- **End-to-end loan application in ~4 minutes** (vs 3–7 days manually)
- **No LLM calls for routing** — deterministic router saves ~$0.02 per turn
- **All underwriting is rule-based** — fully auditable, no black-box decisions
- **Works offline** — mock DB + no LLM fallback for pipeline testing
- **Parallel verification** — KYC and fraud run concurrently

### Known Limitations

- **Mock external APIs only** — CIBIL, DigiLocker, bank verification, and lender offers are simulated with JSON files. Replace with real API clients for production.
- **Document OCR is simplified in `document_agent.py`** — the current active code bypasses Gemini Vision and returns hardcoded verification. The full Vision pipeline exists in the commented-out section.
- **No persistent user auth** — sessions are session-based, not JWT. The auth router exists but password hashing and token validation are minimal.
- **Single-process agents** — the LangGraph pipeline runs in-process. For high throughput, you'd decouple agents into separate workers with a message queue.
- **EMI Engine is in-memory** — dynamic credit score changes are persisted to DB but the simulation logic runs on every graph invocation.
- **PDF templates are basic** — ReportLab generates text-heavy documents without branded formatting.

---

## Roadmap

- [ ] Replace mock APIs with real integrations (CIBIL, DigiLocker, GST, UPI)
- [ ] Add JWT-based auth with OAuth2
- [ ] Implement proper job queue (Celery / Redis Queue) for agent workers
- [ ] Add LLM-as-Judge evaluation harness for sales agent responses
- [ ] Support WhatsApp/Telegram channel via Twilio
- [ ] Add A/B testing framework for underwriting rules
- [ ] Build automated repayment pipeline (ACH/NEFT mandate)
- [ ] Add co-lending / syndication support
- [ ] Real-time credit score simulation dashboard for customers

---

## Contributing

Contributions are welcome. The codebase is structured so each agent is independently testable.

### Quick Start for Contributors

```bash
# Run tests
pytest -q

# With coverage
pytest --cov=agents --cov=api --cov-report=html

# Test a specific agent
pytest tests/test_underwriting.py -v

# Lint
ruff check .
```

### Adding a New Agent

1. Create a node function in `agents/your_agent.py`
2. Add routing logic in `agents/master_router.py`
3. Register the node in `agents/master_graph.py`
4. Add the rule to `supervisor_router()` mapping
5. Create an API endpoint in `api/routers/` if it needs external input

### Design Tenets

- **No LLM in routing decisions** — the supervisor router is pure Python. This is not negotiable.
- **Every agent writes to `action_log`** — the full decision trail is visible in the UI.
- **Sessions are resume-able** — any point in the pipeline can be interrupted and restored from MongoDB.
- **Mock before real** — all external integrations have a mock counterpart for offline development.

---

## License

MIT. See `LICENSE` for details.

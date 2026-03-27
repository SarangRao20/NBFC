# NBFC INC — Lending Orchestration & Agent Framework

> End-to-end NBFC lending orchestration platform combining FastAPI backend, modular agent-based decisioning, and a Vite + React frontend. Designed for development with a file-backed mock database and easy switch to MongoDB Atlas, Redis, and LLM providers.

---

## Table of Contents
- Overview
- Quick Start
- Prerequisites
- Installation
- Environment variables (.env)
- Running the backend
- Running with Mock DB (recommended for local dev)
- Running with MongoDB Atlas (production/dev with real DB)
- Frontend (development & build)
- API surface & routers
- Agents & architecture
- Database & persistence
- Mock APIs
- Tests
- Common development workflows
- Debugging & troubleshooting
- Contributing
- License & acknowledgements

---

## Overview

This repository implements a modular loan origination & servicing platform focused on NBFC workflows (sales, KYC, underwriting, sanctions, fraud checks, EMI/payment flows). It uses:

- FastAPI for the backend REST + WebSocket API (`main.py`).
- A collection of domain-specific agents in `agents/` that orchestrate conversational flows, document extraction, and decisioning.
- A Vite + React frontend in `frontend/` for dashboards and flow-driven UIs.
- MongoDB (via Motor) for persistence, with a file-backed `mock_db.json` and `db/mock_database.py` for local development.
- Optional Redis for caching and LLM caching.
- Optional LLM integrations (Gemini, Groq, OpenRouter) controlled by environment variables.

This README documents navigation, installation, and how to run the system both locally (mocked) and with real infra.

---

## Quick Start (local, mock mode)

1. Clone the repo and change directory:

```bash
git clone <YOUR_REPO_URL> nbfc-inc
cd nbfc-inc
```

2. Create and activate a Python virtual environment (Windows PowerShell example):

```powershell
python -m venv venv
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Start the backend in mock mode (no Mongo required):

```powershell
# ensure MONGO_URI is unset or set to 'mock' in .env
python main.py
# or with uvicorn directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. Open API docs: http://localhost:8000/docs

5. (Optional) Start frontend UI:

```bash
cd frontend
npm install
npm run dev
# frontend served at http://localhost:5173 (Vite default)
```

---

## Prerequisites

- Python 3.10+ (3.11 recommended)
- Node.js 18+ (for frontend dev)
- Git
- Optional: MongoDB Atlas (or local Mongo), Redis, SMTP access for emails
- Optional: API keys for LLM providers (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`)

Dependencies are listed in `requirements.txt`.

---

## Installation (detailed)

1. Clone repository.
2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:

- PowerShell:

```powershell
& .\venv\Scripts\Activate.ps1
```

- Command Prompt:

```cmd
.\venv\Scripts\activate.bat
```

- macOS / Linux:

```bash
source venv/bin/activate
```

4. Install Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5. (Optional) Install frontend dependencies:

```bash
cd frontend
npm install
```

---

## Environment variables (.env)

Create a `.env` file in the project root to control runtime behavior. Example minimal `.env` for mock development:

```ini
MONGO_URI=mock
REDIS_HOST=localhost
REDIS_PORT=6379
# LLM providers — leave empty for mock/non-LLM runs
GEMINI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=

# SMTP (email) — optional
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=yourpassword

# Other toggles
DISABLE_OTP=True
```

Important variables:

- `MONGO_URI` — set to a Mongo connection string to use MongoDB. If empty or `mock`, the project uses `db/mock_database.py` with `mock_db.json`.
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` — Redis connection for caching.
- `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` — LLM provider credentials used by `config.py`.
- SMTP variables for sending emails.

Refer to `api/config.py` and `config.py` for additional available settings and defaults.

---

## Running the backend

Run in development (auto-reload):

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# or
python main.py
```

Endpoints:

- OpenAPI docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

WebSocket endpoint for real-time session updates:

```
ws://localhost:8000/ws/{session_id}
```

Notes:

- On startup the app runs `startup_db()` which pings Mongo (or the mock client) and attempts to initialize collections and ancillary services (Redis, email).
- If you do not have Mongo set, the mock DB path will be used (`mock_db.json` in project root).

---

## Running with Mock DB (recommended for local dev)

The repo ships with a robust `db/mock_database.py` implementation that provides asynchronous, file-backed collections and persists to `mock_db.json`.

To run with the mock DB:

```bash
# either leave MONGO_URI unset
# or put in .env:
MONGO_URI=mock
python main.py
```

Advantages:

- No external services required.
- Fast iteration and deterministic testing.

---

## Running with MongoDB Atlas / Production DB

1. Create an Atlas cluster and obtain a connection string.
2. Set `MONGO_URI` in `.env` to the connection string.
3. Start the app normally — `main.py` will call the `init_collections()` helper to create missing collections.

Notes:

- GridFS integration lives in `db/gridfs_service.py` (may require minor adjustments depending on your GridFS client choice).
- Ensure your Atlas user has appropriate privileges for creating collections and writing documents.

---

## Frontend

The frontend is located in `frontend/` and is a Vite + React TypeScript app.

Common commands (from the `frontend` directory):

```bash
npm install
npm run dev    # start development server (Vite)
npm run build  # produce production build
npm run preview
```

Default dev port: `5173` (open `http://localhost:5173`). The backend CORS list in `main.py` already includes common local values.

---

## API surface & routers

The API is implemented with modular routers. Primary router files live in `api/routers/`.

- `session.py` — session lifecycle and flow state
- `sales.py` — loan sales conversational flows
- `documents.py` — file uploads, extraction hooks
- `kyc.py` — KYC-specific endpoints and verification
- `fraud.py` — fraud scoring and checks
- `underwriting.py` — decisioning and score calculations
- `sanction.py` — sanctions checks
- `advisory.py` — advisor/recommendation endpoints
- `payment.py` — EMI and payment endpoints
- `admin.py` — analytics and admin utilities
- `auth.py` — authentication and profile management

Mountpoints and schema validations are defined using Pydantic models in `data/schemas/`.

---

## Agents & Architecture

High-level agent components live under `agents/`. Each file encapsulates a portion of the business logic and may use LLMs, heuristics, or classical rules:

- `sales_agent.py` — conversational sales flow and persuasion loop
- `session_manager.py` — orchestrates session state and dispatches to agents
- `underwriting.py` — underwriting logic and thresholds
- `kyc_agent.py` — KYC extraction & validation
- `document_agent.py`, `document_query_agent.py` — document extraction and query helpers
- `fraud_agent.py` — fraud checks and signals
- `repayment_agent.py` — EMI calculation and repayment scheduling
- `emi_engine.py` — EMI calculation utilities
- `master_router.py`, `master_graph.py`, `master_state.py` — cross-agent routing and shared state

Design notes:

- Agents are designed to accept a `state` dictionary and return a mutated state; see `tests/test_sales_loop.py` for an example of unit-testing an agent loop.
- LLMs are used conservatively; `config.py` implements a provider fallback chain.

---

## Database & Persistence

- Production DB configuration is in `db/database.py` which uses Motor for async connections.
- Local development uses `db/mock_database.py` and `mock_db.json` (file-backed JSON store).
- Uploaded documents are stored via GridFS when using MongoDB production; the `db/gridfs_service.py` contains helpers for that.

---

## Mock APIs

`mock_apis/` contains simple mock endpoints for external integrations used during development and testing:

- `cibil_api.py`, `bank_details_api.py`, `digilocker_api.py`, `lender_apis.py`, `otp_service.py`

These provide predictable responses for flows that require credit bureau lookups, bank account validation, or OTP verification.

---

## Tests

Run the test suite with `pytest`:

```bash
pytest -q
```

Example: the included `tests/test_sales_loop.py` demonstrates an async unit test of `sales_agent_node`.

When running tests in CI or locally, prefer mock mode (`MONGO_URI=mock`) so tests remain deterministic.

---

## Common development workflows

- Add a new endpoint: create a Pydantic `schema` in `data/schemas/`, add a router under `api/routers/`, and include the router in `main.py`.
- Add an agent: implement the agent in `agents/`, write a small async unit test in `tests/`, and invoke it via `session_manager` or a router for integration testing.
- Switch DB: change `MONGO_URI` in `.env` between `mock` and your Atlas connection string.

---

## Debugging & troubleshooting

Common issues and fixes:

- Mongo connection failures:
  - If `MONGO_URI` is not set, the app uses mock DB. To use real Mongo, set `MONGO_URI` to your Atlas URI.
  - Ensure your IP whitelist and user permissions are correct in Atlas.
- Redis connection failures:
  - The code will fall back gracefully to a DB-backed cache in many places. Make sure `REDIS_HOST/REDIS_PORT` are correct.
- LLM provider errors:
  - If you see import or provider-auth errors, set `GEMINI_API_KEY`, `GROQ_API_KEY`, or `OPENROUTER_API_KEY` in `.env`.
  - The fallback chain is implemented in `config.py` and prints which provider it selects at runtime.
- Email / SMTP issues:
  - Verify `SMTP_USER` / `SMTP_PASSWORD` and consider using an app-specific password if using Google SMTP.

Logs: The app prints helpful status messages on startup (Mongo ping, Redis, email service). If you hit an unhandled exception, `main.py` logs full tracebacks to the terminal.

---

## Contributing

1. Fork the repo and create a feature branch: `feature/your-feature`.
2. Implement code and add tests where applicable.
3. Run `pytest` and ensure lint passes for your changes.
4. Open a PR against `main` with a concise description and testing notes.

Please follow repository coding style and keep changes isolated to the feature scope.

---

## Files of interest (quick links)

- [main.py](main.py) — FastAPI app entrypoint and router mounting
- [requirements.txt](requirements.txt) — Python dependencies
- [config.py](config.py) — LLM & global configuration
- [api/config.py](api/config.py) — FastAPI settings and environment bindings
- [db/mock_database.py](db/mock_database.py) — File-backed mock DB used by default
- `agents/` — Agent implementations (sales, underwriting, kyc, fraud, etc.)
- `mock_apis/` — Local mocks for external integrations
- `frontend/` — Vite + React frontend (dev/build scripts in `package.json`)

---

## Acknowledgements

This project stitches together several libraries (FastAPI, Motor, LangChain adapters, Vite) into a developer-friendly NBFC workflow demo. See individual module comments for more implementation notes.

---

If you'd like, I can also:

- Add a short `DEVELOPMENT.md` with step-by-step contributor workflows.
- Create a minimal `.env.example` file pre-populated with recommended defaults.

Enjoy developing — open an issue or PR for any missing documentation or clarifications.

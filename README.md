# FinServe NBFC - Intelligent Loan Origination & Management Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-red.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2.4-blue.svg)](https://reactjs.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green.svg)](https://www.mongodb.com/atlas)

> **Modern NBFC lending platform** with AI-powered agents, real-time decisioning, and seamless customer experience. Built for scalability, compliance, and rapid deployment.

---

## Business Overview

FinServe NBFC is a comprehensive **Non-Banking Financial Company** management system that orchestrates the entire loan lifecycle from customer acquisition to repayment. The platform leverages:

- **AI-Powered Agents** for intelligent decisioning and customer interaction
- **Real-time Analytics** for risk assessment and portfolio management
- **Enterprise Security** with fraud detection and compliance checks
- **High-Performance Architecture** built on FastAPI and React
- **Cloud-Ready** deployment with MongoDB Atlas and Redis caching

### Key Features

| Feature | Description | Technology |
|---------|-------------|------------|
| **Conversational AI Sales** | Intelligent loan advisory with natural language processing | LangChain + LLMs |
| **Automated Underwriting** | Real-time credit scoring and risk assessment | Custom ML models |
| **Digital KYC** | Document extraction and verification with OCR | Computer Vision APIs |
| **Fraud Detection** | Multi-layer security with behavioral analysis | Rule-based + ML |
| **Multi-Lender Marketplace** | Connect borrowers with optimal loan products | Aggregator Engine |
| **EMI Management** | Flexible repayment scheduling and tracking | Automated Calculators |
| **Admin Dashboard** | Real-time portfolio analytics and oversight | React + Recharts |

---

## Quick Start

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** and npm
- **MongoDB Atlas** (or local MongoDB)
- **Redis** (optional, for caching)
- **Git** for version control

### Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/SarangRao20/NBFC.git
   cd NBFC
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate (Windows PowerShell)
   & .\venv\Scripts\Activate.ps1
   
   # Install dependencies
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your configuration
   # See Environment Variables section below
   ```

4. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

### Running the Application

#### Development Mode (Local)
```bash
# Backend (Terminal 1)
cd NBFC
python main.py
# Backend will be available at http://localhost:8000

# Frontend (Terminal 2)
cd NBFC/frontend
npm run dev
# Frontend will be available at http://localhost:5173
```

#### Production Mode
```bash
# Set production environment variables
export APP_ENV=production
export MONGO_URI=mongodb+srv://...

# Start production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Environment Configuration

Create a `.env` file in the project root:

```ini
# ===========================================
# FINSERVE NBFC CONFIGURATION
# ===========================================

# LLM PROVIDERS
# Choose one or more: Gemini, Groq, OpenRouter
GEMINI_API_KEY=your-google-gemini-key
GROQ_API_KEY=your-groq-api-key
OPENROUTER_API_KEY=your-openrouter-key

# DATABASE CONFIGURATION
# Production: MongoDB Atlas connection string
# Development: Set to 'mock' for local file-based DB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority

# REDIS CACHING (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_CACHE_TTL=3600

# EMAIL NOTIFICATIONS
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@company.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@finserve-nbfc.com
EMAIL_FROM_NAME=FinServe NBFC

# SMS/OTP (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890

# FILE STORAGE
UPLOAD_DIR=data/uploads
SANCTION_DIR=data/sanctions

# DEVELOPMENT SETTINGS
DEBUG=true
DISABLE_OTP=true
DEV_OTP=123456
APP_NAME=FinServe NBFC
APP_VERSION=1.0.0
APP_ENV=development

# UNDERWRITING & RISK
MIN_CREDIT_SCORE=700
MAX_DTI_RATIO=0.50
MAX_EXPOSURE_MULTIPLIER=2.0
MAX_NEGOTIATION_ROUNDS=3
```

### Critical Configuration Notes

- **`MONGO_URI=mock`** enables local development with file-based storage
- **Always set `APP_ENV=production`** for production deployments
- **LLM Keys** are optional but required for AI-powered features
- **Security**: Never commit `.env` file to version control

---

## Architecture Overview

```bash
┌─────────────────────────────────────────────────────────────┐
│                 FRONTEND (React)                │
│  ┌─────────────────────────────────────────────┐    │
│  │ Customer Dashboard │ Loan Application │    │
│  │ Admin Panel      │ Analytics UI    │    │
│  └─────────────────────────────────────────────┘    │
│                     ↕ WebSocket (Real-time)        │
├─────────────────────────────────────────────────────────────┤
│              BACKEND (FastAPI)              │
│  ┌─────────────────────────────────────────────┐    │
│  │ AGENTS LAYER                     │    │
│  │ Sales │ KYC │ Underwriting │ Fraud │    │
│  └─────────────────────────────────────────────┘    │
│                     ↕ REST API                   │
├─────────────────────────────────────────────────────────────┤
│            DATA LAYER                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ MongoDB Atlas │ Redis Cache │ GridFS │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### Backend Services (`/api`)
- **`routers/`** - Modular API endpoints for each domain
- **`schemas/`** - Pydantic models for request/response validation
- **`core/`** - Shared utilities (email, exceptions, websockets)

#### Agent System (`/agents`)
- **`sales_agent.py`** - Conversational AI for loan advisory and sales
- **`underwriting.py`** - Credit scoring engine
- **`kyc_agent.py`** - Digital KYC processing
- **`fraud_agent.py`** - Fraud detection system
- **`document_agent.py`** - OCR & document processing
- **`repayment_agent.py`** - EMI calculation and payment processing

#### Data Layer (`/db`, `/mock_apis`)
- **`database.py`** - MongoDB connection and collection management
- **`mock_database.py`** - Local development with JSON file storage
- **`lender_apis.py`** - Multi-lender integration and offer aggregation

---

## API Documentation

### Base URLs
- **Production**: `https://api.finserve-nbfc.com`
- **Development**: `http://localhost:8000`
- **API Docs**: `http://localhost:8000/docs` (Swagger/OpenAPI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

### Key Endpoints

| Module | Endpoint | Description |
|--------|----------|-------------|
| **Authentication** | `POST /auth/login` | Customer authentication and session creation |
| **Sessions** | `POST /session/start` | Initialize new loan session |
| **Sales Chat** | `POST /session/{id}/chat` | Conversational AI interface |
| **Document Upload** | `POST /session/{id}/upload` | KYC document submission |
| **Underwriting** | `POST /session/{id}/underwrite` | Credit decision engine |
| **Sanctions** | `GET /session/{id}/sanction` | Loan agreement generation |
| **Analytics** | `GET /admin/analytics` | Portfolio and performance metrics |

### WebSocket Integration

Real-time updates for loan processing status:
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

// Events: 'thinking', 'document_processed', 'decision_ready', 'loan_approved'
```

---

## Security & Compliance

### Risk Assessment Engine

- **Credit Score Integration**: CIBIL and other bureau data
- **DTI Calculation**: Debt-to-Income ratio analysis
- **Fraud Detection**: Behavioral pattern analysis
- **Document Verification**: OCR with tampering detection

### Compliance Features

- **AML/Sanctions Checks**: Integrated sanctions list verification
- **Data Encryption**: End-to-end encryption for sensitive data
- **Audit Logging**: Complete traceability of all actions
- **Role-Based Access**: Granular permissions for admin functions

### Security Best Practices

```python
# Example: Secure session management
async def create_session(customer_id: str):
    session_id = generate_secure_uuid()
    await redis.setex(f"session:{session_id}", 3600, json.dumps({
        'customer_id': customer_id,
        'created_at': datetime.utcnow().isoformat(),
        'ip_address': hash_ip(request.client.host)
    }))
    return session_id
```

---

## Performance & Scalability

### Caching Strategy

- **Redis**: Session caching and LLM response caching
- **MongoDB Indexes**: Optimized queries for high-volume access
- **Connection Pooling**: Efficient database connection management

### Monitoring & Analytics

```python
# Built-in performance metrics
METRICS = {
    'loan_processing_time': 'avg_time_from_application_to_decision',
    'conversion_rate': 'applications_to_approvals_ratio',
    'fraud_detection_accuracy': 'false_positives_rate',
    'system_uptime': 'service_availability_percentage'
}
```

---

## Testing & Quality Assurance

### Test Suite

```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=agents --cov=api --cov-report=html

# Specific test modules
pytest tests/test_sales_loop.py -v
pytest tests/test_underwriting.py -v
```

### Test Coverage Areas

- **Unit Tests**: Individual agent logic and utilities
- **Integration Tests**: API endpoint workflows
- **E2E Tests**: Complete loan application flows
- **Performance Tests**: Load testing for concurrent users

### Mock Services

The `/mock_apis` directory provides deterministic mocks for:
- **Credit Bureau APIs** (CIBIL scores and reports)
- **Bank Verification APIs** (Account validation)
- **Lender APIs** (Loan offer aggregation)
- **SMS/OTP Services** (Twilio simulation)

---

## Deployment Guide

### Production Deployment

#### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t finserve-nbfc .
docker run -p 8000:8000 -e MONGO_URI=$MONGO_URI finserve-nbfc
```

#### Cloud Deployment (Render/Vercel)

**Backend (Render)**:
```yaml
# render.yaml
services:
  type: web
  name: finserve-nbfc-api
  env: python
  buildCommand: pip install -r requirements.txt
  startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
  envVars:
    - key: MONGO_URI
      value: mongodb+srv://...
    - key: APP_ENV
      value: production
```

**Frontend (Vercel)**:
```json
// vercel.json
{
  "builds": [{
    "src": "frontend/package.json",
    "use": "@vercel/static-build",
    "config": { "distDir": "dist" }
  }],
  "routes": [{
    "src": "/(.*)",
    "dest": "/$1"
  }]
}
```

### Environment-Specific Configurations

| Environment | Database | Caching | Debug |
|------------|----------|----------|--------|
| Development | mock_db.json | Redis (local) | True |
| Staging | MongoDB Atlas | Redis (cloud) | False |
| Production | MongoDB Atlas | Redis (cloud) | False |

---

## Development Workflow

### Adding New Features

1. **Backend API Endpoint**
   ```python
   # 1. Create schema in data/schemas/
   class LoanApplication(BaseModel):
       amount: float
       tenure: int
       purpose: str
   
   # 2. Create router in api/routers/
   @router.post("/loan/apply")
   async def apply_loan(data: LoanApplication):
       return await process_application(data)
   
   # 3. Register in main.py
   app.include_router(loan_router, prefix="/api/v1")
   ```

2. **New Agent**
   ```python
   # agents/new_agent.py
   async def new_agent_node(state: dict) -> dict:
       # Process state
       result = await process_logic(state)
       
       # Return updated state
       return {
           **state,
           "new_agent_result": result,
           "action_log": state.get("action_log", []) + ["New agent processed"]
       }
   ```

3. **Frontend Component**
   ```typescript
   // frontend/src/components/NewComponent.tsx
   import React, { useState, useEffect } from 'react';
   
   const NewComponent: React.FC = () => {
     const [data, setData] = useState(null);
     
     useEffect(() => {
       // Fetch data from API
       fetchData('/api/endpoint').then(setData);
     }, []);
     
     return <div>{/* Component JSX */}</div>;
   };
   export default NewComponent;
   ```

### Code Quality Standards

- **Python**: Follow PEP 8, use type hints, document with docstrings
- **TypeScript**: Strict mode, proper interface definitions
- **Testing**: Minimum 80% coverage for new features
- **Security**: All user inputs must be validated and sanitized

---

## Contributing

We welcome contributions! Please follow our guidelines:

### Development Process

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-username/NBFC.git
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Develop & Test**
   - Write clean, documented code
   - Add comprehensive tests
   - Ensure all tests pass: `pytest -q`
   - Check coverage: `pytest --cov=.`

4. **Submit Pull Request**
   - Provide clear description of changes
   - Link relevant issues
   - Ensure CI/CD passes

### Code Standards

- **Python**: Follow PEP 8, use Black for formatting
- **TypeScript**: Use Prettier, strict TypeScript mode
- **Commits**: Conventional commit format (`feat:`, `fix:`, `docs:`)
- **Documentation**: Update README for new features

### Bug Reports

- Use GitHub Issues with detailed reproduction steps
- Include environment details and logs
- Provide expected vs actual behavior

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### Commercial Use

For commercial deployment or enterprise support:
- **Email**: business@finserve-nbfc.com
- **Website**: https://finserve-nbfc.com
- **Support**: +91-XXX-XXX-XXXX

---

## Acknowledgments

Built with modern fintech best practices and these amazing technologies:

- **[FastAPI](https://fastapi.tiangolo.com)** - Modern, fast web framework
- **[React](https://reactjs.org)** - User interface library
- **[MongoDB](https://www.mongodb.com)** - Document database
- **[LangChain](https://langchain.com)** - LLM orchestration
- **[Vite](https://vitejs.dev)** - Build tool and dev server
- **[Tailwind CSS](https://tailwindcss.com)** - Utility-first CSS framework

Special thanks to the open-source community and contributors who make this project possible.

---

## Contact & Support

| Channel | Details |
|---------|----------|
| **Documentation** | https://docs.finserve-nbfc.com |
| **API Support** | api-support@finserve-nbfc.com |
| **Business** | business@finserve-nbfc.com |
| **Issues** | https://github.com/SarangRao20/NBFC/issues |
| **Live Demo** | https://nbfc-inc.onrender.com |

---

<div align="center">
  <strong>FinServe NBFC - Intelligent Lending for Modern Finance</strong>
  <br/>
  <em>Built with ❤️ for the future of fintech</em>
</div>

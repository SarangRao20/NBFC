# NBFC Loan Processing — Implementation Plan

## System Overview (Simple)

A LangGraph `StateGraph` with 6 nodes running sequentially. Each node is a **plain Python function** that takes state, collects data via `input()`, calls mock APIs, and returns updated fields.

```
User → SalesAgent → RegistrationAgent → VerificationAgent → FraudAgent → UnderwritingAgent → SanctionAgent → PDF
```

---

## Project Structure

```
NBFCs/
├── .env                          # API keys
├── requirements.txt
├── main.py                       # LangGraph graph + entry point
├── state.py                      # Shared LoanState TypedDict
├── agents/
│   ├── sales_agent.py            # Collect loan type, amount, tenure
│   ├── registration_agent.py     # ★ Detailed below
│   ├── verification_agent.py     # KYC stub
│   ├── fraud_agent.py            # Risk scoring stub
│   ├── underwriting_agent.py     # Decision stub
│   └── sanction_agent.py         # PDF generation
├── mock_apis/
│   ├── abc_id_api.py             # Student ID verification
│   ├── bank_details_api.py       # Bank lookup by name
│   └── otp_service.py            # Simulated OTP
└── utils/
    └── validators.py             # PAN, phone, email validators
```

---

## Registration Agent — Detailed Plan

### What It Does

Collects user profile data, verifies phone via OTP, fetches bank details, verifies student ABC ID (if student loan), and sets a security PIN.

---

### Step-by-Step Flow

```
Step 1 → Collect name, phone, email
Step 2 → Send OTP to phone → verify OTP  (mock_apis/otp_service.py)
Step 3 → Collect employment type + monthly income
Step 4 → Capture PAN number (just store, no verify)
Step 5 → IF student loan → collect ABC ID → verify  (mock_apis/abc_id_api.py)
Step 6 → Collect bank name → fetch details  (mock_apis/bank_details_api.py)
Step 7 → Set 4-digit PIN (enter + confirm + hash)
Step 8 → Return all fields to state
```

---

### File 1: `mock_apis/otp_service.py` — OTP Verification

| Detail | Value |
|--------|-------|
| OTP length | 6 digits |
| Delivery | Printed to console (simulated SMS) |
| Expiry | 5 minutes |
| Max wrong attempts | 3 (then must resend) |
| Max resends | 5 per phone |

**Functions:**
- `send_otp(phone)` → generates OTP, stores in dict, prints to console, returns `{"sent": True}`
- `verify_otp(phone, user_otp)` → checks match + expiry + attempts, returns `{"verified": True/False}`

**Storage:** In-memory dict → `{ phone: { otp, expires_at, attempts } }`

---

### File 2: `mock_apis/abc_id_api.py` — Student ID Verification

> Only called when `loan_type == "student"`

**Mock database** — hardcoded dict of 5-6 ABC IDs:

```
"ABC123456" → { name: "Rahul Sharma",  university: "IIT Delhi",   status: "active" }
"ABC789012" → { name: "Priya Patel",   university: "NIT Trichy",  status: "active" }
"ABC345678" → { name: "Amit Kumar",    university: "BITS Pilani", status: "inactive" }
```

**Function:** `verify_abc_id(abc_id)`
- ✅ Found + active → `{"verified": True, "student_name": "...", "university": "..."}`
- ❌ Not found → `{"verified": False, "error": "ABC ID not found"}`
- ❌ Inactive → `{"verified": False, "error": "ABC ID is inactive"}`

---

### File 3: `mock_apis/bank_details_api.py` — Bank Details Lookup

**Mock database** — dict of 8-10 Indian banks:

```
"sbi"   → { full_name: "State Bank of India", ifsc_prefix: "SBIN0", account_length: 11 }
"hdfc"  → { full_name: "HDFC Bank",           ifsc_prefix: "HDFC0", account_length: 14 }
"icici" → { full_name: "ICICI Bank",           ifsc_prefix: "ICIC0", account_length: 12 }
...
```

**Function:** `get_bank_details(bank_name)`
- Normalizes input (lowercase, strip) for fuzzy matching
- Generates a random account number matching the bank's format
- Returns `{"bank_name": "...", "account_number": "...", "ifsc": "..."}`
- Unknown bank → `{"error": "Bank not found"}`

---

### File 4: PIN Setting (inside `registration_agent.py`)

| Detail | Value |
|--------|-------|
| PIN length | 4 digits |
| Input | Masked prompts — enter PIN + confirm PIN |
| Hashing | SHA-256 (simple prototype hash) |
| Option | "Use existing bank PIN?" — if yes, asks for bank PIN instead |
| Storage | `pin_hash` field in state |

**Logic:**
1. Ask: "Set a new PIN or use your bank account PIN? (new/bank)"
2. If `new` → prompt PIN → prompt confirm → must match → hash → store
3. If `bank` → prompt bank PIN → hash → store

---

### File 5: `agents/registration_agent.py` — Main Orchestrator

```python
def registration_node(state: LoanState) -> dict:
    """
    1. print welcome banner
    2. collect name, phone, email (with validation)
    3. call send_otp(phone) → print OTP to console
    4. loop: ask user for OTP → call verify_otp() → max 3 tries
    5. collect employment_type (salaried/self-employed)
    6. collect monthly_income (validate > 0)
    7. collect PAN (validate format: ABCDE1234F)
    8. if loan_type == "student":
           collect abc_id → call verify_abc_id()
    9. collect bank_name → call get_bank_details()
    10. set PIN (new or bank) → hash → store
    11. return updated state dict
    """
```

**Validation rules:**
- Phone: 10 digits, starts with 6-9
- Email: basic `@` + `.` check (optional field)
- PAN: `[A-Z]{5}[0-9]{4}[A-Z]` regex
- Income: positive number
- PIN: exactly 4 digits

---

### File 6: `utils/validators.py`

Simple functions, each returns `(is_valid: bool, error_msg: str)`:
- `validate_phone(phone)`
- `validate_email(email)`
- `validate_pan(pan)`
- `validate_pin(pin)`

---

## Other Agents (Stubs)

| Agent | What the stub does |
|-------|-------------------|
| **SalesAgent** | `input()` for loan_type, amount, tenure; calculates interest rate |
| **VerificationAgent** | Checks PAN format, sets `kyc_status = "verified"` |
| **FraudAgent** | Rule-based score (high income + low amount = low risk) |
| **UnderwritingAgent** | Simple DTI check → approve/reject |
| **SanctionAgent** | Generates a text-based sanction letter (or PDF with `fpdf2`) |

---

## Verification Plan

```bash
# Run the full pipeline interactively
cd c:\Users\Lenovo\Desktop\NBFCs
python main.py

# Test: Happy path (personal loan)
# Test: Student loan with ABC ID
# Test: Wrong OTP → retry
# Test: Unknown bank name → error + retry
# Test: PIN mismatch → re-enter
```

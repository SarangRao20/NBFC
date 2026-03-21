"""End-to-end workflow test for the NBFC FastAPI backend."""
import requests, sys
import json
import time
import os

BASE = "http://localhost:8000"

def test(step, method, url, json_data=None, files=None, expect_key=None):
    fn = getattr(requests, method)
    try:
        if files:
            r = fn(url, files=files)
        elif json_data:
            r = fn(url, json=json_data)
        else:
            r = fn(url)
        
        ok = r.status_code == 200
        data = r.json()
        val = data.get(expect_key, "") if expect_key else ""
        status = "PASS" if ok else "FAIL"
        print(f"  {status} Step {step}: {r.status_code} | {expect_key}={str(val)[:60]}")
        if not ok:
            print(f"     ERROR: {data}")
        return data, ok
    except Exception as e:
        print(f"  FAIL Step {step}: Exception - {str(e)}")
        return {}, False

print("=" * 60)
print("NBFC Workflow End-to-End Test")
print("=" * 60)

# Ensure mock file exists
mock_file_path = "data/uploads/mock_salary_slip.pdf"
if not os.path.exists(mock_file_path):
    os.makedirs(os.path.dirname(mock_file_path), exist_ok=True)
    with open(mock_file_path, "w") as f:
        f.write("Mock Salary Slip Content")

d, _ = test("1 ", "post", f"{BASE}/session/start", expect_key="session_id")
sid = d["session_id"]

test("2 ", "post", f"{BASE}/session/{sid}/identify-customer",
     json_data={"phone": "9876543210"}, expect_key="message")

d, _ = test("3 ", "post", f"{BASE}/session/{sid}/capture-loan",
     json_data={"loan_type": "personal", "loan_amount": 200000, "tenure_months": 24}, expect_key="emi")

test("5 ", "post", f"{BASE}/session/{sid}/request-documents", expect_key="required_documents")

# Step 6: OCR Extraction (Requires File Upload)
with open(mock_file_path, "rb") as f:
    test("6 ", "post", f"{BASE}/session/{sid}/extract-ocr",
         files={"file": ("salary_slip.pdf", f, "application/pdf")},
         expect_key="document_type")

test("7 ", "post", f"{BASE}/session/{sid}/check-tampering", expect_key="risk_assessment")
test("8 ", "post", f"{BASE}/session/{sid}/verify-income", expect_key="income_verified")
test("9 ", "post", f"{BASE}/session/{sid}/kyc-verify", expect_key="kyc_status")
test("10", "post", f"{BASE}/session/{sid}/fraud-check", expect_key="fraud_score")

d, _ = test("11", "post", f"{BASE}/session/{sid}/underwrite", expect_key="decision")
decision = d["decision"]

if decision == "soft_reject":
    test("12", "post", f"{BASE}/session/{sid}/persuasion/analyze", expect_key="dti_current")
    test("13", "post", f"{BASE}/session/{sid}/persuasion/suggest", expect_key="options")
    test("14", "post", f"{BASE}/session/{sid}/persuasion/respond",
         json_data={"action": "accept_option_a"}, expect_key="next_step")
    d, _ = test("11R", "post", f"{BASE}/session/{sid}/underwrite", expect_key="decision")
    decision = d["decision"]

if decision == "approve":
    test("16", "post", f"{BASE}/session/{sid}/sanction", expect_key="sanction_pdf_path")

test("17", "post", f"{BASE}/session/{sid}/advisory", expect_key="advisory_message")
test("4 ", "get", f"{BASE}/session/{sid}/state", expect_key="current_phase")

d, _ = test("18", "post", f"{BASE}/session/{sid}/end", expect_key="status")
print(f"\n  Phases traversed: {len(d['phase_history'])}")
print("\n" + "=" * 60)
print("ALL WORKFLOW STEPS EXECUTED")
print("=" * 60)


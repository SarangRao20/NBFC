import requests

base_url = "http://localhost:8000"

# 1. Start session
print("Starting session...")
res = requests.post(f"{base_url}/session/start", json={"phone": "1234567890"})
session_id = res.json()["session_id"]
print(f"Session ID: {session_id}")

# 2. Extract OCR
print("Testing extract-ocr...")
with open("test.pdf", "wb") as f:
    f.write(b"dummy pdf content")

with open("test.pdf", "rb") as f:
    files = {"file": ("test.pdf", f, "application/pdf")}
    res = requests.post(f"{base_url}/session/{session_id}/extract-ocr", files=files)
    
print("extract-ocr STATUS:", res.status_code)
if res.status_code != 200:
    print("extract-ocr BODY:", res.text)
    exit()

# 3. Check Tampering
print("Testing check-tampering...")
res = requests.post(f"{base_url}/session/{session_id}/check-tampering")
print("check-tampering STATUS:", res.status_code)
if res.status_code != 200:
    print("check-tampering BODY:", res.text)
    exit()

# 4. Verify Income
print("Testing verify-income...")
res = requests.post(f"{base_url}/session/{session_id}/verify-income")
print("verify-income STATUS:", res.status_code)
if res.status_code != 200:
    print("verify-income BODY:", res.text)
    exit()

# 5. KYC Verify
print("Testing kyc-verify...")
res = requests.post(f"{base_url}/session/{session_id}/kyc-verify")
print("kyc-verify STATUS:", res.status_code)
if res.status_code != 200:
    print("kyc-verify BODY:", res.text)
    exit()

# 6. Fraud Check
print("Testing fraud-check...")
res = requests.post(f"{base_url}/session/{session_id}/fraud-check")
print("fraud-check STATUS:", res.status_code)
if res.status_code != 200:
    print("fraud-check BODY:", res.text)
    exit()

print("All endpoints succeeded!")

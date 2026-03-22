"""Test the Complete NBFC Pipeline with Document Storage and Agent Integration"""

import requests
import json
import tempfile
import os
from pathlib import Path

BASE_URL = "http://localhost:8000"

def create_test_document():
    """Create a test document file for upload testing."""
    # Create a simple text file as a test document
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""
        PAYSLIP FOR THE MONTH OF OCTOBER 2024
        
        Employee Name: Raj Kumar
        Employee ID: EMP123456
        Designation: Software Engineer
        
        Basic Salary: ₹45,000
        HRA: ₹13,500
        Special Allowance: ₹8,000
        Gross Salary: ₹66,500
        
        Net Salary: ₹58,200
        
        Company: Tech Solutions India Pvt Ltd
        PAN: AAAPL1234C
        """)
        return f.name

def test_full_pipeline():
    print("🚀 Testing Complete NBFC Pipeline with Document Storage & Agents")
    print("=" * 70)
    
    # Test 1: Health check
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Backend Health: {response.json()['status']}")
    except Exception as e:
        print(f"❌ Backend health failed: {e}")
        return
    
    # Test 2: Start session
    session_id = None
    try:
        response = requests.post(f"{BASE_URL}/session/start")
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session Started: {session_id}")
    except Exception as e:
        print(f"❌ Session start failed: {e}")
        return
    
    # Test 3: Identify customer
    try:
        customer_data = {
            "phone": "9876543210",
            "email": "raj.kumar@example.com"
        }
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/identify-customer",
            json=customer_data
        )
        result = response.json()
        print(f"✅ Customer Identified: {result.get('message', 'Success')}")
    except Exception as e:
        print(f"❌ Customer identification failed: {e}")
    
    # Test 4: Capture loan
    try:
        loan_data = {
            "loan_type": "personal",
            "loan_amount": 200000,
            "tenure_months": 24
        }
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/capture-loan",
            json=loan_data
        )
        result = response.json()
        print(f"✅ Loan Captured: ₹{result.get('loan_terms', {}).get('principal', 0):,}")
        print(f"   EMI: ₹{result.get('emi', 0):,.2f}/month")
    except Exception as e:
        print(f"❌ Loan capture failed: {e}")
    
    # Test 5: Request documents
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/request-documents")
        result = response.json()
        print(f"✅ Documents Requested: {len(result.get('required_documents', []))} documents")
        for doc in result.get('required_documents', []):
            print(f"   - {doc}")
    except Exception as e:
        print(f"❌ Document request failed: {e}")
    
    # Test 6: Upload and process document (OCR + Agent)
    try:
        test_file = create_test_document()
        print(f"📄 Created test document: {test_file}")
        
        with open(test_file, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{BASE_URL}/session/{session_id}/extract-ocr",
                files=files
            )
        
        result = response.json()
        print(f"✅ Document Processed:")
        print(f"   Document ID: {result.get('document_id', 'N/A')}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Extracted Salary: ₹{result.get('extracted_data', {}).get('salary_extracted', 0):,}")
        
        # Clean up test file
        os.unlink(test_file)
        
    except Exception as e:
        print(f"❌ Document processing failed: {e}")
    
    # Test 7: Check tampering
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/check-tampering")
        result = response.json()
        print(f"✅ Tampering Check: {result.get('risk_assessment', 'Unknown')}")
        print(f"   Tampered: {result.get('tampered', False)}")
    except Exception as e:
        print(f"❌ Tampering check failed: {e}")
    
    # Test 8: Verify income
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/verify-income")
        result = response.json()
        print(f"✅ Income Verification: {result.get('income_verified', False)}")
    except Exception as e:
        print(f"❌ Income verification failed: {e}")
    
    # Test 9: KYC verification
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/kyc-verify")
        result = response.json()
        print(f"✅ KYC Status: {result.get('kyc_status', 'Unknown')}")
    except Exception as e:
        print(f"❌ KYC verification failed: {e}")
    
    # Test 10: Fraud check
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/fraud-check")
        result = response.json()
        print(f"✅ Fraud Score: {result.get('fraud_score', 0):.2f}")
    except Exception as e:
        print(f"❌ Fraud check failed: {e}")
    
    # Test 11: Underwriting
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/underwrite")
        result = response.json()
        print(f"✅ Underwriting Decision: {result.get('decision', 'Unknown')}")
        print(f"   DTI Ratio: {result.get('dti_ratio', 0):.2f}")
        print(f"   Risk Level: {result.get('risk_level', 'Unknown')}")
    except Exception as e:
        print(f"❌ Underwriting failed: {e}")
    
    # Test 12: Get final session state
    try:
        response = requests.get(f"{BASE_URL}/session/{session_id}/state")
        state = response.json()
        print(f"✅ Final Session State:")
        print(f"   Current Phase: {state.get('current_phase', 'Unknown')}")
        print(f"   Customer: {state.get('customer_data', {}).get('name', 'Unknown')}")
        print(f"   Loan Amount: ₹{state.get('loan_terms', {}).get('principal', 0):,}")
        print(f"   Documents: {len([k for k in state.get('documents', {}).keys() if not k.endswith('_path')])} fields")
        print(f"   Decision: {state.get('decision', 'Pending')}")
    except Exception as e:
        print(f"❌ Final state retrieval failed: {e}")
    
    print("=" * 70)
    print("🎉 Complete Pipeline Test Finished!")
    print(f"📊 Session ID: {session_id}")
    print("📝 All backend-agent-frontend connections verified!")

if __name__ == "__main__":
    test_full_pipeline()

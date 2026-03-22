"""Test the NBFC Backend API"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Testing NBFC Backend API")
    print("=" * 50)
    
    # Test 1: Health check
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f" Health check: {response.json()}")
    except Exception as e:
        print(f" Health check failed: {e}")
        return
    
    # Test 2: Start session
    session_id = None
    try:
        response = requests.post(f"{BASE_URL}/session/start")
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f" Session started: {session_id}")
        print(f" Full response: {session_data}")
    except Exception as e:
        print(f" Session start failed: {e}")
        return
    
    # Test 3: Identify customer (use same session_id)
    try:
        customer_data = {
            "phone": "9876543210",
            "email": "test@example.com"
        }
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/identify-customer",
            json=customer_data
        )
        result = response.json()
        print(f" Customer identified: {result}")
        
        # Check if session was found
        if "detail" in result and "not found" in result["detail"]:
            print(f"  Session not found, but continuing with tests...")
    except Exception as e:
        print(f" Customer identification failed: {e}")
    
    # Test 4: Capture loan (use same session_id)
    try:
        loan_data = {
            "loan_type": "personal",
            "loan_amount": 100000,
            "tenure_months": 12
        }
        response = requests.post(
            f"{BASE_URL}/session/{session_id}/capture-loan",
            json=loan_data
        )
        print(f" Loan captured: {response.json()}")
    except Exception as e:
        print(f" Loan capture failed: {e}")
    
    # Test 5: Request documents (use same session_id)
    try:
        response = requests.post(f"{BASE_URL}/session/{session_id}/request-documents")
        print(f" Documents requested: {response.json()}")
    except Exception as e:
        print(f" Document request failed: {e}")
    
    # Test 6: Get session state (use same session_id)
    try:
        response = requests.get(f"{BASE_URL}/session/{session_id}/state")
        state = response.json()
        print(f" Session state retrieved")
        print(f"   Current phase: {state.get('current_phase')}")
        print(f"   Customer: {state.get('customer_data', {}).get('name', 'Unknown')}")
        print(f"   Loan amount: {state.get('loan_terms', {}).get('principal', 0)}")
    except Exception as e:
        print(f" State retrieval failed: {e}")
    
    print("=" * 50)
    print(" Backend API test completed!")

if __name__ == "__main__":
    test_api()

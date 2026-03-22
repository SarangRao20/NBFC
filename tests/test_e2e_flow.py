import asyncio
import requests
from db.database import sessions_collection

BASE_URL = "http://localhost:8000"

async def test_flow():
    print("🚀 Starting E2E Integration Test...")

    # 1. Start Session
    print("\n--- 1. START SESSION ---")
    resp = requests.post(f"{BASE_URL}/session/start")
    if resp.status_code != 200:
        print(f"❌ Failed to start session: {resp.text}")
        return
    
    session_data = resp.json()
    session_id = session_data["session_id"]
    print(f"✅ Created Session: {session_id}")
    print(f"   Response Status: {session_data['status']}")
    print(f"   Current Phase: {session_data['current_phase']}")

    # Check MongoDB directly
    db_session = await sessions_collection.find_one({"_id": session_id})
    if db_session:
        print(f"   📦 Verified in MongoDB Atlas. Phase: {db_session['current_phase']}")
    else:
        print("   ❌ NOT found in MongoDB Atlas.")

    # 2. Identify Customer (Sales)
    print("\n--- 2. IDENTIFY CUSTOMER ---")
    payload = {"phone": "9876543210"}
    resp = requests.post(f"{BASE_URL}/session/{session_id}/identify-customer", json=payload)
    if resp.status_code != 200:
        print(f"❌ Failed to identify customer: {resp.text}")
        return
    
    sales_data = resp.json()
    print(f"✅ Identified Customer: {sales_data['is_existing_customer']}")
    if sales_data.get('customer_data'):
        print(f"   Name: {sales_data['customer_data']['name']}")

    # Check MongoDB directly again
    db_session = await sessions_collection.find_one({"_id": session_id})
    if db_session:
        print(f"   📦 Verified in MongoDB Atlas.")
        print(f"      Phase updated to: {db_session['current_phase']}")
        print(f"      Phone in DB: {db_session['customer_data']['phone']}")
    else:
        print("   ❌ NOT found in MongoDB Atlas.")
        
    print("\n🎉 E2E Test Completed Successfully!")


if __name__ == "__main__":
    asyncio.run(test_flow())

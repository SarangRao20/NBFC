
import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from mock_apis.lender_apis import aggregate_lender_offers
from agents.sales_agent import sales_agent_node

async def test_lender_offers():
    print("--- Testing Lender Offers ---")
    # Test valid request
    offers = await aggregate_lender_offers(principal=50000, tenure=12, credit_score=750, monthly_income=60000)
    print(f"Valid Request Offers: {len(offers.get('offers', []))}")
    assert len(offers.get('offers', [])) > 0
    assert offers.get("selected_lender_name") is not None
    
    # Test high amount (soft reject)
    high_offers = await aggregate_lender_offers(principal=5000000, tenure=12, credit_score=750, monthly_income=60000)
    print(f"High Amount Offers: {len(high_offers.get('offers', []))}")
    assert len(high_offers.get('offers', [])) == 0
    assert high_offers.get("max_eligible_amount") > 0
    print(f"Max Eligible Amount Suggested: {high_offers.get('max_eligible_amount')}")

async def test_sales_agent_flow():
    print("\n--- Testing Sales Agent Flow ---")
    state = {
        "session_id": "test_session",
        "messages": [],
        "current_phase": "sales",
        "loan_terms": {"loan_purpose": "Business"},
        "pending_question": "amount",
        "customer_data": {"name": "Arjun", "credit_score": 750, "salary": 60000}
    }
    
    # Simulate user sending amount
    from langchain_core.messages import HumanMessage
    state["messages"].append(HumanMessage(content="50000"))
    
    result = await sales_agent_node(state)
    print(f"Next Phase: {result.get('current_phase')}")
    print(f"Pending Question: {result.get('pending_question')}")
    print(f"Message: {result['messages'][0].content[:100]}...")
    
    assert result.get("loan_terms", {}).get("principal") == 50000
    assert result.get("pending_question") == "tenure"

if __name__ == "__main__":
    asyncio.run(test_lender_offers())
    asyncio.run(test_sales_agent_flow())
    print("\n✅ Verification and smoke tests passed!")

from typing import Dict, Any
from agents.registration import build_registration_agent, RegistrationState
from agents.verification import build_verification_agent, VerificationState
from langchain_core.messages import HumanMessage

def run_agents():
    """Demonstrates running both Modular Agents sequentially."""
    print("=== NBFC AGENTIC PIPELINE STARTING ===")
    
    # 1. Initialize Agents
    try:
        reg_agent = build_registration_agent()
        verify_agent = build_verification_agent()
    except ValueError as e:
         print(f"Error loading config: {e}")
         return
    
    # --- PHASE 1: REGISTRATION ---
    print("\n--- PHASE 1: REGISTRATION ---")
    
    # We load standard Chat Messages into the LangGraph state. 
    # In a real app, this loops through an API taking user input.
    initial_reg_state: RegistrationState = {
        "messages": [HumanMessage(content="Hi.. I am Sarang and my number is 9876543210. I need a loan.")],
        "collected_name": None,
        "collected_phone": None,
        "registration_complete": False
    }
    
    # Run Registration
    final_reg_state = reg_agent.invoke(initial_reg_state)
    print("Is Registration Complete?", final_reg_state.get("registration_complete"))
    print("Collected Name:", final_reg_state.get("collected_name"))
    print("Collected Phone:", final_reg_state.get("collected_phone"))
    
    # --- PHASE 2: DOCUMENT VERIFICATION ---
    if final_reg_state.get("registration_complete"):
        print("\n--- PHASE 2: VERIFICATION ---")
        
        # Test image path (replace with a real test PAN/Aadhaar image to test OCR)
        # test_image = "path/to/test/pan_card.jpg"
        test_image = "dummy.jpg" # It will fail because this file doesn't exist yet!
        
        initial_verify_state: VerificationState = {
            "user_provided_name": final_reg_state.get("collected_name"),
            "user_provided_phone": final_reg_state.get("collected_phone"),
            "current_doc_path": test_image,
            "verified_docs": {},
            "verification_errors": [],
            "status": "idle",
            "doc_assist_messages": [],
            "extracted_temp": {} 
        }
        
        final_verify_state = verify_agent.invoke(initial_verify_state)
        
        # Will fail gracefully because image doesn't exist, falling back to Doc Assist.
        if final_verify_state.get("verification_errors"):
            print("ERRORS ENCOUNTERED:", final_verify_state["verification_errors"])
        if final_verify_state.get("doc_assist_messages"):
            print("\n>> AI GENERATED HELP MESSAGE FOR USER:")
            print(final_verify_state["doc_assist_messages"][-1])
        else:
            print("Successfully extracted data:", final_verify_state.get("verified_docs"))

if __name__ == "__main__":
    run_agents()

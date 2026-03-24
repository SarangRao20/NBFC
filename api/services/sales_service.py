"""Sales Service — customer identification and loan capture (Steps 2, 3)."""

import json
import os
import asyncio
from api.core.state_manager import get_session, update_session, advance_phase
from api.core.websockets import manager
from mock_apis.loan_products import LOAN_PRODUCTS


def _normalize_phone(phone: str) -> str:
    """Strip +91/91 prefix and spaces to get clean 10-digit number."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12:
        phone = phone[2:]
    return phone[-10:]


def _clean_dict(d):
    """Recursively removes _id and other non-JSON-serializable types."""
    if isinstance(d, list):
        return [_clean_dict(v) for v in d]
    if isinstance(d, dict):
        return {k: _clean_dict(v) for k, v in d.items() if k != "_id"}
    return d



def _lookup_customer_by_phone(phone: str) -> dict | None:
    """CRM lookup by phone number."""
    phone = _normalize_phone(phone)
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if c["phone"] == phone:
                    return c
    except Exception:
        pass
    return None


def _lookup_customer_by_email(email: str, password: str) -> dict | None:
    """CRM lookup by email + password."""
    email = email.strip().lower()
    try:
        with open("mock_apis/customers.json", "r") as f:
            for c in json.load(f):
                if c.get("email", "").lower() == email and c.get("password", "") == password:
                    return c
    except Exception:
        pass
    return None


def _calculate_emi(principal: float, rate_pa: float, tenure: int) -> float:
    """Standard EMI formula: P × R × (1+R)^N / ((1+R)^N - 1)."""
    if principal <= 0 or tenure <= 0 or rate_pa <= 0:
        return 0.0
    r = (rate_pa / 12) / 100
    emi = principal * r * ((1 + r) ** tenure) / (((1 + r) ** tenure) - 1)
    return round(emi, 2)


def _get_rate_for_product(loan_type: str) -> float:
    """Look up base rate from loan products catalog."""
    product = LOAN_PRODUCTS.get(loan_type)
    if product:
        return product.get("base_rate", 12.0)
    return 12.0


async def identify_customer(session_id: str, phone: str, email: str = None, password: str = None) -> dict:
    """Step 2: Identify Existing vs New User via DB lookup."""
    state = await get_session(session_id)
    if not state:
        return None

    customer = None

    # Try phone-based lookup first
    clean_phone = _normalize_phone(phone)
    customer = _lookup_customer_by_phone(clean_phone)

    # Fallback to email-based lookup
    if not customer and email and password:
        customer = _lookup_customer_by_email(email, password)

    if customer:
        from api.services.session_service import search_sessions_by_phone
        past_sessions = await search_sessions_by_phone(clean_phone)
        
        # Extract past loan info
        past_loans = []
        for ps in past_sessions:
            if ps.get("session_id") == session_id: continue # Skip current
            
            p_data = ps.get("state", {}).get("loan_terms", {})
            p_sanction = ps.get("state", {}).get("sanction_pdf")
            p_decision = ps.get("state", {}).get("decision")
            
            if p_data or p_sanction:
                past_loans.append({
                    "amount": p_data.get("principal"),
                    "type": p_data.get("loan_type"),
                    "decision": p_decision,
                    "sanction_letter": p_sanction,
                    "date": ps.get("updated_at")
                })

        await update_session(session_id, {
            "customer_id": customer.get("id", clean_phone),
            "is_existing_customer": True,
            "customer_data": {
                "name": customer.get("name", ""),
                "phone": clean_phone,
                "email": customer.get("email", ""),
                "city": customer.get("city", ""),
                "salary": customer.get("salary", 0),
                "credit_score": customer.get("credit_score", 0),
                "pre_approved_limit": customer.get("pre_approved_limit", 0),
                "existing_emi_total": customer.get("existing_emi_total", 0),
                "current_loans": customer.get("current_loans", []),
                "risk_flags": customer.get("risk_flags", []),
                "past_records": customer.get("past_records", ""),
                "drop_off_history": customer.get("drop_off_history", ""),
                "past_loans": past_loans,
            }
        })
        await advance_phase(session_id, "customer_identified")
        # Broadcast phase update via WebSocket
        asyncio.create_task(manager.broadcast_to_session(session_id, {
            "type": "PHASE_UPDATE",
            "phase": "loan_details"
        }))

        return _clean_dict({
            "is_existing_customer": True,
            "customer_data": {
                "name": customer.get("name", ""),
                "phone": clean_phone,
                "city": customer.get("city", ""),
                "salary": customer.get("salary", 0),
                "credit_score": customer.get("credit_score", 0),
                "pre_approved_limit": customer.get("pre_approved_limit", 0),
                "existing_emi_total": customer.get("existing_emi_total", 0),
                "current_loans": customer.get("current_loans", []),
                "past_loans": past_loans,
                "past_records": customer.get("past_records", ""),
            },
            "message": f"Welcome back, {customer.get('name', 'Customer')}!"
        })
    else:
        # New customer — create minimal profile
        await update_session(session_id, {
            "customer_id": clean_phone,
            "is_existing_customer": False,
            "customer_data": {
                "name": "",
                "phone": clean_phone,
                "email": email or "",
                "city": "",
                "salary": 0,
                "credit_score": 700,
                "pre_approved_limit": 25000,
                "existing_emi_total": 0,
                "current_loans": [],
                "risk_flags": [],
            }
        })
        await advance_phase(session_id, "customer_identified")
        # Broadcast phase update via WebSocket for new customer
        asyncio.create_task(manager.broadcast_to_session(session_id, {
            "type": "PHASE_UPDATE",
            "phase": "loan_details"
        }))

        return _clean_dict({
            "is_existing_customer": False,
            "customer_data": None,
            "message": "New customer. Profile created with default values. Proceed to capture loan requirement."
        })


async def capture_loan_requirement(session_id: str, loan_type: str, loan_amount: float, tenure_months: int) -> dict:
    """Step 3: Capture Loan Requirement → compute EMI → State Update: Profile & Intent."""
    state = await get_session(session_id)
    if not state:
        return None

    rate = _get_rate_for_product(loan_type)
    emi = _calculate_emi(loan_amount, rate, tenure_months)
    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - loan_amount, 2)

    loan_terms = {
        "loan_type": loan_type,
        "principal": loan_amount,
        "rate": rate,
        "tenure": tenure_months,
        "emi": emi,
    }

    await update_session(session_id, {"loan_terms": loan_terms})
    await advance_phase(session_id, "loan_captured")

    # Broadcast phase update via WebSocket
    asyncio.create_task(manager.broadcast_to_session(session_id, {
        "type": "PHASE_UPDATE",
        "phase": "document"
    }))

    return _clean_dict({
        "loan_terms": loan_terms,
        "emi": emi,
        "total_interest": total_interest,
        "total_repayment": total_payment,
        "message": f"Loan captured: ₹{loan_amount:,.0f} at {rate}% for {tenure_months} months. EMI: ₹{emi:,.2f}/month."
    })
async def chat_with_agent(session_id: str, user_message: str, history: list[dict] = None) -> dict:
    """Conversational interface using the Master LangGraph."""
    from agents.master_graph import compile_master_graph
    from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
    
    state = await get_session(session_id)
    if not state:
        # Create new session if it doesn't exist
        from api.core.state_manager import create_session, _default_state
        from datetime import datetime
        state = _default_state()
        state["session_id"] = session_id
        state["created_at"] = datetime.utcnow().isoformat()
        state["current_phase"] = "session_started"
        # Insert directly into MongoDB
        from db.database import sessions_collection
        sessions_collection.insert_one({"_id": session_id, **state})

    # Fast-path for EMI reminder queries using stored sanction/loan records.
    lowered = (user_message or "").lower()
    if any(k in lowered for k in ["emi", "existing emis", "due date", "when do i need to pay"]):
        try:
            from db.database import loan_applications_collection
            phone = state.get("customer_data", {}).get("phone")
            if phone:
                apps_cursor = loan_applications_collection.find({"phone": phone})
                apps = []
                for app in apps_cursor:
                    if app.get("status") in ["Approved", "Signed & Disbursed"]:
                        apps.append(app)

                if apps:
                    lines = ["Your active EMI obligations are:"]
                    for idx, app in enumerate(apps[:5], start=1):
                        amount = app.get("amount", 0)
                        emi = app.get("emi", 0)
                        due = app.get("first_emi_due_date") or "Not available"
                        lines.append(f"{idx}. Loan ₹{amount:,.0f} | EMI ₹{emi:,.0f} | Next due: {due}")
                    lines.append("Please pay on or before due date to avoid penalties.")
                    reply = "\n".join(lines)
                    return _clean_dict({
                        "reply": reply,
                        "all_replies": [{"type": "text", "content": reply}],
                        "next_agent": "advisor_agent",
                        "intent": state.get("intent", "advice"),
                        "is_authenticated": state.get("is_authenticated", True),
                        "loan_terms": state.get("loan_terms", {}),
                        "customer_data": state.get("customer_data", {}),
                    })
        except Exception as emi_err:
            print(f"⚠️ EMI lookup failed: {emi_err}")

    # Rebuild message list from history or stored state
    current_messages = []
    if history:
        for m in history:
            role_type = m.get("sender", m.get("role"))
            role = HumanMessage if role_type == "user" else AIMessage
            content = m.get("content", m.get("text", ""))
            current_messages.append(role(content=content))
    else:
        for m in state.get("messages", []):
            if isinstance(m, dict):
                # Skip frontend-specific message types that aren't LangChain messages
                if m.get("type") in ["agent_steps", "sanction_letter", "emi_slider"]:
                    continue
                role_type = m.get("sender", m.get("role"))
                role = HumanMessage if role_type == "user" else AIMessage
                content = m.get("kwargs", {}).get("content", m.get("content", m.get("text", "")))
                current_messages.append(role(content=content))
            else:
                current_messages.append(m)

    # Add the new user message
    current_messages.append(HumanMessage(content=user_message))
    
    # Track how many AI messages exist before the graph runs
    pre_run_ai_count = sum(1 for m in current_messages if isinstance(m, AIMessage))

    # Update local state for graph invocation - ONLY pass LangChain messages
    clean_state = state.copy()
    # Aggressive filtering: ONLY allow HumanMessage and AIMessage objects
    clean_state["messages"] = [m for m in current_messages if not isinstance(m, dict)]
    
    # Debug: Check for any dict messages that slipped through
    for i, msg in enumerate(clean_state["messages"]):
        if isinstance(msg, dict):
            print(f"⚠️ [CRITICAL] Found dict message at index {i}: {msg}")
    
    # Run the Master Graph
    print(f"🧠 [SALES SERVICE] Invoking MasterGraph for session {session_id}...")
    graph = compile_master_graph()
    
    try:
        print(f"📊 [DEBUG] State keys before graph invocation: {list(clean_state.keys())}")
        print(f"📊 [DEBUG] customer_data keys: {list(clean_state.get('customer_data', {}).keys())}")
        print(f"📊 [DEBUG] Messages count before graph: {len(clean_state['messages'])}")
        final_state = await graph.ainvoke(clean_state, config={"recursion_limit": 100})
        print("✅ [SALES SERVICE] Graph run complete.")

        # CRITICAL: Filter out ALL dict messages from final_state - only allow LangChain message objects
        filtered_final_messages = []
        for msg in final_state.get("messages", []):
            if isinstance(msg, dict):
                print(f"⚠️ [FILTER] Removed dict message: {msg.get('type', 'unknown')}")
                continue
            filtered_final_messages.append(msg)
        final_state["messages"] = filtered_final_messages

        # Collect NEW AI messages (not re-emitting old history)
        all_messages = final_state.get("messages", [])
        new_ai = []
        ai_seen = 0
        for m in all_messages:
            if isinstance(m, AIMessage):
                ai_seen += 1
                if ai_seen > pre_run_ai_count:
                    # Try to parse if it's already a JSON dict string
                    try:
                        import json
                        parsed = json.loads(m.content)
                        new_ai.append(parsed)
                    except:
                        new_ai.append({"type": "text", "content": m.content})
        
        # Insert action log block before the final reply, if any steps were collected
        logs = final_state.get("action_log", [])
        if logs:
            import json
            # Update: Push individual agent steps to WS for live "Thinking"
            asyncio.create_task(manager.broadcast_to_session(session_id, {
                "type": "AGENT_STEP",
                "steps": _clean_dict(logs)
            }))

            # REMOVED: Don't add agent_steps to chat messages - they show in UI
            # step_msg = {
            #     "type": "agent_steps", 
            #     "content": json.dumps({"steps": _clean_dict(logs)})
            # }
            # new_ai.insert(0, step_msg)

        # Attach options to the last AI message for frontend rendering
        if final_state.get("options") and new_ai:
            if isinstance(new_ai[-1], dict):
                new_ai[-1]["options"] = final_state.get("options")

        # For the legacy string reply, concat just the text bits
        texts = [m["content"] for m in new_ai if isinstance(m, dict) and m.get("type") == "text"]
        reply = "\n\n".join(texts) if texts else "I'm here — what would you like to do next?"
        
        # Ensure session metadata is preserved in the final state
        final_state["session_id"] = session_id
        final_state["status"] = state.get("status", "active")

        # Filter out frontend-specific message types from state before saving
        filtered_messages = []
        for msg in final_state.get("messages", []):
            if isinstance(msg, dict) and msg.get("type") in ["agent_steps", "sanction_letter", "emi_slider"]:
                continue  # Skip frontend-specific messages
            filtered_messages.append(msg)
        final_state["messages"] = filtered_messages

        # Persist final state to DB (Bypassing Redis for state sync per user request)
        await update_session(session_id, final_state)
        # await cache.set_session(session_id, final_state) # User asked NOT to use Redis for sidebar


        
        # If loan is signed, log it for future historical lookups
        if final_state.get("is_signed"):
            try:
                from db.mock_database import loan_applications_collection
                from datetime import datetime
                loan_doc = {
                    "session_id": session_id,
                    "phone": final_state.get("customer_data", {}).get("phone"),
                    "name": final_state.get("customer_data", {}).get("name"),
                    "loan_type": final_state.get("loan_terms", {}).get("loan_type", "Personal"),
                    "amount": final_state.get("loan_terms", {}).get("principal", 0),
                    "status": "Signed & Disbursed",
                    "created_at": datetime.now().isoformat()
                }
                loan_applications_collection.insert_one(loan_doc)
                print(f"✅ [SALES SERVICE] Loan logged for {loan_doc['name']}")
            except Exception as le:
                print(f"⚠️ [SALES SERVICE] Failed to log loan: {le}")
        return _clean_dict({
            "reply": reply,
            "all_replies": new_ai,
            "next_agent": final_state.get("next_agent", "unknown"),
            "intent": final_state.get("intent", "none"),
            "is_authenticated": final_state.get("is_authenticated", False),
            "loan_terms": final_state.get("loan_terms", {}),
            "customer_data": final_state.get("customer_data", {}),
            "options": final_state.get("options"),
        })

        
    except Exception as e:
        import traceback, json
        print(f"❌ Master Graph Error: {e}")
        traceback.print_exc()
        # Persist an error action to the session so it's visible in logs
        try:
            await update_session(session_id, {"action_log": [f"❌ Master Graph Error: {str(e)}"]})
        except Exception:
            pass
        # Return structured error for frontend and include minimal safe fields
        return _clean_dict({
            "reply": f"Technical issue in the brain: {str(e)}",
            "error": True,
            "error_detail": str(e),
            "customer_data": state.get("customer_data", {}),
        })

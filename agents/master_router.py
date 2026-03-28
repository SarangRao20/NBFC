"""Deterministic Router — Rule-based routing with NO LLM overhead."""

from agents.master_state import MasterState

def route_next_agent(state: MasterState):
    """Deterministic, rule-based routing for the 8-phase pipeline. NO LLM calls."""
    
    intent = state.get("intent", "none")
    customer = state.get("customer_data", {})
    terms = state.get("loan_terms", {})
    docs = state.get("documents", {})
    kyc = state.get("kyc_status", "pending")
    fraud = state.get("fraud_score", -1)
    decision = state.get("decision", "")
    current_phase = state.get("current_phase", "registration")
    pending_q = state.get("pending_question")
    
    # ─── PHASE 0: SMART RE-EVALUATION (avoid loops) ────────────────────────
    from langchain_core.messages import HumanMessage
    import re as _re
    msgs = state.get("messages", [])
    if msgs and isinstance(msgs[-1], HumanMessage):
        last_msg = str(msgs[-1].content).lower()
        
        # ─── HANDLE REQUEST FOR REVISED AMOUNT ────────────────────────────────
        # When user asks for "lower amount", "different amount", "less loan", etc.
        # OR when they mention explicit amounts like "75k", "50000", "1.4 lakh"
        # during rejection phase: clear decision and route back to sales
        
        # Check for keyword-based requests
        has_reduction_keyword = any(keyword in last_msg for keyword in 
            ["lower", "less", "smaller", "different", "another", "reduce", "different amount", "lower loan"])
        
        # Check for explicit amount mentions (k, lakh, rupees, ₹, etc.)
        has_explicit_amount = bool(
            _re.search(r"\d+\s*k\b", last_msg) or         # 75k
            _re.search(r"\d+\s*lakh", last_msg) or        # 1.4 lakh
            _re.search(r"\d+\s*lac\b", last_msg) or       # 1.4 lac
            _re.search(r"\d+\s*thousand", last_msg) or    # 75 thousand
            _re.search(r"₹\s*\d+", last_msg) or           # ₹75000
            (_re.search(r"\d{5,}", last_msg) and (       # 75000 (5+ digits)
                "rupee" in last_msg or "loan" in last_msg or "amount" in last_msg))
        )
        
        # Route to sales if rejection + (keyword OR explicit amount)
        if decision in ("hard_reject", "soft_reject") and (has_reduction_keyword or has_explicit_amount):
            return "sales_agent", "User requesting revised loan amount. Reopening with Arjun for new collection."
        
        # Skip re-evaluation if:
        # 1. Already in decision/advisory phase
        # 2. Already processing a loan (in sales/document/verification/underwriting phase)
        # 3. Intent was just set in the last message
        if decision not in ("approve", "soft_reject", "hard_reject") and current_phase not in ("sales", "document", "verification", "fraud_check", "underwriting", "sanction"):
            log = state.get("action_log", [])
            recent_logs = "".join(str(e) for e in log[-5:])  # Check last 5 entries
            
            # Only re-evaluate if Intent Agent explicitly hasn't run recently AND intent was not just set
            if "Intent Agent" not in recent_logs and "✅ Intent" not in recent_logs and intent == "none":
                return "intent_agent", "New human message detected. Re-evaluating vague/unclear intent."

    # ─── PHASE 3: ADVICE ONLY (Now handled by Sales Agent in advisor mode) ────
    if intent == "advice":
        return "sales_agent", "Routing to Sales Agent for financial advisory mode."
        
    if intent == "kyc" and not state.get("documents_uploaded"):
        return "document_query_agent", "User asking about documents/KYC rules."

    if intent == "payment":
        return "repayment_agent", "Routing to loan repayment portal."

    if intent == "document_request":
        return "sanction_agent", "User requesting official loan documentation (Sanction/Rejection)."

    # ─── PHASE 8: HYBRID DISBURSEMENT & NEGOTIATION LOOP ───────────────────────
    
    # 🟢 1. The Disbursement Hook (Approved)
    if decision == "approve":
        # If the 5-step disbursement is totally finished, route to the final advisor greeting
        if state.get("disbursement_step") == "completed":
            return "sales_agent", "Disbursement complete. Providing post-sanction orientation."
            
        # Otherwise, hand off to our new Subgraph!
        return "disbursement_process", "Loan approved. Routing to 5-Step Disbursement Subgraph."

    # 🟡 2. The Soft-Reject Loop (Negotiation — handled by Sales Agent)
    if decision == "soft_reject" or state.get("negotiation_requested"):
        accepted_offer = state.get("user_accepted_counter_offer", False)
        
        if not accepted_offer:
            # Route to Sales Agent (Arjun) who now handles negotiation/persuasion
            return "sales_agent", "Soft reject detected. Routing to Sales Agent for counter-offer negotiation."
        else:
            # User clicked 'Accept' on the UI or typed yes. Route back to Underwriting to formalize the new math.
            return "underwriting_agent", "User accepted counter-offer. Re-running underwriting math for final approval."

    # 🔴 3. The Hard Reject (Advisory)
    if decision == "hard_reject":
        return "sales_agent", "Hard reject. Providing alternative financial wellness advice."

    # ─── PHASE 4: SALES DISCOVERY (Arjun - Collecting Terms) ─────────────────
    if intent == "loan":
        # 4a. Collect and verify terms (Amount, Tenure, Purpose)
        if not state.get("loan_confirmed"):
            return "sales_agent", "Gathering loan requirements one variable at a time."
            
        # 4b. If terms confirmed but NO lender selected, stay in sales for lender selection
        if not state.get("selected_lender_id"):
            return "sales_agent", "Terms confirmed. Presenting lender options for user selection."

    # ─── PHASE 5: DOCUMENT UPLOAD (KYC & Income) ───────────────────────────
    # We only enter document collection if:
    # 1. Lender is selected
    # 2. Preliminary decision is 'approve' (or similar positive state)
    # 3. Documents are still missing
    if intent == "loan" and state.get("selected_lender_id") and decision == "approve":
        docs_missing = not state.get("documents_uploaded") or not state.get("document_paths")
        if not state.get("esign_completed") and docs_missing:
            return "document_agent", "Mandatory KYC verification required after lender selection."

    # ─── PHASE 6: KYC & FRAUD (Parallel Verification) ────────────────────────
    if intent == "loan" and state.get("selected_lender_id"):
        if kyc == "pending" or fraud == -1:
            if kyc == "pending" and state.get("documents_uploaded"):
                return "verification_agent", "Proceeding to KYC verification."
            if fraud == -1:
                return "fraud_agent", "Performing automated fraud analysis."

    # ─── PHASE 7: UNDERWRITING (Credit Decision) ─────────────────────────────
    if intent == "loan":
        if not decision:
            if kyc == "verified":
                return "underwriting_agent", "KYC verified. Reviewing for credit decision."
            else:
                return "verification_agent", "Awaiting KYC completion before underwriting."

    # ─── PHASE 8: SANCTION & ADVICE (Priya - Now via Sales Agent advisor mode) ──
    if intent == "unclear" or intent == "unclear_greeting":
        return "__end__", "Waiting for user clarification (unclear intent)."

    if decision in ("approve", "hard_reject"):
        # If hard reject, we stay in sales (Arjun) for final communication
        if decision == "hard_reject" and current_phase != "sanction_esign" and not state.get("sanction_pdf"):
            # Only go to sanction if the user has accepted the negotiation (this would be set by Arjun)
            if not state.get("negotiation_signed_off"):
                return "sales_agent", "Loan soft-rejected. Arjun is handling the persuasion/negotiation loop."
        
        if not state.get("sanction_pdf"):
            return "sanction_agent", "Generating finalized loan agreement and sanction documentation."
        return "sales_agent", "Documentation complete. Providing post-sanction orientation via advisor mode."

    # GLOBAL FALLBACK
    if intent == "loan" or current_phase in ("sales", "document", "verification", "underwriting"):
        return "sales_agent", "Continuing loan conversation with Arjun to ensure human-first support."
    
    return "sales_agent", "Portfolio management and financial wellness orientation via advisor mode."

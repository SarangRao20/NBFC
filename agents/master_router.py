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
    
    # ─── PHASE 0: FORCE RE-EVALUATION ──────────────────────────
    from langchain_core.messages import HumanMessage
    msgs = state.get("messages", [])
    if msgs and isinstance(msgs[-1], HumanMessage):
        # We look at the last few log entries for Arjun's signature
        log = state.get("action_log", [])
        # If the last 3 entries don't mention Intent Agent, we MUST re-evaluate
        recent_logs = "".join(str(e) for e in log[-3:])
        if "Intent Agent" not in recent_logs and "✅ Intent" not in recent_logs:
            return "intent_agent", "New human message detected. Re-evaluating intent."

    # ─── PHASE 3: ADVICE ONLY (Parallel/Side Branch) ─────────────────────────
    if intent == "advice":
        return "advisor_agent", "Direct route to financial advisory."
        
    if intent == "kyc" and not state.get("documents_uploaded"):
        return "document_query_agent", "User asking about documents/KYC rules."

    # ─── PHASE 4: SALES DISCOVERY (Arjun - Collecting Terms) ─────────────────
    if intent == "loan":
        # If we are in sales phase and have a pending question (e.g., confirmation or tenure), Sales Agent must handle it
        if current_phase == "sales" and pending_q:
            return "sales_agent", "Arjun handling pending discovery question."

        # 4a. Basic term collection
        if not terms.get("principal") or not terms.get("tenure"):
            return "sales_agent", "Collecting loan requirements with Arjun."
        
        # 4b. EMI Visualization & Confirmation
        if current_phase == "sales" and not state.get("loan_confirmed"):
            return "emi_agent", "Show rich EMI visualization/slider before confirmation."

    # ─── PHASE 5: DOCUMENT UPLOAD (Document Agent) ───────────────────────────
    if intent == "loan":
        # Skip document agent if e-sign is already completed (post-sanction phase)
        if not state.get("esign_completed") and (not state.get("documents_uploaded") or not state.get("document_paths")):
            return "document_agent", "Terms confirmed. Collecting documents."

    # ─── PHASE 6: KYC & FRAUD (Parallel Verification) ────────────────────────
    if intent == "loan":
        if kyc == "pending" or fraud == -1:
            # Note: Graph parallelization handles the double-fire
            if kyc == "pending": return "verification_agent", "Running KYC verification."
            return "fraud_agent", "Performing fraud analysis."

    # ─── PHASE 7: UNDERWRITING (Credit Decision) ─────────────────────────────
    if intent == "loan":
        if not decision:
            if kyc == "verified":
                return "underwriting_agent", "KYC verified. Reviewing for credit decision."
            else:
                return "verification_agent", "Awaiting KYC completion before underwriting."

    # ─── PHASE 8: SANCTION & ADVICE (Priya - Closing) ────────────────────────
    if decision in ("approve", "soft_reject", "hard_reject"):
        if not state.get("sanction_pdf"):
            return "sanction_agent", "Generating official sanction/rejection letter."
        return "advisor_agent", "Letter ready. Priya providing closing guidance."

    # GLOBAL FALLBACK
    if intent == "loan":
        return "sales_agent", "Fallback: In loan flow but state unclear. Routing to Sales Specialist."
    
    return "advisor_agent", "Fallback to wellness specialist."

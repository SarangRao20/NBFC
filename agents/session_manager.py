"""Session Manager — Synchronous MongoDB persistence for NBFC pipeline."""

from typing import Optional, Dict, Any
from datetime import datetime
from db.database import chat_sessions_collection, documents_collection

class SessionManager:
    """Sync PyMongo session persistence layer."""
    
    @staticmethod
    def save_session(session_id: str, state: Dict[str, Any]) -> bool:
        """Save session state to MongoDB (sync PyMongo)."""
        try:
            session_doc = {
                "session_id": session_id,
                "customer_id": state.get("customer_id", ""),
                "customer_data": state.get("customer_data", {}),
                "loan_terms": state.get("loan_terms", {}),
                "documents": state.get("documents", {}),
                "document_paths": state.get("document_paths", {}),
                "fraud_score": state.get("fraud_score", -1),
                "kyc_status": state.get("kyc_status", "pending"),
                "decision": state.get("decision", ""),
                "current_phase": state.get("current_phase", "registration"),
                "intent": state.get("intent", "none"),
                "is_authenticated": state.get("is_authenticated", False),
                "profile_complete": state.get("profile_complete", False),
                "dti_ratio": state.get("dti_ratio", 0.0),
                "risk_level": state.get("risk_level", ""),
                "sanction_pdf": state.get("sanction_pdf", ""),
                "messages_count": len(state.get("messages", [])),
                "messages": state.get("messages", []),
                "action_log": state.get("action_log", []),
                "last_updated": datetime.utcnow(),
                "is_signed": state.get("is_signed", False),
            }
            
            # Upsert (save or update)
            chat_sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": session_doc},
                upsert=True
            )
            print(f"✅ Session {session_id} saved to MongoDB")
            return True
        except Exception as e:
            print(f"❌ Error saving session: {e}")
            return False
    
    @staticmethod
    def load_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Load session state from MongoDB (sync PyMongo). Always returns complete state schema."""
        try:
            session_doc = chat_sessions_collection.find_one({"session_id": session_id})
            if not session_doc:
                print(f"⚠️ Session {session_id} not found")
                return None
            
            print(f"✅ Session {session_id} loaded from MongoDB")
            # Remove MongoDB _id field
            session_doc.pop("_id", None)
            
            # Ensure all required fields exist with proper structure (same as state_manager.py)
            default_customer = {
                "name": "",
                "phone": "",
                "email": "",
                "city": "",
                "salary": 0,
                "credit_score": 0,
                "pre_approved_limit": 0,
                "existing_emi_total": 0,
            }
            default_loan_terms = {
                "loan_type": "",
                "principal": 0,
                "rate": 0.0,
                "tenure": 0,
                "emi": 0.0,
            }
            default_documents = {
                "salary_slip_path": "",
                "verified": False,
            }
            
            # Merge with defaults
            if "customer_data" not in session_doc or not isinstance(session_doc.get("customer_data"), dict):
                session_doc["customer_data"] = {}
            session_doc["customer_data"] = {**default_customer, **session_doc.get("customer_data", {})}
            
            if "loan_terms" not in session_doc or not isinstance(session_doc.get("loan_terms"), dict):
                session_doc["loan_terms"] = {}
            session_doc["loan_terms"] = {**default_loan_terms, **session_doc.get("loan_terms", {})}
            
            if "documents" not in session_doc or not isinstance(session_doc.get("documents"), dict):
                session_doc["documents"] = {}
            session_doc["documents"] = {**default_documents, **session_doc.get("documents", {})}
            
            # Ensure other required fields
            if "is_authenticated" not in session_doc:
                session_doc["is_authenticated"] = False
            if "intent" not in session_doc:
                session_doc["intent"] = "none"
            if "current_phase" not in session_doc:
                session_doc["current_phase"] = "init"
            if "messages" not in session_doc:
                session_doc["messages"] = []
            if "action_log" not in session_doc:
                session_doc["action_log"] = []
            
            return session_doc
        except Exception as e:
            print(f"❌ Error loading session: {e}")
            return None
    
    @staticmethod
    def save_document(session_id: str, document_type: str, document_path: str, 
                     extracted_data: Dict[str, Any], confidence: float = 0.0) -> bool:
        """Save document metadata to MongoDB."""
        try:
            doc_record = {
                "session_id": session_id,
                "document_type": document_type,  # "pan", "aadhaar", "salary_slip", "bank_statement"
                "document_path": document_path,
                "extracted_data": extracted_data,
                "confidence": confidence,
                "uploaded_at": datetime.utcnow(),
                "is_verified": False,
            }
            
            result = documents_collection.insert_one(doc_record)
            print(f"✅ Document {document_type} saved: {result.inserted_id}")
            return True
        except Exception as e:
            print(f"❌ Error saving document: {e}")
            return False
    
    @staticmethod
    def get_session_documents(session_id: str) -> list:
        """Retrieve all documents for a session."""
        try:
            docs = list(documents_collection.find({"session_id": session_id}))
            for doc in docs:
                doc.pop("_id", None)
            return docs
        except Exception as e:
            print(f"❌ Error retrieving documents: {e}")
            return []
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete a session (after completion/timeout)."""
        try:
            chat_sessions_collection.delete_one({"session_id": session_id})
            documents_collection.delete_many({"session_id": session_id})
            print(f"✅ Session {session_id} deleted from MongoDB")
            return True
        except Exception as e:
            print(f"❌ Error deleting session: {e}")
            return False

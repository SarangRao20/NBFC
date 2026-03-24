"""Session Manager — Synchronous MongoDB persistence for NBFC pipeline."""

from typing import Optional, Dict, Any
from datetime import datetime
from db.database import sessions_collection, documents_collection
try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
except Exception:
    AIMessage = HumanMessage = SystemMessage = None
class SessionManager:
    """Async Motor session persistence layer."""
    
    @staticmethod
    async def save_session(session_id: str, state: Dict[str, Any]) -> bool:
        """Save session state to MongoDB (async Motor)."""
        try:
            # Ensure messages are serializable (convert langchain message objects to dicts)
            raw_messages = state.get("messages", [])
            serializable_messages = []
            for m in raw_messages:
                # already a dict (serialized elsewhere)
                if isinstance(m, dict):
                    serializable_messages.append(m)
                    continue

                # langchain message objects have a `content` attribute
                if hasattr(m, "content"):
                    if HumanMessage is not None and isinstance(m, HumanMessage):
                        role = "user"
                    elif SystemMessage is not None and isinstance(m, SystemMessage):
                        role = "system"
                    else:
                        role = "assistant"
                    serializable_messages.append({"role": role, "content": getattr(m, "content", "")})
                    continue

                # fallback to string representation
                serializable_messages.append({"role": "system", "content": str(m)})

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
                "messages_count": len(serializable_messages),
                "messages": serializable_messages,
                "action_log": state.get("action_log", []),
                "last_updated": datetime.utcnow(),
                "is_signed": state.get("is_signed", False),
            }
            
            # Upsert (save or update)
            await sessions_collection.update_one(
                {"_id": session_id},
                {"$set": session_doc},
                upsert=True
            )
            
            # ── CRM SYNC (Sync back to Users collection if phone exists) ──
            phone = state.get("customer_data", {}).get("phone")
            if phone:
                from db.database import users_collection
                cust_update = {
                    "credit_score": state.get("customer_data", {}).get("credit_score"),
                    "pre_approved_limit": state.get("customer_data", {}).get("pre_approved_limit"),
                    "city": state.get("customer_data", {}).get("city"),
                    "salary": state.get("customer_data", {}).get("salary"),
                    "address": state.get("customer_data", {}).get("address"),
                    "last_active": datetime.utcnow()
                }
                # Remove None values
                cust_update = {k: v for k, v in cust_update.items() if v is not None}
                await users_collection.update_one(
                    {"phone": phone},
                    {"$set": cust_update},
                    upsert=True
                )

            print(f"✅ Session {session_id} saved to MongoDB and CRM synced")
            return True
        except Exception as e:
            print(f"❌ Error saving session: {e}")
            return False
    
    @staticmethod
    async def load_session(session_id: str) -> Optional[Dict[str, Any]]:
        """Load session state from MongoDB (async Motor). Always returns complete state schema."""
        try:
            session_doc = await sessions_collection.find_one({"_id": session_id})
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
                "requested_amount": 0,  # Original amount user asked for
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
    async def save_document(session_id: str, document_type: str, document_path: str, 
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
            
            result = await documents_collection.insert_one(doc_record)
            print(f"✅ Document {document_type} saved with ID: {result.inserted_id}")
            return True
        except Exception as e:
            print(f"❌ Error saving document: {e}")
            return False
    
    @staticmethod
    async def get_session_documents(session_id: str) -> list:
        """Retrieve all documents for a session."""
        try:
            cursor = documents_collection.find({"session_id": session_id})
            docs = await cursor.to_list(length=100)
            for doc in docs:
                doc.pop("_id", None)
            return docs
        except Exception as e:
            print(f"❌ Error retrieving documents: {e}")
            return []
    
    @staticmethod
    async def delete_session(session_id: str) -> bool:
        """Delete a session (after completion/timeout)."""
        try:
            await sessions_collection.delete_one({"_id": session_id})
            await documents_collection.delete_many({"session_id": session_id})
            print(f"Session {session_id} deleted from MongoDB")
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False

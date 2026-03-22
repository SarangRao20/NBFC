"""Mock Database for Testing - When MongoDB is not available."""

from typing import Dict, Any, List
import uuid
from datetime import datetime

import json
import os

# Global in-memory mock database - persists across requests
MOCK_DB_FILE = "mock_db.json"

def load_mock_db():
    if os.path.exists(MOCK_DB_FILE):
        try:
            with open(MOCK_DB_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "users": {},
        "sessions": {},
        "loan_applications": {},
        "chat_sessions": {},
        "uploaded_documents": {}
    }

def save_mock_db(data):
    try:
        with open(MOCK_DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to save mock DB: {e}")

mock_db = load_mock_db()

class MockCollection:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        if collection_name not in mock_db:
            mock_db[collection_name] = {}
        self.data = mock_db[collection_name]
    
    def _persist(self):
        save_mock_db(mock_db)
    
    async def insert_one(self, document: Dict[str, Any]):
        doc_id = document.get("_id", str(uuid.uuid4()))
        document["_id"] = doc_id
        self.data[doc_id] = document
        self._persist()
        print(f"📝 Inserted into {self.collection_name}: {doc_id}")
        return type("Result", (), {"inserted_id": doc_id})()
    
    async def find_one(self, query: Dict[str, Any]):
        if "_id" in query:
            doc_id = query["_id"]
            result = self.data.get(doc_id)
            print(f"🔍 Find one in {self.collection_name} by ID {doc_id}: {'Found' if result else 'Not found'}")
            return result
        # Simple mock - return first matching document
        for doc_id, doc in self.data.items():
            if all(doc.get(k) == v for k, v in query.items()):
                print(f"🔍 Find one in {self.collection_name} by query: Found {doc_id}")
                return doc
        print(f"🔍 Find one in {self.collection_name} by query: Not found")
        return None
    
    async def find(self):
        print(f"🔍 Find all in {self.collection_name}: {len(self.data)} documents")
        return list(self.data.values())
    
    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        # Find the first document that matches the query
        doc_to_update = None
        for doc_id, doc in self.data.items():
            if all(doc.get(k) == v for k, v in query.items()):
                doc_to_update = doc
                break
        
        if doc_to_update:
            doc_id = doc_to_update["_id"]
            if "$set" in update:
                self.data[doc_id].update(update["$set"])
                print(f"✏️ Updated {self.collection_name}: {doc_id}")
            else:
                # Basic update without $set (Atlas style)
                self.data[doc_id].update(update)
                print(f"✏️ Updated {self.collection_name} (direct): {doc_id}")
            self._persist()
            return type("Result", (), {"matched_count": 1, "modified_count": 1})()
            
        print(f"❌ Update failed in {self.collection_name}: No document matching {query}")
        return type("Result", (), {"matched_count": 0, "modified_count": 0})()
    
    async def replace_one(self, query: Dict[str, Any], replacement: Dict[str, Any]):
        # Find the first document that matches the query
        doc_to_replace = None
        for doc_id, doc in self.data.items():
            if all(doc.get(k) == v for k, v in query.items()):
                doc_to_replace = doc
                break
        
        if doc_to_replace:
            doc_id = doc_to_replace["_id"]
            # Ensure replacement has the same _id if it doesn't have one
            if "_id" not in replacement:
                replacement["_id"] = doc_id
            self.data[doc_id] = replacement
            self._persist()
            print(f"🔄 Replaced {self.collection_name}: {doc_id}")
            return type("Result", (), {"matched_count": 1, "modified_count": 1})()
            
        print(f"❌ Replace failed in {self.collection_name}: No document matching {query}")
        return type("Result", (), {"matched_count": 0, "modified_count": 0})()
    
    async def delete_one(self, query: Dict[str, Any]):
        # Find the first document that matches the query
        doc_to_delete = None
        for doc_id, doc in self.data.items():
            if all(doc.get(k) == v for k, v in query.items()):
                doc_to_delete = doc
                break
        
        if doc_to_delete:
            doc_id = doc_to_delete["_id"]
            del self.data[doc_id]
            self._persist()
            print(f"🗑️ Deleted from {self.collection_name}: {doc_id}")
            return type("Result", (), {"deleted_count": 1})()
            
        print(f"❌ Delete failed in {self.collection_name}: No document matching {query}")
        return type("Result", (), {"deleted_count": 0})()

# Mock client
class MockClient:
    def __init__(self):
        self.admin = type("Admin", (), {"command": self._ping})()
    
    async def _ping(self, command):
        print("🏓 MongoDB ping successful (mock)")
        return {"ok": 1}

# Mock database
class MockDatabase:
    def __init__(self):
        self.collections = {}
    
    def __getitem__(self, name: str):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]
    
    async def list_collection_names(self):
        print(f"📋 Listing collections: {list(mock_db.keys())}")
        return list(mock_db.keys())
    
    async def create_collection(self, name: str):
        if name not in mock_db:
            mock_db[name] = {}
            print(f"📦 Created collection: {name}")
        else:
            print(f"✅ Collection already exists: {name}")
        return None

# Initialize mock database (only once)
print("🔧 Initializing mock database for development")
client = MockClient()
database = MockDatabase()

# Collections
users_collection = database["users"]
sessions_collection = database["sessions"]
loan_applications_collection = database["loan_applications"]
chat_sessions_collection = database["chat_sessions"]
documents_collection = database["uploaded_documents"]

async def init_collections():
    """Initialize mock collections."""
    print("📦 Using mock database (no MongoDB required)")
    for name in mock_db.keys():
        print(f"  ✅ Mock collection ready: {name}")
    return True

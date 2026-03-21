"""Mock Database for Testing - When MongoDB is not available."""

from typing import Dict, Any, List
import uuid
from datetime import datetime

# Global in-memory mock database - persists across requests
mock_db = {
    "users": {},
    "sessions": {},
    "loan_applications": {},
    "chat_sessions": {},
    "uploaded_documents": {}
}

class MockCollection:
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self.data = mock_db[collection_name]
    
    async def insert_one(self, document: Dict[str, Any]):
        doc_id = document.get("_id", str(uuid.uuid4()))
        document["_id"] = doc_id
        self.data[doc_id] = document
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
        if "_id" in query:
            doc_id = query["_id"]
            if doc_id in self.data:
                if "$set" in update:
                    self.data[doc_id].update(update["$set"])
                    print(f"✏️ Updated {self.collection_name}: {doc_id}")
                return type("Result", (), {"matched_count": 1, "modified_count": 1})()
        print(f"❌ Update failed in {self.collection_name}: Document not found")
        return type("Result", (), {"matched_count": 0, "modified_count": 0})()
    
    async def replace_one(self, query: Dict[str, Any], replacement: Dict[str, Any]):
        if "_id" in query:
            doc_id = query["_id"]
            if doc_id in self.data:
                self.data[doc_id] = replacement
                print(f"🔄 Replaced {self.collection_name}: {doc_id}")
                return type("Result", (), {"matched_count": 1, "modified_count": 1})()
        print(f"❌ Replace failed in {self.collection_name}: Document not found")
        return type("Result", (), {"matched_count": 0, "modified_count": 0})()
    
    async def delete_one(self, query: Dict[str, Any]):
        if "_id" in query:
            doc_id = query["_id"]
            if doc_id in self.data:
                del self.data[doc_id]
                print(f"🗑️ Deleted from {self.collection_name}: {doc_id}")
                return type("Result", (), {"deleted_count": 1})()
        print(f"❌ Delete failed in {self.collection_name}: Document not found")
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

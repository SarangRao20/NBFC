from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

# Use mock database if no MongoDB URI is provided
if not MONGO_URI or MONGO_URI == "mock":
    from .mock_database import (
        client, database, users_collection, sessions_collection,
        loan_applications_collection, chat_sessions_collection,
        documents_collection, init_collections
    )
    print("🔧 Using mock database for development")
else:
    # ── SYNCHRONOUS PYMONGO CLIENT ──────────────────────────────────────────────
    client = MongoClient(MONGO_URI)
    database = client["nbfc_db"]   # Master Database

    # Synchronous Collections (PyMongo)
    users_collection = database["users"]
    sessions_collection = database["sessions"]
    loan_applications_collection = database["loan_applications"]
    chat_sessions_collection = database["chat_sessions"]
    documents_collection = database["uploaded_documents"]

# ── All collection names to ensure exist in Atlas ───────────────────────────
COLLECTION_NAMES = [
    "users",
    "sessions",
    "loan_applications",
    "chat_sessions",
    "uploaded_documents",
]


def init_collections():
    """Initialize collections and GridFS in MongoDB Atlas."""
    if not MONGO_URI or MONGO_URI == "mock":
        # Mock database already initialized
        return True
    else:
        # MongoDB Atlas initialization
        existing = database.list_collection_names()
        for name in COLLECTION_NAMES:
            if name not in existing:
                database.create_collection(name)
                print(f"  📦 Created collection: {name}")
        
        # Initialize GridFS
        from db.gridfs_service import init_gridfs_sync
        init_gridfs_sync(database)
        
        return True

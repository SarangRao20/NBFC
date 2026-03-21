from motor.motor_asyncio import AsyncIOMotorClient
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
    # ── ASYNC CLIENT FOR FASTAPI ────────────────────────────────────────────────
    client = AsyncIOMotorClient(MONGO_URI)
    database = client["nbfc_db"]   # Master Database

    # Async Collections
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


async def init_collections():
    """Initialize collections in MongoDB Atlas or mock database."""
    if not MONGO_URI or MONGO_URI == "mock":
        # Mock database already initialized
        return True
    else:
        # MongoDB Atlas initialization
        existing = await database.list_collection_names()
        for name in COLLECTION_NAMES:
            if name not in existing:
                await database.create_collection(name)
                print(f"  📦 Created collection: {name}")
            else:
                print(f"  ✅ Collection already exists: {name}")

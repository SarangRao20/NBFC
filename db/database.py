from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from api.config import get_settings

load_dotenv()

settings = get_settings()

# Use MongoDB URI from settings
MONGO_URI = settings.MONGO_URI

print(f"🔍 MongoDB URI from settings: {MONGO_URI[:20]}..." if MONGO_URI else "None")

# Use mock database if no MongoDB URI is provided
if not MONGO_URI or MONGO_URI == "mongodb://localhost:27017/nbfc":
    from .mock_database import (
        client, database, users_collection, sessions_collection,
        loan_applications_collection, chat_sessions_collection,
        documents_collection, init_collections
    )
    print("🔧 Using mock database for development")
else:
    print(f"🌐 Connecting to MongoDB: {MONGO_URI[:30]}...")
    try:
        # ── ASYNCHRONOUS MOTOR CLIENT ──────────────────────────────────────
        client = AsyncIOMotorClient(MONGO_URI)
        database = client["nbfc_db"]   # Master Database

        # Asynchronous Collections (Motor)
        users_collection = database["users"]
        sessions_collection = database["sessions"]
        loan_applications_collection = database["loan_applications"]
        chat_sessions_collection = database["chat_sessions"]
        documents_collection = database["uploaded_documents"]
        print("✅ MongoDB collections initialized successfully")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("🔧 Falling back to mock database")
        from .mock_database import (
            client, database, users_collection, sessions_collection,
            loan_applications_collection, chat_sessions_collection,
            documents_collection, init_collections
        )

# ── All collection names to ensure exist in Atlas ───────────────────────────
COLLECTION_NAMES = [
    "users",
    "sessions",
    "loan_applications",
    "chat_sessions",
    "uploaded_documents",
]


async def init_collections():
    """Initialize collections and GridFS in MongoDB Atlas."""
    if not MONGO_URI or MONGO_URI == "mock":
        # Mock database already initialized - no need to do anything
        return
    else:
        # MongoDB Atlas initialization
        existing = await database.list_collection_names()
        for name in COLLECTION_NAMES:
            if name not in existing:
                await database.create_collection(name)
                print(f"  📦 Created collection: {name}")
        
        # Initialize GridFS
        from db.gridfs_service import init_gridfs_sync # Note: GridFS might still be sync, check later
        # init_gridfs_sync(database) # GridFS usually needs a sync client or a specific async wrapper
        
        return True

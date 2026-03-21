from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

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
    """Explicitly create all collections in MongoDB Atlas so they are visible,
    even before any documents are inserted.  Skips collections that already exist."""
    existing = await database.list_collection_names()
    for name in COLLECTION_NAMES:
        if name not in existing:
            await database.create_collection(name)
            print(f"  📦 Created collection: {name}")
        else:
            print(f"  ✅ Collection already exists: {name}")

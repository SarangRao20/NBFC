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

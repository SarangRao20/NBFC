"""FinServe NBFC — Unified Main Entry Point."""

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from db.schemas import User
from db.database import users_collection, client
from api.config import get_settings
from api.routers import (
    session, sales, documents, kyc, fraud,
    underwriting, persuasion, sanction, advisory
)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="End-to-end NBFC loan origination API with MongoDB persistence.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.on_event("startup")
async def startup_db():
    try:
        await client.admin.command("ping")
        print("✅ MongoDB Atlas connected")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise

# ── 1. Users CRUD (MongoDB Atlas) ──────────────────────────────────────────

@app.post("/users", tags=["Users"])
async def create_user(user: User):
    try:
        user_dict = user.dict()
        result = await users_collection.insert_one(user_dict)
        return {"id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/users", tags=["Users"])
async def get_users():
    users = []
    async for user in users_collection.find():
        user["_id"] = str(user["_id"])
        users.append(user)
    return users

@app.get("/users/{user_id}", tags=["Users"])
async def get_user(user_id: str):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return user

@app.put("/users/{user_id}", tags=["Users"])
async def update_user(user_id: str, user: User):
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": user.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Updated", "modified": result.modified_count}

@app.delete("/users/{user_id}", tags=["Users"])
async def delete_user(user_id: str):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Deleted"}

# ── 2. Loan Workflow Routers ────────────────────────────────────────────────

app.include_router(session.router)       # Steps 1, 4, 18
app.include_router(sales.router)         # Steps 2, 3
app.include_router(documents.router)     # Steps 5, 6, 7, 8
app.include_router(kyc.router)           # Step 9
app.include_router(fraud.router)         # Step 10
app.include_router(underwriting.router)  # Step 11
app.include_router(persuasion.router)    # Steps 12, 13, 14, 15
app.include_router(sanction.router)      # Step 16
app.include_router(advisory.router)      # Step 17

@app.get("/", tags=["Root"])
def root():
    """API health check and workflow summary."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

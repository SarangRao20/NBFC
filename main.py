"""FinServe NBFC — Unified Main Entry Point."""

import traceback
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from api.core.websockets import manager
from contextlib import asynccontextmanager
from db.schemas import User
from db.database import users_collection, client, init_collections
from api.config import get_settings
from api.routers import (
    session, sales, documents, kyc, fraud,
    underwriting, sanction, advisory, payment, admin
)
from api.routers.auth import router as auth_router

settings = get_settings()

# Ensure stdout/stderr use UTF-8 on Windows to avoid UnicodeEncodeError when printing
import sys, os
if os.name == "nt":
    try:
        # Force UTF-8 mode for the interpreter and reconfigure text streams
        os.environ.setdefault("PYTHONUTF8", "1")
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        # Reconfigure existing text streams to utf-8 and replace invalid chars
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Fallback for older Python versions: wrap buffers with TextIOWrapper
            import io
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
            except Exception:
                pass
    except Exception:
        # Best-effort: if reconfigure not available, fall back silently
        pass

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="End-to-end NBFC loan origination API with MongoDB persistence.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Global Exception Handler to log full tracebacks to terminal
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print("\n" + "="*50)
    print(f"🔥 UNHANDLED EXCEPTION: {request.method} {request.url}")
    print("="*50)
    traceback.print_exc()
    print("="*50 + "\n")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check terminal logs."},
        headers={"Access-Control-Allow-Origin": "*"}
    )

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173", 
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:5173",
        # Add your Vercel frontend URL here after deployment
        "https://*.vercel.app",  # Allow all Vercel domains
        "https://nbfc-inc.vercel.app",  # Your actual Vercel URL
        # Allow all origins for development (remove in production)
        "*"  # Temporary fix for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"❌ [VALIDATION ERROR] {request.method} {request.url}")
    print(f"❌ Body: {exc.body}")
    print(f"❌ Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    print(f"❌ [RESPONSE VALIDATION ERROR] {request.method} {request.url}")
    print(f"❌ Error details: {exc.errors()}")
    # Log the first few fields that failed
    for error in exc.errors():
        print(f"   - Field: {'.'.join(str(i) for i in error['loc'])} | Issue: {error['msg']}")
        
    return JSONResponse(
        status_code=500,
        content={"detail": f"Response validation error: {str(exc)}"},
        headers={"Access-Control-Allow-Origin": "*"} # Ensure browser sees the 500
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_db()
    yield
    # Shutdown
    client.close()

# Lifespan event handler
app.router.lifespan_context = lifespan

async def startup_db():
    try:
        await client.admin.command("ping")
        print("✅ MongoDB Atlas connected")
        await init_collections()
        print("✅ All collections initialized")
        
        # Initialize Redis and Email services
        from api.core.redis_cache import get_cache
        from api.core.email_service import get_email_service
        
        cache = await get_cache()
        if cache.connected:
            print("✅ Redis cache connected")
        else:
            print("⚠️ Redis cache not available - using database fallback")
        
        email_service = await get_email_service()
        print("✅ Email service initialized")
        
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
    cursor = users_collection.find()
    async for user in cursor:
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
app.include_router(sanction.router)      # Step 16
app.include_router(advisory.router)      # Step 17
app.include_router(payment.router)       # EMI Payments
app.include_router(admin.router)         # Admin dashboard & analytics (Phase 5)
app.include_router(auth_router)          # Authentication & Profile Management

@app.get("/", tags=["Root"])
def root():
    """API health check and workflow summary."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }

# WebSocket Endpoint for Real-time Updates
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WS messages if needed (currently focus on Push from server)
            print(f"📥 [WS] Message from {session_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"⚠️ [WS] Error in {session_id}: {e}")
        manager.disconnect(websocket, session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

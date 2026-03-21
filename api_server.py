from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import importlib
import pkgutil
import os
import shutil
from typing import Any

app = FastAPI(title="NBFC Agents API")

# Allow frontend dev server origins (adjust if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentCall(BaseModel):
    node: str | None = None
    state: dict = {}


def _serialize(obj: Any):
    """Recursively serialize objects returned by agents into plain JSON."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list) or isinstance(obj, tuple):
        return [_serialize(v) for v in obj]
    # Common message objects have a .content attribute
    if hasattr(obj, "content"):
        return getattr(obj, "content")
    # Fallback to string
    try:
        return str(obj)
    except Exception:
        return None


@app.get("/api/agents")
def list_agents():
    pkg = importlib.import_module("agents")
    mods = [m.name for m in pkgutil.iter_modules(pkg.__path__)]
    return {"agents": mods}


@app.post("/api/agent/{agent_name}")
def call_agent(agent_name: str, body: AgentCall):
    try:
        mod = importlib.import_module(f"agents.{agent_name}")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_name}")

    fn = None
    # If user provided explicit node name, try that first
    if body.node:
        fn = getattr(mod, body.node, None)

    # Common fallbacks
    if fn is None:
        for candidate in ["agent_node", f"{agent_name}_node", "chat_node", "extraction_node", "document_query_agent_node"]:
            fn = getattr(mod, candidate, None)
            if fn:
                break

    if fn is None:
        # If module exposes a builder, return a notice instead of executing
        builder_name = f"build_{agent_name}_agent"
        if hasattr(mod, builder_name):
            return {"ok": True, "message": f"Agent compiled via {builder_name}. Use agent-specific nodes for runtime."}
        raise HTTPException(status_code=400, detail="No callable agent node found in module.")

    # Call the node function with provided state
    try:
        result = fn(body.state)
    except TypeError:
        # try calling without args
        result = fn()

    return {"result": _serialize(result)}


@app.post("/api/upload")
def upload_file(file: UploadFile = File(...)):
    uploads_dir = os.path.join(os.getcwd(), "data", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    dest_path = os.path.join(uploads_dir, file.filename)
    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        file.file.close()
    return {"path": dest_path}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)

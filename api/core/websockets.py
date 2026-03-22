from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # session_id -> List[WebSocket] (allow multiple tabs for same session)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        print(f"🔌 [WS] Connected: {session_id} (Total: {len(self.active_connections[session_id])})")

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        print(f"🔌 [WS] Disconnected: {session_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a JSON message to all connections for a specific session."""
        if session_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"⚠️ [WS] Failed to send to {session_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up dead connections
            for conn in disconnected:
                self.disconnect(conn, session_id)

manager = ConnectionManager()

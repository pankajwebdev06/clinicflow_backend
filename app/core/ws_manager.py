from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Dictionary mapping clinic_id to list of active WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, clinic_id: str, websocket: WebSocket):
        await websocket.accept()
        if clinic_id not in self.active_connections:
            self.active_connections[clinic_id] = []
        self.active_connections[clinic_id].append(websocket)

    def disconnect(self, clinic_id: str, websocket: WebSocket):
        if clinic_id in self.active_connections:
            self.active_connections[clinic_id].remove(websocket)
            if not self.active_connections[clinic_id]:
                del self.active_connections[clinic_id]

    async def broadcast_to_clinic(self, clinic_id: str, message: dict):
        """Send a message to all connected devices in a specific clinic."""
        if clinic_id in self.active_connections:
            for connection in self.active_connections[clinic_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Connection might be closed
                    continue

manager = ConnectionManager()

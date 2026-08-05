from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from typing import Optional
import json
from app.core.logging import logger
from app.core.security import decode_jwt_token
from app.websocket.manager import ws_manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """Authenticated WebSocket endpoint for real-time Meta telemetry updates."""
    user_id = "anonymous"
    if token:
        payload = decode_jwt_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning("websocket_auth_failed_invalid_jwt")
            return
        user_id = payload.get("sub", "authenticated_user")

    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data) if data.startswith("{") else {"event": data}
            except Exception:
                msg = {"event": data}

            if msg.get("event") == "ping" or data == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "timestamp": "ok", "user_id": user_id}))
            else:
                await ws_manager.broadcast({"event": "telemetry_ack", "payload": msg, "sender": user_id})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("websocket_session_error", error=str(e))
        ws_manager.disconnect(websocket)

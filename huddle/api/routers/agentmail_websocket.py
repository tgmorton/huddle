"""WebSocket router for real-time AgentMail updates."""

import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from huddle.api.services.agentmail_service import (
    AgentMailWSMessage,
    AgentMailWSMessageType,
    agentmail_session_manager,
    get_file_watcher,
)

router = APIRouter(tags=["agentmail-websocket"])

# Path to agentmail folder (relative to project root)
AGENTMAIL_PATH = Path(__file__).parent.parent.parent.parent / "agentmail"


@router.websocket("/ws/agentmail")
async def agentmail_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time AgentMail updates.

    Clients connect to receive:
    - Full state syncs (dashboard data)
    - Message added/updated notifications
    - Agent status changes
    - Agent online/offline notifications

    Clients can send:
    - request_sync: Request a full state sync
    """
    await websocket.accept()

    # Register this connection
    await agentmail_session_manager.connect(websocket)

    # Start file watcher if not running (lazily starts on first client)
    file_watcher = get_file_watcher(AGENTMAIL_PATH)
    await file_watcher.start()

    try:
        # Send initial state sync
        from huddle.api.routers.agentmail import get_dashboard_data

        try:
            dashboard_data = await get_dashboard_data()
            state_sync = AgentMailWSMessage.state_sync(dashboard_data)
            await websocket.send_json(state_sync.to_dict())
        except Exception as e:
            await websocket.send_json(
                AgentMailWSMessage.create_error(
                    f"Failed to load initial state: {str(e)}",
                    "INIT_ERROR"
                ).to_dict()
            )

        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await _handle_client_message(websocket, message)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json(
                    AgentMailWSMessage.create_error(
                        "Invalid JSON",
                        "INVALID_JSON"
                    ).to_dict()
                )

    except Exception as e:
        try:
            await websocket.send_json(
                AgentMailWSMessage.create_error(str(e), "ERROR").to_dict()
            )
        except Exception:
            pass
    finally:
        # Unregister this connection
        await agentmail_session_manager.disconnect(websocket)


async def _handle_client_message(websocket: WebSocket, message: dict) -> None:
    """Handle incoming client WebSocket message."""
    msg_type = message.get("type")

    if msg_type == AgentMailWSMessageType.REQUEST_SYNC.value:
        # Send full state sync
        from huddle.api.routers.agentmail import get_dashboard_data

        try:
            dashboard_data = await get_dashboard_data()
            state_sync = AgentMailWSMessage.state_sync(dashboard_data)
            await websocket.send_json(state_sync.to_dict())
        except Exception as e:
            await websocket.send_json(
                AgentMailWSMessage.create_error(
                    f"Failed to sync: {str(e)}",
                    "SYNC_ERROR"
                ).to_dict()
            )
    else:
        # Unknown message type
        await websocket.send_json(
            AgentMailWSMessage.create_error(
                f"Unknown message type: {msg_type}",
                "UNKNOWN_TYPE"
            ).to_dict()
        )

"""WebSocket router for real-time game updates."""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from huddle.api.schemas.events import WSMessage, WSMessageType
from huddle.api.services.session_manager import session_manager
from huddle.core.enums import PassType, RunType
from huddle.core.models.play import PlayCall

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/games/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: UUID) -> None:
    """
    WebSocket endpoint for real-time game updates.

    Clients connect to receive play-by-play events and can send control messages.
    """
    await websocket.accept()

    # Get or validate session
    session = session_manager.get_session(game_id)
    if not session:
        await websocket.send_json(
            WSMessage.error(f"Game {game_id} not found", "GAME_NOT_FOUND").model_dump(mode="json")
        )
        await websocket.close()
        return

    # Attach WebSocket to session
    session_manager.attach_websocket(game_id, websocket)

    try:
        # Send initial state sync
        state_sync = WSMessage.state_sync(
            session.service.game_state,
            session.service.home_team,
            session.service.away_team,
        )
        await websocket.send_json(state_sync.model_dump(mode="json"))

        # Start simulation if not already running
        if not session.service.is_running:
            session.start_simulation()

        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await _handle_client_message(session, message)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json(
                    WSMessage.error("Invalid JSON", "INVALID_JSON").model_dump(mode="json")
                )

    except Exception as e:
        try:
            await websocket.send_json(
                WSMessage.error(str(e), "ERROR").model_dump(mode="json")
            )
        except Exception:
            pass
    finally:
        # Detach WebSocket from session
        session_manager.detach_websocket(game_id)


async def _handle_client_message(session, message: dict) -> None:
    """Handle incoming client WebSocket message."""
    msg_type = message.get("type")

    if msg_type == WSMessageType.PAUSE.value:
        session.service.pause()

    elif msg_type == WSMessageType.RESUME.value:
        session.service.resume()

    elif msg_type == WSMessageType.SET_PACING.value:
        pacing = message.get("payload", {}).get("pacing")
        if pacing:
            session.service.set_pacing(pacing)

    elif msg_type == WSMessageType.PLAY_CALL.value:
        payload = message.get("payload", {})
        play_call = _create_play_call_from_ws(payload)
        if play_call:
            session.service.submit_play_call(play_call)

    elif msg_type == WSMessageType.REQUEST_SYNC.value:
        # Send current state
        if session.websocket:
            state_sync = WSMessage.state_sync(
                session.service.game_state,
                session.service.home_team,
                session.service.away_team,
            )
            await session.websocket.send_json(state_sync.model_dump(mode="json"))


def _create_play_call_from_ws(payload: dict) -> PlayCall:
    """Create PlayCall from WebSocket payload."""
    play_type = payload.get("play_type", "RUN")

    if play_type == "RUN":
        run_type_str = payload.get("run_type", "INSIDE")
        run_type = RunType[run_type_str] if run_type_str else RunType.INSIDE
        return PlayCall.run(run_type)

    elif play_type == "PASS":
        pass_type_str = payload.get("pass_type", "SHORT")
        pass_type = PassType[pass_type_str] if pass_type_str else PassType.SHORT
        return PlayCall.pass_play(pass_type)

    elif play_type == "PUNT":
        return PlayCall.punt()

    elif play_type == "FIELD_GOAL":
        return PlayCall.field_goal()

    else:
        # Default to run
        return PlayCall.run(RunType.INSIDE)

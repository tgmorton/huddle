"""WebSocket router for real-time management updates."""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from huddle.management import TimeSpeed, ClipboardTab
from huddle.api.schemas.management import (
    ManagementWSMessage,
    ManagementWSMessageType,
    TimeSpeedSchema,
    ClipboardTabSchema,
)
from huddle.api.services.management_service import management_session_manager

router = APIRouter(tags=["management-websocket"])


@router.websocket("/ws/management/{franchise_id}")
async def management_websocket(websocket: WebSocket, franchise_id: UUID) -> None:
    """
    WebSocket endpoint for real-time management updates.

    Clients connect to receive:
    - Calendar updates (time progression)
    - Event notifications (new events, expirations)
    - Ticker updates (news feed)
    - Auto-pause notifications

    Clients can send:
    - Time controls (pause, play, set speed)
    - Clipboard navigation (tab selection, go back)
    - Event actions (attend, dismiss)
    """
    await websocket.accept()

    # Get session
    session = management_session_manager.get_session(franchise_id)
    if not session:
        await websocket.send_json(
            ManagementWSMessage.create_error(
                f"Franchise {franchise_id} not found",
                "FRANCHISE_NOT_FOUND"
            ).model_dump(mode="json")
        )
        await websocket.close()
        return

    # Attach WebSocket to session
    management_session_manager.attach_websocket(franchise_id, websocket)

    try:
        # Send initial state sync
        state = session.service.get_full_state()
        state_sync = ManagementWSMessage.state_sync(state)
        await websocket.send_json(state_sync.model_dump(mode="json"))

        # Listen for client messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await _handle_client_message(session, websocket, message)
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json(
                    ManagementWSMessage.create_error(
                        "Invalid JSON",
                        "INVALID_JSON"
                    ).model_dump(mode="json")
                )

    except Exception as e:
        try:
            await websocket.send_json(
                ManagementWSMessage.create_error(str(e), "ERROR").model_dump(mode="json")
            )
        except Exception:
            pass
    finally:
        # Detach WebSocket
        management_session_manager.detach_websocket(franchise_id)


async def _handle_client_message(session, websocket: WebSocket, message: dict) -> None:
    """Handle incoming client WebSocket message."""
    msg_type = message.get("type")
    payload = message.get("payload", {})

    if msg_type == ManagementWSMessageType.PAUSE.value:
        session.service.pause()
        await _send_calendar_update(session, websocket)

    elif msg_type == ManagementWSMessageType.PLAY.value:
        speed_str = payload.get("speed", "NORMAL")
        try:
            speed = TimeSpeed[speed_str]
        except KeyError:
            speed = TimeSpeed.NORMAL
        session.service.play(speed)
        await _send_calendar_update(session, websocket)

    elif msg_type == ManagementWSMessageType.SET_SPEED.value:
        speed_str = payload.get("speed", "NORMAL")
        try:
            speed = TimeSpeed[speed_str]
        except KeyError:
            speed = TimeSpeed.NORMAL
        session.service.set_speed(speed)
        await _send_calendar_update(session, websocket)

    elif msg_type == ManagementWSMessageType.SELECT_TAB.value:
        tab_str = payload.get("tab", "EVENTS")
        try:
            tab = ClipboardTab[tab_str]
        except KeyError:
            tab = ClipboardTab.EVENTS
        session.service.select_tab(tab)
        await _send_clipboard_update(session, websocket)

    elif msg_type == ManagementWSMessageType.ATTEND_EVENT.value:
        event_id_str = payload.get("event_id")
        if event_id_str:
            try:
                event_id = UUID(event_id_str)
                session.service.attend_event(event_id)
                await _send_clipboard_update(session, websocket)
            except ValueError:
                await websocket.send_json(
                    ManagementWSMessage.create_error(
                        "Invalid event ID",
                        "INVALID_EVENT_ID"
                    ).model_dump(mode="json")
                )

    elif msg_type == ManagementWSMessageType.DISMISS_EVENT.value:
        event_id_str = payload.get("event_id")
        if event_id_str:
            try:
                event_id = UUID(event_id_str)
                session.service.dismiss_event(event_id)
                await _send_events_update(session, websocket)
            except ValueError:
                pass

    elif msg_type == ManagementWSMessageType.RUN_PRACTICE.value:
        event_id_str = payload.get("event_id")
        allocation = payload.get("allocation", {})
        if event_id_str:
            try:
                event_id = UUID(event_id_str)
                session.service.run_practice(
                    event_id,
                    playbook=allocation.get("playbook", 34),
                    development=allocation.get("development", 33),
                    game_prep=allocation.get("gamePrep", 33),
                )
                await _send_clipboard_update(session, websocket)
                await _send_events_update(session, websocket)
            except ValueError:
                await websocket.send_json(
                    ManagementWSMessage.create_error(
                        "Invalid event ID",
                        "INVALID_EVENT_ID"
                    ).model_dump(mode="json")
                )

    elif msg_type == ManagementWSMessageType.PLAY_GAME.value:
        event_id_str = payload.get("event_id")
        if event_id_str:
            try:
                event_id = UUID(event_id_str)
                # For now, play_game does the same as sim - just with more fanfare later
                session.service.sim_game(event_id)
                await _send_clipboard_update(session, websocket)
                await _send_events_update(session, websocket)
            except ValueError:
                await websocket.send_json(
                    ManagementWSMessage.create_error(
                        "Invalid event ID",
                        "INVALID_EVENT_ID"
                    ).model_dump(mode="json")
                )

    elif msg_type == ManagementWSMessageType.SIM_GAME.value:
        event_id_str = payload.get("event_id")
        if event_id_str:
            try:
                event_id = UUID(event_id_str)
                session.service.sim_game(event_id)
                await _send_clipboard_update(session, websocket)
                await _send_events_update(session, websocket)
            except ValueError:
                await websocket.send_json(
                    ManagementWSMessage.create_error(
                        "Invalid event ID",
                        "INVALID_EVENT_ID"
                    ).model_dump(mode="json")
                )

    elif msg_type == ManagementWSMessageType.GO_BACK.value:
        session.service.go_back()
        await _send_clipboard_update(session, websocket)

    elif msg_type == ManagementWSMessageType.REQUEST_SYNC.value:
        # Send full state sync
        state = session.service.get_full_state()
        state_sync = ManagementWSMessage.state_sync(state)
        await websocket.send_json(state_sync.model_dump(mode="json"))


async def _send_calendar_update(session, websocket: WebSocket) -> None:
    """Send calendar update."""
    calendar = session.service._get_calendar_response()
    msg = ManagementWSMessage.calendar_update(calendar)
    await websocket.send_json(msg.model_dump(mode="json"))


async def _send_clipboard_update(session, websocket: WebSocket) -> None:
    """Send clipboard update."""
    clipboard = session.service._get_clipboard_response()
    msg = ManagementWSMessage(
        type=ManagementWSMessageType.CLIPBOARD_UPDATE,
        payload=clipboard.model_dump(mode="json"),
    )
    await websocket.send_json(msg.model_dump(mode="json"))


async def _send_events_update(session, websocket: WebSocket) -> None:
    """Send events update."""
    events = session.service._get_events_response()
    msg = ManagementWSMessage(
        type=ManagementWSMessageType.EVENT_UPDATED,
        payload=events.model_dump(mode="json"),
    )
    await websocket.send_json(msg.model_dump(mode="json"))

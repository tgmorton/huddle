"""WebSocket router for sandbox simulation real-time updates."""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from huddle.simulation.sandbox import SandboxPlayer, SimulationState, TickResult, get_session_manager

router = APIRouter(tags=["sandbox-websocket"])


def _player_to_dict(player: SandboxPlayer) -> dict:
    """Convert SandboxPlayer to dict."""
    return {
        "id": str(player.id),
        "name": player.name,
        "role": player.role.value,
        "strength": player.strength,
        "speed": player.speed,
        "agility": player.agility,
        "pass_block": player.pass_block,
        "awareness": player.awareness,
        "block_shedding": player.block_shedding,
        "power_moves": player.power_moves,
        "finesse_moves": player.finesse_moves,
    }


def _state_to_payload(session) -> dict:
    """Convert session state to payload dict."""
    state = session.simulator.get_state()
    return {
        "session_id": str(session.session_id),
        "blocker": _player_to_dict(session.simulator.blocker),
        "rusher": _player_to_dict(session.simulator.rusher),
        "tick_rate_ms": session.simulator.tick_rate_ms,
        "max_ticks": session.simulator.max_ticks,
        "qb_zone_depth": session.simulator.qb_zone_depth,
        "current_tick": state.current_tick,
        "is_running": not state.is_complete,
        "is_complete": state.is_complete,
        "blocker_position": {"x": state.blocker_position.x, "y": state.blocker_position.y},
        "rusher_position": {"x": state.rusher_position.x, "y": state.rusher_position.y},
        "outcome": state.outcome.value,
        "stats": {
            "rusher_wins_contest": state.rusher_wins_contest,
            "blocker_wins_contest": state.blocker_wins_contest,
            "neutral_contests": state.neutral_contests,
        },
    }


@router.websocket("/ws/sandbox/{session_id}")
async def sandbox_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for sandbox simulation.

    Client messages:
    - start_simulation: Start the tick loop
    - pause_simulation: Pause the simulation
    - resume_simulation: Resume paused simulation
    - reset_simulation: Reset to initial state
    - update_player: Update player attributes (when not running)
    - set_tick_rate: Change tick rate (when not running)
    - request_sync: Request full state sync

    Server messages:
    - tick_update: Sent each tick with positions and results
    - simulation_complete: Sent when simulation ends
    - state_sync: Full state on connect or request
    - error: Error message
    """
    await websocket.accept()

    manager = get_session_manager()

    # Validate session ID
    try:
        uuid = UUID(session_id)
    except ValueError:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid session ID format",
            "code": "INVALID_SESSION_ID",
        })
        await websocket.close()
        return

    session = await manager.get_session(uuid)
    if session is None:
        await websocket.send_json({
            "type": "error",
            "message": "Session not found",
            "code": "SESSION_NOT_FOUND",
        })
        await websocket.close()
        return

    # Send initial state
    await websocket.send_json({
        "type": "state_sync",
        "payload": _state_to_payload(session),
    })

    # Callback for tick updates
    async def send_tick(tick: TickResult) -> None:
        try:
            await websocket.send_json({
                "type": "tick_update",
                "payload": tick.to_dict(),
            })
        except Exception:
            pass

    # Callback for simulation complete
    async def send_complete(state: SimulationState) -> None:
        try:
            await websocket.send_json({
                "type": "simulation_complete",
                "payload": _state_to_payload(session),
            })
        except Exception:
            pass

    # We need sync wrappers for the async callbacks
    import asyncio

    loop = asyncio.get_event_loop()

    def on_tick(tick: TickResult) -> None:
        asyncio.run_coroutine_threadsafe(send_tick(tick), loop)

    def on_complete(state: SimulationState) -> None:
        asyncio.run_coroutine_threadsafe(send_complete(state), loop)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                    "code": "INVALID_JSON",
                })
                continue

            msg_type = message.get("type")

            if msg_type == "start_simulation":
                # Start the simulation
                success = await manager.start_simulation(
                    uuid,
                    on_tick=on_tick,
                    on_complete=on_complete,
                )
                if not success:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Could not start simulation (already running?)",
                        "code": "START_FAILED",
                    })

            elif msg_type == "pause_simulation":
                await manager.pause_simulation(uuid)

            elif msg_type == "resume_simulation":
                await manager.resume_simulation(uuid)

            elif msg_type == "reset_simulation":
                await manager.reset_simulation(uuid)
                await websocket.send_json({
                    "type": "state_sync",
                    "payload": _state_to_payload(session),
                })

            elif msg_type == "update_player":
                role = message.get("role")
                player_data = message.get("player")
                if role and player_data:
                    success = await manager.update_player(uuid, player_data, role)
                    if success:
                        await websocket.send_json({
                            "type": "state_sync",
                            "payload": _state_to_payload(session),
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Could not update player (simulation running?)",
                            "code": "UPDATE_FAILED",
                        })

            elif msg_type == "set_tick_rate":
                tick_rate = message.get("tick_rate_ms")
                if tick_rate:
                    success = await manager.set_tick_rate(uuid, tick_rate)
                    if success:
                        await websocket.send_json({
                            "type": "state_sync",
                            "payload": _state_to_payload(session),
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Could not set tick rate (simulation running?)",
                            "code": "TICK_RATE_FAILED",
                        })

            elif msg_type == "request_sync":
                await websocket.send_json({
                    "type": "state_sync",
                    "payload": _state_to_payload(session),
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                    "code": "UNKNOWN_MESSAGE",
                })

    except WebSocketDisconnect:
        # Clean up - stop simulation if running
        await manager.stop_simulation(uuid)

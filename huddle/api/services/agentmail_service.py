"""Service for managing AgentMail WebSocket connections and file watching."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Set
from enum import Enum

from fastapi import WebSocket


class AgentMailWSMessageType(str, Enum):
    """WebSocket message types for AgentMail."""
    STATE_SYNC = "state_sync"
    MESSAGE_ADDED = "message_added"
    MESSAGE_UPDATED = "message_updated"
    STATUS_CHANGED = "status_changed"
    AGENT_ONLINE = "agent_online"
    NOTE_ADDED = "note_added"
    NOTE_UPDATED = "note_updated"
    ERROR = "error"
    REQUEST_SYNC = "request_sync"


@dataclass
class AgentMailWSMessage:
    """WebSocket message for AgentMail."""
    type: AgentMailWSMessageType
    payload: Optional[dict] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"type": self.type.value}
        if self.payload is not None:
            result["payload"] = self.payload
        if self.error_message is not None:
            result["error_message"] = self.error_message
        if self.error_code is not None:
            result["error_code"] = self.error_code
        return result

    @classmethod
    def state_sync(cls, payload: dict) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.STATE_SYNC, payload=payload)

    @classmethod
    def message_added(cls, message: dict) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.MESSAGE_ADDED, payload=message)

    @classmethod
    def message_updated(cls, message: dict) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.MESSAGE_UPDATED, payload=message)

    @classmethod
    def status_changed(cls, agent: str, status: dict) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.STATUS_CHANGED, payload={"agent": agent, "status": status})

    @classmethod
    def agent_online(cls, agent: str, is_online: bool) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.AGENT_ONLINE, payload={"agent": agent, "is_online": is_online})

    @classmethod
    def note_added(cls, note: dict) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.NOTE_ADDED, payload=note)

    @classmethod
    def create_error(cls, message: str, code: str) -> "AgentMailWSMessage":
        return cls(type=AgentMailWSMessageType.ERROR, error_message=message, error_code=code)


class AgentMailSessionManager:
    """
    Manages WebSocket connections for AgentMail dashboard.

    Features:
    - Tracks all connected WebSocket clients
    - Broadcasts updates to all clients
    - Debounces file system changes
    """

    def __init__(self):
        self._websockets: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._last_broadcast: dict[str, datetime] = {}
        self._debounce_ms = 100  # Debounce file changes

    async def connect(self, websocket: WebSocket) -> None:
        """Add a WebSocket connection."""
        async with self._lock:
            self._websockets.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self._websockets.discard(websocket)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._websockets)

    async def broadcast(self, message: AgentMailWSMessage) -> None:
        """Broadcast a message to all connected clients."""
        if not self._websockets:
            return

        # Debounce repeated messages of the same type
        msg_key = f"{message.type.value}"
        now = datetime.now()
        last = self._last_broadcast.get(msg_key)
        if last and (now - last).total_seconds() * 1000 < self._debounce_ms:
            return
        self._last_broadcast[msg_key] = now

        message_dict = message.to_dict()

        # Send to all connected clients
        disconnected = set()
        async with self._lock:
            for ws in self._websockets:
                try:
                    await ws.send_json(message_dict)
                except Exception:
                    disconnected.add(ws)

            # Clean up disconnected clients
            self._websockets -= disconnected

    async def broadcast_state_sync(self, dashboard_data: dict) -> None:
        """Broadcast full state sync to all clients."""
        await self.broadcast(AgentMailWSMessage.state_sync(dashboard_data))

    async def broadcast_message_added(self, message: dict) -> None:
        """Broadcast that a new message was added."""
        await self.broadcast(AgentMailWSMessage.message_added(message))

    async def broadcast_message_updated(self, message: dict) -> None:
        """Broadcast that a message was updated."""
        await self.broadcast(AgentMailWSMessage.message_updated(message))

    async def broadcast_status_changed(self, agent: str, status: dict) -> None:
        """Broadcast that an agent's status changed."""
        await self.broadcast(AgentMailWSMessage.status_changed(agent, status))

    async def broadcast_agent_online(self, agent: str, is_online: bool) -> None:
        """Broadcast that an agent came online/offline."""
        await self.broadcast(AgentMailWSMessage.agent_online(agent, is_online))


# Global session manager instance
agentmail_session_manager = AgentMailSessionManager()


class AgentMailFileWatcher:
    """
    Watches the agentmail folder for file changes and broadcasts updates.

    Uses polling instead of watchdog for simplicity and cross-platform support.
    """

    def __init__(self, agentmail_path: Path, session_manager: AgentMailSessionManager):
        self.agentmail_path = agentmail_path
        self.session_manager = session_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._file_mtimes: dict[str, float] = {}
        self._poll_interval = 2.0  # Poll every 2 seconds

    async def start(self) -> None:
        """Start watching for file changes."""
        if self._running:
            return
        self._running = True
        self._file_mtimes = self._scan_files()
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        """Stop watching for file changes."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def _scan_files(self) -> dict[str, float]:
        """Scan all .md files and return their modification times."""
        mtimes = {}
        if not self.agentmail_path.exists():
            return mtimes

        for md_file in self.agentmail_path.rglob("*.md"):
            try:
                mtimes[str(md_file)] = md_file.stat().st_mtime
            except OSError:
                pass
        return mtimes

    async def _watch_loop(self) -> None:
        """Main watch loop - polls for file changes."""
        while self._running:
            try:
                await asyncio.sleep(self._poll_interval)

                if not self.session_manager.connection_count:
                    continue  # No clients connected, skip scanning

                new_mtimes = self._scan_files()

                # Find changes
                added = set(new_mtimes.keys()) - set(self._file_mtimes.keys())
                removed = set(self._file_mtimes.keys()) - set(new_mtimes.keys())
                modified = {
                    f for f in new_mtimes
                    if f in self._file_mtimes and new_mtimes[f] != self._file_mtimes[f]
                }

                # If any changes, broadcast state sync
                if added or removed or modified:
                    # Import here to avoid circular imports
                    from huddle.api.routers.agentmail import get_dashboard_data

                    try:
                        dashboard_data = await get_dashboard_data()
                        await self.session_manager.broadcast_state_sync(dashboard_data)
                    except Exception as e:
                        print(f"Error broadcasting state sync: {e}")

                self._file_mtimes = new_mtimes

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in file watcher: {e}")
                await asyncio.sleep(5)  # Back off on error


# Global file watcher instance (initialized lazily)
_file_watcher: Optional[AgentMailFileWatcher] = None


def get_file_watcher(agentmail_path: Path) -> AgentMailFileWatcher:
    """Get or create the file watcher instance."""
    global _file_watcher
    if _file_watcher is None:
        _file_watcher = AgentMailFileWatcher(agentmail_path, agentmail_session_manager)
    return _file_watcher

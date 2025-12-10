"""Session manager for sandbox simulations."""

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Optional
from uuid import UUID, uuid4

from .blocking_resolver import BlockingSimulator
from .models import SandboxPlayer, SimulationState, TickResult


@dataclass
class SandboxSession:
    """A sandbox simulation session."""

    session_id: UUID
    simulator: BlockingSimulator
    on_tick: Optional[Callable[[TickResult], None]] = None
    on_complete: Optional[Callable[[SimulationState], None]] = None

    # Async control
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _paused: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _stop_requested: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize pause event to running state."""
        self._paused.set()  # Start unpaused


class SandboxSessionManager:
    """
    Manages active sandbox simulation sessions.

    Thread-safe session storage with async tick loops.
    """

    def __init__(self) -> None:
        """Initialize the session manager."""
        self._sessions: dict[UUID, SandboxSession] = {}
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        blocker: Optional[SandboxPlayer] = None,
        rusher: Optional[SandboxPlayer] = None,
        tick_rate_ms: int = 100,
        max_ticks: int = 50,
        qb_zone_depth: float = 7.0,
    ) -> SandboxSession:
        """
        Create a new sandbox session.

        Args:
            blocker: Offensive lineman (defaults to SandboxPlayer.default_blocker())
            rusher: Defensive lineman (defaults to SandboxPlayer.default_rusher())
            tick_rate_ms: Milliseconds per simulation tick
            max_ticks: Maximum ticks before blocker wins
            qb_zone_depth: Yards from LOS where rusher wins

        Returns:
            New SandboxSession
        """
        if blocker is None:
            blocker = SandboxPlayer.default_blocker()
        if rusher is None:
            rusher = SandboxPlayer.default_rusher()

        simulator = BlockingSimulator(
            blocker=blocker,
            rusher=rusher,
            tick_rate_ms=tick_rate_ms,
            max_ticks=max_ticks,
            qb_zone_depth=qb_zone_depth,
        )

        session_id = uuid4()
        session = SandboxSession(session_id=session_id, simulator=simulator)

        async with self._lock:
            self._sessions[session_id] = session

        return session

    async def get_session(self, session_id: UUID) -> Optional[SandboxSession]:
        """Get a session by ID."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete a session.

        Stops the simulation if running.
        Returns True if session existed and was deleted.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            # Stop if running
            await self._stop_session(session)

            del self._sessions[session_id]
            return True

    async def list_sessions(self) -> list[UUID]:
        """List all active session IDs."""
        async with self._lock:
            return list(self._sessions.keys())

    async def start_simulation(
        self,
        session_id: UUID,
        on_tick: Optional[Callable[[TickResult], None]] = None,
        on_complete: Optional[Callable[[SimulationState], None]] = None,
    ) -> bool:
        """
        Start the simulation loop for a session.

        Args:
            session_id: Session to start
            on_tick: Callback for each tick result
            on_complete: Callback when simulation completes

        Returns:
            True if started, False if session not found or already running
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            if session._task is not None and not session._task.done():
                return False  # Already running

            session.on_tick = on_tick
            session.on_complete = on_complete
            session._stop_requested = False
            session._paused.set()

            # Start the tick loop
            session._task = asyncio.create_task(self._run_tick_loop(session))
            return True

    async def pause_simulation(self, session_id: UUID) -> bool:
        """Pause a running simulation."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            session._paused.clear()
            return True

    async def resume_simulation(self, session_id: UUID) -> bool:
        """Resume a paused simulation."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            session._paused.set()
            return True

    async def stop_simulation(self, session_id: UUID) -> bool:
        """Stop a running simulation."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            await self._stop_session(session)
            return True

    async def reset_simulation(self, session_id: UUID) -> bool:
        """Reset a simulation to initial state."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            # Stop if running
            await self._stop_session(session)

            # Reset the simulator
            session.simulator.reset()
            return True

    async def update_player(
        self, session_id: UUID, player_data: dict, role: str
    ) -> bool:
        """
        Update a player's attributes.

        Only works when simulation is not running.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            # Don't update while running
            if session._task is not None and not session._task.done():
                return False

            player = SandboxPlayer.from_dict(player_data)

            if role == "blocker":
                session.simulator.blocker = player
            elif role == "rusher":
                session.simulator.rusher = player
            else:
                return False

            # Reset simulation with new player
            session.simulator.reset()
            return True

    async def set_tick_rate(self, session_id: UUID, tick_rate_ms: int) -> bool:
        """Update the tick rate (only when not running)."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False

            if session._task is not None and not session._task.done():
                return False

            session.simulator.tick_rate_ms = tick_rate_ms
            return True

    async def _stop_session(self, session: SandboxSession) -> None:
        """Stop a session's tick loop (must hold lock)."""
        if session._task is not None and not session._task.done():
            session._stop_requested = True
            session._paused.set()  # Unblock if paused
            try:
                await asyncio.wait_for(session._task, timeout=1.0)
            except asyncio.TimeoutError:
                session._task.cancel()
                try:
                    await session._task
                except asyncio.CancelledError:
                    pass
            session._task = None

    async def _run_tick_loop(self, session: SandboxSession) -> None:
        """Run the simulation tick loop."""
        simulator = session.simulator
        tick_rate_s = simulator.tick_rate_ms / 1000.0

        while not simulator.is_complete() and not session._stop_requested:
            # Wait if paused
            await session._paused.wait()

            if session._stop_requested:
                break

            # Run one tick
            result = simulator.tick()

            # Notify callback
            if session.on_tick:
                try:
                    session.on_tick(result)
                except Exception:
                    pass  # Don't let callback errors stop simulation

            # Check if complete after this tick
            if simulator.is_complete():
                break

            # Wait for next tick
            await asyncio.sleep(tick_rate_s)

        # Simulation complete
        if session.on_complete:
            try:
                session.on_complete(simulator.get_state())
            except Exception:
                pass


# Global session manager instance
_session_manager: Optional[SandboxSessionManager] = None


def get_session_manager() -> SandboxSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SandboxSessionManager()
    return _session_manager

"""Centralized trace system for AI decision debugging.

Captures AI decision traces for all players, organized by tick.
Enables SimAnalyzer to show timeline of player decisions and rewind to any tick.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class TraceCategory(Enum):
    """Categories of trace messages."""
    PERCEPTION = "perception"  # What the player sees/detects
    DECISION = "decision"      # What they decide to do
    ACTION = "action"          # What they actually do


@dataclass
class TraceEntry:
    """A single trace entry from a player."""
    tick: int
    time: float
    player_id: str
    player_name: str
    category: TraceCategory
    message: str


class TraceSystem:
    """Centralized trace system for all player AI decisions.

    Usage:
        trace = get_trace_system()
        trace.enable(True)

        # At start of each tick in orchestrator:
        trace.set_tick(tick_num, sim_time)

        # In each brain:
        trace.trace(player.id, player.name, TraceCategory.DECISION, "Breaking on ball")

        # To get entries for WebSocket:
        entries = trace.get_entries(since_tick=last_sent_tick)
    """

    def __init__(self):
        self._enabled = False
        self._entries: List[TraceEntry] = []
        self._current_tick = 0
        self._current_time = 0.0
        self._last_retrieved_tick = -1

    def enable(self, enabled: bool = True) -> None:
        """Enable or disable trace collection."""
        self._enabled = enabled
        if enabled:
            self._entries.clear()
            self._last_retrieved_tick = -1

    def is_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._enabled

    def set_tick(self, tick: int, time: float) -> None:
        """Set the current tick/time for subsequent trace calls."""
        self._current_tick = tick
        self._current_time = time

    def trace(self, player_id: str, player_name: str, category: TraceCategory, message: str) -> None:
        """Add a trace entry for a player.

        Args:
            player_id: Unique player identifier
            player_name: Human-readable player name
            category: Type of trace (perception, decision, action)
            message: Concise description of what happened
        """
        if not self._enabled:
            return
        self._entries.append(TraceEntry(
            tick=self._current_tick,
            time=self._current_time,
            player_id=player_id,
            player_name=player_name,
            category=category,
            message=message
        ))

    def get_entries(self, since_tick: Optional[int] = None) -> List[TraceEntry]:
        """Get trace entries, optionally filtered by tick.

        Args:
            since_tick: If provided, only return entries from this tick onwards

        Returns:
            List of trace entries
        """
        if since_tick is None:
            return list(self._entries)
        return [e for e in self._entries if e.tick >= since_tick]

    def get_entries_for_tick(self, tick: int) -> List[TraceEntry]:
        """Get all trace entries for a specific tick."""
        return [e for e in self._entries if e.tick == tick]

    def get_entries_for_player(self, player_id: str, since_tick: Optional[int] = None) -> List[TraceEntry]:
        """Get trace entries for a specific player."""
        entries = self._entries if since_tick is None else [e for e in self._entries if e.tick >= since_tick]
        return [e for e in entries if e.player_id == player_id]

    def get_new_entries(self) -> List[TraceEntry]:
        """Get entries since last retrieval and update marker.

        Useful for incremental WebSocket sends.
        """
        new_entries = [e for e in self._entries if e.tick > self._last_retrieved_tick]
        if self._entries:
            self._last_retrieved_tick = self._current_tick
        return new_entries

    def clear(self) -> None:
        """Clear all trace entries."""
        self._entries.clear()
        self._last_retrieved_tick = -1

    def to_dict_list(self, entries: Optional[List[TraceEntry]] = None) -> List[Dict]:
        """Convert entries to list of dicts for JSON serialization."""
        if entries is None:
            entries = self._entries
        return [
            {
                "tick": e.tick,
                "time": e.time,
                "player_id": e.player_id,
                "player_name": e.player_name,
                "category": e.category.value,
                "message": e.message
            }
            for e in entries
        ]


# Global singleton instance
_trace_system = TraceSystem()


def get_trace_system() -> TraceSystem:
    """Get the global trace system instance."""
    return _trace_system

"""Play logging for behavioral analysis.

Produces detailed tick-by-tick logs that can be analyzed to assess
whether simulation behavior looks realistic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json

from ..core.vec2 import Vec2
from ..core.entities import Player, Ball
from ..core.clock import Clock
from ..core.events import Event


@dataclass
class PlayerSnapshot:
    """Snapshot of a player at a single tick."""
    id: str
    name: str
    position: str
    pos: tuple[float, float]
    velocity: tuple[float, float]
    speed: float
    has_ball: bool
    is_engaged: bool
    is_down: bool
    assignment: str
    decision: str
    reasoning: str

    @classmethod
    def from_player(cls, player: Player) -> PlayerSnapshot:
        return cls(
            id=player.id,
            name=player.name,
            position=player.position.value,
            pos=(round(player.pos.x, 2), round(player.pos.y, 2)),
            velocity=(round(player.velocity.x, 2), round(player.velocity.y, 2)),
            speed=round(player.velocity.length(), 2),
            has_ball=player.has_ball,
            is_engaged=player.is_engaged,
            is_down=player.is_down,
            assignment=player.assignment,
            decision=player._last_decision,
            reasoning=player._last_decision_reason,
        )

    def format(self) -> str:
        """Single-line format for logs."""
        status = []
        if self.has_ball:
            status.append("BALL")
        if self.is_engaged:
            status.append("ENG")
        if self.is_down:
            status.append("DOWN")
        status_str = f" [{','.join(status)}]" if status else ""

        return (
            f"  {self.name:12} ({self.position:3}) "
            f"pos=({self.pos[0]:6.1f}, {self.pos[1]:6.1f}) "
            f"vel=({self.velocity[0]:5.1f}, {self.velocity[1]:5.1f}) "
            f"spd={self.speed:4.1f}{status_str}"
        )

    def format_detailed(self) -> str:
        """Multi-line detailed format."""
        lines = [self.format()]
        if self.assignment:
            lines.append(f"    Assignment: {self.assignment}")
        if self.decision:
            lines.append(f"    Decision: {self.decision}")
        if self.reasoning:
            lines.append(f"    Reasoning: {self.reasoning}")
        return "\n".join(lines)


@dataclass
class BallSnapshot:
    """Snapshot of ball state."""
    state: str
    pos: tuple[float, float]
    carrier_id: Optional[str]
    in_flight: bool
    flight_progress: float  # 0-1 if in flight
    height: float  # yards above ground

    @classmethod
    def from_ball(cls, ball: Ball, current_time: float) -> BallSnapshot:
        in_flight = ball.state.value == "in_flight"
        progress = 0.0
        height = 0.0

        if in_flight and ball.flight_duration > 0:
            elapsed = current_time - ball.flight_start_time
            progress = min(1.0, elapsed / ball.flight_duration)
            height = ball.height_at_progress(progress)

        return cls(
            state=ball.state.value,
            pos=(round(ball.pos.x, 2), round(ball.pos.y, 2)),
            carrier_id=ball.carrier_id,
            in_flight=in_flight,
            flight_progress=round(progress, 2),
            height=round(height, 2),
        )


@dataclass
class TickLog:
    """Complete log of a single simulation tick."""
    tick: int
    time: float
    phase: str
    offense: List[PlayerSnapshot]
    defense: List[PlayerSnapshot]
    ball: BallSnapshot
    events: List[str]
    notes: List[str] = field(default_factory=list)

    def format(self, verbose: bool = False) -> str:
        """Format tick for display."""
        lines = [
            f"{'='*60}",
            f"TICK {self.tick} | TIME {self.time:.2f}s | PHASE: {self.phase}",
            f"{'='*60}",
        ]

        # Events first (important)
        if self.events:
            lines.append("EVENTS:")
            for event in self.events:
                lines.append(f"  >> {event}")

        # Ball state
        ball_line = f"BALL: {self.ball.state} @ ({self.ball.pos[0]:.1f}, {self.ball.pos[1]:.1f})"
        if self.ball.carrier_id:
            ball_line += f" (held by {self.ball.carrier_id})"
        if self.ball.in_flight:
            ball_line += f" [FLIGHT {self.ball.flight_progress:.0%}, height={self.ball.height:.1f}yd]"
        lines.append(ball_line)

        # Offense
        lines.append("\nOFFENSE:")
        for p in self.offense:
            if verbose:
                lines.append(p.format_detailed())
            else:
                lines.append(p.format())

        # Defense
        lines.append("\nDEFENSE:")
        for p in self.defense:
            if verbose:
                lines.append(p.format_detailed())
            else:
                lines.append(p.format())

        # Notes
        if self.notes:
            lines.append("\nNOTES:")
            for note in self.notes:
                lines.append(f"  - {note}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "tick": self.tick,
            "time": self.time,
            "phase": self.phase,
            "ball": {
                "state": self.ball.state,
                "pos": self.ball.pos,
                "carrier_id": self.ball.carrier_id,
                "in_flight": self.ball.in_flight,
                "flight_progress": self.ball.flight_progress,
            },
            "offense": [
                {"id": p.id, "pos": p.pos, "vel": p.velocity, "speed": p.speed}
                for p in self.offense
            ],
            "defense": [
                {"id": p.id, "pos": p.pos, "vel": p.velocity, "speed": p.speed}
                for p in self.defense
            ],
            "events": self.events,
        }


class PlayLogger:
    """Logs an entire play for analysis."""

    def __init__(self):
        self.ticks: List[TickLog] = []
        self.events: List[Event] = []
        self._current_phase: str = "pre_snap"

    def set_phase(self, phase: str) -> None:
        """Update current play phase."""
        self._current_phase = phase

    def log_tick(
        self,
        clock: Clock,
        offense: List[Player],
        defense: List[Player],
        ball: Ball,
        events: List[Event] = None,
    ) -> TickLog:
        """Log a single tick."""
        tick_events = []
        if events:
            for e in events:
                tick_events.append(str(e))
                self.events.append(e)

        tick_log = TickLog(
            tick=clock.tick_count,
            time=clock.current_time,
            phase=self._current_phase,
            offense=[PlayerSnapshot.from_player(p) for p in offense],
            defense=[PlayerSnapshot.from_player(p) for p in defense],
            ball=BallSnapshot.from_ball(ball, clock.current_time),
            events=tick_events,
        )

        self.ticks.append(tick_log)
        return tick_log

    def add_note(self, note: str) -> None:
        """Add a note to the current tick."""
        if self.ticks:
            self.ticks[-1].notes.append(note)

    def format_play(self, verbose: bool = False, every_n_ticks: int = 1) -> str:
        """Format entire play log."""
        lines = [
            "#" * 60,
            "# PLAY LOG",
            f"# Total ticks: {len(self.ticks)}",
            f"# Duration: {self.ticks[-1].time:.2f}s" if self.ticks else "# No ticks",
            "#" * 60,
            "",
        ]

        for i, tick in enumerate(self.ticks):
            if i % every_n_ticks == 0 or tick.events:
                lines.append(tick.format(verbose))
                lines.append("")

        return "\n".join(lines)

    def format_summary(self) -> str:
        """Format a brief summary of the play."""
        if not self.ticks:
            return "No ticks logged"

        lines = [
            "PLAY SUMMARY",
            f"  Duration: {self.ticks[-1].time:.2f}s ({len(self.ticks)} ticks)",
            f"  Events: {len(self.events)}",
        ]

        # Key events
        key_event_types = {"throw", "catch", "incomplete", "interception", "tackle", "touchdown"}
        key_events = [e for e in self.events if e.type.value in key_event_types]
        if key_events:
            lines.append("  Key events:")
            for e in key_events:
                lines.append(f"    - {e}")

        return "\n".join(lines)

    def get_player_trace(self, player_id: str) -> List[tuple[float, float]]:
        """Get position trace for a player (for plotting)."""
        trace = []
        for tick in self.ticks:
            for p in tick.offense + tick.defense:
                if p.id == player_id:
                    trace.append(p.pos)
                    break
        return trace

    def get_separation_over_time(
        self,
        receiver_id: str,
        defender_id: str,
    ) -> List[tuple[float, float]]:
        """Get separation between two players over time (time, separation)."""
        separations = []
        for tick in self.ticks:
            r_pos = None
            d_pos = None
            for p in tick.offense:
                if p.id == receiver_id:
                    r_pos = Vec2(p.pos[0], p.pos[1])
            for p in tick.defense:
                if p.id == defender_id:
                    d_pos = Vec2(p.pos[0], p.pos[1])

            if r_pos and d_pos:
                sep = r_pos.distance_to(d_pos)
                separations.append((tick.time, sep))

        return separations

    def to_json(self) -> str:
        """Export as JSON for external analysis."""
        return json.dumps(
            {
                "ticks": [t.to_dict() for t in self.ticks],
                "summary": {
                    "duration": self.ticks[-1].time if self.ticks else 0,
                    "tick_count": len(self.ticks),
                    "event_count": len(self.events),
                },
            },
            indent=2,
        )

    def clear(self) -> None:
        """Clear the log for a new play."""
        self.ticks.clear()
        self.events.clear()
        self._current_phase = "pre_snap"

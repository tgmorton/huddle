"""Models for sandbox blocking simulation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class PlayerRole(str, Enum):
    """Player role in the sandbox."""

    BLOCKER = "blocker"
    RUSHER = "rusher"


class RusherTechnique(str, Enum):
    """Pass rush techniques available to the rusher."""

    BULL_RUSH = "bull_rush"  # Power-based, straight ahead
    SWIM = "swim"  # Finesse, arm-over move
    SPIN = "spin"  # Finesse, spin move
    RIP = "rip"  # Hybrid power/finesse, rip under arm


class BlockerTechnique(str, Enum):
    """Blocking techniques available to the blocker."""

    ANCHOR = "anchor"  # Set feet, absorb power (good vs bull rush)
    MIRROR = "mirror"  # Lateral movement, stay in front (good vs finesse)
    PUNCH = "punch"  # Aggressive hand fighting


class MatchupState(str, Enum):
    """Current state of the blocking matchup."""

    INITIAL = "initial"  # Pre-snap
    ENGAGED = "engaged"  # Normal blocking engagement
    RUSHER_WINNING = "rusher_winning"  # Rusher gaining ground
    BLOCKER_WINNING = "blocker_winning"  # Blocker pushing back
    SHED = "shed"  # Rusher beat the block
    PANCAKE = "pancake"  # Blocker pancaked the rusher


class MatchupOutcome(str, Enum):
    """Final outcome of the matchup."""

    IN_PROGRESS = "in_progress"
    RUSHER_WIN = "rusher_win"  # Rusher reached QB zone
    BLOCKER_WIN = "blocker_win"  # Blocker sustained block
    PANCAKE = "pancake"  # Blocker dominated


@dataclass
class SandboxPlayer:
    """
    Simplified player model for sandbox simulation.

    Contains only the attributes relevant to blocking/rushing.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = "Player"
    role: PlayerRole = PlayerRole.BLOCKER

    # Physical attributes (0-99)
    strength: int = 75
    speed: int = 75
    agility: int = 75

    # Blocker-specific attributes
    pass_block: int = 75
    awareness: int = 75

    # Rusher-specific attributes
    block_shedding: int = 75
    power_moves: int = 75
    finesse_moves: int = 75

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": self.name,
            "role": self.role.value,
            "strength": self.strength,
            "speed": self.speed,
            "agility": self.agility,
            "pass_block": self.pass_block,
            "awareness": self.awareness,
            "block_shedding": self.block_shedding,
            "power_moves": self.power_moves,
            "finesse_moves": self.finesse_moves,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SandboxPlayer":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data.get("name", "Player"),
            role=PlayerRole(data.get("role", "blocker")),
            strength=data.get("strength", 75),
            speed=data.get("speed", 75),
            agility=data.get("agility", 75),
            pass_block=data.get("pass_block", 75),
            awareness=data.get("awareness", 75),
            block_shedding=data.get("block_shedding", 75),
            power_moves=data.get("power_moves", 75),
            finesse_moves=data.get("finesse_moves", 75),
        )

    @classmethod
    def default_blocker(cls, name: str = "OL") -> "SandboxPlayer":
        """Create a default offensive lineman."""
        return cls(
            name=name,
            role=PlayerRole.BLOCKER,
            strength=80,
            speed=60,
            agility=65,
            pass_block=78,
            awareness=75,
            block_shedding=50,
            power_moves=50,
            finesse_moves=50,
        )

    @classmethod
    def default_rusher(cls, name: str = "DT") -> "SandboxPlayer":
        """Create a default defensive tackle."""
        return cls(
            name=name,
            role=PlayerRole.RUSHER,
            strength=82,
            speed=68,
            agility=70,
            pass_block=50,
            awareness=72,
            block_shedding=80,
            power_moves=78,
            finesse_moves=72,
        )


@dataclass
class Position2D:
    """2D position on the field."""

    x: float = 0.0  # Yards from line of scrimmage (positive = toward QB)
    y: float = 0.0  # Lateral position (0 = center)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"x": self.x, "y": self.y}


@dataclass
class TickResult:
    """Result of a single simulation tick."""

    tick_number: int
    timestamp_ms: int  # Game time in milliseconds

    # Positions
    blocker_position: Position2D
    rusher_position: Position2D

    # Techniques used this tick
    rusher_technique: RusherTechnique
    blocker_technique: BlockerTechnique

    # Contest results
    rusher_score: float
    blocker_score: float
    margin: float  # rusher_score - blocker_score

    # Movement this tick
    movement: float  # Yards moved (positive = toward QB)

    # State
    matchup_state: MatchupState
    outcome: MatchupOutcome

    # Cumulative stats
    rusher_depth: float  # Total yards gained toward QB
    engagement_duration_ms: int

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "tick_number": self.tick_number,
            "timestamp_ms": self.timestamp_ms,
            "blocker_position": self.blocker_position.to_dict(),
            "rusher_position": self.rusher_position.to_dict(),
            "rusher_technique": self.rusher_technique.value,
            "blocker_technique": self.blocker_technique.value,
            "rusher_score": round(self.rusher_score, 2),
            "blocker_score": round(self.blocker_score, 2),
            "margin": round(self.margin, 2),
            "movement": round(self.movement, 3),
            "matchup_state": self.matchup_state.value,
            "outcome": self.outcome.value,
            "rusher_depth": round(self.rusher_depth, 2),
            "engagement_duration_ms": self.engagement_duration_ms,
        }


@dataclass
class SimulationState:
    """Full state of a sandbox simulation session."""

    session_id: UUID = field(default_factory=uuid4)
    blocker: SandboxPlayer = field(default_factory=SandboxPlayer.default_blocker)
    rusher: SandboxPlayer = field(default_factory=SandboxPlayer.default_rusher)

    # Simulation parameters
    tick_rate_ms: int = 100  # Milliseconds per tick
    max_ticks: int = 50  # ~5 seconds
    qb_zone_depth: float = 7.0  # Yards from LOS where rusher wins

    # Current state
    current_tick: int = 0
    is_running: bool = False
    is_complete: bool = False

    # Positions
    blocker_position: Position2D = field(default_factory=Position2D)
    rusher_position: Position2D = field(default_factory=Position2D)

    # Results
    outcome: MatchupOutcome = MatchupOutcome.IN_PROGRESS
    tick_history: list[TickResult] = field(default_factory=list)

    # Stats
    rusher_wins_contest: int = 0
    blocker_wins_contest: int = 0
    neutral_contests: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "session_id": str(self.session_id),
            "blocker": self.blocker.to_dict(),
            "rusher": self.rusher.to_dict(),
            "tick_rate_ms": self.tick_rate_ms,
            "max_ticks": self.max_ticks,
            "qb_zone_depth": self.qb_zone_depth,
            "current_tick": self.current_tick,
            "is_running": self.is_running,
            "is_complete": self.is_complete,
            "blocker_position": self.blocker_position.to_dict(),
            "rusher_position": self.rusher_position.to_dict(),
            "outcome": self.outcome.value,
            "stats": {
                "rusher_wins_contest": self.rusher_wins_contest,
                "blocker_wins_contest": self.blocker_wins_contest,
                "neutral_contests": self.neutral_contests,
            },
        }

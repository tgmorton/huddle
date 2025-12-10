"""Role-specific player attribute dataclasses for simulations.

These lightweight attribute structures are optimized for simulation use,
containing only the attributes relevant to each player role. They can be
constructed directly or created from the core PlayerAttributes system.

Each class provides a from_core() method to map from the comprehensive
core attribute system when full player data is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from huddle.core.attributes import PlayerAttributes as CorePlayerAttributes


# =============================================================================
# Base Simulation Attributes
# =============================================================================

@dataclass
class BaseSimAttributes:
    """Base attributes shared by all player roles.

    These physical/mental attributes apply to nearly all positions.
    """
    speed: int = 75
    acceleration: int = 75
    agility: int = 75
    strength: int = 75
    awareness: int = 75

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "speed": self.speed,
            "acceleration": self.acceleration,
            "agility": self.agility,
            "strength": self.strength,
            "awareness": self.awareness,
        }


# =============================================================================
# Offensive Line Attributes
# =============================================================================

@dataclass
class OLineAttributes(BaseSimAttributes):
    """Attributes for offensive linemen in blocking simulations.

    Used by: LT, LG, C, RG, RT
    """
    pass_block: int = 75
    run_block: int = 75
    impact_blocking: int = 75  # Pancake ability

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = super().to_dict()
        d.update({
            "pass_block": self.pass_block,
            "run_block": self.run_block,
            "impact_blocking": self.impact_blocking,
        })
        return d

    @classmethod
    def from_core(cls, core: "CorePlayerAttributes") -> OLineAttributes:
        """Create from core player attributes."""
        return cls(
            speed=core.get("speed", 75),
            acceleration=core.get("acceleration", 75),
            agility=core.get("agility", 75),
            strength=core.get("strength", 75),
            awareness=core.get("awareness", 75),
            pass_block=core.get("pass_block", 75),
            run_block=core.get("run_block", 75),
            impact_blocking=core.get("impact_blocking", 75),
        )

    @classmethod
    def elite(cls) -> OLineAttributes:
        """Create elite O-line attributes for testing."""
        return cls(
            speed=70, acceleration=75, agility=70, strength=92, awareness=88,
            pass_block=95, run_block=90, impact_blocking=85,
        )

    @classmethod
    def average(cls) -> OLineAttributes:
        """Create average O-line attributes for testing."""
        return cls(
            speed=65, acceleration=68, agility=65, strength=78, awareness=72,
            pass_block=75, run_block=75, impact_blocking=70,
        )

    @classmethod
    def poor(cls) -> OLineAttributes:
        """Create below-average O-line attributes for testing."""
        return cls(
            speed=60, acceleration=62, agility=58, strength=70, awareness=65,
            pass_block=62, run_block=65, impact_blocking=55,
        )


# =============================================================================
# Defensive Line Attributes
# =============================================================================

@dataclass
class DLineAttributes(BaseSimAttributes):
    """Attributes for defensive linemen in pass rush simulations.

    Used by: DE, DT, NT
    """
    block_shedding: int = 75
    power_moves: int = 75
    finesse_moves: int = 75
    pursuit: int = 75
    tackle: int = 75

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = super().to_dict()
        d.update({
            "block_shedding": self.block_shedding,
            "power_moves": self.power_moves,
            "finesse_moves": self.finesse_moves,
            "pursuit": self.pursuit,
            "tackle": self.tackle,
        })
        return d

    @classmethod
    def from_core(cls, core: "CorePlayerAttributes") -> DLineAttributes:
        """Create from core player attributes."""
        return cls(
            speed=core.get("speed", 75),
            acceleration=core.get("acceleration", 75),
            agility=core.get("agility", 75),
            strength=core.get("strength", 75),
            awareness=core.get("awareness", 75),
            block_shedding=core.get("block_shedding", 75),
            power_moves=core.get("power_moves", 75),
            finesse_moves=core.get("finesse_moves", 75),
            pursuit=core.get("pursuit", 75),
            tackle=core.get("tackle", 75),
        )

    @classmethod
    def elite_edge(cls) -> DLineAttributes:
        """Create elite edge rusher attributes for testing."""
        return cls(
            speed=88, acceleration=90, agility=85, strength=82, awareness=80,
            block_shedding=92, power_moves=88, finesse_moves=95, pursuit=90, tackle=82,
        )

    @classmethod
    def elite_interior(cls) -> DLineAttributes:
        """Create elite interior D-line attributes for testing."""
        return cls(
            speed=72, acceleration=78, agility=70, strength=95, awareness=78,
            block_shedding=88, power_moves=95, finesse_moves=75, pursuit=75, tackle=85,
        )

    @classmethod
    def average(cls) -> DLineAttributes:
        """Create average D-line attributes for testing."""
        return cls(
            speed=75, acceleration=78, agility=72, strength=80, awareness=72,
            block_shedding=75, power_moves=75, finesse_moves=75, pursuit=75, tackle=75,
        )


# =============================================================================
# Quarterback Attributes
# =============================================================================

@dataclass
class QBSimAttributes(BaseSimAttributes):
    """Attributes for quarterback in play simulations.

    Note: Base 'speed' is for pocket movement, not scrambling.
    """
    arm_strength: int = 85       # Ball velocity
    accuracy_short: int = 85     # Throws < 10 yards
    accuracy_mid: int = 85       # Throws 10-25 yards
    accuracy_deep: int = 80      # Throws > 25 yards
    throw_on_run: int = 75       # Accuracy penalty reduction when moving
    decision_making: int = 80    # Read speed and throw selection
    pocket_awareness: int = 75   # Pressure detection, escape timing

    @property
    def accuracy(self) -> int:
        """Overall accuracy (average of all ranges)."""
        return (self.accuracy_short + self.accuracy_mid + self.accuracy_deep) // 3

    def get_accuracy_for_distance(self, distance: float) -> int:
        """Get accuracy rating based on throw distance.

        Args:
            distance: Throw distance in yards

        Returns:
            Appropriate accuracy rating
        """
        if distance < 10:
            return self.accuracy_short
        elif distance < 25:
            return self.accuracy_mid
        else:
            return self.accuracy_deep

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = super().to_dict()
        d.update({
            "arm_strength": self.arm_strength,
            "accuracy_short": self.accuracy_short,
            "accuracy_mid": self.accuracy_mid,
            "accuracy_deep": self.accuracy_deep,
            "accuracy": self.accuracy,
            "throw_on_run": self.throw_on_run,
            "decision_making": self.decision_making,
            "pocket_awareness": self.pocket_awareness,
        })
        return d

    @classmethod
    def from_core(cls, core: "CorePlayerAttributes") -> QBSimAttributes:
        """Create from core player attributes."""
        return cls(
            speed=core.get("speed", 75),
            acceleration=core.get("acceleration", 75),
            agility=core.get("agility", 75),
            strength=core.get("strength", 70),
            awareness=core.get("awareness", 80),
            arm_strength=core.get("throw_power", 85),
            accuracy_short=core.get("throw_accuracy_short", 85),
            accuracy_mid=core.get("throw_accuracy_mid", 85),
            accuracy_deep=core.get("throw_accuracy_deep", 80),
            throw_on_run=core.get("throw_on_run", 75),
            decision_making=core.get("awareness", 80),  # Map awareness to decision
            pocket_awareness=core.get("awareness", 75),
        )

    @classmethod
    def elite(cls) -> QBSimAttributes:
        """Create elite QB attributes for testing."""
        return cls(
            speed=78, acceleration=80, agility=82, strength=72, awareness=95,
            arm_strength=95, accuracy_short=95, accuracy_mid=92, accuracy_deep=88,
            throw_on_run=85, decision_making=95, pocket_awareness=92,
        )

    @classmethod
    def average(cls) -> QBSimAttributes:
        """Create average QB attributes for testing."""
        return cls(
            speed=72, acceleration=74, agility=72, strength=68, awareness=78,
            arm_strength=82, accuracy_short=80, accuracy_mid=78, accuracy_deep=72,
            throw_on_run=70, decision_making=75, pocket_awareness=72,
        )

    @classmethod
    def rookie(cls) -> QBSimAttributes:
        """Create rookie QB attributes for testing."""
        return cls(
            speed=80, acceleration=82, agility=78, strength=65, awareness=68,
            arm_strength=88, accuracy_short=75, accuracy_mid=70, accuracy_deep=65,
            throw_on_run=72, decision_making=62, pocket_awareness=58,
        )


# =============================================================================
# Receiver Attributes
# =============================================================================

@dataclass
class ReceiverSimAttributes(BaseSimAttributes):
    """Attributes for receivers in route/play simulations.

    Used by: WR, TE, RB (as receivers)
    """
    route_running: int = 80
    release: int = 75            # Beating press coverage
    catching: int = 80           # Base catch ability
    catch_in_traffic: int = 75   # Contested catches
    spectacular_catch: int = 70  # Diving/one-handed catches
    jumping: int = 75            # High point ability

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = super().to_dict()
        d.update({
            "route_running": self.route_running,
            "release": self.release,
            "catching": self.catching,
            "catch_in_traffic": self.catch_in_traffic,
            "spectacular_catch": self.spectacular_catch,
            "jumping": self.jumping,
        })
        return d

    @classmethod
    def from_core(cls, core: "CorePlayerAttributes") -> ReceiverSimAttributes:
        """Create from core player attributes."""
        return cls(
            speed=core.get("speed", 85),
            acceleration=core.get("acceleration", 85),
            agility=core.get("agility", 85),
            strength=core.get("strength", 65),
            awareness=core.get("awareness", 75),
            route_running=core.get("route_running", 80),
            release=core.get("release", 75),
            catching=core.get("catching", 80),
            catch_in_traffic=core.get("catch_in_traffic", 75),
            spectacular_catch=core.get("spectacular_catch", 70),
            jumping=core.get("jumping", 75),
        )

    @classmethod
    def elite_outside(cls) -> ReceiverSimAttributes:
        """Create elite outside WR attributes for testing."""
        return cls(
            speed=95, acceleration=94, agility=92, strength=70, awareness=85,
            route_running=95, release=88, catching=92, catch_in_traffic=85,
            spectacular_catch=90, jumping=88,
        )

    @classmethod
    def elite_slot(cls) -> ReceiverSimAttributes:
        """Create elite slot WR attributes for testing."""
        return cls(
            speed=90, acceleration=92, agility=95, strength=65, awareness=88,
            route_running=95, release=82, catching=90, catch_in_traffic=88,
            spectacular_catch=82, jumping=78,
        )

    @classmethod
    def average(cls) -> ReceiverSimAttributes:
        """Create average WR attributes for testing."""
        return cls(
            speed=88, acceleration=86, agility=85, strength=62, awareness=75,
            route_running=80, release=75, catching=80, catch_in_traffic=75,
            spectacular_catch=70, jumping=75,
        )

    @classmethod
    def tight_end(cls) -> ReceiverSimAttributes:
        """Create tight end attributes for testing."""
        return cls(
            speed=82, acceleration=80, agility=78, strength=80, awareness=78,
            route_running=75, release=70, catching=82, catch_in_traffic=85,
            spectacular_catch=68, jumping=75,
        )


# =============================================================================
# Defensive Back Attributes
# =============================================================================

@dataclass
class DBSimAttributes(BaseSimAttributes):
    """Attributes for defensive backs in coverage simulations.

    Used by: CB, FS, SS
    """
    man_coverage: int = 80
    zone_coverage: int = 80
    play_recognition: int = 75   # Reading routes, anticipating
    press: int = 75              # Press coverage ability
    tackle: int = 70
    jumping: int = 78

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = super().to_dict()
        d.update({
            "man_coverage": self.man_coverage,
            "zone_coverage": self.zone_coverage,
            "play_recognition": self.play_recognition,
            "press": self.press,
            "tackle": self.tackle,
            "jumping": self.jumping,
        })
        return d

    @classmethod
    def from_core(cls, core: "CorePlayerAttributes") -> DBSimAttributes:
        """Create from core player attributes."""
        return cls(
            speed=core.get("speed", 88),
            acceleration=core.get("acceleration", 88),
            agility=core.get("agility", 88),
            strength=core.get("strength", 60),
            awareness=core.get("awareness", 80),
            man_coverage=core.get("man_coverage", 80),
            zone_coverage=core.get("zone_coverage", 80),
            play_recognition=core.get("play_recognition", 75),
            press=core.get("press", 75),
            tackle=core.get("tackle", 70),
            jumping=core.get("jumping", 78),
        )

    @classmethod
    def elite_man(cls) -> DBSimAttributes:
        """Create elite man coverage CB attributes for testing."""
        return cls(
            speed=94, acceleration=93, agility=92, strength=62, awareness=85,
            man_coverage=95, zone_coverage=82, play_recognition=85,
            press=92, tackle=72, jumping=88,
        )

    @classmethod
    def elite_zone(cls) -> DBSimAttributes:
        """Create elite zone coverage safety attributes for testing."""
        return cls(
            speed=90, acceleration=88, agility=85, strength=70, awareness=92,
            man_coverage=78, zone_coverage=95, play_recognition=92,
            press=70, tackle=82, jumping=85,
        )

    @classmethod
    def average(cls) -> DBSimAttributes:
        """Create average CB attributes for testing."""
        return cls(
            speed=88, acceleration=86, agility=85, strength=58, awareness=75,
            man_coverage=78, zone_coverage=78, play_recognition=72,
            press=75, tackle=68, jumping=78,
        )


# =============================================================================
# Linebacker Attributes (for blitz/coverage)
# =============================================================================

@dataclass
class LBSimAttributes(BaseSimAttributes):
    """Attributes for linebackers in pass rush or coverage.

    Used by: MLB, OLB, ILB when blitzing or dropping into coverage
    """
    block_shedding: int = 75     # Getting through OL
    pursuit: int = 80            # Chasing QB/ball
    tackle: int = 82
    man_coverage: int = 65       # Coverage ability (usually lower)
    zone_coverage: int = 72
    play_recognition: int = 78

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = super().to_dict()
        d.update({
            "block_shedding": self.block_shedding,
            "pursuit": self.pursuit,
            "tackle": self.tackle,
            "man_coverage": self.man_coverage,
            "zone_coverage": self.zone_coverage,
            "play_recognition": self.play_recognition,
        })
        return d

    @classmethod
    def from_core(cls, core: "CorePlayerAttributes") -> LBSimAttributes:
        """Create from core player attributes."""
        return cls(
            speed=core.get("speed", 82),
            acceleration=core.get("acceleration", 84),
            agility=core.get("agility", 80),
            strength=core.get("strength", 78),
            awareness=core.get("awareness", 80),
            block_shedding=core.get("block_shedding", 75),
            pursuit=core.get("pursuit", 80),
            tackle=core.get("tackle", 82),
            man_coverage=core.get("man_coverage", 65),
            zone_coverage=core.get("zone_coverage", 72),
            play_recognition=core.get("play_recognition", 78),
        )

    @classmethod
    def elite_pass_rusher(cls) -> LBSimAttributes:
        """Create elite pass rushing LB attributes for testing."""
        return cls(
            speed=88, acceleration=90, agility=85, strength=82, awareness=82,
            block_shedding=88, pursuit=92, tackle=85,
            man_coverage=62, zone_coverage=68, play_recognition=80,
        )

    @classmethod
    def elite_coverage(cls) -> LBSimAttributes:
        """Create elite coverage LB attributes for testing."""
        return cls(
            speed=85, acceleration=86, agility=88, strength=75, awareness=88,
            block_shedding=72, pursuit=85, tackle=82,
            man_coverage=80, zone_coverage=85, play_recognition=88,
        )

    @classmethod
    def average(cls) -> LBSimAttributes:
        """Create average LB attributes for testing."""
        return cls(
            speed=82, acceleration=83, agility=80, strength=78, awareness=78,
            block_shedding=75, pursuit=78, tackle=80,
            man_coverage=65, zone_coverage=72, play_recognition=75,
        )

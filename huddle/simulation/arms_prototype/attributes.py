"""
Player attributes for the arms prototype.

Two core attributes drive physical capability:
- Strength (STR): Force generation and resistance
- Agility (AGI): Speed of movement and recovery

These are the "engine" that powers the physical systems.
Everything else (technique, leverage) is situational multipliers.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class PhysicalAttributes:
    """
    Core physical attributes that affect gameplay.

    Values are 0-100 ratings that map to physical capability.
    50 = average NFL player at that position
    """

    # STRENGTH - force generation and resistance
    # Affects: push power, anchor strength, arm power, force debt capacity
    strength: float = 50.0

    # AGILITY - quickness and recovery
    # Affects: step frequency, hand speed, move execution speed
    agility: float = 50.0

    def __post_init__(self):
        # Clamp to valid range
        self.strength = max(0.0, min(100.0, self.strength))
        self.agility = max(0.0, min(100.0, self.agility))

    # =========================================================================
    # Strength-derived factors
    # =========================================================================

    @property
    def str_force_mult(self) -> float:
        """
        Multiplier for force generation (pushing, punching).
        Maps 0-100 to 0.5-1.5 range.

        50 STR = 1.0x force
        0 STR = 0.5x force (half strength)
        100 STR = 1.5x force (elite power)
        """
        return 0.5 + (self.strength / 100.0)

    @property
    def str_resistance_mult(self) -> float:
        """
        Multiplier for resisting force (anchoring, absorbing pushes).
        Higher = harder to move. Maps 0-100 to 0.6-1.4 range.

        Resistance is slightly less variable than force generation
        because mass also plays a role.
        """
        return 0.6 + 0.8 * (self.strength / 100.0)

    @property
    def str_debt_capacity(self) -> float:
        """
        Max force debt before losing balance.
        Stronger players can absorb more force before getting driven.
        Maps 0-100 to 0.3-0.7 range.
        """
        return 0.3 + 0.4 * (self.strength / 100.0)

    # =========================================================================
    # Agility-derived factors
    # =========================================================================

    @property
    def agi_step_frequency(self) -> float:
        """
        Steps per second per foot.
        Quicker players pump feet faster, recovering from debt faster.
        Maps 0-100 to 2.0-4.0 steps/sec.

        50 AGI = 3.0 steps/sec (baseline)
        0 AGI = 2.0 steps/sec (slow feet)
        100 AGI = 4.0 steps/sec (elite quickness)
        """
        return 2.0 + 2.0 * (self.agility / 100.0)

    @property
    def agi_hand_speed(self) -> float:
        """
        Speed multiplier for arm movements (punches, swims, rips).
        Maps 0-100 to 0.7-1.3 range.

        This affects both execution and reaction.
        """
        return 0.7 + 0.6 * (self.agility / 100.0)

    @property
    def agi_step_distance(self) -> float:
        """
        Max effective step distance while maintaining balance.
        More agile players can take bigger steps.
        Maps 0-100 to 0.25-0.45 yards per step.
        """
        return 0.25 + 0.2 * (self.agility / 100.0)

    # =========================================================================
    # Combined factors
    # =========================================================================

    @property
    def power_rating(self) -> float:
        """
        Overall power for move execution.
        Combines strength (force) and agility (speed) for moves like
        bull rush (STR heavy) or swim (AGI heavy).

        This is a balanced 60/40 STR/AGI blend.
        """
        return 0.6 * self.str_force_mult + 0.4 * self.agi_hand_speed

    @property
    def anchor_rating(self) -> float:
        """
        Ability to hold ground.
        Heavily STR-dependent but AGI helps with foot repositioning.

        80/20 STR/AGI blend.
        """
        return 0.8 * self.str_resistance_mult + 0.2 * (self.agi_step_frequency / 3.0)

    # =========================================================================
    # Factory methods for typical players
    # =========================================================================

    @classmethod
    def elite_pass_rusher(cls) -> PhysicalAttributes:
        """Von Miller, Myles Garrett type - explosive and quick."""
        return cls(strength=75, agility=85)

    @classmethod
    def power_rusher(cls) -> PhysicalAttributes:
        """Aaron Donald type - absurdly strong and quick."""
        return cls(strength=95, agility=80)

    @classmethod
    def average_dt(cls) -> PhysicalAttributes:
        """Typical interior DL."""
        return cls(strength=65, agility=45)

    @classmethod
    def elite_tackle(cls) -> PhysicalAttributes:
        """Trent Williams type - athletic and strong."""
        return cls(strength=80, agility=70)

    @classmethod
    def mauler_guard(cls) -> PhysicalAttributes:
        """Quenton Nelson type - extremely powerful."""
        return cls(strength=90, agility=50)

    @classmethod
    def average_ol(cls) -> PhysicalAttributes:
        """Typical starting OL."""
        return cls(strength=60, agility=45)

    @classmethod
    def backup_ol(cls) -> PhysicalAttributes:
        """Roster depth OL."""
        return cls(strength=50, agility=40)

    # =========================================================================
    # Edge Players - Speed and bend matter most
    # =========================================================================

    @classmethod
    def elite_edge(cls) -> PhysicalAttributes:
        """Myles Garrett, Micah Parsons type - explosive, bendy, powerful."""
        return cls(strength=80, agility=90)

    @classmethod
    def speed_rusher(cls) -> PhysicalAttributes:
        """Pure speed edge - wins with get-off and bend."""
        return cls(strength=60, agility=95)

    @classmethod
    def power_edge(cls) -> PhysicalAttributes:
        """Power edge rusher - can bull but also speed rush."""
        return cls(strength=85, agility=70)

    @classmethod
    def average_edge(cls) -> PhysicalAttributes:
        """Average starting edge rusher."""
        return cls(strength=65, agility=70)

    @classmethod
    def elite_tackle(cls) -> PhysicalAttributes:
        """Trent Williams type - athletic and strong."""
        return cls(strength=80, agility=75)

    @classmethod
    def average_tackle(cls) -> PhysicalAttributes:
        """Average starting OT."""
        return cls(strength=65, agility=55)

    @classmethod
    def athletic_tackle(cls) -> PhysicalAttributes:
        """Quick-footed OT - can mirror speed rushers."""
        return cls(strength=60, agility=70)

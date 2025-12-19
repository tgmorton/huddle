"""Body models for players.

Physical dimensions that affect collision, tackling, and space control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.entities import Position


@dataclass
class BodyModel:
    """Physical body representation for collision and space.

    All dimensions in yards.

    Attributes:
        height: Standing height (for high points, hurdles)
        weight: Weight in pounds (for contact outcomes)
        shoulder_width: Side-to-side width
        arm_length: Reach for tackles, catches
    """
    height: float           # yards
    weight: float           # pounds
    shoulder_width: float   # yards
    arm_length: float       # yards (~0.9 = 33 inches)

    @property
    def collision_radius(self) -> float:
        """Simplified collision radius."""
        return self.shoulder_width / 2

    @property
    def tackle_reach(self) -> float:
        """How far can this player reach to tackle."""
        return self.collision_radius + self.arm_length

    @property
    def catch_radius(self) -> float:
        """How far can reach to catch a ball."""
        return self.arm_length * 1.1  # Can extend a bit more for catches

    @classmethod
    def from_measurements(
        cls,
        height_inches: int,
        weight_lbs: int,
        arm_length_inches: int = 33,
    ) -> BodyModel:
        """Create from real measurements."""
        # Height in yards
        height = height_inches / 36

        # Shoulder width estimated from weight and build
        # Heavier players are wider
        base_width = 0.5 + (weight_lbs - 180) / 350
        shoulder_width = max(0.45, min(1.0, base_width))  # Cap at reasonable range

        return cls(
            height=height,
            weight=weight_lbs,
            shoulder_width=shoulder_width,
            arm_length=arm_length_inches / 36,
        )

    @classmethod
    def for_position(cls, position: Position) -> BodyModel:
        """Create typical body model for a position."""
        # Default measurements by position
        defaults = {
            # Offense
            Position.QB: (76, 225, 33),     # 6'4", 225
            Position.RB: (70, 215, 32),     # 5'10", 215
            Position.FB: (72, 245, 32),     # 6'0", 245
            Position.WR: (73, 200, 33),     # 6'1", 200
            Position.TE: (77, 255, 34),     # 6'5", 255
            Position.LT: (78, 315, 34),     # 6'6", 315
            Position.LG: (76, 315, 33),     # 6'4", 315
            Position.C: (75, 305, 33),      # 6'3", 305
            Position.RG: (76, 315, 33),     # 6'4", 315
            Position.RT: (78, 315, 34),     # 6'6", 315

            # Defense
            Position.DT: (75, 310, 33),     # 6'3", 310
            Position.DE: (76, 275, 34),     # 6'4", 275
            Position.NT: (74, 330, 33),     # 6'2", 330
            Position.MLB: (74, 245, 33),    # 6'2", 245
            Position.OLB: (74, 240, 33),    # 6'2", 240
            Position.ILB: (73, 245, 32),    # 6'1", 245
            Position.CB: (71, 195, 32),     # 5'11", 195
            Position.FS: (72, 200, 32),     # 6'0", 200
            Position.SS: (72, 210, 32),     # 6'0", 210
        }

        height, weight, arm = defaults.get(position, (73, 220, 32))
        return cls.from_measurements(height, weight, arm)

    def describe(self) -> str:
        """Human-readable description."""
        height_ft = int(self.height * 36 / 12)
        height_in = int(self.height * 36) % 12
        return f"{height_ft}'{height_in}\", {self.weight:.0f} lbs"

    def __repr__(self) -> str:
        return f"BodyModel({self.describe()}, width={self.shoulder_width:.2f}yd)"


# =============================================================================
# Position-specific body templates
# =============================================================================

# Pre-built bodies for quick access
BODY_TEMPLATES = {
    "elite_wr": BodyModel.from_measurements(75, 210, 33),    # 6'3", 210 - big WR
    "slot_wr": BodyModel.from_measurements(70, 185, 31),     # 5'10", 185 - quick slot
    "speed_wr": BodyModel.from_measurements(72, 190, 32),    # 6'0", 190 - speedster
    "power_rb": BodyModel.from_measurements(70, 230, 31),    # 5'10", 230 - power back
    "scat_rb": BodyModel.from_measurements(68, 195, 30),     # 5'8", 195 - scat back
    "receiving_te": BodyModel.from_measurements(78, 250, 34),# 6'6", 250 - move TE
    "blocking_te": BodyModel.from_measurements(77, 270, 33), # 6'5", 270 - inline TE
    "mobile_qb": BodyModel.from_measurements(74, 215, 32),   # 6'2", 215 - mobile QB
    "pocket_qb": BodyModel.from_measurements(77, 235, 33),   # 6'5", 235 - pocket QB
    "edge_rusher": BodyModel.from_measurements(76, 265, 34), # 6'4", 265 - speed rusher
    "3_tech": BodyModel.from_measurements(75, 295, 33),      # 6'3", 295 - penetrating DT
    "nose_tackle": BodyModel.from_measurements(74, 340, 33), # 6'2", 340 - space eater
    "mike_lb": BodyModel.from_measurements(74, 250, 33),     # 6'2", 250 - thumper
    "coverage_lb": BodyModel.from_measurements(73, 235, 33), # 6'1", 235 - coverage LB
    "press_cb": BodyModel.from_measurements(73, 200, 33),    # 6'1", 200 - physical CB
    "slot_cb": BodyModel.from_measurements(70, 185, 31),     # 5'10", 185 - quick CB
    "rangy_safety": BodyModel.from_measurements(73, 205, 33),# 6'1", 205 - center fielder
    "box_safety": BodyModel.from_measurements(72, 215, 32),  # 6'0", 215 - run support
}


def get_body_template(template_name: str) -> BodyModel:
    """Get a predefined body template."""
    return BODY_TEMPLATES.get(template_name, BodyModel.for_position(Position.WR))

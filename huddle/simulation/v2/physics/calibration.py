"""NGS Movement Physics Calibration.

Position-specific movement calibration data derived from Next Gen Stats
tracking data. These values constrain player movement to be physically
realistic - players can't make sharp turns at high speed.

Key insight: Turn radius increases with speed. A player sprinting at 8+ yds/sec
has a minimum turn radius of ~20 yards. This affects routes, pursuit, and
all player movement in the simulation.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class NGSCalibration:
    """Position-specific movement calibration from NGS data.

    Curvature is the inverse of turn radius (1/radius in yards).
    Higher curvature = tighter turns allowed.

    Attributes:
        position: Position code (WR, RB, CB, etc.)
        max_curvature_slow: Max curvature at 0-4 yds/sec
        max_curvature_medium: Max curvature at 4-6 yds/sec
        max_curvature_fast: Max curvature at 6-8 yds/sec
        max_curvature_sprint: Max curvature at 8+ yds/sec
        small_cut_retention: Speed retention for 30-60 degree cuts
        medium_cut_retention: Speed retention for 60-90 degree cuts
        hard_cut_retention: Speed retention for 90+ degree cuts
        recovery_time_sec: Time to regain full speed after a cut
        max_turn_rate_deg_sec: Maximum turn rate in degrees/second
    """

    position: str

    # Curvature limits by speed bucket (1/yards)
    max_curvature_slow: float  # 0-4 yps
    max_curvature_medium: float  # 4-6 yps
    max_curvature_fast: float  # 6-8 yps
    max_curvature_sprint: float  # 8+ yps

    # Cut mechanics (speed retention factors)
    small_cut_retention: float  # 30-60 degree cuts
    medium_cut_retention: float  # 60-90 degree cuts
    hard_cut_retention: float  # 90+ degree cuts
    recovery_time_sec: float  # Time to regain speed after cut

    # Turn rate limit
    max_turn_rate_deg_sec: float  # Maximum degrees/second

    def get_max_curvature(self, speed: float) -> float:
        """Get maximum curvature (1/turn_radius) at given speed.

        Args:
            speed: Current speed in yards/second

        Returns:
            Maximum curvature in 1/yards. Higher = can turn sharper.
        """
        if speed < 4.0:
            return self.max_curvature_slow
        elif speed < 6.0:
            return self.max_curvature_medium
        elif speed < 8.0:
            return self.max_curvature_fast
        else:
            return self.max_curvature_sprint

    def get_min_turn_radius(self, speed: float) -> float:
        """Get minimum turn radius at given speed.

        Args:
            speed: Current speed in yards/second

        Returns:
            Minimum turn radius in yards. Lower = can turn sharper.
        """
        curvature = self.get_max_curvature(speed)
        return 1.0 / max(curvature, 0.01)

    def get_cut_retention(self, cut_angle_rad: float) -> float:
        """Get speed retention factor for a cut of given angle.

        Args:
            cut_angle_rad: Cut angle in radians

        Returns:
            Speed retention factor (0-1+). Values > 1 mean slight acceleration
            through the cut (common for sharp stops then acceleration).
        """
        cut_angle_deg = math.degrees(abs(cut_angle_rad))

        if cut_angle_deg < 30:
            # Very small cuts - no real speed loss
            return 1.0
        elif cut_angle_deg < 60:
            return self.small_cut_retention
        elif cut_angle_deg < 90:
            return self.medium_cut_retention
        else:
            return self.hard_cut_retention

    def get_max_turn_angle(self, speed: float, dt: float) -> float:
        """Get maximum direction change angle for a tick.

        This is the key constraint: at high speed, you can only turn so much
        per tick. This creates realistic curved paths instead of sharp angles.

        Args:
            speed: Current speed in yards/second
            dt: Time step in seconds

        Returns:
            Maximum turn angle in radians for this tick
        """
        # Two constraints:
        # 1. Curvature limit: max_turn = curvature * speed * dt
        # 2. Turn rate limit: max_turn = turn_rate_rad * dt
        curvature_limit = self.get_max_curvature(speed) * speed * dt
        turn_rate_limit = math.radians(self.max_turn_rate_deg_sec) * dt

        return min(curvature_limit, turn_rate_limit)


# =============================================================================
# Default Calibration Data (from NGS analysis)
# =============================================================================

# These values are derived from research/exports/reference/simulation/ngs_physics_calibration.json
# Using max_curvature_by_speed for turn limits and juke data for cut retention

_DEFAULT_CALIBRATION: Dict[str, NGSCalibration] = {
    "WR": NGSCalibration(
        position="WR",
        max_curvature_slow=0.299,
        max_curvature_medium=0.185,
        max_curvature_fast=0.103,
        max_curvature_sprint=0.053,
        small_cut_retention=0.91,
        medium_cut_retention=0.84,
        hard_cut_retention=0.95,
        recovery_time_sec=0.60,
        max_turn_rate_deg_sec=73.2,
    ),
    "RB": NGSCalibration(
        position="RB",
        max_curvature_slow=0.314,
        max_curvature_medium=0.184,
        max_curvature_fast=0.091,
        max_curvature_sprint=0.052,
        small_cut_retention=1.02,
        medium_cut_retention=1.10,
        hard_cut_retention=1.01,
        recovery_time_sec=0.57,
        max_turn_rate_deg_sec=67.4,
    ),
    "TE": NGSCalibration(
        position="TE",
        max_curvature_slow=0.294,
        max_curvature_medium=0.176,
        max_curvature_fast=0.095,
        max_curvature_sprint=0.046,
        small_cut_retention=0.92,
        medium_cut_retention=0.67,
        hard_cut_retention=1.02,
        recovery_time_sec=0.56,
        max_turn_rate_deg_sec=64.6,
    ),
    "QB": NGSCalibration(
        position="QB",
        max_curvature_slow=0.234,
        max_curvature_medium=0.174,
        max_curvature_fast=0.088,
        max_curvature_sprint=0.047,
        small_cut_retention=0.95,
        medium_cut_retention=0.44,
        hard_cut_retention=1.00,
        recovery_time_sec=0.49,
        max_turn_rate_deg_sec=62.6,
    ),
    "OL": NGSCalibration(
        position="OL",
        max_curvature_slow=0.203,
        max_curvature_medium=0.100,
        max_curvature_fast=0.053,
        max_curvature_sprint=0.029,
        small_cut_retention=0.87,
        medium_cut_retention=0.41,
        hard_cut_retention=1.07,
        recovery_time_sec=0.45,
        max_turn_rate_deg_sec=38.2,
    ),
    "DL": NGSCalibration(
        position="DL",
        max_curvature_slow=0.264,
        max_curvature_medium=0.165,
        max_curvature_fast=0.070,
        max_curvature_sprint=0.033,
        small_cut_retention=0.97,
        medium_cut_retention=0.89,
        hard_cut_retention=1.04,
        recovery_time_sec=0.49,
        max_turn_rate_deg_sec=50.3,
    ),
    "LB": NGSCalibration(
        position="LB",
        max_curvature_slow=0.319,
        max_curvature_medium=0.189,
        max_curvature_fast=0.087,
        max_curvature_sprint=0.040,
        small_cut_retention=0.99,
        medium_cut_retention=0.90,
        hard_cut_retention=1.08,
        recovery_time_sec=0.54,
        max_turn_rate_deg_sec=64.1,
    ),
    "CB": NGSCalibration(
        position="CB",
        max_curvature_slow=0.346,
        max_curvature_medium=0.191,
        max_curvature_fast=0.090,
        max_curvature_sprint=0.043,
        small_cut_retention=0.96,
        medium_cut_retention=0.54,
        hard_cut_retention=1.01,
        recovery_time_sec=0.60,
        max_turn_rate_deg_sec=64.8,
    ),
    "S": NGSCalibration(
        position="S",
        max_curvature_slow=0.373,
        max_curvature_medium=0.205,
        max_curvature_fast=0.095,
        max_curvature_sprint=0.047,
        small_cut_retention=1.02,
        medium_cut_retention=0.88,
        hard_cut_retention=1.08,
        recovery_time_sec=0.55,
        max_turn_rate_deg_sec=71.9,
    ),
}

# Position aliases (map specific positions to calibration categories)
_POSITION_ALIASES = {
    # Offensive
    "WR": "WR",
    "WR1": "WR",
    "WR2": "WR",
    "WR3": "WR",
    "RB": "RB",
    "HB": "RB",
    "FB": "RB",
    "TE": "TE",
    "QB": "QB",
    "LT": "OL",
    "LG": "OL",
    "C": "OL",
    "RG": "OL",
    "RT": "OL",
    "OL": "OL",
    # Defensive
    "DE": "DL",
    "DT": "DL",
    "NT": "DL",
    "DL": "DL",
    "MLB": "LB",
    "ILB": "LB",
    "OLB": "LB",
    "EDGE": "LB",
    "LB": "LB",
    "CB": "CB",
    "CB1": "CB",
    "CB2": "CB",
    "FS": "S",
    "SS": "S",
    "S": "S",
}


def get_calibration(position: str) -> NGSCalibration:
    """Get NGS calibration for a position.

    Args:
        position: Position string (e.g., "WR", "MLB", "LT")

    Returns:
        NGSCalibration for that position category
    """
    # Normalize position
    pos_upper = position.upper()

    # Map to category
    category = _POSITION_ALIASES.get(pos_upper, "LB")  # Default to LB as middle-ground

    return _DEFAULT_CALIBRATION.get(category, _DEFAULT_CALIBRATION["LB"])


def get_calibration_for_position_enum(position) -> NGSCalibration:
    """Get NGS calibration from a Position enum.

    Args:
        position: Position enum value

    Returns:
        NGSCalibration for that position
    """
    pos_str = position.value if hasattr(position, "value") else str(position)
    return get_calibration(pos_str)


# =============================================================================
# Recovery State
# =============================================================================


@dataclass
class RecoveryState:
    """Tracks post-cut recovery for a player.

    After making a cut, players need time to recover before regaining
    full acceleration capability. This creates realistic momentum effects.
    """

    recovery_ticks_remaining: int = 0
    recovery_factor: float = 1.0  # 0-1, how much acceleration is limited

    def apply_cut(self, calibration: NGSCalibration, tick_rate: float = 20.0) -> None:
        """Start recovery period after a cut.

        Args:
            calibration: Position-specific calibration
            tick_rate: Simulation ticks per second (default 20)
        """
        self.recovery_ticks_remaining = int(calibration.recovery_time_sec * tick_rate)
        self.recovery_factor = 0.5  # 50% acceleration during recovery

    def tick(self) -> None:
        """Process one tick of recovery."""
        if self.recovery_ticks_remaining > 0:
            self.recovery_ticks_remaining -= 1

            # Gradually restore acceleration capability
            if self.recovery_ticks_remaining == 0:
                self.recovery_factor = 1.0
            else:
                # Linear recovery toward 1.0
                self.recovery_factor = min(1.0, self.recovery_factor + 0.05)

    def is_recovering(self) -> bool:
        """Check if still in recovery period."""
        return self.recovery_ticks_remaining > 0

    def get_effective_acceleration(self, base_acceleration: float) -> float:
        """Get acceleration limited by recovery state.

        Args:
            base_acceleration: Normal acceleration rate

        Returns:
            Effective acceleration (reduced during recovery)
        """
        return base_acceleration * self.recovery_factor


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    "NGSCalibration",
    "RecoveryState",
    "get_calibration",
    "get_calibration_for_position_enum",
]

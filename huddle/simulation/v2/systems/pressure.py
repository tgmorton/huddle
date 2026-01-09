"""Pressure Accumulation System.

Tracks pocket pressure over time with accumulation and decay.
Pressure builds from nearby unblocked rushers and decays when
threats are neutralized.

Key concepts:
- Instantaneous pressure: Current threat level this tick
- Accumulated pressure: Total pressure built up over time
- Pressure affects QB decision-making and throw quality
- High accumulated pressure enables sack attempts

NFL calibration targets:
- Clean pocket rate: ~60% of dropbacks
- Pressure rate: ~35% of dropbacks
- Sack rate: ~6.5% of dropbacks
- Average time to pressure: ~2.5 seconds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.vec2 import Vec2
    from ..core.entities import Player


class PressureLevel(str, Enum):
    """Discrete pressure levels for decision-making."""
    CLEAN = "clean"           # No pressure, clean pocket
    LIGHT = "light"           # Minor pressure, can still operate
    MODERATE = "moderate"     # Platform starting to break down
    HEAVY = "heavy"           # Must throw now or escape
    CRITICAL = "critical"     # Imminent sack, survival mode


@dataclass
class ThreatInfo:
    """Information about a single pressure threat."""
    defender_id: str
    distance: float
    eta: float  # Estimated time to arrival
    closing_speed: float
    threat_score: float
    is_blocked: bool
    is_blind_side: bool  # Coming from QB's blind side


@dataclass
class PressureState:
    """Current state of pocket pressure.

    Tracks both instantaneous and accumulated pressure to model
    the gradual degradation of the pocket over time.
    """
    # Instantaneous pressure this tick
    instant_level: PressureLevel = PressureLevel.CLEAN
    instant_score: float = 0.0

    # Accumulated pressure over time
    accumulated: float = 0.0
    peak_accumulated: float = 0.0  # Highest accumulated this play

    # Threat tracking
    threats: List[ThreatInfo] = field(default_factory=list)
    closest_threat_distance: float = 15.0
    closest_threat_eta: float = 10.0

    # Timing
    time_under_pressure: float = 0.0  # Total time with pressure > LIGHT
    time_clean: float = 0.0  # Total time with CLEAN pocket

    # Pocket geometry
    pocket_width: float = 6.0  # Width of clean pocket
    pocket_depth: float = 3.0  # Depth behind QB still clean
    pocket_collapsed: bool = False


# =============================================================================
# Pressure Accumulation Constants
# =============================================================================

# How quickly pressure accumulates (per second of exposure)
PRESSURE_ACCUMULATION_RATE = 2.0

# How quickly pressure decays when threats are neutralized (per second)
PRESSURE_DECAY_RATE = 1.5

# Threshold for accumulated pressure to enable sack attempts
SACK_THRESHOLD = 5.0

# Pressure level thresholds (for instant pressure)
PRESSURE_THRESHOLDS = {
    PressureLevel.CLEAN: 0.5,
    PressureLevel.LIGHT: 1.0,
    PressureLevel.MODERATE: 2.0,
    PressureLevel.HEAVY: 3.5,
    # CRITICAL: anything above HEAVY
}

# Accumulated pressure thresholds for level
ACCUMULATED_THRESHOLDS = {
    PressureLevel.CLEAN: 1.0,
    PressureLevel.LIGHT: 2.5,
    PressureLevel.MODERATE: 4.0,
    PressureLevel.HEAVY: 6.0,
    # CRITICAL: anything above HEAVY
}


class PressureSystem:
    """Manages pressure accumulation and decay throughout a play.

    Usage:
        pressure = PressureSystem()
        pressure.reset()  # At start of play

        # Each tick:
        state = pressure.update(qb_pos, defenders, blockers, dt)

        # Query state:
        if state.accumulated > SACK_THRESHOLD:
            # Can attempt sack
    """

    def __init__(self):
        self._state = PressureState()
        self._play_start_time: float = 0.0

    @property
    def state(self) -> PressureState:
        """Current pressure state."""
        return self._state

    def reset(self, play_start_time: float = 0.0) -> None:
        """Reset for a new play."""
        self._state = PressureState()
        self._play_start_time = play_start_time

    def update(
        self,
        qb_pos: 'Vec2',
        defenders: List[Any],  # List of PlayerView or Player
        blockers: List[Any],   # List of PlayerView or Player
        dt: float,
        current_time: float = 0.0,
    ) -> PressureState:
        """Update pressure state for this tick.

        Args:
            qb_pos: QB's current position
            defenders: All defensive players
            blockers: Offensive linemen (for protection checking)
            dt: Time delta this tick
            current_time: Current simulation time

        Returns:
            Updated PressureState
        """
        # Calculate instantaneous pressure from all threats
        threats, instant_score = self._calculate_instant_pressure(
            qb_pos, defenders, blockers
        )

        self._state.threats = threats
        self._state.instant_score = instant_score
        self._state.instant_level = self._score_to_level(instant_score)

        # Update closest threat tracking
        if threats:
            closest = min(threats, key=lambda t: t.distance)
            self._state.closest_threat_distance = closest.distance
            self._state.closest_threat_eta = closest.eta
        else:
            self._state.closest_threat_distance = 15.0
            self._state.closest_threat_eta = 10.0

        # Accumulate or decay pressure
        if instant_score > PRESSURE_THRESHOLDS[PressureLevel.CLEAN]:
            # Accumulate pressure based on instant score
            accumulation = instant_score * PRESSURE_ACCUMULATION_RATE * dt
            self._state.accumulated += accumulation
            self._state.time_under_pressure += dt
        else:
            # Decay pressure when clean
            decay = PRESSURE_DECAY_RATE * dt
            self._state.accumulated = max(0, self._state.accumulated - decay)
            self._state.time_clean += dt

        # Track peak
        self._state.peak_accumulated = max(
            self._state.peak_accumulated,
            self._state.accumulated
        )

        # Update pocket geometry
        self._update_pocket_geometry(qb_pos, threats)

        return self._state

    def _calculate_instant_pressure(
        self,
        qb_pos: 'Vec2',
        defenders: List[Any],
        blockers: List[Any],
    ) -> tuple[List[ThreatInfo], float]:
        """Calculate instantaneous pressure from all defenders.

        Returns:
            (list of ThreatInfo, total threat score)
        """
        threats = []
        total_score = 0.0

        for defender in defenders:
            # Get position (handle both Player and PlayerView)
            def_pos = getattr(defender, 'pos', None)
            if def_pos is None:
                continue

            distance = def_pos.distance_to(qb_pos)

            # Only consider players within threat range
            if distance > 15.0:
                continue

            # Check engagement status - engaged defenders contribute less pressure
            # but still contribute if they're winning their blocking battle
            is_engaged = getattr(defender, 'is_engaged', False)
            engagement_modifier = 1.0
            if is_engaged:
                # Check if defender is winning the block (still contributing pressure)
                # DL_WINNING = 0.4 pressure, DL_DOMINANT = 0.7 pressure
                block_outcome = getattr(defender, '_block_outcome', None)
                if block_outcome == 'dl_winning':
                    engagement_modifier = 0.4  # Partial pressure
                elif block_outcome == 'dl_dominant':
                    engagement_modifier = 0.7  # Strong pressure despite engagement
                else:
                    continue  # OL winning or neutral, skip this defender

            # Calculate closing speed and ETA
            velocity = getattr(defender, 'velocity', None)
            if velocity:
                # Project velocity toward QB
                to_qb = qb_pos - def_pos
                if to_qb.length() > 0.1:
                    closing_speed = velocity.dot(to_qb.normalized())
                    closing_speed = max(closing_speed, 1.0)  # Minimum closing speed
                else:
                    closing_speed = 5.0
            else:
                speed = getattr(defender, 'speed', 5.0)
                closing_speed = speed if speed > 0 else 5.0

            eta = distance / closing_speed if closing_speed > 0 else 10.0

            # Base threat score inversely proportional to ETA
            threat_score = 1.0 / (eta + 0.1)

            # Apply engagement modifier (engaged but winning DL still create pressure)
            threat_score *= engagement_modifier

            # Blind side bonus (left side for right-handed QB)
            is_blind_side = def_pos.x < qb_pos.x
            if is_blind_side:
                threat_score *= 1.5

            # Check if blocker is protecting this lane (for unengaged threats)
            is_blocked = self._is_threat_blocked(def_pos, qb_pos, blockers) if not is_engaged else False
            if is_blocked:
                threat_score *= 0.3

            total_score += threat_score

            # Only track as immediate threat if close
            if eta < 2.0 or distance < 5.0:
                threats.append(ThreatInfo(
                    defender_id=getattr(defender, 'id', 'unknown'),
                    distance=distance,
                    eta=eta,
                    closing_speed=closing_speed,
                    threat_score=threat_score,
                    is_blocked=is_blocked,
                    is_blind_side=is_blind_side,
                ))

        return threats, total_score

    def _is_threat_blocked(
        self,
        threat_pos: 'Vec2',
        qb_pos: 'Vec2',
        blockers: List[Any],
    ) -> bool:
        """Check if a blocker is protecting the QB from this threat."""
        from ..core.entities import Position

        threat_to_qb = qb_pos - threat_pos
        if threat_to_qb.length() < 0.1:
            return False

        distance = threat_pos.distance_to(qb_pos)

        for blocker in blockers:
            # Only OL can provide protection
            pos = getattr(blocker, 'position', None)
            if pos not in (Position.LT, Position.LG, Position.C, Position.RG, Position.RT):
                continue

            blocker_pos = getattr(blocker, 'pos', None)
            if blocker_pos is None:
                continue

            # Blocker must be closer to threat than QB is
            blocker_to_threat = blocker_pos.distance_to(threat_pos)
            if blocker_to_threat >= distance:
                continue

            # Check if blocker is in the lane (perpendicular distance)
            threat_to_blocker = blocker_pos - threat_pos
            t = threat_to_blocker.dot(threat_to_qb) / threat_to_qb.dot(threat_to_qb)

            if 0 < t < 1:  # Blocker is between threat and QB
                closest_point = threat_pos + threat_to_qb * t
                lane_distance = blocker_pos.distance_to(closest_point)
                if lane_distance < 2.0:  # Within 2 yards of direct path
                    return True

        return False

    def _score_to_level(self, score: float) -> PressureLevel:
        """Convert pressure score to discrete level."""
        if score < PRESSURE_THRESHOLDS[PressureLevel.CLEAN]:
            return PressureLevel.CLEAN
        elif score < PRESSURE_THRESHOLDS[PressureLevel.LIGHT]:
            return PressureLevel.LIGHT
        elif score < PRESSURE_THRESHOLDS[PressureLevel.MODERATE]:
            return PressureLevel.MODERATE
        elif score < PRESSURE_THRESHOLDS[PressureLevel.HEAVY]:
            return PressureLevel.HEAVY
        else:
            return PressureLevel.CRITICAL

    def _update_pocket_geometry(
        self,
        qb_pos: 'Vec2',
        threats: List[ThreatInfo],
    ) -> None:
        """Update pocket geometry based on threat positions."""
        if not threats:
            self._state.pocket_width = 6.0
            self._state.pocket_depth = 3.0
            self._state.pocket_collapsed = False
            return

        # Find closest threats on each side
        left_closest = 15.0
        right_closest = 15.0
        front_closest = 15.0

        for threat in threats:
            # Would need threat position to calculate this properly
            # For now, use distance as approximation
            if threat.is_blind_side:
                left_closest = min(left_closest, threat.distance)
            else:
                right_closest = min(right_closest, threat.distance)
            front_closest = min(front_closest, threat.distance)

        # Update pocket dimensions
        self._state.pocket_width = min(left_closest, right_closest) * 2
        self._state.pocket_depth = front_closest
        self._state.pocket_collapsed = (
            self._state.pocket_width < 3.0 or
            self._state.pocket_depth < 2.0
        )

    def get_effective_level(self) -> PressureLevel:
        """Get effective pressure level considering both instant and accumulated.

        Uses the higher of:
        - Instant pressure level
        - Level derived from accumulated pressure
        """
        instant = self._state.instant_level

        # Convert accumulated to level
        acc = self._state.accumulated
        if acc < ACCUMULATED_THRESHOLDS[PressureLevel.CLEAN]:
            acc_level = PressureLevel.CLEAN
        elif acc < ACCUMULATED_THRESHOLDS[PressureLevel.LIGHT]:
            acc_level = PressureLevel.LIGHT
        elif acc < ACCUMULATED_THRESHOLDS[PressureLevel.MODERATE]:
            acc_level = PressureLevel.MODERATE
        elif acc < ACCUMULATED_THRESHOLDS[PressureLevel.HEAVY]:
            acc_level = PressureLevel.HEAVY
        else:
            acc_level = PressureLevel.CRITICAL

        # Return the more severe level
        levels = [PressureLevel.CLEAN, PressureLevel.LIGHT, PressureLevel.MODERATE,
                  PressureLevel.HEAVY, PressureLevel.CRITICAL]
        return levels[max(levels.index(instant), levels.index(acc_level))]

    def can_attempt_sack(self) -> bool:
        """Check if accumulated pressure is high enough for sack attempt."""
        return self._state.accumulated >= SACK_THRESHOLD

    def get_sack_probability_modifier(self) -> float:
        """Get modifier for sack probability based on accumulated pressure.

        Returns:
            Multiplier for base sack probability (1.0 = normal, higher = more likely)
        """
        excess = self._state.accumulated - SACK_THRESHOLD
        if excess <= 0:
            return 0.0

        # Each point over threshold adds 20% to sack probability
        return 1.0 + (excess * 0.2)

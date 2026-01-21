"""Special Teams Resolution - Statistical outcomes for kicks.

Handles non-simulation special teams plays:
- Kickoffs: Touchback vs return, starting field position
- Punts: Net yardage, fair catch, return
- Field Goals: Make/miss probability by distance
- PAT: Extra point success rate
- Two-Point: Delegates to V2 simulation

Statistical models based on NFL averages with player rating modifiers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from huddle.core.models.player import Player as CorePlayer


# =============================================================================
# Constants - NFL Statistical Baselines
# =============================================================================

# Kickoff outcomes (from research/exports/special_teams_model.json)
KICKOFF_TOUCHBACK_RATE = 0.625  # NFL 2019-2024 average
KICKOFF_OUT_OF_BOUNDS_RATE = 0.02  # Penalty, ball at 40
KICKOFF_RETURN_AVG_YARDS = 21.4  # Average return when not touchback
KICKOFF_RETURN_STD = 12.5  # Standard deviation

# Punt outcomes (from research/exports/special_teams_model.json)
PUNT_INSIDE_20_RATE = 0.40  # Coffin corner success
PUNT_TOUCHBACK_RATE = 0.069  # Kicked into end zone
PUNT_FAIR_CATCH_RATE = 0.279  # Fair catch called
PUNT_GROSS_AVG = 46.3  # Gross punt yards
PUNT_AVG_NET = 42.5  # Average net yards
PUNT_NET_STD = 10.8  # Standard deviation

# Field goal rates by kick distance (from research/exports/special_teams_model.json)
# Note: kick_distance = 100 - yard_line + 17 (snap + hold)
FG_BY_DISTANCE = {
    19: 1.0, 20: 0.987, 21: 1.0, 22: 0.986, 23: 1.0, 24: 0.986, 25: 0.980,
    26: 0.981, 27: 0.965, 28: 0.982, 29: 0.938, 30: 0.983, 31: 0.971,
    32: 0.948, 33: 0.955, 34: 0.920, 35: 0.907, 36: 0.911, 37: 0.910,
    38: 0.921, 39: 0.888, 40: 0.884, 41: 0.792, 42: 0.817, 43: 0.805,
    44: 0.800, 45: 0.746, 46: 0.773, 47: 0.694, 48: 0.728, 49: 0.741,
    50: 0.739, 51: 0.715, 52: 0.741, 53: 0.667, 54: 0.745, 55: 0.617,
    56: 0.583, 57: 0.569, 58: 0.585, 59: 0.625, 60: 0.388, 61: 0.388,
    62: 0.388, 63: 0.200, 64: 0.200, 65: 0.200,
}

# Fallback bucket rates for distances outside specific data
FG_BUCKET_RATES = {
    (0, 20): 1.0,
    (20, 25): 0.992,
    (25, 30): 0.968,
    (30, 35): 0.955,
    (35, 40): 0.908,
    (40, 45): 0.819,
    (45, 50): 0.736,
    (50, 55): 0.720,
    (55, 60): 0.596,
    (60, 65): 0.388,
    (65, 100): 0.10,  # Hail mary kicks
}

# PAT rates (from research/exports/special_teams_model.json)
PAT_BASE_RATE = 0.944  # NFL 2019-2024 rate
PAT_DISTANCE = 33  # Yards from goal line

# Two-point conversion rate (from research/exports/two_point_model.json)
TWO_PT_BASE_RATE = 0.477
TWO_PT_PASS_RATE = 0.448  # Pass 2PT success rate
TWO_PT_RUN_RATE = 0.551  # Run 2PT success rate


# =============================================================================
# Result Types
# =============================================================================

class KickoffResult(Enum):
    """Outcome of a kickoff."""
    TOUCHBACK = "touchback"
    RETURN = "return"
    OUT_OF_BOUNDS = "out_of_bounds"
    ONSIDE_RECOVERED = "onside_recovered"
    ONSIDE_LOST = "onside_lost"


class PuntResult(Enum):
    """Outcome of a punt."""
    FAIR_CATCH = "fair_catch"
    RETURN = "return"
    TOUCHBACK = "touchback"
    DOWNED = "downed"
    MUFFED = "muffed"
    BLOCKED = "blocked"


class FieldGoalResult(Enum):
    """Outcome of a field goal attempt."""
    GOOD = "good"
    MISSED = "missed"
    BLOCKED = "blocked"


class PATResult(Enum):
    """Outcome of an extra point attempt."""
    GOOD = "good"
    MISSED = "missed"
    BLOCKED = "blocked"


@dataclass
class SpecialTeamsOutcome:
    """Result of a special teams play.

    Attributes:
        play_type: Type of play (kickoff, punt, fg, pat)
        result: Specific result enum
        new_los: New line of scrimmage (for kickoffs/punts)
        points: Points scored (for FG/PAT)
        return_yards: Yards gained on return
        kicking_team_ball: Whether kicking team has possession
    """
    play_type: str
    result: str
    new_los: float = 25.0  # Default touchback
    points: int = 0
    return_yards: float = 0.0
    kicking_team_ball: bool = False


# =============================================================================
# Special Teams Resolver
# =============================================================================

@dataclass
class SpecialTeamsResolver:
    """Resolves special teams plays using statistical models.

    All methods return SpecialTeamsOutcome with field position
    or points scored.
    """

    def resolve_kickoff(
        self,
        kicker: Optional["CorePlayer"] = None,
        returner: Optional["CorePlayer"] = None,
        onside: bool = False,
    ) -> SpecialTeamsOutcome:
        """Resolve a kickoff.

        Args:
            kicker: Kicking team's kicker (for power modifier)
            returner: Returning team's returner (for return modifier)
            onside: Whether this is an onside kick attempt

        Returns:
            Outcome with new line of scrimmage
        """
        if onside:
            return self._resolve_onside_kick(kicker)

        # Get kicker power modifier (affects touchback rate)
        kick_power = 75
        if kicker:
            kick_power = kicker.attributes.get("kick_power", 75)

        # Adjust touchback rate based on kicker power
        # 85+ power = more touchbacks, 65- power = fewer
        power_mod = (kick_power - 75) * 0.005
        touchback_rate = min(0.90, max(0.40, KICKOFF_TOUCHBACK_RATE + power_mod))

        # Roll for outcome
        roll = random.random()

        if roll < KICKOFF_OUT_OF_BOUNDS_RATE:
            # Penalty - ball at 40
            return SpecialTeamsOutcome(
                play_type="kickoff",
                result=KickoffResult.OUT_OF_BOUNDS.value,
                new_los=40.0,
            )

        if roll < KICKOFF_OUT_OF_BOUNDS_RATE + touchback_rate:
            # Touchback - ball at 25
            return SpecialTeamsOutcome(
                play_type="kickoff",
                result=KickoffResult.TOUCHBACK.value,
                new_los=25.0,
            )

        # Return
        return_yards = self._calculate_return_yards(returner)
        new_los = max(1.0, min(99.0, return_yards))

        return SpecialTeamsOutcome(
            play_type="kickoff",
            result=KickoffResult.RETURN.value,
            new_los=new_los,
            return_yards=return_yards,
        )

    def _resolve_onside_kick(
        self,
        kicker: Optional["CorePlayer"] = None,
    ) -> SpecialTeamsOutcome:
        """Resolve an onside kick attempt.

        NFL recovery rate is about 10-15%.
        """
        recovery_rate = 0.12

        if random.random() < recovery_rate:
            # Kicking team recovers!
            return SpecialTeamsOutcome(
                play_type="kickoff",
                result=KickoffResult.ONSIDE_RECOVERED.value,
                new_los=45.0,  # Approximate recovery point
                kicking_team_ball=True,
            )

        # Receiving team gets it
        return SpecialTeamsOutcome(
            play_type="kickoff",
            result=KickoffResult.ONSIDE_LOST.value,
            new_los=55.0,  # Great field position for receiving team
        )

    def _calculate_return_yards(
        self,
        returner: Optional["CorePlayer"] = None,
    ) -> float:
        """Calculate kickoff return yards."""
        base = KICKOFF_RETURN_AVG_YARDS
        std = KICKOFF_RETURN_STD

        # Modify based on returner speed/elusiveness
        if returner:
            speed = returner.attributes.get("speed", 75)
            elusiveness = returner.attributes.get("elusiveness", 75)
            avg_rating = (speed + elusiveness) / 2
            # +/- 5 yards based on rating
            base += (avg_rating - 75) * 0.2

        # Normal distribution with floor
        return_yards = max(5.0, random.gauss(base, std))

        # Chance of big return (5% chance of 40+ yards)
        if random.random() < 0.05:
            return_yards = random.uniform(40, 75)

        # Rare TD (1% chance)
        if random.random() < 0.01:
            return_yards = 100.0

        return return_yards

    def resolve_punt(
        self,
        punter: Optional["CorePlayer"] = None,
        returner: Optional["CorePlayer"] = None,
        los: float = 30.0,
    ) -> SpecialTeamsOutcome:
        """Resolve a punt.

        Args:
            punter: Punter for net yardage modifier
            returner: Returner for return modifier
            los: Current line of scrimmage

        Returns:
            Outcome with new line of scrimmage
        """
        # Handle FieldPosition objects
        if hasattr(los, 'yard_line'):
            los = float(los.yard_line)
        else:
            los = float(los)

        # Calculate punt distance
        punt_power = 75
        if punter:
            punt_power = punter.attributes.get("kick_power", 75)

        # Base net yards with modifier
        base_net = PUNT_AVG_NET + (punt_power - 75) * 0.2
        net_yards = max(20.0, random.gauss(base_net, PUNT_NET_STD))

        # Calculate landing spot
        landing_los = los + net_yards

        # Check for touchback (punted into end zone)
        if landing_los >= 100:
            return SpecialTeamsOutcome(
                play_type="punt",
                result=PuntResult.TOUCHBACK.value,
                new_los=20.0,  # Touchback at 20
            )

        # Roll for outcome type
        roll = random.random()

        if roll < 0.02:
            # Blocked punt! (2% chance)
            return SpecialTeamsOutcome(
                play_type="punt",
                result=PuntResult.BLOCKED.value,
                new_los=los,  # Ball at LOS
                kicking_team_ball=False,  # Turnover unless recovered
            )

        if roll < PUNT_FAIR_CATCH_RATE:
            # Fair catch
            new_los = 100 - landing_los  # Convert to receiving team's perspective
            return SpecialTeamsOutcome(
                play_type="punt",
                result=PuntResult.FAIR_CATCH.value,
                new_los=max(1.0, new_los),
            )

        if roll < PUNT_FAIR_CATCH_RATE + PUNT_INSIDE_20_RATE:
            # Downed inside 20
            new_los = min(19.0, 100 - landing_los)
            return SpecialTeamsOutcome(
                play_type="punt",
                result=PuntResult.DOWNED.value,
                new_los=max(1.0, new_los),
            )

        # Punt return
        return_yards = self._calculate_punt_return(returner)
        final_los = 100 - landing_los + return_yards

        return SpecialTeamsOutcome(
            play_type="punt",
            result=PuntResult.RETURN.value,
            new_los=max(1.0, min(99.0, final_los)),
            return_yards=return_yards,
        )

    def _calculate_punt_return(
        self,
        returner: Optional["CorePlayer"] = None,
    ) -> float:
        """Calculate punt return yards."""
        base = 8.0  # Average punt return
        std = 5.0

        if returner:
            speed = returner.attributes.get("speed", 75)
            elusiveness = returner.attributes.get("elusiveness", 75)
            avg_rating = (speed + elusiveness) / 2
            base += (avg_rating - 75) * 0.15

        return_yards = max(0.0, random.gauss(base, std))

        # Big return chance (3%)
        if random.random() < 0.03:
            return_yards = random.uniform(25, 60)

        return return_yards

    def resolve_field_goal(
        self,
        distance: float,
        kicker: Optional["CorePlayer"] = None,
    ) -> SpecialTeamsOutcome:
        """Resolve a field goal attempt.

        Args:
            distance: Distance in yards (kick distance, not yard line)
            kicker: Kicker for accuracy modifier

        Returns:
            Outcome with points if made

        Note:
            Kick distance = 100 - yard_line + 17 (snap + hold)
            E.g., from the 30 yard line: kick distance = 100 - 30 + 17 = 87... wait no.
            Actually: from own 30 yard line means 70 yards to goal, + 17 = 87 (impossible)
            From opponent 30: 30 + 17 = 47 yard FG attempt
        """
        kick_dist = int(distance)

        # Get base rate from precise lookup or fallback to bucket
        if kick_dist in FG_BY_DISTANCE:
            base_rate = FG_BY_DISTANCE[kick_dist]
        else:
            # Fallback to bucket rates
            base_rate = 0.10
            for (low, high), rate in FG_BUCKET_RATES.items():
                if low <= kick_dist < high:
                    base_rate = rate
                    break

        # Modify based on kicker accuracy
        kicker_acc = 75
        if kicker:
            kicker_acc = kicker.attributes.get("kick_accuracy", 75)

        # P(make) = base_rate * (1 + (kicker_rating - 75) / 100)
        # From research implementation hints
        accuracy_mod = (kicker_acc - 75) / 100
        make_rate = min(0.99, max(0.05, base_rate * (1 + accuracy_mod)))

        # Blocked chance (1.5%)
        if random.random() < 0.015:
            return SpecialTeamsOutcome(
                play_type="field_goal",
                result=FieldGoalResult.BLOCKED.value,
                points=0,
            )

        # Make or miss
        if random.random() < make_rate:
            return SpecialTeamsOutcome(
                play_type="field_goal",
                result=FieldGoalResult.GOOD.value,
                points=3,
            )

        return SpecialTeamsOutcome(
            play_type="field_goal",
            result=FieldGoalResult.MISSED.value,
            points=0,
        )

    def resolve_pat(
        self,
        kicker: Optional["CorePlayer"] = None,
    ) -> SpecialTeamsOutcome:
        """Resolve an extra point attempt.

        Args:
            kicker: Kicker for accuracy modifier

        Returns:
            Outcome with points if made
        """
        # Use field goal logic at PAT distance
        result = self.resolve_field_goal(PAT_DISTANCE, kicker)

        # Adjust result type
        if result.result == FieldGoalResult.GOOD.value:
            return SpecialTeamsOutcome(
                play_type="pat",
                result=PATResult.GOOD.value,
                points=1,
            )
        elif result.result == FieldGoalResult.BLOCKED.value:
            return SpecialTeamsOutcome(
                play_type="pat",
                result=PATResult.BLOCKED.value,
                points=0,
            )
        else:
            return SpecialTeamsOutcome(
                play_type="pat",
                result=PATResult.MISSED.value,
                points=0,
            )

    def resolve_two_point_statistical(self) -> SpecialTeamsOutcome:
        """Resolve a two-point conversion statistically.

        Note: For full simulation, use the V2 orchestrator with
        a goal-line play instead.

        Returns:
            Outcome with points if converted
        """
        if random.random() < TWO_PT_BASE_RATE:
            return SpecialTeamsOutcome(
                play_type="two_point",
                result="converted",
                points=2,
            )

        return SpecialTeamsOutcome(
            play_type="two_point",
            result="failed",
            points=0,
        )

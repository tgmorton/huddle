"""Decision Logic - AI play-calling decisions based on NFL research data.

Contains logic for:
- Fourth-down decisions (go for it, punt, or field goal)
- Two-point conversion decisions
- Clock/pace management

All probabilities derived from research/exports/ data (2019-2024 NFL seasons).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Literal


# =============================================================================
# Fourth Down Decision
# =============================================================================

# Fourth-down go rates by field position and distance (from research data)
# Key format: "field_position_distance" -> go_rate
FOURTH_DOWN_LOOKUP = {
    # Inside opponent 30 (field position 1-30 means 70-99 yard line for offense)
    "1-30_1": 0.789, "1-30_2": 0.464, "1-30_3": 0.249,
    "1-30_4-5": 0.163, "1-30_6-7": 0.096, "1-30_8-10": 0.086, "1-30_11+": 0.074,
    # Opponent 31-40
    "31-40_1": 0.884, "31-40_2": 0.660, "31-40_3": 0.535,
    "31-40_4-5": 0.389, "31-40_6-7": 0.236, "31-40_8-10": 0.152, "31-40_11+": 0.092,
    # Opponent 41-50
    "41-50_1": 0.893, "41-50_2": 0.655, "41-50_3": 0.451,
    "41-50_4-5": 0.307, "41-50_6-7": 0.137, "41-50_8-10": 0.146, "41-50_11+": 0.091,
    # Midfield (51-60 = own 40-49)
    "51-60_1": 0.636, "51-60_2": 0.260, "51-60_3": 0.123,
    "51-60_4-5": 0.120, "51-60_6-7": 0.095, "51-60_8-10": 0.083, "51-60_11+": 0.079,
    # Own 30-39 (61-70)
    "61-70_1": 0.405, "61-70_2": 0.148, "61-70_3": 0.085,
    "61-70_4-5": 0.081, "61-70_6-7": 0.045, "61-70_8-10": 0.089, "61-70_11+": 0.051,
    # Own 20-29 (71-80)
    "71-80_1": 0.260, "71-80_2": 0.119, "71-80_3": 0.048,
    "71-80_4-5": 0.064, "71-80_6-7": 0.047, "71-80_8-10": 0.050, "71-80_11+": 0.035,
    # Own 10-19 (81-90)
    "81-90_1": 0.143, "81-90_2": 0.063, "81-90_3": 0.067,
    "81-90_4-5": 0.062, "81-90_6-7": 0.019, "81-90_8-10": 0.036, "81-90_11+": 0.048,
    # Deep own territory (91-100)
    "91-100_3": 0.091, "91-100_4-5": 0.028, "91-100_6-7": 0.021,
    "91-100_8-10": 0.019, "91-100_11+": 0.028,
}

# Fourth-down conversion rates by distance
FOURTH_DOWN_CONVERSION = {
    1: 0.675,
    2: 0.583,
    3: 0.515,
    4: 0.488, 5: 0.488,
    6: 0.405, 7: 0.405,
    8: 0.323, 9: 0.323, 10: 0.323,
}
FOURTH_DOWN_CONVERSION_LONG = 0.188  # 11+ yards


class FourthDownDecision(Enum):
    """Fourth down decision options."""
    GO = "go"
    PUNT = "punt"
    FIELD_GOAL = "fg"


def _get_field_position_bucket(yard_line: int) -> str:
    """Convert yard line to field position bucket.

    Args:
        yard_line: Yards from own goal line (1-99)

    Returns:
        Bucket string like "1-30", "31-40", etc.
    """
    # Field position is inverted: yard_line 70 = inside opponent 30
    field_pos = 100 - yard_line

    if field_pos <= 30:
        return "1-30"
    elif field_pos <= 40:
        return "31-40"
    elif field_pos <= 50:
        return "41-50"
    elif field_pos <= 60:
        return "51-60"
    elif field_pos <= 70:
        return "61-70"
    elif field_pos <= 80:
        return "71-80"
    elif field_pos <= 90:
        return "81-90"
    else:
        return "91-100"


def _get_distance_bucket(yards_to_go: int) -> str:
    """Convert yards to go to distance bucket."""
    if yards_to_go <= 1:
        return "1"
    elif yards_to_go <= 2:
        return "2"
    elif yards_to_go <= 3:
        return "3"
    elif yards_to_go <= 5:
        return "4-5"
    elif yards_to_go <= 7:
        return "6-7"
    elif yards_to_go <= 10:
        return "8-10"
    else:
        return "11+"


def get_fourth_down_go_probability(
    yard_line: int,
    yards_to_go: int,
) -> float:
    """Get base probability of going for it on fourth down.

    Args:
        yard_line: Yards from own goal line (1-99)
        yards_to_go: Yards needed for first down

    Returns:
        Probability (0-1) of going for it based on NFL historical data
    """
    field_bucket = _get_field_position_bucket(yard_line)
    dist_bucket = _get_distance_bucket(yards_to_go)
    key = f"{field_bucket}_{dist_bucket}"

    return FOURTH_DOWN_LOOKUP.get(key, 0.05)


def fourth_down_decision(
    yard_line: int,
    yards_to_go: int,
    score_diff: int = 0,
    time_remaining: int = 3600,
    aggression: float = 0.0,
) -> FourthDownDecision:
    """Decide whether to go for it, punt, or kick a field goal on fourth down.

    Args:
        yard_line: Yards from own goal line (1-99)
        yards_to_go: Yards needed for first down
        score_diff: Our score - opponent score
        time_remaining: Seconds remaining in game
        aggression: Team aggression modifier (-1 to +1), 0 = average

    Returns:
        FourthDownDecision enum (GO, PUNT, or FIELD_GOAL)
    """
    # Field goal range check
    fg_distance = (100 - yard_line) + 17  # Add snap/hold distance
    in_fg_range = fg_distance <= 57  # Max reasonable FG

    # Get base go probability from lookup table
    base_go_prob = get_fourth_down_go_probability(yard_line, yards_to_go)

    # Adjust for team aggression
    go_prob = base_go_prob * (1 + aggression * 0.5)

    # Adjust for game situation
    if score_diff < 0 and time_remaining < 300:  # Trailing, under 5 min
        go_prob *= 1.5  # More aggressive
    if score_diff > 7 and time_remaining < 300:  # Leading, under 5 min
        go_prob *= 0.5  # More conservative

    # Desperate situations: always go
    if score_diff < 0 and time_remaining < 120:  # Trailing under 2 min
        go_prob = min(1.0, go_prob * 2.0)

    # Goal line (inside 3): almost always go
    if yard_line >= 97:
        return FourthDownDecision.GO

    # Decision
    if in_fg_range and yards_to_go >= 3 and fg_distance <= 50:
        # In comfortable FG range with medium/long distance
        if random.random() > go_prob * 0.7:  # FG bias in range
            return FourthDownDecision.FIELD_GOAL

    if random.random() < go_prob:
        return FourthDownDecision.GO

    # Default to punt if not going for it and not in FG range
    if in_fg_range and fg_distance <= 55:
        return FourthDownDecision.FIELD_GOAL

    return FourthDownDecision.PUNT


def get_fourth_down_conversion_rate(yards_to_go: int) -> float:
    """Get probability of converting fourth down.

    Args:
        yards_to_go: Yards needed for first down

    Returns:
        Probability of conversion (0-1)
    """
    if yards_to_go >= 11:
        return FOURTH_DOWN_CONVERSION_LONG
    return FOURTH_DOWN_CONVERSION.get(yards_to_go, 0.5)


# =============================================================================
# Two-Point Conversion Decision
# =============================================================================

# Score differentials where going for 2 is recommended
# Key insight: these are AFTER the TD, BEFORE the PAT/2PT
GO_FOR_TWO_DIFFS = {
    -8,   # 2PT ties game
    -5,   # 2PT gets within FG
    -2,   # 2PT ties
    -9,   # 2PT makes it one score (down 7)
    -15,  # 2PT makes it two scores (down 13)
    -11,  # 2PT down 9 (TD+2PT ties), PAT down 10 (need TD+FG)
    1,    # 2PT up 3 (need FG to tie)
}


def should_go_for_two(
    score_diff_after_td: int,
    quarter: int = 1,
    time_remaining: int = 3600,
) -> bool:
    """Decide whether to attempt a two-point conversion.

    Args:
        score_diff_after_td: Our score - opponent score AFTER TD (before PAT/2PT)
        quarter: Current quarter (1-4)
        time_remaining: Seconds remaining in game

    Returns:
        True if should go for 2, False for PAT
    """
    # Classic chart situations (always go for 2)
    if score_diff_after_td in GO_FOR_TWO_DIFFS:
        return True

    # Late game trailing - more aggressive
    if quarter == 4 and time_remaining < 300 and score_diff_after_td < 0:
        # Down multiple scores late, go for 2
        if score_diff_after_td <= -8:
            return True

    # Default: kick PAT
    return False


# =============================================================================
# Clock Management
# =============================================================================

class Pace(Enum):
    """Offensive pace options."""
    HURRY_UP = "hurry_up"
    NORMAL = "normal"
    MILK_CLOCK = "milk_clock"


def select_pace(
    score_diff: int,
    quarter: int,
    time_remaining: int,
) -> Pace:
    """Determine offensive pace based on game situation.

    Args:
        score_diff: Our score - opponent score
        quarter: Current quarter (1-4)
        time_remaining: Seconds remaining in quarter

    Returns:
        Pace enum
    """
    # Two-minute drill
    if quarter in [2, 4] and time_remaining <= 120 and score_diff <= 0:
        return Pace.HURRY_UP

    # Trailing late
    if quarter == 4 and time_remaining <= 300 and score_diff < -8:
        return Pace.HURRY_UP

    # Leading late - milk clock
    if quarter == 4 and time_remaining <= 300 and score_diff >= 8:
        return Pace.MILK_CLOCK

    # Leading big anytime
    if score_diff >= 17:
        return Pace.MILK_CLOCK

    return Pace.NORMAL


def time_off_clock(
    play_type: Literal["pass", "run"],
    complete: bool = True,
    first_down: bool = False,
    out_of_bounds: bool = False,
    pace: Pace = Pace.NORMAL,
) -> int:
    """Calculate seconds elapsed for a play.

    Args:
        play_type: 'pass' or 'run'
        complete: Whether pass was complete (ignored for runs)
        first_down: Whether play resulted in first down
        out_of_bounds: Whether ball carrier went out of bounds
        pace: Current offensive pace

    Returns:
        Seconds elapsed
    """
    # Base time by pace (from research data)
    if pace == Pace.HURRY_UP:
        base = 13  # ~13 seconds hurry-up
    elif pace == Pace.MILK_CLOCK:
        base = 40  # Use full play clock
    else:
        base = 33  # Normal pace ~33 seconds

    # Adjustments for clock-stopping plays
    if play_type == "pass" and not complete:
        # Incomplete pass - clock stops, faster next play
        return max(5, base - 10)

    if out_of_bounds:
        # Out of bounds - clock stops
        return max(5, base - 8)

    if first_down:
        # First down - brief stop for chains
        return base + 3

    return base


@dataclass
class TimeoutDecision:
    """Decision about calling a timeout."""
    should_call: bool
    reason: str = ""


def should_call_timeout(
    score_diff: int,
    quarter: int,
    time_remaining: int,
    timeouts_remaining: int,
    is_offense: bool,
) -> TimeoutDecision:
    """Decide whether to call a timeout.

    Args:
        score_diff: Our score - opponent score
        quarter: Current quarter (1-4)
        time_remaining: Seconds remaining in quarter
        timeouts_remaining: Number of timeouts left
        is_offense: Whether we have the ball

    Returns:
        TimeoutDecision with recommendation and reason
    """
    if timeouts_remaining <= 0:
        return TimeoutDecision(False, "No timeouts remaining")

    # End of half/game, trailing, on offense - save clock
    if quarter in [2, 4] and time_remaining <= 120:
        if score_diff < 0 and is_offense:
            return TimeoutDecision(True, "Two-minute drill, save clock")

        # On defense, stop clock to get ball back
        if score_diff < 0 and not is_offense and time_remaining <= 60:
            return TimeoutDecision(True, "Stop clock to get ball back")

    # Avoid delay of game
    # (This would need play clock info to implement properly)

    return TimeoutDecision(False)

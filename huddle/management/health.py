"""Player health, injury, and fatigue management system.

Calibrated from NFL injury data and snap count analysis.
Research source: research/exports/active/injury_model.json, fatigue_model.json
"""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4


# =============================================================================
# Load Calibration Data
# =============================================================================

_RESEARCH_DIR = Path(__file__).parent.parent.parent / "research" / "exports" / "active"


def _load_model(filename: str) -> dict:
    """Load a model JSON file from research exports."""
    path = _RESEARCH_DIR / filename
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


# Load models at module import
INJURY_MODEL = _load_model("injury_model.json")
FATIGUE_MODEL = _load_model("fatigue_model.json")


# =============================================================================
# Injury System
# =============================================================================

class InjuryStatus(Enum):
    """Player injury status."""
    HEALTHY = "healthy"
    QUESTIONABLE = "questionable"  # Game-time decision
    DOUBTFUL = "doubtful"  # Unlikely to play
    OUT = "out"  # Will not play
    IR = "ir"  # Injured reserve (min 4 weeks)
    PUP = "pup"  # Physically unable to perform


class InjuryType(Enum):
    """Types of injuries."""
    LEG_MUSCLE = "Leg Muscle"
    KNEE_OTHER = "Knee (Other)"
    KNEE_LIGAMENT = "Knee Ligament"
    ANKLE = "Ankle"
    SHOULDER = "Shoulder"
    CONCUSSION = "Concussion"
    FOOT = "Foot"
    BACK = "Back"
    HIP = "Hip"
    CHEST_RIBS = "Chest/Ribs"
    HAND_WRIST = "Hand/Wrist"
    NECK = "Neck"
    ARM = "Arm"
    ACHILLES = "Achilles"
    ILLNESS = "Illness"
    OTHER = "Other"


# Position injury rates (per game probability)
POSITION_INJURY_RATES = INJURY_MODEL.get("position_injury_rates", {
    "QB": {"per_game_rate": 0.033, "modifier": 0.6},
    "RB": {"per_game_rate": 0.047, "modifier": 0.85},
    "WR": {"per_game_rate": 0.078, "modifier": 1.42},
    "TE": {"per_game_rate": 0.063, "modifier": 1.14},
    "OL": {"per_game_rate": 0.059, "modifier": 1.07},
    "DL": {"per_game_rate": 0.078, "modifier": 1.42},
    "LB": {"per_game_rate": 0.075, "modifier": 1.35},
    "CB": {"per_game_rate": 0.072, "modifier": 1.30},
    "S": {"per_game_rate": 0.047, "modifier": 0.85},
})

# Injury type probabilities
INJURY_TYPE_PROBS = INJURY_MODEL.get("injury_type_probabilities", {
    "Leg Muscle": 0.111,
    "Knee (Other)": 0.079,
    "Ankle": 0.070,
    "Shoulder": 0.032,
    "Concussion": 0.028,
    "Foot": 0.027,
    "Back": 0.017,
    "Hip": 0.015,
    "Chest/Ribs": 0.014,
    "Hand/Wrist": 0.013,
    "Neck": 0.010,
    "Arm": 0.007,
    "Other": 0.577,  # Includes Unknown
})

# Injury duration distributions
INJURY_DURATIONS = INJURY_MODEL.get("duration_distributions", {
    "Leg Muscle": {"min_weeks": 1, "typical_weeks": 2, "season_ending_rate": 0.05},
    "Knee (Other)": {"min_weeks": 1, "typical_weeks": 3, "season_ending_rate": 0.12},
    "Knee Ligament": {"min_weeks": 6, "typical_weeks": 12, "season_ending_rate": 0.65},
    "Ankle": {"min_weeks": 1, "typical_weeks": 3, "season_ending_rate": 0.10},
    "Shoulder": {"min_weeks": 2, "typical_weeks": 4, "season_ending_rate": 0.15},
    "Concussion": {"min_weeks": 1, "typical_weeks": 2, "season_ending_rate": 0.05},
    "Foot": {"min_weeks": 2, "typical_weeks": 4, "season_ending_rate": 0.20},
    "Back": {"min_weeks": 1, "typical_weeks": 3, "season_ending_rate": 0.08},
    "Hip": {"min_weeks": 1, "typical_weeks": 3, "season_ending_rate": 0.10},
    "Achilles": {"min_weeks": 6, "typical_weeks": 16, "season_ending_rate": 0.80},
    "Other": {"min_weeks": 1, "typical_weeks": 2, "season_ending_rate": 0.05},
})


@dataclass
class Injury:
    """Active injury on a player."""
    id: UUID = field(default_factory=uuid4)
    injury_type: str = "Other"
    body_part: str = "Unknown"
    severity: str = "minor"  # minor, moderate, severe, season_ending
    weeks_remaining: int = 1
    occurred_date: Optional[datetime] = None
    is_season_ending: bool = False
    on_ir: bool = False  # Explicitly set by management
    weeks_on_ir: int = 0  # Track time on IR for activation eligibility
    affected_side: str = "unknown"  # "left", "right", or "unknown"

    @property
    def status(self) -> InjuryStatus:
        """Get game status based on weeks remaining."""
        # IR is now a management decision, not automatic
        if self.on_ir:
            return InjuryStatus.IR
        if self.is_season_ending:
            return InjuryStatus.OUT  # Not IR until placed there
        if self.weeks_remaining >= 2:
            return InjuryStatus.OUT
        if self.weeks_remaining == 1:
            return InjuryStatus.DOUBTFUL
        return InjuryStatus.QUESTIONABLE

    def heal_week(self) -> bool:
        """Advance healing by one week. Returns True if healed."""
        if self.on_ir:
            self.weeks_on_ir += 1
        if self.is_season_ending:
            return False
        self.weeks_remaining = max(0, self.weeks_remaining - 1)
        return self.weeks_remaining == 0

    def place_on_ir(self) -> None:
        """Management decision to place player on IR."""
        self.on_ir = True
        self.weeks_on_ir = 0

    def activate_from_ir(self) -> bool:
        """
        Attempt to activate from IR.

        Returns True if activation successful, False if not eligible.
        NFL rule: minimum 4 weeks on IR before activation.
        """
        if self.weeks_on_ir < 4:
            return False  # Not eligible yet
        self.on_ir = False
        return True

    @property
    def ir_eligible_for_return(self) -> bool:
        """Check if player has served minimum IR time."""
        return self.on_ir and self.weeks_on_ir >= 4

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "injury_type": self.injury_type,
            "body_part": self.body_part,
            "severity": self.severity,
            "weeks_remaining": self.weeks_remaining,
            "occurred_date": self.occurred_date.isoformat() if self.occurred_date else None,
            "is_season_ending": self.is_season_ending,
            "on_ir": self.on_ir,
            "weeks_on_ir": self.weeks_on_ir,
            "affected_side": self.affected_side,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Injury":
        """Deserialize from dictionary."""
        occurred = None
        if data.get("occurred_date"):
            occurred = datetime.fromisoformat(data["occurred_date"])
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            injury_type=data.get("injury_type", "Other"),
            body_part=data.get("body_part", "Unknown"),
            severity=data.get("severity", "minor"),
            weeks_remaining=data.get("weeks_remaining", 1),
            occurred_date=occurred,
            is_season_ending=data.get("is_season_ending", False),
            on_ir=data.get("on_ir", False),
            weeks_on_ir=data.get("weeks_on_ir", 0),
            affected_side=data.get("affected_side", "unknown"),
        )


def get_injury_rate(position: str) -> float:
    """Get per-game injury rate for a position."""
    # Normalize position (handle OT, OG, C -> OL, etc.)
    pos_map = {"OT": "OL", "OG": "OL", "C": "OL", "EDGE": "DL", "NT": "DL", "DE": "DL", "DT": "DL"}
    normalized = pos_map.get(position, position)

    if normalized in POSITION_INJURY_RATES:
        return POSITION_INJURY_RATES[normalized]["per_game_rate"]
    return 0.055  # Default rate


def sample_injury_type() -> str:
    """Sample an injury type based on probabilities."""
    types = list(INJURY_TYPE_PROBS.keys())
    probs = list(INJURY_TYPE_PROBS.values())

    # Normalize probabilities
    total = sum(probs)
    probs = [p / total for p in probs]

    return random.choices(types, weights=probs, k=1)[0]


def generate_injury(position: str, current_date: Optional[datetime] = None) -> Optional[Injury]:
    """
    Check if a player gets injured and generate injury details.

    Args:
        position: Player position
        current_date: When the injury occurred

    Returns:
        Injury if player got injured, None otherwise
    """
    rate = get_injury_rate(position)

    if random.random() >= rate:
        return None  # No injury

    # Player is injured - determine type
    injury_type = sample_injury_type()

    # Get duration info
    duration_info = INJURY_DURATIONS.get(injury_type, INJURY_DURATIONS["Other"])

    # Check for season-ending
    is_season_ending = random.random() < duration_info["season_ending_rate"]

    if is_season_ending:
        weeks = 52  # Out for season
        severity = "season_ending"
    else:
        # Sample duration (triangular distribution)
        min_weeks = duration_info["min_weeks"]
        typical_weeks = duration_info["typical_weeks"]
        max_weeks = typical_weeks * 2

        weeks = int(random.triangular(min_weeks, max_weeks, typical_weeks))

        # Determine severity
        if weeks >= 8:
            severity = "severe"
        elif weeks >= 4:
            severity = "moderate"
        else:
            severity = "minor"

    return Injury(
        injury_type=injury_type,
        body_part=injury_type,  # Simplified
        severity=severity,
        weeks_remaining=weeks,
        occurred_date=current_date or datetime.now(),
        is_season_ending=is_season_ending,
    )


def check_practice_injury(position: str, intensity: str = "normal") -> Optional[Injury]:
    """
    Check for injury during practice.

    Practice injuries are less common than game injuries.

    Args:
        position: Player position
        intensity: Practice intensity (light, normal, intense)

    Returns:
        Injury if player got injured, None otherwise
    """
    # Practice injury rate is ~10% of game rate
    base_rate = get_injury_rate(position) * 0.1

    # Intensity modifiers
    intensity_mods = {"light": 0.5, "normal": 1.0, "intense": 1.5}
    rate = base_rate * intensity_mods.get(intensity, 1.0)

    if random.random() >= rate:
        return None

    # Practice injuries tend to be less severe
    injury = generate_injury(position)
    if injury and not injury.is_season_ending:
        # Reduce duration for practice injuries
        injury.weeks_remaining = max(1, injury.weeks_remaining - 1)

    return injury


# =============================================================================
# Fatigue System
# =============================================================================

# Snap percentage targets by position
SNAP_TARGETS = FATIGUE_MODEL.get("snap_targets", {
    "QB": {"starter_target_pct": 1.0, "rotation_target_pct": 1.0},
    "RB": {"starter_target_pct": 0.69, "rotation_target_pct": 0.27},
    "WR": {"starter_target_pct": 0.92, "rotation_target_pct": 0.53},
    "TE": {"starter_target_pct": 0.83, "rotation_target_pct": 0.41},
    "OL": {"starter_target_pct": 1.0, "rotation_target_pct": 1.0},
    "DL": {"starter_target_pct": 0.77, "rotation_target_pct": 0.47},
    "EDGE": {"starter_target_pct": 0.90, "rotation_target_pct": 0.42},
    "LB": {"starter_target_pct": 1.0, "rotation_target_pct": 0.37},
    "CB": {"starter_target_pct": 1.0, "rotation_target_pct": 0.60},
    "S": {"starter_target_pct": 1.0, "rotation_target_pct": 0.65},
})

# Fatigue curve - performance penalty by snap percentage
FATIGUE_CURVE = FATIGUE_MODEL.get("fatigue_curve", {
    "0.0": 1.0,
    "0.5": 1.0,
    "0.7": 0.99,
    "0.8": 0.97,
    "0.9": 0.94,
    "0.95": 0.90,
    "1.0": 0.85,
    "position_modifiers": {
        "QB": 0.7,
        "RB": 1.3,
        "WR": 1.0,
        "TE": 1.1,
        "OL": 0.9,
        "DL": 1.4,
        "EDGE": 1.2,
        "LB": 1.1,
        "CB": 1.0,
        "S": 0.9,
    }
})

# Rotation recommendations
ROTATION_RECS = FATIGUE_MODEL.get("rotation_recommendations", {
    "RB": {"typical_rotation_size": 2, "optimal_lead_pct": 0.70},
    "DL": {"typical_rotation_size": 6, "optimal_lead_pct": 0.30},
    "WR": {"typical_rotation_size": 4, "optimal_lead_pct": 0.50},
    "TE": {"typical_rotation_size": 2, "optimal_lead_pct": 0.70},
    "LB": {"typical_rotation_size": 4, "optimal_lead_pct": 0.50},
    "CB": {"typical_rotation_size": 3, "optimal_lead_pct": 0.60},
})

# Cumulative game effects
CUMULATIVE_EFFECTS = FATIGUE_MODEL.get("cumulative_effects", {
    "games_1": 1.0,
    "games_2": 0.98,
    "games_3": 0.95,
    "games_4": 0.92,
    "bye_week_recovery": 1.05,
    "thursday_game_penalty": 0.97,
})


@dataclass
class PlayerFatigue:
    """Tracks player fatigue state."""
    player_id: UUID
    current_fatigue: float = 0.0  # 0-1, 0 = fresh, 1 = exhausted
    games_since_rest: int = 0
    snap_pct_last_game: float = 0.0
    is_rested: bool = True

    def apply_game(self, snap_pct: float, position: str) -> None:
        """Apply fatigue from a game."""
        # Get position modifier
        pos_mods = FATIGUE_CURVE.get("position_modifiers", {})
        pos_mod = pos_mods.get(position, 1.0)

        # Calculate fatigue accumulation
        fatigue_gain = snap_pct * 0.3 * pos_mod
        self.current_fatigue = min(1.0, self.current_fatigue + fatigue_gain)

        self.snap_pct_last_game = snap_pct
        self.games_since_rest += 1
        self.is_rested = False

    def apply_rest(self, is_bye_week: bool = False) -> None:
        """Apply rest/recovery."""
        if is_bye_week:
            # Full recovery on bye
            self.current_fatigue = 0.0
            self.games_since_rest = 0
            self.is_rested = True
        else:
            # Normal weekly recovery
            recovery = 0.4 if self.is_rested else 0.25
            self.current_fatigue = max(0, self.current_fatigue - recovery)
            self.is_rested = True

    def get_performance_modifier(self, position: str) -> float:
        """Get performance modifier based on fatigue."""
        # Base penalty from fatigue level
        if self.current_fatigue <= 0.3:
            base_penalty = 0.0
        elif self.current_fatigue <= 0.5:
            base_penalty = 0.02
        elif self.current_fatigue <= 0.7:
            base_penalty = 0.05
        elif self.current_fatigue <= 0.9:
            base_penalty = 0.10
        else:
            base_penalty = 0.15

        # Cumulative games penalty
        games_key = f"games_{min(4, self.games_since_rest)}"
        games_mod = CUMULATIVE_EFFECTS.get(games_key, 1.0)

        return (1.0 - base_penalty) * games_mod

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "player_id": str(self.player_id),
            "current_fatigue": self.current_fatigue,
            "games_since_rest": self.games_since_rest,
            "snap_pct_last_game": self.snap_pct_last_game,
            "is_rested": self.is_rested,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerFatigue":
        """Deserialize from dictionary."""
        return cls(
            player_id=UUID(data["player_id"]),
            current_fatigue=data.get("current_fatigue", 0.0),
            games_since_rest=data.get("games_since_rest", 0),
            snap_pct_last_game=data.get("snap_pct_last_game", 0.0),
            is_rested=data.get("is_rested", True),
        )


def calculate_snap_penalty(snap_pct: float, position: str) -> float:
    """
    Calculate performance penalty from snap percentage.

    Args:
        snap_pct: Percentage of snaps played (0.0-1.0)
        position: Player position

    Returns:
        Performance multiplier (0.85-1.0)
    """
    # Find the appropriate fatigue level from curve
    thresholds = sorted([float(k) for k in FATIGUE_CURVE.keys() if k != "position_modifiers"])

    base_mod = 1.0
    for thresh in thresholds:
        if snap_pct >= thresh:
            base_mod = FATIGUE_CURVE.get(str(thresh), 1.0)

    # Apply position modifier
    pos_mods = FATIGUE_CURVE.get("position_modifiers", {})
    pos_mod = pos_mods.get(position, 1.0)

    # Adjust penalty by position (DL tires faster, QB slower)
    penalty = 1.0 - base_mod
    adjusted_penalty = penalty * pos_mod

    return max(0.85, 1.0 - adjusted_penalty)


def get_optimal_snap_share(position: str, is_starter: bool = True) -> float:
    """Get optimal snap percentage for a position."""
    # Normalize position
    pos_map = {"OT": "OL", "OG": "OL", "C": "OL"}
    normalized = pos_map.get(position, position)

    targets = SNAP_TARGETS.get(normalized, {"starter_target_pct": 0.8, "rotation_target_pct": 0.5})

    if is_starter:
        return targets["starter_target_pct"]
    return targets["rotation_target_pct"]


def get_rotation_recommendation(position: str) -> dict:
    """Get rotation size recommendation for a position."""
    # Normalize position
    pos_map = {"OT": "OL", "OG": "OL", "C": "OL"}
    normalized = pos_map.get(position, position)

    return ROTATION_RECS.get(normalized, {
        "typical_rotation_size": 1,
        "optimal_lead_pct": 1.0,
    })


# =============================================================================
# Player Health State
# =============================================================================

@dataclass
class PlayerHealth:
    """Complete health state for a player."""
    player_id: UUID
    injuries: list[Injury] = field(default_factory=list)
    fatigue: PlayerFatigue = field(default_factory=lambda: PlayerFatigue(player_id=UUID(int=0)))
    injury_history: list[dict] = field(default_factory=list)  # Past injuries

    def __post_init__(self):
        if self.fatigue.player_id == UUID(int=0):
            self.fatigue = PlayerFatigue(player_id=self.player_id)

    @property
    def is_healthy(self) -> bool:
        """Check if player has no active injuries."""
        return len(self.injuries) == 0

    @property
    def status(self) -> InjuryStatus:
        """Get overall injury status."""
        if not self.injuries:
            return InjuryStatus.HEALTHY

        # Return worst status
        statuses = [inj.status for inj in self.injuries]
        priority = [InjuryStatus.IR, InjuryStatus.OUT, InjuryStatus.DOUBTFUL,
                    InjuryStatus.QUESTIONABLE, InjuryStatus.HEALTHY]

        for status in priority:
            if status in statuses:
                return status

        return InjuryStatus.HEALTHY

    @property
    def can_play(self) -> bool:
        """Check if player is available to play."""
        return self.status in [InjuryStatus.HEALTHY, InjuryStatus.QUESTIONABLE]

    def add_injury(self, injury: Injury) -> None:
        """Add a new injury."""
        self.injuries.append(injury)

    def heal_week(self) -> list[Injury]:
        """
        Advance healing by one week.

        Returns list of healed injuries.
        """
        healed = []
        remaining = []

        for injury in self.injuries:
            if injury.heal_week():
                healed.append(injury)
                # Add to history
                self.injury_history.append({
                    "type": injury.injury_type,
                    "severity": injury.severity,
                    "was_season_ending": injury.is_season_ending,
                })
            else:
                remaining.append(injury)

        self.injuries = remaining
        return healed

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "player_id": str(self.player_id),
            "injuries": [inj.to_dict() for inj in self.injuries],
            "fatigue": self.fatigue.to_dict(),
            "injury_history": self.injury_history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerHealth":
        """Deserialize from dictionary."""
        player_id = UUID(data["player_id"])
        injuries = [Injury.from_dict(i) for i in data.get("injuries", [])]
        fatigue = PlayerFatigue.from_dict(data["fatigue"]) if data.get("fatigue") else PlayerFatigue(player_id=player_id)

        return cls(
            player_id=player_id,
            injuries=injuries,
            fatigue=fatigue,
            injury_history=data.get("injury_history", []),
        )


# =============================================================================
# Action-Based Injury System
# =============================================================================

# Map actions to body parts they stress
ACTION_BODY_STRESS: dict[str, list[str]] = {
    # Ballcarrier moves
    "juke": ["left_leg", "right_leg"],
    "spin": ["left_leg", "right_leg", "torso"],
    "cut": ["left_leg", "right_leg"],  # High ACL risk
    "truck": ["torso", "left_arm", "right_arm"],
    "hurdle": ["left_leg", "right_leg"],
    "stiff_arm": ["left_arm", "right_arm"],
    "sprint": ["left_leg", "right_leg"],
    "dive": ["torso", "head"],

    # Receiver actions
    "route_break": ["left_leg", "right_leg"],
    "catch_contested": ["left_arm", "right_arm", "head"],
    "release": ["left_arm", "right_arm"],
    "high_point": ["left_arm", "right_arm"],

    # QB actions
    "throw": ["right_arm", "torso"],  # Assume right-handed
    "scramble": ["left_leg", "right_leg"],
    "sack": ["torso", "head", "left_arm", "right_arm"],
    "dropback": ["left_leg", "right_leg"],

    # Blocking/tackling
    "block": ["left_arm", "right_arm", "torso"],
    "pass_block": ["left_arm", "right_arm", "left_leg", "right_leg"],
    "run_block": ["torso", "left_arm", "right_arm"],
    "tackle": ["left_arm", "right_arm", "head"],
    "get_tackled": ["left_leg", "right_leg", "torso", "head"],

    # Coverage
    "backpedal": ["left_leg", "right_leg"],
    "break_on_ball": ["left_leg", "right_leg"],
    "jam": ["left_arm", "right_arm"],
}

# Base injury risk per action (probability per occurrence)
ACTION_BASE_RISK: dict[str, float] = {
    # High risk actions
    "cut": 0.0008,  # ACL risk
    "tackle": 0.0006,
    "get_tackled": 0.0005,
    "sack": 0.0010,

    # Medium risk actions
    "juke": 0.0004,
    "hurdle": 0.0005,
    "truck": 0.0004,
    "route_break": 0.0003,
    "block": 0.0003,
    "catch_contested": 0.0004,
    "dive": 0.0006,

    # Low risk actions
    "spin": 0.0002,
    "stiff_arm": 0.0002,
    "throw": 0.0001,
    "sprint": 0.0001,
    "backpedal": 0.0002,
    "break_on_ball": 0.0002,
    "pass_block": 0.0002,
    "run_block": 0.0002,
    "scramble": 0.0002,
    "dropback": 0.0001,
    "release": 0.0001,
    "high_point": 0.0002,
    "jam": 0.0002,
}

# Map body part to injury types
BODY_PART_INJURIES: dict[str, list[str]] = {
    "left_leg": ["Leg Muscle", "Knee (Other)", "Knee Ligament", "Ankle", "Foot", "Hip", "Achilles"],
    "right_leg": ["Leg Muscle", "Knee (Other)", "Knee Ligament", "Ankle", "Foot", "Hip", "Achilles"],
    "left_arm": ["Shoulder", "Arm", "Hand/Wrist"],
    "right_arm": ["Shoulder", "Arm", "Hand/Wrist"],
    "torso": ["Back", "Chest/Ribs", "Hip"],
    "head": ["Concussion", "Neck"],
}

# Weights for injury type selection (some more common than others)
BODY_PART_INJURY_WEIGHTS: dict[str, list[float]] = {
    "left_leg": [0.30, 0.25, 0.10, 0.20, 0.08, 0.05, 0.02],
    "right_leg": [0.30, 0.25, 0.10, 0.20, 0.08, 0.05, 0.02],
    "left_arm": [0.50, 0.25, 0.25],
    "right_arm": [0.50, 0.25, 0.25],
    "torso": [0.50, 0.30, 0.20],
    "head": [0.70, 0.30],
}


def get_player_durability(player_attributes: dict[str, int]) -> dict[str, int]:
    """
    Extract body-part durability from player attributes.

    Args:
        player_attributes: Player's attribute dictionary

    Returns:
        Mapping of body part to durability rating (40-99)
    """
    return {
        "left_leg": player_attributes.get("left_leg_durability", 75),
        "right_leg": player_attributes.get("right_leg_durability", 75),
        "left_arm": player_attributes.get("left_arm_durability", 75),
        "right_arm": player_attributes.get("right_arm_durability", 75),
        "torso": player_attributes.get("torso_durability", 75),
        "head": player_attributes.get("head_durability", 75),
    }


def check_action_injury(
    player_durability: dict[str, int],
    action: str,
    intensity: float = 1.0,
    current_date: Optional[datetime] = None,
) -> Optional[Injury]:
    """
    Check if an action causes injury based on body-part durability.

    Args:
        player_durability: Mapping of body part to durability rating (40-99)
        action: The action being performed (e.g., "juke", "tackle")
        intensity: Multiplier for injury risk (0.5=light, 1.0=normal, 1.5=critical)
        current_date: When the action occurred

    Returns:
        Injury if one occurs, None otherwise
    """
    if action not in ACTION_BODY_STRESS:
        return None

    stressed_parts = ACTION_BODY_STRESS[action]
    base_risk = ACTION_BASE_RISK.get(action, 0.0002)

    # Pick a random body part that could be injured
    body_part = random.choice(stressed_parts)
    durability = player_durability.get(body_part, 75)

    # Lower durability = higher risk (exponential scaling)
    # 99 durability = 0.02x risk, 75 durability = 0.5x, 50 durability = 1x, 40 durability = 1.2x
    risk_multiplier = (100 - durability) / 50
    final_risk = base_risk * risk_multiplier * intensity

    if random.random() >= final_risk:
        return None  # No injury

    # Injury occurred - determine type based on body part
    injury_types = BODY_PART_INJURIES.get(body_part, ["Other"])
    injury_weights = BODY_PART_INJURY_WEIGHTS.get(body_part, [1.0])
    injury_type = random.choices(injury_types, weights=injury_weights, k=1)[0]

    # Get duration info
    duration_info = INJURY_DURATIONS.get(injury_type, INJURY_DURATIONS["Other"])

    # Check for season-ending
    is_season_ending = random.random() < duration_info["season_ending_rate"]

    if is_season_ending:
        weeks = 52
        severity = "season_ending"
    else:
        min_weeks = duration_info["min_weeks"]
        typical_weeks = duration_info["typical_weeks"]
        max_weeks = typical_weeks * 2
        weeks = int(random.triangular(min_weeks, max_weeks, typical_weeks))

        if weeks >= 8:
            severity = "severe"
        elif weeks >= 4:
            severity = "moderate"
        else:
            severity = "minor"

    # Determine which side was affected
    if "left" in body_part:
        affected_side = "left"
    elif "right" in body_part:
        affected_side = "right"
    else:
        affected_side = "unknown"

    return Injury(
        injury_type=injury_type,
        body_part=body_part,
        severity=severity,
        weeks_remaining=weeks,
        occurred_date=current_date or datetime.now(),
        is_season_ending=is_season_ending,
        affected_side=affected_side,
    )


# =============================================================================
# Injury Degradation System
# =============================================================================

# How much durability to lose by injury type
INJURY_DEGRADATION: dict[str, tuple[int, int]] = {
    "Knee Ligament": (8, 15),  # ACL/MCL tears are serious
    "Achilles": (10, 18),  # Very impactful
    "Shoulder": (5, 10),
    "Concussion": (3, 8),  # Cumulative concern
    "Knee (Other)": (3, 7),
    "Ankle": (2, 5),
    "Leg Muscle": (1, 4),
    "Foot": (2, 5),
    "Back": (3, 7),
    "Hip": (2, 5),
    "Chest/Ribs": (1, 3),
    "Hand/Wrist": (1, 3),
    "Neck": (2, 5),
    "Arm": (1, 3),
    "Other": (1, 3),
}


def calculate_injury_degradation(injury: Injury) -> int:
    """
    Calculate how much durability should be lost from an injury.

    Args:
        injury: The injury that occurred

    Returns:
        Durability points to subtract from the affected body part
    """
    deg_range = INJURY_DEGRADATION.get(injury.injury_type, (1, 3))

    # Severity affects degradation
    if injury.is_season_ending:
        # Season-ending injuries cause max degradation
        return deg_range[1]
    elif injury.severity == "severe":
        return random.randint(deg_range[0] + 2, deg_range[1])
    elif injury.severity == "moderate":
        return random.randint(deg_range[0], deg_range[1] - 2)
    else:  # minor
        return random.randint(deg_range[0], max(deg_range[0], deg_range[1] - 4))


def get_durability_attribute_name(body_part: str) -> str:
    """Map body part to attribute name."""
    mapping = {
        "left_leg": "left_leg_durability",
        "right_leg": "right_leg_durability",
        "left_arm": "left_arm_durability",
        "right_arm": "right_arm_durability",
        "torso": "torso_durability",
        "head": "head_durability",
    }
    return mapping.get(body_part, "toughness")


# =============================================================================
# Body-Part Fatigue System
# =============================================================================

@dataclass
class BodyPartFatigue:
    """Per-body-part fatigue tracking during a game."""
    legs: float = 0.0      # Affects speed, acceleration, agility
    arms: float = 0.0      # Affects throw power, catch, tackle
    core: float = 0.0      # Affects balance, blocking, breaking tackles
    cardio: float = 0.0    # Affects stamina, late-game performance

    def reset(self) -> None:
        """Reset all fatigue (e.g., between games)."""
        self.legs = 0.0
        self.arms = 0.0
        self.core = 0.0
        self.cardio = 0.0

    def apply_action(self, action: str) -> None:
        """Apply fatigue from an action."""
        fatigue_map = ACTION_FATIGUE.get(action, {})
        self.legs = min(1.0, self.legs + fatigue_map.get("legs", 0.0))
        self.arms = min(1.0, self.arms + fatigue_map.get("arms", 0.0))
        self.core = min(1.0, self.core + fatigue_map.get("core", 0.0))
        self.cardio = min(1.0, self.cardio + fatigue_map.get("cardio", 0.0))

    def get_attribute_modifier(self, attribute: str) -> float:
        """
        Get performance modifier for a specific attribute based on fatigue.

        Returns multiplier from 0.85 (exhausted) to 1.0 (fresh).
        """
        # Find which body part affects this attribute
        for body_part, attrs in FATIGUE_ATTRIBUTE_IMPACT.items():
            if attribute in attrs:
                fatigue_level = getattr(self, body_part, 0.0)
                return _fatigue_to_modifier(fatigue_level)
        return 1.0  # No fatigue impact

    def get_all_modifiers(self) -> dict[str, float]:
        """Get modifiers for all affected attributes."""
        modifiers = {}
        for body_part, attrs in FATIGUE_ATTRIBUTE_IMPACT.items():
            fatigue_level = getattr(self, body_part, 0.0)
            modifier = _fatigue_to_modifier(fatigue_level)
            for attr in attrs:
                modifiers[attr] = modifier
        return modifiers

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "legs": self.legs,
            "arms": self.arms,
            "core": self.core,
            "cardio": self.cardio,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BodyPartFatigue":
        """Deserialize from dictionary."""
        return cls(
            legs=data.get("legs", 0.0),
            arms=data.get("arms", 0.0),
            core=data.get("core", 0.0),
            cardio=data.get("cardio", 0.0),
        )


# Action -> body part fatigue accumulation
ACTION_FATIGUE: dict[str, dict[str, float]] = {
    # Movement
    "sprint": {"legs": 0.02, "cardio": 0.01},
    "cut": {"legs": 0.03},
    "juke": {"legs": 0.02, "core": 0.01},
    "spin": {"legs": 0.02, "core": 0.015},
    "hurdle": {"legs": 0.025, "core": 0.01},
    "backpedal": {"legs": 0.015, "cardio": 0.005},
    "break_on_ball": {"legs": 0.02},
    "scramble": {"legs": 0.025, "cardio": 0.015},

    # Contact
    "truck": {"core": 0.02, "arms": 0.01},
    "stiff_arm": {"arms": 0.015},
    "block": {"arms": 0.02, "core": 0.02, "legs": 0.01},
    "pass_block": {"arms": 0.015, "core": 0.015, "legs": 0.01},
    "run_block": {"arms": 0.02, "core": 0.025, "legs": 0.01},
    "tackle": {"arms": 0.02, "legs": 0.02, "cardio": 0.01},
    "get_tackled": {"core": 0.015, "legs": 0.01},

    # Skill actions
    "throw": {"arms": 0.015, "core": 0.01},
    "dropback": {"legs": 0.005},
    "route_break": {"legs": 0.02},
    "catch_contested": {"arms": 0.015, "core": 0.01},
    "release": {"arms": 0.01},
    "high_point": {"arms": 0.015, "legs": 0.01},
    "jam": {"arms": 0.015},
    "dive": {"core": 0.02, "cardio": 0.01},
    "sack": {"core": 0.025, "arms": 0.015},  # Getting sacked
}

# Body part fatigue -> attribute penalties
FATIGUE_ATTRIBUTE_IMPACT: dict[str, list[str]] = {
    "legs": ["speed", "acceleration", "agility", "jumping", "elusiveness"],
    "arms": ["throw_power", "throw_accuracy_short", "throw_accuracy_mid",
             "throw_accuracy_deep", "catching", "tackle", "block_strength"],
    "core": ["balance", "break_tackle", "trucking", "block_shed",
             "impact_blocking", "run_blocking", "pass_blocking"],
    "cardio": ["stamina", "pursuit", "play_recognition", "awareness"],
}


def _fatigue_to_modifier(fatigue_level: float) -> float:
    """
    Convert fatigue (0.0-1.0) to attribute penalty multiplier.

    0.0 fatigue = 1.0x (no penalty)
    0.5 fatigue = 0.95x (-5%)
    1.0 fatigue = 0.85x (-15%)
    """
    # Linear interpolation from 1.0 to 0.85
    return 1.0 - (fatigue_level * 0.15)

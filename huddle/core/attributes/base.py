"""Base attribute definitions."""

from dataclasses import dataclass, field
from enum import Enum, auto


class AttributeCategory(Enum):
    """Categories for player attributes."""

    # Core categories
    META = auto()  # Overall, Potential, Learning - the "big three"
    PHYSICAL = auto()
    PASSING = auto()
    RUSHING = auto()
    RECEIVING = auto()
    BLOCKING = auto()
    DEFENSE = auto()
    SPECIAL_TEAMS = auto()
    MENTAL = auto()
    DURABILITY = auto()  # Body part health for wear & tear system


@dataclass(frozen=True)
class AttributeDefinition:
    """
    Defines an attribute type (not a value).

    Attributes are defined once and registered globally.
    Each player then has values for these attributes.
    """

    name: str
    category: AttributeCategory
    abbreviation: str
    description: str = ""
    min_value: int = 0
    max_value: int = 99

    # Position relevance weights (0.0-1.0)
    # Higher weight = more important for that position's overall rating
    position_weights: dict[str, float] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AttributeDefinition):
            return NotImplemented
        return self.name == other.name

    def clamp(self, value: int) -> int:
        """Clamp a value to valid range."""
        return max(self.min_value, min(self.max_value, value))


# ============================================================================
# Physical Attributes
# ============================================================================

SPEED = AttributeDefinition(
    name="speed",
    category=AttributeCategory.PHYSICAL,
    abbreviation="SPD",
    description="Top running speed",
    position_weights={
        "QB": 0.3,
        "RB": 0.9,
        "FB": 0.4,
        "WR": 1.0,
        "TE": 0.6,
        "CB": 0.95,
        "FS": 0.85,
        "SS": 0.75,
        "OLB": 0.6,
        "DE": 0.5,
    },
)

ACCELERATION = AttributeDefinition(
    name="acceleration",
    category=AttributeCategory.PHYSICAL,
    abbreviation="ACC",
    description="How quickly player reaches top speed",
    position_weights={
        "QB": 0.3,
        "RB": 0.85,
        "WR": 0.9,
        "CB": 0.9,
        "FS": 0.8,
        "SS": 0.7,
        "DE": 0.6,
    },
)

AGILITY = AttributeDefinition(
    name="agility",
    category=AttributeCategory.PHYSICAL,
    abbreviation="AGI",
    description="Quickness in changing direction",
    position_weights={
        "RB": 0.9,
        "WR": 0.85,
        "CB": 0.8,
        "FS": 0.6,
        "SS": 0.5,
        "QB": 0.4,
    },
)

STRENGTH = AttributeDefinition(
    name="strength",
    category=AttributeCategory.PHYSICAL,
    abbreviation="STR",
    description="Raw physical power",
    position_weights={
        "LT": 0.9,
        "LG": 0.95,
        "C": 0.9,
        "RG": 0.95,
        "RT": 0.9,
        "DT": 0.95,
        "NT": 1.0,
        "DE": 0.8,
        "MLB": 0.7,
        "FB": 0.75,
        "TE": 0.6,
        "SS": 0.6,
    },
)

JUMPING = AttributeDefinition(
    name="jumping",
    category=AttributeCategory.PHYSICAL,
    abbreviation="JMP",
    description="Vertical leap ability",
    position_weights={
        "WR": 0.7,
        "TE": 0.5,
        "CB": 0.6,
        "FS": 0.5,
        "SS": 0.4,
    },
)

STAMINA = AttributeDefinition(
    name="stamina",
    category=AttributeCategory.PHYSICAL,
    abbreviation="STA",
    description="Endurance throughout game",
    position_weights={
        "RB": 0.5,
        "WR": 0.4,
        "LT": 0.4,
        "LG": 0.4,
        "C": 0.4,
        "RG": 0.4,
        "RT": 0.4,
    },
)

INJURY = AttributeDefinition(
    name="injury",
    category=AttributeCategory.PHYSICAL,
    abbreviation="INJ",
    description="Resistance to injury (higher = more durable)",
    position_weights={},  # Affects all equally, not used in overall
)

# ============================================================================
# Passing Attributes
# ============================================================================

THROW_POWER = AttributeDefinition(
    name="throw_power",
    category=AttributeCategory.PASSING,
    abbreviation="THP",
    description="Arm strength for deep throws",
    position_weights={"QB": 0.85},
)

THROW_ACCURACY_SHORT = AttributeDefinition(
    name="throw_accuracy_short",
    category=AttributeCategory.PASSING,
    abbreviation="TAS",
    description="Accuracy on short passes (0-20 yards)",
    position_weights={"QB": 0.9},
)

THROW_ACCURACY_MED = AttributeDefinition(
    name="throw_accuracy_med",
    category=AttributeCategory.PASSING,
    abbreviation="TAM",
    description="Accuracy on medium passes (20-40 yards)",
    position_weights={"QB": 0.85},
)

THROW_ACCURACY_DEEP = AttributeDefinition(
    name="throw_accuracy_deep",
    category=AttributeCategory.PASSING,
    abbreviation="TAD",
    description="Accuracy on deep passes (40+ yards)",
    position_weights={"QB": 0.7},
)

THROW_ON_RUN = AttributeDefinition(
    name="throw_on_run",
    category=AttributeCategory.PASSING,
    abbreviation="TOR",
    description="Passing accuracy while moving",
    position_weights={"QB": 0.5},
)

PLAY_ACTION = AttributeDefinition(
    name="play_action",
    category=AttributeCategory.PASSING,
    abbreviation="PAC",
    description="Effectiveness of play action fakes",
    position_weights={"QB": 0.3},
)

# ============================================================================
# Rushing Attributes
# ============================================================================

CARRYING = AttributeDefinition(
    name="carrying",
    category=AttributeCategory.RUSHING,
    abbreviation="CAR",
    description="Ball security while running",
    position_weights={"RB": 0.8, "FB": 0.6, "QB": 0.4, "WR": 0.3},
)

TRUCKING = AttributeDefinition(
    name="trucking",
    category=AttributeCategory.RUSHING,
    abbreviation="TRK",
    description="Running through defenders",
    position_weights={"RB": 0.6, "FB": 0.8},
)

ELUSIVENESS = AttributeDefinition(
    name="elusiveness",
    category=AttributeCategory.RUSHING,
    abbreviation="ELU",
    description="Avoiding tackles in open field",
    position_weights={"RB": 0.85, "WR": 0.5, "QB": 0.3},
)

SPIN_MOVE = AttributeDefinition(
    name="spin_move",
    category=AttributeCategory.RUSHING,
    abbreviation="SPN",
    description="Spin move effectiveness",
    position_weights={"RB": 0.5, "WR": 0.3},
)

JUKE_MOVE = AttributeDefinition(
    name="juke_move",
    category=AttributeCategory.RUSHING,
    abbreviation="JKM",
    description="Juke move effectiveness",
    position_weights={"RB": 0.5, "WR": 0.4},
)

STIFF_ARM = AttributeDefinition(
    name="stiff_arm",
    category=AttributeCategory.RUSHING,
    abbreviation="SFA",
    description="Stiff arm effectiveness",
    position_weights={"RB": 0.4, "TE": 0.3},
)

BREAK_TACKLE = AttributeDefinition(
    name="break_tackle",
    category=AttributeCategory.RUSHING,
    abbreviation="BTK",
    description="Breaking through tackle attempts",
    position_weights={"RB": 0.7, "FB": 0.6, "TE": 0.4},
)

# ============================================================================
# Receiving Attributes
# ============================================================================

CATCHING = AttributeDefinition(
    name="catching",
    category=AttributeCategory.RECEIVING,
    abbreviation="CTH",
    description="Ability to catch the ball",
    position_weights={"WR": 0.95, "TE": 0.85, "RB": 0.5, "FB": 0.3},
)

CATCH_IN_TRAFFIC = AttributeDefinition(
    name="catch_in_traffic",
    category=AttributeCategory.RECEIVING,
    abbreviation="CIT",
    description="Catching with defenders nearby",
    position_weights={"WR": 0.7, "TE": 0.8, "RB": 0.4},
)

SPECTACULAR_CATCH = AttributeDefinition(
    name="spectacular_catch",
    category=AttributeCategory.RECEIVING,
    abbreviation="SPC",
    description="Making difficult catches",
    position_weights={"WR": 0.6, "TE": 0.3},
)

ROUTE_RUNNING = AttributeDefinition(
    name="route_running",
    category=AttributeCategory.RECEIVING,
    abbreviation="RTE",
    description="Precision in running routes",
    position_weights={"WR": 0.9, "TE": 0.7, "RB": 0.4},
)

RELEASE = AttributeDefinition(
    name="release",
    category=AttributeCategory.RECEIVING,
    abbreviation="REL",
    description="Getting off the line against press coverage",
    position_weights={"WR": 0.7, "TE": 0.5},
)

# ============================================================================
# Blocking Attributes
# ============================================================================

PASS_BLOCK = AttributeDefinition(
    name="pass_block",
    category=AttributeCategory.BLOCKING,
    abbreviation="PBK",
    description="Pass protection ability",
    position_weights={
        "LT": 1.0,
        "LG": 0.85,
        "C": 0.85,
        "RG": 0.85,
        "RT": 0.9,
        "TE": 0.4,
        "FB": 0.4,
    },
)

RUN_BLOCK = AttributeDefinition(
    name="run_block",
    category=AttributeCategory.BLOCKING,
    abbreviation="RBK",
    description="Run blocking ability",
    position_weights={
        "LT": 0.85,
        "LG": 1.0,
        "C": 0.9,
        "RG": 1.0,
        "RT": 0.85,
        "TE": 0.6,
        "FB": 0.7,
    },
)

IMPACT_BLOCKING = AttributeDefinition(
    name="impact_blocking",
    category=AttributeCategory.BLOCKING,
    abbreviation="IMP",
    description="Blocking at the second level",
    position_weights={"LG": 0.6, "RG": 0.6, "FB": 0.5, "TE": 0.4},
)

# ============================================================================
# Defensive Attributes
# ============================================================================

TACKLE = AttributeDefinition(
    name="tackle",
    category=AttributeCategory.DEFENSE,
    abbreviation="TAK",
    description="Ability to bring down ball carrier",
    position_weights={
        "MLB": 0.95,
        "ILB": 0.9,
        "OLB": 0.85,
        "SS": 0.8,
        "FS": 0.7,
        "CB": 0.6,
        "DE": 0.75,
        "DT": 0.7,
    },
)

HIT_POWER = AttributeDefinition(
    name="hit_power",
    category=AttributeCategory.DEFENSE,
    abbreviation="POW",
    description="Force of tackles and hits",
    position_weights={"MLB": 0.7, "SS": 0.8, "OLB": 0.6, "DE": 0.5},
)

BLOCK_SHEDDING = AttributeDefinition(
    name="block_shedding",
    category=AttributeCategory.DEFENSE,
    abbreviation="BSH",
    description="Getting past blockers",
    position_weights={"DE": 0.9, "DT": 0.95, "NT": 0.9, "OLB": 0.7, "MLB": 0.6},
)

PURSUIT = AttributeDefinition(
    name="pursuit",
    category=AttributeCategory.DEFENSE,
    abbreviation="PUR",
    description="Chase angles and effort",
    position_weights={
        "MLB": 0.8,
        "OLB": 0.85,
        "DE": 0.8,
        "FS": 0.75,
        "SS": 0.8,
        "CB": 0.7,
    },
)

PLAY_RECOGNITION = AttributeDefinition(
    name="play_recognition",
    category=AttributeCategory.DEFENSE,
    abbreviation="PRC",
    description="Reading offensive plays",
    position_weights={
        "MLB": 0.9,
        "FS": 0.85,
        "SS": 0.8,
        "CB": 0.7,
        "OLB": 0.75,
        "DE": 0.6,
    },
)

MAN_COVERAGE = AttributeDefinition(
    name="man_coverage",
    category=AttributeCategory.DEFENSE,
    abbreviation="MAN",
    description="Man-to-man coverage ability",
    position_weights={"CB": 0.95, "FS": 0.6, "SS": 0.7, "OLB": 0.4},
)

ZONE_COVERAGE = AttributeDefinition(
    name="zone_coverage",
    category=AttributeCategory.DEFENSE,
    abbreviation="ZON",
    description="Zone coverage ability",
    position_weights={"CB": 0.8, "FS": 0.9, "SS": 0.8, "MLB": 0.5, "OLB": 0.5},
)

PRESS = AttributeDefinition(
    name="press",
    category=AttributeCategory.DEFENSE,
    abbreviation="PRS",
    description="Press coverage at the line",
    position_weights={"CB": 0.7, "SS": 0.3},
)

FINESSE_MOVES = AttributeDefinition(
    name="finesse_moves",
    category=AttributeCategory.DEFENSE,
    abbreviation="FNM",
    description="Pass rush finesse technique",
    position_weights={"DE": 0.85, "OLB": 0.7, "DT": 0.5},
)

POWER_MOVES = AttributeDefinition(
    name="power_moves",
    category=AttributeCategory.DEFENSE,
    abbreviation="PWM",
    description="Pass rush power technique",
    position_weights={"DE": 0.8, "DT": 0.85, "NT": 0.7, "OLB": 0.5},
)

# ============================================================================
# Special Teams Attributes
# ============================================================================

KICK_POWER = AttributeDefinition(
    name="kick_power",
    category=AttributeCategory.SPECIAL_TEAMS,
    abbreviation="KPW",
    description="Kicking distance",
    position_weights={"K": 0.9, "P": 0.8},
)

KICK_ACCURACY = AttributeDefinition(
    name="kick_accuracy",
    category=AttributeCategory.SPECIAL_TEAMS,
    abbreviation="KAC",
    description="Kicking precision",
    position_weights={"K": 0.95, "P": 0.7},
)

# ============================================================================
# Mental Attributes
# ============================================================================

AWARENESS = AttributeDefinition(
    name="awareness",
    category=AttributeCategory.MENTAL,
    abbreviation="AWR",
    description="Football IQ and instincts",
    position_weights={
        "QB": 0.95,
        "MLB": 0.85,
        "FS": 0.8,
        "C": 0.7,
        "SS": 0.7,
        "CB": 0.6,
    },
)

# ============================================================================
# Meta Attributes (The "Big Three" for Franchise Mode)
# ============================================================================

POTENTIAL = AttributeDefinition(
    name="potential",
    category=AttributeCategory.META,
    abbreviation="POT",
    description="The player's ceiling - maximum achievable overall rating",
    position_weights={},  # Not used in overall calculation - this IS the ceiling
)

LEARNING = AttributeDefinition(
    name="learning",
    category=AttributeCategory.META,
    abbreviation="LRN",
    description="How fast player learns plays (Unlearned -> Learned -> Mastered)",
    position_weights={
        # All positions benefit from learning, but some more critical
        "QB": 0.3,  # QBs need to master complex reads
        "C": 0.2,  # Centers make line calls
        "MLB": 0.2,  # Mike LBs make defensive calls
        "FS": 0.15,
    },
)

# ============================================================================
# Additional Rushing Attributes
# ============================================================================

BALL_CARRIER_VISION = AttributeDefinition(
    name="ball_carrier_vision",
    category=AttributeCategory.RUSHING,
    abbreviation="BCV",
    description="AI ability to find and hit the open hole/lane",
    position_weights={"RB": 0.8, "FB": 0.5, "QB": 0.3},
)

# ============================================================================
# Additional Special Teams Attributes
# ============================================================================

KICK_RETURN = AttributeDefinition(
    name="kick_return",
    category=AttributeCategory.SPECIAL_TEAMS,
    abbreviation="KR",
    description="Effectiveness at fielding and returning kicks/punts",
    position_weights={"WR": 0.2, "RB": 0.2, "CB": 0.2},
)

# ============================================================================
# Durability Attributes (Body Part Health for Wear & Tear System)
# ============================================================================

TOUGHNESS = AttributeDefinition(
    name="toughness",
    category=AttributeCategory.DURABILITY,
    abbreviation="TGH",
    description="Overall durability and pain tolerance",
    position_weights={},  # Affects all positions equally
)

# Individual body part durability (used for NFL HC09 style wear & tear)
# These represent the "baseline health" of each body part
# Lower values = more prone to injury in that area

HEAD_DURABILITY = AttributeDefinition(
    name="head_durability",
    category=AttributeCategory.DURABILITY,
    abbreviation="HDR",
    description="Head/neck injury resistance (concussion risk)",
    position_weights={},
)

TORSO_DURABILITY = AttributeDefinition(
    name="torso_durability",
    category=AttributeCategory.DURABILITY,
    abbreviation="TDR",
    description="Core/ribs injury resistance",
    position_weights={},
)

LEFT_ARM_DURABILITY = AttributeDefinition(
    name="left_arm_durability",
    category=AttributeCategory.DURABILITY,
    abbreviation="LAD",
    description="Left arm/shoulder injury resistance",
    position_weights={},
)

RIGHT_ARM_DURABILITY = AttributeDefinition(
    name="right_arm_durability",
    category=AttributeCategory.DURABILITY,
    abbreviation="RAD",
    description="Right arm/shoulder injury resistance",
    position_weights={},
)

LEFT_LEG_DURABILITY = AttributeDefinition(
    name="left_leg_durability",
    category=AttributeCategory.DURABILITY,
    abbreviation="LLD",
    description="Left leg/knee injury resistance",
    position_weights={},
)

RIGHT_LEG_DURABILITY = AttributeDefinition(
    name="right_leg_durability",
    category=AttributeCategory.DURABILITY,
    abbreviation="RLD",
    description="Right leg/knee injury resistance",
    position_weights={},
)

# ============================================================================
# All Attributes List
# ============================================================================

ALL_ATTRIBUTES: list[AttributeDefinition] = [
    # Meta (The Big Three for Franchise Mode)
    POTENTIAL,
    LEARNING,
    # Physical
    SPEED,
    ACCELERATION,
    AGILITY,
    STRENGTH,
    JUMPING,
    STAMINA,
    INJURY,
    # Passing
    THROW_POWER,
    THROW_ACCURACY_SHORT,
    THROW_ACCURACY_MED,
    THROW_ACCURACY_DEEP,
    THROW_ON_RUN,
    PLAY_ACTION,
    # Rushing
    CARRYING,
    TRUCKING,
    ELUSIVENESS,
    SPIN_MOVE,
    JUKE_MOVE,
    STIFF_ARM,
    BREAK_TACKLE,
    BALL_CARRIER_VISION,
    # Receiving
    CATCHING,
    CATCH_IN_TRAFFIC,
    SPECTACULAR_CATCH,
    ROUTE_RUNNING,
    RELEASE,
    # Blocking
    PASS_BLOCK,
    RUN_BLOCK,
    IMPACT_BLOCKING,
    # Defense
    TACKLE,
    HIT_POWER,
    BLOCK_SHEDDING,
    PURSUIT,
    PLAY_RECOGNITION,
    MAN_COVERAGE,
    ZONE_COVERAGE,
    PRESS,
    FINESSE_MOVES,
    POWER_MOVES,
    # Special Teams
    KICK_POWER,
    KICK_ACCURACY,
    KICK_RETURN,
    # Mental
    AWARENESS,
    # Durability (Wear & Tear System)
    TOUGHNESS,
    HEAD_DURABILITY,
    TORSO_DURABILITY,
    LEFT_ARM_DURABILITY,
    RIGHT_ARM_DURABILITY,
    LEFT_LEG_DURABILITY,
    RIGHT_LEG_DURABILITY,
]

"""
Scouting reports and grades.

Provides human-readable scouting reports with letter grades and
descriptive assessments.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional
from enum import Enum

from huddle.core.scouting.stages import ScoutingStage, get_attributes_for_stage
from huddle.core.scouting.projections import (
    PlayerProjection,
    ScoutingAccuracy,
    ScoutedAttribute,
)

if TYPE_CHECKING:
    from huddle.core.philosophy.evaluation import TeamPhilosophies


class ScoutingGrade(Enum):
    """
    Letter grades for scouted attributes.

    Maps to value ranges, with uncertainty factored in.
    """
    A_PLUS = "A+"  # Elite (90+)
    A = "A"  # Excellent (85-89)
    A_MINUS = "A-"  # Very Good (80-84)
    B_PLUS = "B+"  # Good (75-79)
    B = "B"  # Above Average (70-74)
    B_MINUS = "B-"  # Solid (65-69)
    C_PLUS = "C+"  # Average (60-64)
    C = "C"  # Below Average (55-59)
    C_MINUS = "C-"  # Weak (50-54)
    D = "D"  # Poor (40-49)
    F = "F"  # Very Poor (Below 40)
    UNKNOWN = "?"  # Not scouted


def value_to_grade(value: int, accuracy: ScoutingAccuracy) -> ScoutingGrade:
    """
    Convert a projected value to a letter grade.

    Low accuracy projections may show broader grade ranges.
    """
    # With exact accuracy, use precise grades
    if accuracy == ScoutingAccuracy.EXACT:
        if value >= 90:
            return ScoutingGrade.A_PLUS
        elif value >= 85:
            return ScoutingGrade.A
        elif value >= 80:
            return ScoutingGrade.A_MINUS
        elif value >= 75:
            return ScoutingGrade.B_PLUS
        elif value >= 70:
            return ScoutingGrade.B
        elif value >= 65:
            return ScoutingGrade.B_MINUS
        elif value >= 60:
            return ScoutingGrade.C_PLUS
        elif value >= 55:
            return ScoutingGrade.C
        elif value >= 50:
            return ScoutingGrade.C_MINUS
        elif value >= 40:
            return ScoutingGrade.D
        else:
            return ScoutingGrade.F

    # With lower accuracy, clamp to broader grades
    if accuracy == ScoutingAccuracy.LOW:
        # Very uncertain - only show broad categories
        if value >= 75:
            return ScoutingGrade.A_MINUS  # Could be anywhere in A range
        elif value >= 60:
            return ScoutingGrade.B  # Could be B+, B, or B-
        elif value >= 45:
            return ScoutingGrade.C  # Could be C+, C, or C-
        else:
            return ScoutingGrade.D

    elif accuracy == ScoutingAccuracy.MEDIUM:
        # Moderate - show +/- grades
        if value >= 88:
            return ScoutingGrade.A_PLUS
        elif value >= 82:
            return ScoutingGrade.A
        elif value >= 77:
            return ScoutingGrade.B_PLUS
        elif value >= 68:
            return ScoutingGrade.B
        elif value >= 58:
            return ScoutingGrade.C_PLUS
        elif value >= 48:
            return ScoutingGrade.C
        else:
            return ScoutingGrade.D

    else:  # HIGH accuracy
        # Pretty precise
        return value_to_grade(value, ScoutingAccuracy.EXACT)


def grade_to_range(grade: ScoutingGrade) -> tuple[int, int]:
    """
    Get the typical value range for a grade.

    Useful for displaying "B+ (75-79)" type info.
    """
    ranges = {
        ScoutingGrade.A_PLUS: (90, 99),
        ScoutingGrade.A: (85, 89),
        ScoutingGrade.A_MINUS: (80, 84),
        ScoutingGrade.B_PLUS: (75, 79),
        ScoutingGrade.B: (70, 74),
        ScoutingGrade.B_MINUS: (65, 69),
        ScoutingGrade.C_PLUS: (60, 64),
        ScoutingGrade.C: (55, 59),
        ScoutingGrade.C_MINUS: (50, 54),
        ScoutingGrade.D: (40, 49),
        ScoutingGrade.F: (0, 39),
        ScoutingGrade.UNKNOWN: (0, 99),
    }
    return ranges.get(grade, (0, 99))


@dataclass
class PlayerScoutingStatus:
    """
    Summary of a player's scouting status for a team.
    """
    player_id: str
    player_name: str
    position: str
    stage: ScoutingStage
    projected_overall: int
    overall_grade: ScoutingGrade
    scheme_fit: str  # "Perfect Fit", "Good Fit", etc.
    key_strengths: list[str] = field(default_factory=list)
    key_weaknesses: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)


@dataclass
class ScoutingReport:
    """
    Full scouting report on a player.

    Contains grades, assessments, and detailed attribute breakdowns.
    """
    player_id: str
    player_name: str
    position: str
    age: int
    stage: ScoutingStage

    # Overall assessment
    projected_overall: int
    overall_grade: ScoutingGrade
    overall_confidence: str  # "Low", "Medium", "High"

    # Scheme fit
    scheme_fit: str
    scheme_fit_delta: int  # +/- from generic OVR

    # Attribute grades by category
    physical_grades: dict[str, ScoutingGrade] = field(default_factory=dict)
    skill_grades: dict[str, ScoutingGrade] = field(default_factory=dict)
    mental_grades: dict[str, ScoutingGrade] = field(default_factory=dict)

    # Narrative assessment
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    comparison: str = ""  # "Plays like a young..."

    # Projection
    ceiling_grade: ScoutingGrade = ScoutingGrade.UNKNOWN
    floor_grade: ScoutingGrade = ScoutingGrade.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "age": self.age,
            "stage": self.stage.name,
            "projected_overall": self.projected_overall,
            "overall_grade": self.overall_grade.value,
            "overall_confidence": self.overall_confidence,
            "scheme_fit": self.scheme_fit,
            "scheme_fit_delta": self.scheme_fit_delta,
            "physical_grades": {k: v.value for k, v in self.physical_grades.items()},
            "skill_grades": {k: v.value for k, v in self.skill_grades.items()},
            "mental_grades": {k: v.value for k, v in self.mental_grades.items()},
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "red_flags": self.red_flags,
            "comparison": self.comparison,
            "ceiling_grade": self.ceiling_grade.value,
            "floor_grade": self.floor_grade.value,
        }


# Attribute category mappings for report organization
PHYSICAL_ATTRIBUTES = [
    "speed", "acceleration", "agility", "strength", "jumping", "stamina",
]

SKILL_ATTRIBUTES = [
    # Passing
    "throw_power", "throw_accuracy_short", "throw_accuracy_med",
    "throw_accuracy_deep", "throw_on_run", "play_action",
    # Rushing
    "carrying", "trucking", "elusiveness", "spin_move", "juke_move",
    "stiff_arm", "break_tackle", "ball_carrier_vision",
    # Receiving
    "catching", "catch_in_traffic", "spectacular_catch", "route_running", "release",
    # Blocking
    "pass_block", "run_block", "impact_blocking",
    # Defense
    "tackle", "hit_power", "block_shedding", "pursuit", "man_coverage",
    "zone_coverage", "press", "finesse_moves", "power_moves",
    # Special
    "kick_power", "kick_accuracy",
]

MENTAL_ATTRIBUTES = [
    "awareness", "play_recognition", "learning",
]


def create_scouting_report(
    projection: PlayerProjection,
    player_name: str,
    position: str,
    age: int,
    team_philosophies: Optional["TeamPhilosophies"] = None,
) -> ScoutingReport:
    """
    Create a full scouting report from a player projection.

    Args:
        projection: The team's projection of the player
        player_name: Player's name
        position: Player's position
        age: Player's age
        team_philosophies: Team's evaluation philosophies (for scheme fit)

    Returns:
        Complete ScoutingReport
    """
    # Calculate projected overall from visible attributes
    visible_attrs = get_attributes_for_stage(projection.scouting_stage)

    total_value = 0
    count = 0
    for attr_name in visible_attrs:
        if attr_name in projection.attributes:
            total_value += projection.attributes[attr_name].projected_value
            count += 1

    projected_overall = int(total_value / count) if count > 0 else 50

    # Determine overall confidence based on stage
    confidence_map = {
        ScoutingStage.UNKNOWN: "Very Low",
        ScoutingStage.BASIC: "Low",
        ScoutingStage.INTERMEDIATE: "Medium",
        ScoutingStage.ADVANCED: "High",
        ScoutingStage.COMPLETE: "Very High",
    }
    overall_confidence = confidence_map.get(projection.scouting_stage, "Low")

    # Calculate scheme fit if philosophies provided
    scheme_fit = "Unknown"
    scheme_fit_delta = 0
    if team_philosophies:
        from huddle.core.philosophy.evaluation import (
            calculate_philosophy_difference,
            get_scheme_fit_label,
        )
        from huddle.core.attributes.registry import PlayerAttributes

        # Build attributes from projections
        attrs = PlayerAttributes()
        for name, scouted in projection.attributes.items():
            attrs.set(name, scouted.projected_value)

        scheme_fit_delta = calculate_philosophy_difference(
            attrs, position, team_philosophies
        )
        scheme_fit = get_scheme_fit_label(scheme_fit_delta)

    # Grade overall
    # Use average accuracy of all scouted attributes
    avg_accuracy = ScoutingAccuracy.LOW
    if projection.scouting_stage == ScoutingStage.COMPLETE:
        avg_accuracy = ScoutingAccuracy.EXACT
    elif projection.scouting_stage == ScoutingStage.ADVANCED:
        avg_accuracy = ScoutingAccuracy.HIGH
    elif projection.scouting_stage == ScoutingStage.INTERMEDIATE:
        avg_accuracy = ScoutingAccuracy.MEDIUM

    overall_grade = value_to_grade(projected_overall, avg_accuracy)

    # Build attribute grades by category
    physical_grades = {}
    skill_grades = {}
    mental_grades = {}

    for attr_name in visible_attrs:
        if attr_name not in projection.attributes:
            continue
        scouted = projection.attributes[attr_name]
        grade = value_to_grade(scouted.projected_value, scouted.accuracy)

        if attr_name in PHYSICAL_ATTRIBUTES:
            physical_grades[attr_name] = grade
        elif attr_name in SKILL_ATTRIBUTES:
            skill_grades[attr_name] = grade
        elif attr_name in MENTAL_ATTRIBUTES:
            mental_grades[attr_name] = grade

    # Identify strengths and weaknesses
    strengths = []
    weaknesses = []
    red_flags = []

    for attr_name, scouted in projection.attributes.items():
        grade = value_to_grade(scouted.projected_value, scouted.accuracy)
        if grade in (ScoutingGrade.A_PLUS, ScoutingGrade.A):
            strengths.append(_attr_to_readable(attr_name))
        elif grade in (ScoutingGrade.D, ScoutingGrade.F):
            weaknesses.append(_attr_to_readable(attr_name))

        # Red flags for concerning attributes
        if attr_name == "injury" and scouted.projected_value < 60:
            red_flags.append("Injury concerns")
        if attr_name == "learning" and scouted.projected_value < 50:
            red_flags.append("Slow learner")

    # Ceiling/floor based on potential if known
    ceiling_grade = ScoutingGrade.UNKNOWN
    floor_grade = ScoutingGrade.UNKNOWN
    if "potential" in projection.attributes:
        pot = projection.attributes["potential"]
        if pot.is_revealed or pot.accuracy in (ScoutingAccuracy.HIGH, ScoutingAccuracy.EXACT):
            ceiling_grade = value_to_grade(pot.projected_value, pot.accuracy)
            # Floor is current OVR minus some delta
            floor_value = max(40, projected_overall - 10)
            floor_grade = value_to_grade(floor_value, avg_accuracy)

    return ScoutingReport(
        player_id=projection.player_id,
        player_name=player_name,
        position=position,
        age=age,
        stage=projection.scouting_stage,
        projected_overall=projected_overall,
        overall_grade=overall_grade,
        overall_confidence=overall_confidence,
        scheme_fit=scheme_fit,
        scheme_fit_delta=scheme_fit_delta,
        physical_grades=physical_grades,
        skill_grades=skill_grades,
        mental_grades=mental_grades,
        strengths=strengths[:5],  # Top 5
        weaknesses=weaknesses[:3],  # Top 3
        red_flags=red_flags,
        ceiling_grade=ceiling_grade,
        floor_grade=floor_grade,
    )


def _attr_to_readable(attr_name: str) -> str:
    """Convert attribute name to readable format."""
    readable_map = {
        "throw_power": "Arm Strength",
        "throw_accuracy_short": "Short Accuracy",
        "throw_accuracy_med": "Medium Accuracy",
        "throw_accuracy_deep": "Deep Accuracy",
        "throw_on_run": "Throw on the Run",
        "play_action": "Play Action",
        "ball_carrier_vision": "Vision",
        "catch_in_traffic": "Contested Catches",
        "spectacular_catch": "Spectacular Catch",
        "route_running": "Route Running",
        "pass_block": "Pass Protection",
        "run_block": "Run Blocking",
        "impact_blocking": "Impact Blocking",
        "hit_power": "Hit Power",
        "block_shedding": "Block Shedding",
        "play_recognition": "Play Recognition",
        "man_coverage": "Man Coverage",
        "zone_coverage": "Zone Coverage",
        "finesse_moves": "Finesse Pass Rush",
        "power_moves": "Power Pass Rush",
        "kick_power": "Leg Strength",
        "kick_accuracy": "Accuracy",
    }
    if attr_name in readable_map:
        return readable_map[attr_name]
    return attr_name.replace("_", " ").title()

"""
Scouting System.

Implements a fog-of-war system for player attributes where true values
are hidden until revealed through scouting. Scouting progresses through
stages, revealing more accurate information at each level.

Key concepts:
- True attributes are hidden from teams that haven't scouted
- Teams see "projected" values with uncertainty ranges
- Scout quality affects projection accuracy
- Multiple scouting stages reveal more attributes
- Team philosophies affect how valuable scouting intel is

Inspired by NFL Head Coach 09's scouting system.
"""

from huddle.core.scouting.projections import (
    ScoutingAccuracy,
    ScoutedAttribute,
    PlayerProjection,
    generate_initial_projection,
    refine_projection,
    reveal_attribute,
)

from huddle.core.scouting.stages import (
    ScoutingStage,
    ScoutingLevel,
    STAGE_REQUIREMENTS,
    get_attributes_for_stage,
    calculate_scouting_cost,
    get_next_stage,
)

from huddle.core.scouting.report import (
    ScoutingReport,
    ScoutingGrade,
    PlayerScoutingStatus,
    create_scouting_report,
    grade_to_range,
)

from huddle.core.scouting.staff import (
    Scout,
    ScoutSpecialty,
    ScoutingDepartment,
    SPECIALTY_POSITIONS,
)

__all__ = [
    # Projections
    "ScoutingAccuracy",
    "ScoutedAttribute",
    "PlayerProjection",
    "generate_initial_projection",
    "refine_projection",
    "reveal_attribute",
    # Stages
    "ScoutingStage",
    "ScoutingLevel",
    "STAGE_REQUIREMENTS",
    "get_attributes_for_stage",
    "calculate_scouting_cost",
    "get_next_stage",
    # Reports
    "ScoutingReport",
    "ScoutingGrade",
    "PlayerScoutingStatus",
    "create_scouting_report",
    "grade_to_range",
    # Staff
    "Scout",
    "ScoutSpecialty",
    "ScoutingDepartment",
    "SPECIALTY_POSITIONS",
]

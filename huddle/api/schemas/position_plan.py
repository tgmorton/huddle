"""
Pydantic schemas for Position Planning API.

Frontend-friendly format for displaying:
- Current roster by position
- Draft prospects ranked
- FA options ranked
- GM's acquisition plan for each position
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum


class AcquisitionPath(str, Enum):
    """How the GM plans to fill a position."""
    KEEP_CURRENT = "keep_current"
    FREE_AGENCY = "free_agency"
    DRAFT_EARLY = "draft_early"
    DRAFT_MID = "draft_mid"
    DRAFT_LATE = "draft_late"
    TRADE = "trade"
    UNDECIDED = "undecided"


class CurrentPlayer(BaseModel):
    """Current roster player at a position."""
    player_id: str
    name: str
    overall: int
    age: int
    contract_years_remaining: int = 1
    salary: int = 0  # In thousands


class DraftProspectOption(BaseModel):
    """A draft prospect option for a position."""
    player_id: str
    name: str
    position: str
    grade: float = Field(..., description="Scout grade 0-100")
    projected_round: int
    projected_pick: int
    is_reachable: bool = Field(..., description="Can team realistically get them")
    scheme_fit: float = Field(0.5, description="Fit with team's scheme 0-1")


class FAOption(BaseModel):
    """A free agent option for a position."""
    player_id: str
    name: str
    position: str
    overall: int
    age: int
    asking_price: int  # In thousands
    market_value: int  # Fair market value in thousands
    personality: str = "agreeable"
    is_upgrade: bool = Field(..., description="Better than current starter")
    upgrade_amount: int = Field(0, description="OVR difference from current")


class PositionPlanItem(BaseModel):
    """Complete plan for a single position."""
    position: str
    side: str = Field(..., description="'offense' or 'defense'")

    # Need assessment
    need_score: float = Field(..., ge=0, le=1, description="0=no need, 1=critical")
    need_description: str = Field("", description="Human readable need level")

    # Current roster
    current_starter: Optional[CurrentPlayer] = None
    depth_count: int = 0

    # Options
    draft_options: List[DraftProspectOption] = []
    fa_options: List[FAOption] = []

    # GM's decision
    acquisition_path: AcquisitionPath
    target_player_id: Optional[str] = None
    target_player_name: Optional[str] = None

    # Reasoning
    reasoning: str = Field("", description="Why this path was chosen")


class DraftPick(BaseModel):
    """A team's draft pick."""
    round: int
    pick: int  # Overall pick number
    is_own: bool = True  # True if team's own pick, False if acquired via trade
    acquired_from: Optional[str] = None  # Team name if traded for
    allocated_to: Optional[str] = None  # Position it's been allocated to


class MockDraftPick(BaseModel):
    """A predicted pick in the mock draft."""
    pick_number: int
    round: int
    team_name: str
    player_name: str
    position: str
    grade: float
    is_user_pick: bool = False  # Highlight user's picks
    reasoning: str = ""  # Why this team took this player


class OffseasonPlanSummary(BaseModel):
    """Summary of the team's offseason priorities."""
    fa_targets: List[Dict] = Field(..., description="Ranked FA targets")
    draft_board: List[DraftProspectOption] = Field(..., description="Team's draft board")
    total_fa_budget: int = Field(0, description="Cap allocated to FA")
    positions_addressed_in_draft: List[str] = []
    positions_addressed_in_fa: List[str] = []
    # Pick inventory
    draft_picks: List[DraftPick] = Field(default_factory=list, description="Team's draft picks")
    # Mock draft prediction
    mock_draft: List[MockDraftPick] = Field(default_factory=list, description="Predicted first round picks")


class TeamPositionPlan(BaseModel):
    """Complete position plan for a team."""
    team_id: str
    team_name: str

    # Team context
    gm_archetype: str
    gm_archetype_description: str
    draft_position: int
    cap_room: int

    # Position-by-position breakdown
    offense: List[PositionPlanItem]
    defense: List[PositionPlanItem]

    # Summary
    summary: OffseasonPlanSummary


class CreatePlanRequest(BaseModel):
    """Request to create/update a position plan."""
    team_id: str
    # Optional overrides
    gm_archetype: Optional[str] = None
    draft_position: Optional[int] = None
    cap_room: Optional[int] = None
    # Pick inventory (if not provided, generates default 7 picks)
    draft_picks: Optional[List[DraftPick]] = None


class UpdatePlanDecisionRequest(BaseModel):
    """Request to manually override a position decision."""
    position: str
    new_path: AcquisitionPath
    target_player_id: Optional[str] = None


# Response helpers for need descriptions
NEED_DESCRIPTIONS = {
    (0.0, 0.2): "No need - position is locked down",
    (0.2, 0.4): "Low need - solid but could upgrade",
    (0.4, 0.6): "Moderate need - looking for improvement",
    (0.6, 0.8): "High need - priority to address",
    (0.8, 1.0): "Critical need - must address immediately",
}


def get_need_description(score: float) -> str:
    """Get human-readable need description."""
    for (low, high), desc in NEED_DESCRIPTIONS.items():
        if low <= score < high:
            return desc
    return "Critical need - must address immediately"


# Path reasoning templates
PATH_REASONING = {
    AcquisitionPath.KEEP_CURRENT: "Current starter is performing well, no action needed.",
    AcquisitionPath.DRAFT_EARLY: "Elite prospect available within draft range - best value option.",
    AcquisitionPath.DRAFT_MID: "Solid prospect available in mid rounds - good value.",
    AcquisitionPath.DRAFT_LATE: "Depth option available in late rounds.",
    AcquisitionPath.FREE_AGENCY: "Best option to fill this need is in free agency.",
    AcquisitionPath.UNDECIDED: "Still evaluating options - no clear best path yet.",
    AcquisitionPath.TRADE: "Exploring trade options to acquire proven talent.",
}


def get_path_reasoning(
    path: AcquisitionPath,
    draft_grade: Optional[float] = None,
    fa_overall: Optional[int] = None,
    current_overall: Optional[int] = None,
    gm_archetype: str = "balanced",
) -> str:
    """Generate reasoning for the chosen path."""
    base = PATH_REASONING.get(path, "")

    if path == AcquisitionPath.DRAFT_EARLY and draft_grade:
        return f"Elite prospect (Grade {draft_grade:.0f}) available - rookie contract provides excellent value."

    if path == AcquisitionPath.FREE_AGENCY and fa_overall and current_overall:
        upgrade = fa_overall - current_overall
        return f"FA upgrade of +{upgrade} OVR available. Best path to immediate improvement."

    if path == AcquisitionPath.KEEP_CURRENT and current_overall:
        if current_overall >= 85:
            return f"Starter rated {current_overall} OVR - among the best at the position."
        else:
            return f"Current starter adequate ({current_overall} OVR) - resources better spent elsewhere."

    return base

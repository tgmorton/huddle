"""
Position Plan API Router.

Endpoints for viewing and managing team offseason plans.
This is the HC09-style holistic team building interface.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from uuid import UUID, uuid4

from huddle.api.schemas.position_plan import (
    TeamPositionPlan,
    PositionPlanItem,
    CurrentPlayer,
    DraftProspectOption,
    DraftPick,
    MockDraftPick,
    FAOption,
    OffseasonPlanSummary,
    AcquisitionPath,
    CreatePlanRequest,
    UpdatePlanDecisionRequest,
    get_need_description,
    get_path_reasoning,
)
from huddle.core.ai.position_planner import (
    create_position_plan,
    DraftProspect,
    AcquisitionPath as CoreAcquisitionPath,
)
from huddle.core.ai.gm_archetypes import (
    GMArchetype,
    get_gm_profile,
    GM_PROFILES,
)
from huddle.core.ai.allocation_tables import (
    get_rookie_premium,
    should_draft_position,
    get_position_priority,
)


# Map specific positions to research position groups
POSITION_TO_GROUP = {
    # Offense
    "QB": ("QB", "offense"),
    "RB": ("RB", "offense"),
    "WR": ("WR", "offense"),
    "TE": ("TE", "offense"),
    "LT": ("OL", "offense"),
    "LG": ("OL", "offense"),
    "C": ("OL", "offense"),
    "RG": ("OL", "offense"),
    "RT": ("OL", "offense"),
    # Defense
    "DE": ("EDGE", "defense"),
    "DT": ("DL", "defense"),
    "OLB": ("LB", "defense"),
    "ILB": ("LB", "defense"),
    "CB": ("CB", "defense"),
    "FS": ("S", "defense"),
    "SS": ("S", "defense"),
}


router = APIRouter(prefix="/position-plan", tags=["position-plan"])

# In-memory storage for plans (would be persisted in real app)
_plans: dict[str, dict] = {}


# GM archetype descriptions for frontend
GM_DESCRIPTIONS = {
    "analytics": "Data-driven decision maker. Values rookie contracts and optimal allocation.",
    "old_school": "Traditional approach. Prefers proven veterans and values 'premium' positions.",
    "cap_wizard": "Cap efficiency expert. Maximizes value through smart contracts and draft picks.",
    "win_now": "Championship focused. Willing to pay premium for immediate impact.",
    "balanced": "Balanced approach. Weighs all factors equally.",
}


@router.get("/{team_id}", response_model=TeamPositionPlan)
async def get_position_plan(team_id: str):
    """
    Get the complete position plan for a team.

    Shows for each position:
    - Current roster player
    - Best draft options
    - Best FA options
    - GM's chosen acquisition path
    """
    if team_id not in _plans:
        raise HTTPException(status_code=404, detail="Plan not found. Create one first.")

    return _plans[team_id]


@router.post("/{team_id}", response_model=TeamPositionPlan)
async def create_or_update_plan(team_id: str, request: CreatePlanRequest):
    """
    Create or update a position plan for a team.

    This generates the full HC09-style breakdown:
    - Assesses every position's need level
    - Evaluates draft and FA options
    - Recommends acquisition path for each
    """
    # For demo, use sample data (in real app, would fetch from franchise)
    plan_data = _generate_sample_plan(
        team_id=team_id,
        gm_archetype=request.gm_archetype or "analytics",
        draft_position=request.draft_position or 10,
        cap_room=request.cap_room or 50000,
    )

    _plans[team_id] = plan_data
    return plan_data


@router.patch("/{team_id}/position/{position}")
async def update_position_decision(
    team_id: str,
    position: str,
    request: UpdatePlanDecisionRequest,
):
    """
    Manually override the GM's decision for a position.

    Allows user to say "I want to draft CB instead of signing in FA".
    """
    if team_id not in _plans:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = _plans[team_id]

    # Find the position in offense or defense
    for section in [plan["offense"], plan["defense"]]:
        for item in section:
            if item["position"] == position.upper():
                item["acquisition_path"] = request.new_path
                item["target_player_id"] = request.target_player_id
                item["reasoning"] = "Manually overridden by user."
                return {"status": "updated", "position": position}

    raise HTTPException(status_code=404, detail=f"Position {position} not found")


@router.get("/{team_id}/fa-targets", response_model=List[dict])
async def get_fa_targets(team_id: str):
    """Get the team's prioritized FA targets."""
    if team_id not in _plans:
        raise HTTPException(status_code=404, detail="Plan not found")

    return _plans[team_id]["summary"]["fa_targets"]


@router.get("/{team_id}/draft-board", response_model=List[DraftProspectOption])
async def get_draft_board(team_id: str):
    """Get the team's draft board."""
    if team_id not in _plans:
        raise HTTPException(status_code=404, detail="Plan not found")

    return _plans[team_id]["summary"]["draft_board"]


def _generate_sample_plan(
    team_id: str,
    gm_archetype: str,
    draft_position: int,
    cap_room: int,
    draft_picks: Optional[List[DraftPick]] = None,
) -> dict:
    """Generate a sample plan (demo data).

    Key insight: Team can only draft at positions for which they have picks.
    Uses two-pass approach:
    1. Score each position's draft value
    2. Allocate limited picks to highest-value opportunities
    3. Remaining positions fall back to FA or keep current
    """

    # Generate default pick inventory if not provided
    if draft_picks is None:
        draft_picks = [
            DraftPick(round=1, pick=draft_position),
            DraftPick(round=2, pick=draft_position + 32),
            DraftPick(round=3, pick=draft_position + 64),
            DraftPick(round=4, pick=draft_position + 100),
            DraftPick(round=5, pick=draft_position + 135),
            DraftPick(round=6, pick=draft_position + 175),
            DraftPick(round=7, pick=draft_position + 215),
        ]

    # Sample roster
    roster_data = {
        "QB": {"name": "Tyson Bagent", "overall": 68, "age": 24, "depth": 2},
        "RB": {"name": "Khalil Herbert", "overall": 78, "age": 25, "depth": 3},
        "WR": {"name": "DJ Moore", "overall": 89, "age": 26, "depth": 4},
        "TE": {"name": "Cole Kmet", "overall": 82, "age": 25, "depth": 2},
        "LT": {"name": "Braxton Jones", "overall": 72, "age": 24, "depth": 2},
        "LG": {"name": "Cody Whitehair", "overall": 70, "age": 31, "depth": 2},
        "C": {"name": "Doug Kramer", "overall": 75, "age": 26, "depth": 2},
        "RG": {"name": "Nate Davis", "overall": 71, "age": 27, "depth": 2},
        "RT": {"name": "Darnell Wright", "overall": 79, "age": 23, "depth": 2},
        "DE": {"name": "Montez Sweat", "overall": 88, "age": 27, "depth": 3},
        "DT": {"name": "Justin Jones", "overall": 80, "age": 28, "depth": 3},
        "OLB": {"name": "Tremaine Edmunds", "overall": 82, "age": 25, "depth": 3},
        "ILB": {"name": "TJ Edwards", "overall": 79, "age": 27, "depth": 2},
        "CB": {"name": "Jaylon Johnson", "overall": 84, "age": 24, "depth": 4},
        "FS": {"name": "Eddie Jackson", "overall": 77, "age": 30, "depth": 2},
        "SS": {"name": "Jaquan Brisker", "overall": 81, "age": 24, "depth": 2},
    }

    # Sample draft class
    draft_prospects = [
        {"name": "Caleb Williams", "position": "QB", "grade": 96, "round": 1, "pick": 1},
        {"name": "Jayden Daniels", "position": "QB", "grade": 91, "round": 1, "pick": 2},
        {"name": "Drake Maye", "position": "QB", "grade": 88, "round": 1, "pick": 3},
        {"name": "Marvin Harrison Jr", "position": "WR", "grade": 94, "round": 1, "pick": 4},
        {"name": "Joe Alt", "position": "LT", "grade": 92, "round": 1, "pick": 5},
        {"name": "Malik Nabers", "position": "WR", "grade": 90, "round": 1, "pick": 6},
        {"name": "JC Latham", "position": "RT", "grade": 88, "round": 1, "pick": 7},
        {"name": "Byron Murphy II", "position": "DT", "grade": 89, "round": 1, "pick": 8},
        {"name": "Rome Odunze", "position": "WR", "grade": 87, "round": 1, "pick": 9},
        {"name": "Laiatu Latu", "position": "DE", "grade": 87, "round": 1, "pick": 10},
        {"name": "Dallas Turner", "position": "OLB", "grade": 86, "round": 1, "pick": 11},
        {"name": "Olu Fashanu", "position": "LT", "grade": 85, "round": 1, "pick": 12},
        {"name": "Brock Bowers", "position": "TE", "grade": 91, "round": 1, "pick": 13},
        {"name": "Quinyon Mitchell", "position": "CB", "grade": 85, "round": 1, "pick": 15},
        {"name": "Taliese Fuaga", "position": "LG", "grade": 82, "round": 1, "pick": 20},
        {"name": "Kool-Aid McKinstry", "position": "CB", "grade": 82, "round": 2, "pick": 38},
        {"name": "Jonathon Brooks", "position": "RB", "grade": 83, "round": 2, "pick": 40},
        {"name": "Payton Wilson", "position": "ILB", "grade": 80, "round": 2, "pick": 45},
        {"name": "Tyler Nubin", "position": "FS", "grade": 79, "round": 3, "pick": 70},
        {"name": "Blake Corum", "position": "RB", "grade": 78, "round": 3, "pick": 75},
    ]

    # Sample FA market
    fa_market = [
        {"name": "Kirk Cousins", "position": "QB", "overall": 83, "age": 35, "asking": 45000},
        {"name": "Russell Wilson", "position": "QB", "overall": 79, "age": 35, "asking": 25000},
        {"name": "Saquon Barkley", "position": "RB", "overall": 89, "age": 27, "asking": 14000},
        {"name": "Derrick Henry", "position": "RB", "overall": 88, "age": 30, "asking": 12000},
        {"name": "Mike Evans", "position": "WR", "overall": 88, "age": 30, "asking": 22000},
        {"name": "Jonah Williams", "position": "LT", "overall": 79, "age": 26, "asking": 12000},
        {"name": "Robert Hunt", "position": "RG", "overall": 81, "age": 27, "asking": 14000},
        {"name": "Matt Feiler", "position": "LG", "overall": 76, "age": 32, "asking": 6000},
        {"name": "Danielle Hunter", "position": "DE", "overall": 86, "age": 29, "asking": 20000},
        {"name": "Stephon Gilmore", "position": "CB", "overall": 80, "age": 33, "asking": 8000},
        {"name": "Justin Simmons", "position": "FS", "overall": 84, "age": 30, "asking": 10000},
        {"name": "LVE", "position": "ILB", "overall": 78, "age": 28, "asking": 7000},
    ]

    # =========================================================================
    # MOCK DRAFT: Simulate other teams' picks to predict availability
    # =========================================================================
    # Other teams and their primary needs (simplified)
    # This list excludes the user's team - their pick is inserted based on draft_position
    all_other_teams = [
        {"pick": 1, "name": "Washington Commanders", "needs": ["QB", "WR", "CB"], "has_qb": False},
        {"pick": 2, "name": "New England Patriots", "needs": ["QB", "WR", "OLB"], "has_qb": False},
        {"pick": 3, "name": "Arizona Cardinals", "needs": ["WR", "OLB", "CB"], "has_qb": True},
        {"pick": 4, "name": "Los Angeles Chargers", "needs": ["LT", "WR", "DT"], "has_qb": True},
        {"pick": 5, "name": "New York Giants", "needs": ["WR", "LT", "CB"], "has_qb": True},
        {"pick": 6, "name": "Tennessee Titans", "needs": ["LT", "RT", "WR"], "has_qb": True},
        {"pick": 7, "name": "Atlanta Falcons", "needs": ["DT", "DE", "CB"], "has_qb": True},
        {"pick": 8, "name": "New York Jets", "needs": ["LT", "WR", "DE"], "has_qb": True},
        {"pick": 9, "name": "Minnesota Vikings", "needs": ["QB", "OLB", "CB"], "has_qb": False},
        {"pick": 10, "name": "Denver Broncos", "needs": ["LT", "CB", "WR"], "has_qb": True},
        {"pick": 11, "name": "Las Vegas Raiders", "needs": ["TE", "WR", "CB"], "has_qb": True},
        {"pick": 12, "name": "New Orleans Saints", "needs": ["QB", "WR", "DT"], "has_qb": False},
        {"pick": 13, "name": "Indianapolis Colts", "needs": ["CB", "WR", "DE"], "has_qb": True},
        {"pick": 14, "name": "Seattle Seahawks", "needs": ["DT", "OLB", "CB"], "has_qb": True},
        {"pick": 15, "name": "Jacksonville Jaguars", "needs": ["CB", "OLB", "WR"], "has_qb": True},
        {"pick": 16, "name": "Houston Texans", "needs": ["DE", "CB", "LB"], "has_qb": True},
    ]

    # Build mock draft order - insert user's team at their pick position
    other_teams = []
    for team in all_other_teams:
        if team["pick"] < draft_position:
            other_teams.append(team)
        elif team["pick"] >= draft_position:
            # Shift other teams' picks down by 1
            other_teams.append({**team, "pick": team["pick"] + 1})

    # Insert user's team at their draft position
    other_teams.append({
        "pick": draft_position,
        "name": "Chicago Bears",
        "needs": ["QB", "WR", "LT"],  # Based on roster_data
        "has_qb": roster_data["QB"]["overall"] < 75
    })

    def run_mock_draft(
        prospects: List[dict],
        teams: List[dict],
        user_pick: int,
        user_team_name: str = "Chicago Bears",
    ) -> tuple[List[MockDraftPick], set, str]:
        """Run a mock draft and return picks + set of taken player names + user's projected pick."""
        available = prospects.copy()
        mock_picks = []
        taken_before_user = set()  # Only players taken BEFORE user's pick
        user_projected_player = None

        for team in sorted(teams, key=lambda t: t["pick"]):
            if not available:
                break

            is_user = team["name"] == user_team_name

            # Find best available player matching team needs
            best_player = None
            reasoning = ""

            for need_pos in team["needs"]:
                candidates = [p for p in available if p["position"] == need_pos]
                if candidates:
                    best_player = max(candidates, key=lambda p: p["grade"])
                    reasoning = f"Fills {need_pos} need with BPA"
                    break

            # If no need matches, take BPA
            if not best_player and available:
                best_player = max(available, key=lambda p: p["grade"])
                reasoning = "Best player available"

            if best_player:
                mock_picks.append(MockDraftPick(
                    pick_number=team["pick"],
                    round=1,
                    team_name=team["name"],
                    player_name=best_player["name"],
                    position=best_player["position"],
                    grade=best_player["grade"],
                    is_user_pick=is_user,
                    reasoning=reasoning,
                ))

                if is_user:
                    user_projected_player = best_player["name"]
                else:
                    # Only add to "taken" if picked by other teams
                    taken_before_user.add(best_player["name"])

                available = [p for p in available if p["name"] != best_player["name"]]

        return mock_picks, taken_before_user, user_projected_player

    # Run mock draft to see who's available
    first_round_prospects = [p for p in draft_prospects if p["round"] == 1]
    mock_draft_results, taken_in_mock, user_mock_pick = run_mock_draft(
        first_round_prospects,
        other_teams,
        user_pick=draft_position,
        user_team_name="Chicago Bears",
    )

    # The mock draft tells us who the team SHOULD draft
    # This informs the position planning

    # Build position items
    offense_positions = ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT"]
    defense_positions = ["DE", "DT", "OLB", "ILB", "CB", "FS", "SS"]

    # =========================================================================
    # PASS 1: Collect position data and calculate draft value scores
    # =========================================================================
    position_data = {}  # pos -> {need, roster, draft_opts, fa_opts, best_draft, best_fa, draft_value}

    for pos in offense_positions + defense_positions:
        roster = roster_data.get(pos, {"name": "Unknown", "overall": 65, "age": 25, "depth": 1})
        side = "offense" if pos in offense_positions else "defense"

        # Calculate need
        ovr = roster["overall"]
        if ovr >= 85:
            need = 0.1
        elif ovr >= 80:
            need = 0.3
        elif ovr >= 75:
            need = 0.5
        elif ovr >= 70:
            need = 0.7
        else:
            need = 0.9

        # Find best draft option
        pos_prospects = [p for p in draft_prospects if p["position"] == pos]
        draft_opts = []
        for p in pos_prospects[:3]:
            # Check if player is predicted to be taken before our pick
            # taken_in_mock only contains players taken by OTHER teams before our pick
            is_taken = p["name"] in taken_in_mock
            reachable = p["pick"] <= draft_position + 15 and not is_taken
            draft_opts.append(DraftProspectOption(
                player_id=str(uuid4()),
                name=p["name"],
                position=p["position"],
                grade=p["grade"],
                projected_round=p["round"],
                projected_pick=p["pick"],
                is_reachable=reachable,
            ))

        # Find best FA option
        pos_fas = [f for f in fa_market if f["position"] == pos]
        fa_opts = []
        for f in pos_fas[:3]:
            upgrade = f["overall"] - ovr
            fa_opts.append(FAOption(
                player_id=str(uuid4()),
                name=f["name"],
                position=f["position"],
                overall=f["overall"],
                age=f["age"],
                asking_price=f["asking"],
                market_value=int(f["asking"] * 0.9),
                is_upgrade=upgrade > 0,
                upgrade_amount=max(0, upgrade),
            ))

        # Find best REACHABLE draft option (not just first in list)
        reachable_drafts = [d for d in draft_opts if d.is_reachable]
        best_draft = reachable_drafts[0] if reachable_drafts else None
        best_fa = fa_opts[0] if fa_opts else None

        # Calculate draft value score (used for pick allocation)
        # Higher = more valuable to use a pick here
        draft_value = 0.0
        preferred_round = None
        if best_draft and need >= 0.3:
            # Get research-backed rookie premium for this position
            group, group_side = POSITION_TO_GROUP.get(pos, (pos, side))
            rookie_premium_data = get_rookie_premium(group, group_side)
            rookie_multiplier = rookie_premium_data.get('value_multiplier', 1.0)

            # Get GM archetype adjustment for this position
            gm_profile = get_gm_profile(GMArchetype(gm_archetype))
            gm_position_adj = gm_profile.position_adjustments.get(pos, 1.0)
            gm_rookie_pref = gm_profile.rookie_premium  # How much GM values rookie deals

            # Value = need * prospect_grade * rookie_premium * GM_adjustments
            base_value = need * (best_draft.grade / 100)
            draft_value = base_value * rookie_multiplier * gm_rookie_pref * gm_position_adj

            # Check if research says this position is good to draft
            is_draft_position = should_draft_position(group, group_side)
            if not is_draft_position:
                draft_value *= 0.7  # Reduce value if research says sign in FA

            if best_fa and best_fa.is_upgrade:
                # Reduce value if FA is also good (less urgency to draft)
                fa_value = (best_fa.overall / 100) * 0.85
                draft_value = draft_value - fa_value * 0.3

            # Determine which round pick this needs
            if best_draft.projected_round == 1:
                preferred_round = 1
            elif best_draft.projected_round == 2:
                preferred_round = 2
            elif best_draft.projected_round <= 4:
                preferred_round = 3  # "mid rounds"
            else:
                preferred_round = 5  # "late rounds"

        position_data[pos] = {
            "side": side,
            "need": need,
            "roster": roster,
            "draft_opts": draft_opts,
            "fa_opts": fa_opts,
            "best_draft": best_draft,
            "best_fa": best_fa,
            "draft_value": draft_value,
            "preferred_round": preferred_round,
        }

    # =========================================================================
    # PASS 2: Allocate picks to highest-value positions
    # =========================================================================
    # Group picks by round tier
    early_picks = [p for p in draft_picks if p.round == 1]  # Round 1
    mid_picks = [p for p in draft_picks if p.round in (2, 3, 4)]  # Rounds 2-4
    late_picks = [p for p in draft_picks if p.round >= 5]  # Rounds 5-7

    # Track which positions get draft allocations
    draft_allocations = {}  # pos -> DraftPick

    # Sort positions wanting early picks by draft value
    early_candidates = [
        (pos, data) for pos, data in position_data.items()
        if data["preferred_round"] == 1 and data["draft_value"] > 0.5
    ]
    early_candidates.sort(key=lambda x: -x[1]["draft_value"])

    # Allocate early picks
    for i, pick in enumerate(early_picks):
        if i < len(early_candidates):
            pos, data = early_candidates[i]
            draft_allocations[pos] = pick
            pick.allocated_to = pos

    # Sort positions wanting mid picks
    mid_candidates = [
        (pos, data) for pos, data in position_data.items()
        if data["preferred_round"] in (2, 3) and data["draft_value"] > 0.3
        and pos not in draft_allocations
    ]
    mid_candidates.sort(key=lambda x: -x[1]["draft_value"])

    # Allocate mid picks
    for i, pick in enumerate(mid_picks):
        if i < len(mid_candidates):
            pos, data = mid_candidates[i]
            draft_allocations[pos] = pick
            pick.allocated_to = pos

    # =========================================================================
    # PASS 3: Build final position items with allocated paths
    # =========================================================================
    offense_items = []
    defense_items = []
    fa_targets = []
    draft_board = []

    for pos in offense_positions + defense_positions:
        data = position_data[pos]
        roster = data["roster"]
        need = data["need"]
        draft_opts = data["draft_opts"]
        fa_opts = data["fa_opts"]
        best_draft = data["best_draft"]
        best_fa = data["best_fa"]
        side = data["side"]

        # Determine path based on pick allocation
        if need < 0.3:
            path = AcquisitionPath.KEEP_CURRENT
            target_name = None
            reasoning = get_path_reasoning(path, current_overall=roster["overall"])
        elif pos in draft_allocations:
            # This position got a draft pick allocated
            allocated_pick = draft_allocations[pos]
            if allocated_pick.round == 1:
                path = AcquisitionPath.DRAFT_EARLY
            elif allocated_pick.round <= 4:
                path = AcquisitionPath.DRAFT_MID
            else:
                path = AcquisitionPath.DRAFT_LATE
            target_name = best_draft.name
            draft_board.append(best_draft)
            reasoning = f"Round {allocated_pick.round} pick (#{allocated_pick.pick}) allocated. {get_path_reasoning(path, draft_grade=best_draft.grade)}"
        elif best_fa and best_fa.is_upgrade:
            # No pick allocated, but FA upgrade available
            path = AcquisitionPath.FREE_AGENCY
            target_name = best_fa.name
            fa_targets.append({
                "position": pos,
                "need_score": need,
                "player": best_fa.model_dump(),
            })
            # Explain why not drafting
            if best_draft and best_draft.is_reachable:
                reasoning = f"Draft picks allocated to higher-priority positions. FA upgrade of +{best_fa.upgrade_amount} OVR available."
            else:
                reasoning = get_path_reasoning(path, fa_overall=best_fa.overall, current_overall=roster["overall"])
        elif best_draft and best_draft.is_reachable:
            # Wanted to draft but no picks available
            path = AcquisitionPath.UNDECIDED
            target_name = None
            reasoning = f"Would draft {best_draft.name} but no picks available in round {best_draft.projected_round}. Exploring trade options."
        else:
            path = AcquisitionPath.KEEP_CURRENT
            target_name = None
            reasoning = get_path_reasoning(path, current_overall=roster["overall"])

        item = PositionPlanItem(
            position=pos,
            side=side,
            need_score=need,
            need_description=get_need_description(need),
            current_starter=CurrentPlayer(
                player_id=str(uuid4()),
                name=roster["name"],
                overall=roster["overall"],
                age=roster["age"],
            ),
            depth_count=roster["depth"],
            draft_options=draft_opts,
            fa_options=fa_opts,
            acquisition_path=path,
            target_player_name=target_name,
            reasoning=reasoning,
        )

        if side == "offense":
            offense_items.append(item)
        else:
            defense_items.append(item)

    # Sort FA targets by need
    fa_targets.sort(key=lambda x: -x["need_score"])

    # Sort draft board by grade
    draft_board.sort(key=lambda x: -x.grade)

    return TeamPositionPlan(
        team_id=team_id,
        team_name="Chicago Bears",  # Would come from franchise
        gm_archetype=gm_archetype,
        gm_archetype_description=GM_DESCRIPTIONS.get(gm_archetype, ""),
        draft_position=draft_position,
        cap_room=cap_room,
        offense=offense_items,
        defense=defense_items,
        summary=OffseasonPlanSummary(
            fa_targets=fa_targets,
            draft_board=draft_board[:10],
            total_fa_budget=int(cap_room * 0.6),
            positions_addressed_in_draft=[
                item.position for item in offense_items + defense_items
                if item.acquisition_path in (AcquisitionPath.DRAFT_EARLY, AcquisitionPath.DRAFT_MID, AcquisitionPath.DRAFT_LATE)
            ],
            positions_addressed_in_fa=[
                item.position for item in offense_items + defense_items
                if item.acquisition_path == AcquisitionPath.FREE_AGENCY
            ],
            draft_picks=draft_picks,  # Include pick inventory with allocations
            mock_draft=mock_draft_results,  # Predicted first round picks
        ),
    ).model_dump()

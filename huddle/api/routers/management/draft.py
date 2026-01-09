"""
Draft management router.

Handles draft prospects, scouting, and draft board endpoints:
- Draft prospects listing
- Individual prospect details
- Draft board management
- Scouting actions
"""

import random
from collections import defaultdict
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.api.schemas.management import (
    CombineMeasurables,
    ScoutEstimate,
    ProspectInfo,
    DraftProspectsResponse,
    BoardEntryResponse,
    DraftBoardResponse,
    AddToBoardRequest,
    UpdateBoardEntryRequest,
    ReorderBoardRequest,
)
from .deps import get_session

router = APIRouter(tags=["draft"])


def _calculate_position_percentiles(draft_class: list) -> dict:
    """
    Calculate position-relative percentiles for combine stats.

    Returns dict: {player_id: {forty: pct, bench: pct, vertical: pct, broad: pct}}
    """
    # Group players by position
    by_position = defaultdict(list)
    for p in draft_class:
        pos = p.position.value if p.position else "UNK"
        by_position[pos].append(p)

    percentiles = {}

    for pos, players in by_position.items():
        # Collect stats for this position (filter None values)
        forties = [(p.id, p.forty_yard_dash) for p in players if p.forty_yard_dash]
        benches = [(p.id, p.bench_press_reps) for p in players if p.bench_press_reps]
        verticals = [(p.id, p.vertical_jump) for p in players if p.vertical_jump]
        broads = [(p.id, p.broad_jump) for p in players if p.broad_jump]

        # Sort and assign percentiles
        # 40-yard: lower is better
        forties.sort(key=lambda x: x[1])  # ascending (4.3 better than 5.0)
        for rank, (pid, _) in enumerate(forties):
            if pid not in percentiles:
                percentiles[pid] = {}
            # Flip so fastest = 99th percentile
            percentiles[pid]["forty"] = (
                int(100 - (rank / max(len(forties) - 1, 1)) * 100) if len(forties) > 1 else 50
            )

        # Bench, vertical, broad: higher is better
        for stat_name, stat_list in [
            ("bench", benches),
            ("vertical", verticals),
            ("broad", broads),
        ]:
            stat_list.sort(key=lambda x: x[1], reverse=True)  # descending (higher = better)
            for rank, (pid, _) in enumerate(stat_list):
                if pid not in percentiles:
                    percentiles[pid] = {}
                percentiles[pid][stat_name] = (
                    int(100 - (rank / max(len(stat_list) - 1, 1)) * 100)
                    if len(stat_list) > 1
                    else 50
                )

    return percentiles


@router.get("/franchise/{franchise_id}/draft-prospects", response_model=DraftProspectsResponse)
async def get_draft_prospects(franchise_id: UUID) -> DraftProspectsResponse:
    """Get draft class prospects with scouting data."""
    from huddle.core.scouting.report import value_to_grade
    from huddle.core.scouting.projections import ScoutingAccuracy

    session = get_session(franchise_id)
    league = session.service.league
    prospects = []

    # Calculate position-relative percentiles for combine stats
    percentiles = _calculate_position_percentiles(league.draft_class)

    # Key attributes to show for prospects
    KEY_ATTRS = ["speed", "acceleration", "strength", "agility", "awareness"]

    for player in league.draft_class:
        # Seed random per-player for consistent results across requests
        player_rng = random.Random(hash(str(player.id)))

        # Calculate scouted percentage from flags
        # Base: 25% just from being in draft class (basic film)
        # +25% if interviewed, +50% if private workout
        scouted_pct = 25
        if player.scouting_interviewed:
            scouted_pct += 25
        if player.scouting_private_workout:
            scouted_pct += 50

        # Determine accuracy based on scouting progress
        if scouted_pct >= 100:
            accuracy = ScoutingAccuracy.HIGH
        elif scouted_pct >= 50:
            accuracy = ScoutingAccuracy.MEDIUM
        else:
            accuracy = ScoutingAccuracy.LOW

        # Build scout estimates with uncertainty
        scout_estimates = []
        for attr_name in KEY_ATTRS:
            true_value = player.attributes.get(attr_name, 50)

            # Add noise based on accuracy (using player-seeded RNG)
            if accuracy == ScoutingAccuracy.LOW:
                noise = player_rng.randint(-12, 12)
                min_est = max(0, true_value - 15)
                max_est = min(99, true_value + 15)
            elif accuracy == ScoutingAccuracy.MEDIUM:
                noise = player_rng.randint(-7, 7)
                min_est = max(0, true_value - 10)
                max_est = min(99, true_value + 10)
            else:  # HIGH
                noise = player_rng.randint(-3, 3)
                min_est = max(0, true_value - 5)
                max_est = min(99, true_value + 5)

            projected = max(0, min(99, true_value + noise))
            grade = value_to_grade(projected, accuracy)

            scout_estimates.append(
                ScoutEstimate(
                    name=attr_name,
                    projected_value=projected,
                    accuracy=accuracy.value,
                    min_estimate=min_est,
                    max_estimate=max_est,
                    grade=grade.value,
                )
            )

        # Calculate overall projection (average of key attrs with noise)
        avg_true = sum(player.attributes.get(a, 50) for a in KEY_ATTRS) // len(KEY_ATTRS)
        overall_proj = max(40, min(99, avg_true + player_rng.randint(-5, 5)))

        prospects.append(
            ProspectInfo(
                player_id=str(player.id),
                name=player.full_name,
                position=player.position.value if player.position else "UNK",
                college=player.college,
                age=player.age or 21,
                height=player.height_display,
                weight=player.weight_lbs,
                scouted_percentage=scouted_pct,
                interviewed=player.scouting_interviewed,
                private_workout=player.scouting_private_workout,
                combine=CombineMeasurables(
                    forty_yard_dash=player.forty_yard_dash,
                    forty_percentile=percentiles.get(player.id, {}).get("forty"),
                    bench_press_reps=player.bench_press_reps,
                    bench_percentile=percentiles.get(player.id, {}).get("bench"),
                    vertical_jump=player.vertical_jump,
                    vertical_percentile=percentiles.get(player.id, {}).get("vertical"),
                    broad_jump=player.broad_jump,
                    broad_percentile=percentiles.get(player.id, {}).get("broad"),
                ),
                scout_estimates=scout_estimates,
                overall_projection=overall_proj,
                projected_round=player.projected_draft_round,
            )
        )

    # Sort by overall projection descending
    prospects.sort(key=lambda p: p.overall_projection, reverse=True)

    return DraftProspectsResponse(count=len(prospects), prospects=prospects)


@router.get("/franchise/{franchise_id}/draft-prospects/{player_id}", response_model=ProspectInfo)
async def get_draft_prospect(franchise_id: UUID, player_id: UUID) -> ProspectInfo:
    """Get a single draft prospect with scouting data."""
    from huddle.core.scouting.report import value_to_grade
    from huddle.core.scouting.projections import ScoutingAccuracy

    session = get_session(franchise_id)
    league = session.service.league

    # Find the prospect
    player = None
    for p in league.draft_class:
        if p.id == player_id:
            player = p
            break

    if not player:
        raise HTTPException(status_code=404, detail="Prospect not found in draft class")

    # Calculate position-relative percentiles for combine stats
    percentiles = _calculate_position_percentiles(league.draft_class)
    player_percentiles = percentiles.get(player.id, {})

    # Key attributes to show for prospects
    KEY_ATTRS = ["speed", "acceleration", "strength", "agility", "awareness"]

    # Use player-seeded RNG for consistent results
    player_rng = random.Random(hash(str(player.id)))

    # Calculate scouted percentage from flags
    scouted_pct = 25
    if player.scouting_interviewed:
        scouted_pct += 25
    if player.scouting_private_workout:
        scouted_pct += 50

    # Determine accuracy based on scouting progress
    if scouted_pct >= 100:
        accuracy = ScoutingAccuracy.HIGH
    elif scouted_pct >= 50:
        accuracy = ScoutingAccuracy.MEDIUM
    else:
        accuracy = ScoutingAccuracy.LOW

    # Build scout estimates with uncertainty
    scout_estimates = []
    for attr_name in KEY_ATTRS:
        true_value = player.attributes.get(attr_name, 50)

        # Add noise based on accuracy
        if accuracy == ScoutingAccuracy.LOW:
            noise = player_rng.randint(-12, 12)
            min_est = max(0, true_value - 15)
            max_est = min(99, true_value + 15)
        elif accuracy == ScoutingAccuracy.MEDIUM:
            noise = player_rng.randint(-7, 7)
            min_est = max(0, true_value - 10)
            max_est = min(99, true_value + 10)
        else:  # HIGH
            noise = player_rng.randint(-3, 3)
            min_est = max(0, true_value - 5)
            max_est = min(99, true_value + 5)

        projected = max(0, min(99, true_value + noise))
        grade = value_to_grade(projected, accuracy)

        scout_estimates.append(
            ScoutEstimate(
                name=attr_name,
                projected_value=projected,
                accuracy=accuracy.value,
                min_estimate=min_est,
                max_estimate=max_est,
                grade=grade.value,
            )
        )

    # Calculate overall projection
    avg_true = sum(player.attributes.get(a, 50) for a in KEY_ATTRS) // len(KEY_ATTRS)
    overall_proj = max(40, min(99, avg_true + player_rng.randint(-5, 5)))

    return ProspectInfo(
        player_id=str(player.id),
        name=player.full_name,
        position=player.position.value if player.position else "UNK",
        college=player.college,
        age=player.age or 21,
        height=player.height_display,
        weight=player.weight_lbs,
        scouted_percentage=scouted_pct,
        interviewed=player.scouting_interviewed,
        private_workout=player.scouting_private_workout,
        combine=CombineMeasurables(
            forty_yard_dash=player.forty_yard_dash,
            forty_percentile=player_percentiles.get("forty"),
            bench_press_reps=player.bench_press_reps,
            bench_percentile=player_percentiles.get("bench"),
            vertical_jump=player.vertical_jump,
            vertical_percentile=player_percentiles.get("vertical"),
            broad_jump=player.broad_jump,
            broad_percentile=player_percentiles.get("broad"),
        ),
        scout_estimates=scout_estimates,
        overall_projection=overall_proj,
        projected_round=player.projected_draft_round,
    )


# === Draft Board Endpoints ===


@router.get("/franchise/{franchise_id}/draft-board", response_model=DraftBoardResponse)
async def get_draft_board(franchise_id: UUID) -> DraftBoardResponse:
    """Get the user's draft board."""
    session = get_session(franchise_id)

    entries = session.service.get_draft_board()
    return DraftBoardResponse(
        entries=[BoardEntryResponse(**e) for e in entries],
        count=len(entries),
    )


@router.post("/franchise/{franchise_id}/draft-board", response_model=BoardEntryResponse)
async def add_to_draft_board(franchise_id: UUID, request: AddToBoardRequest) -> BoardEntryResponse:
    """Add a prospect to the draft board."""
    session = get_session(franchise_id)

    entry = session.service.add_to_draft_board(request.prospect_id, tier=request.tier)
    if not entry:
        raise HTTPException(
            status_code=400,
            detail="Could not add prospect to board (may already be on board or not exist)",
        )

    return BoardEntryResponse(**entry)


@router.delete("/franchise/{franchise_id}/draft-board/{prospect_id}")
async def remove_from_draft_board(franchise_id: UUID, prospect_id: str) -> dict:
    """Remove a prospect from the draft board."""
    session = get_session(franchise_id)

    success = session.service.remove_from_draft_board(prospect_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prospect not found on board")

    return {"message": "Prospect removed from board", "prospect_id": prospect_id}


@router.patch(
    "/franchise/{franchise_id}/draft-board/{prospect_id}", response_model=BoardEntryResponse
)
async def update_board_entry(
    franchise_id: UUID,
    prospect_id: str,
    request: UpdateBoardEntryRequest,
) -> BoardEntryResponse:
    """Update a prospect's tier or notes on the board."""
    session = get_session(franchise_id)

    entry = session.service.update_board_entry(prospect_id, tier=request.tier, notes=request.notes)
    if not entry:
        raise HTTPException(status_code=404, detail="Prospect not found on board")

    return BoardEntryResponse(**entry)


@router.post("/franchise/{franchise_id}/draft-board/{prospect_id}/reorder")
async def reorder_board_entry(
    franchise_id: UUID,
    prospect_id: str,
    request: ReorderBoardRequest,
) -> dict:
    """Reorder a prospect on the board."""
    session = get_session(franchise_id)

    success = session.service.reorder_board_entry(prospect_id, request.new_rank)
    if not success:
        raise HTTPException(status_code=404, detail="Prospect not found on board")

    return {
        "message": "Prospect reordered",
        "prospect_id": prospect_id,
        "new_rank": request.new_rank,
    }


@router.get("/franchise/{franchise_id}/draft-board/{prospect_id}/status")
async def check_board_status(franchise_id: UUID, prospect_id: str) -> dict:
    """Check if a prospect is on the user's draft board."""
    session = get_session(franchise_id)

    on_board = session.service.is_on_draft_board(prospect_id)
    return {"prospect_id": prospect_id, "on_board": on_board}

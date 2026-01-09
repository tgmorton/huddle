"""
Practice management router.

Handles practice, playbook mastery, and development endpoints:
- Run practice sessions
- Get playbook mastery data
- Get development/potential data
- Get weekly development gains
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.api.schemas.management import (
    RunPracticeRequest,
    PracticeResultsResponse,
    PlaybookPracticeStats,
    DevelopmentPracticeStats,
    GamePrepStats,
    MasteryLevelSchema,
    PlayMasteryInfo,
    PlayerPlaybookMastery,
    PlaybookMasteryResponse,
    AttributePotential,
    PlayerDevelopmentInfo,
    DevelopmentResponse,
    PlayerWeeklyGain,
    WeeklyDevelopmentResponse,
)
from .deps import get_session, get_session_with_team

router = APIRouter(tags=["practice"])


@router.post("/franchise/{franchise_id}/run-practice", response_model=PracticeResultsResponse)
async def run_practice(franchise_id: UUID, request: RunPracticeRequest) -> PracticeResultsResponse:
    """
    Execute a practice session with the given time allocation.

    This applies actual effects to players:
    - Playbook learning: Players gain reps toward play mastery
    - Development: Young players improve their attributes
    - Game prep: Team gains bonuses for the next opponent

    Returns detailed stats about what improved during practice.
    """
    session = get_session(franchise_id)

    # Run practice and get results
    result = session.service.run_practice(
        event_id=request.event_id,
        playbook=request.playbook,
        development=request.development,
        game_prep=request.game_prep,
    )

    if not result.get("success"):
        return PracticeResultsResponse(
            success=False,
            error=result.get("error", "Practice failed"),
        )

    # Build response from result stats
    playbook_stats = result.get("playbook_stats", {})
    dev_stats = result.get("development_stats", {})
    prep_stats = result.get("game_prep_stats", {})

    return PracticeResultsResponse(
        success=True,
        duration_minutes=result.get("duration_minutes", 120),
        playbook_stats=PlaybookPracticeStats(
            players_practiced=playbook_stats.get("players_practiced", 0),
            total_reps_given=playbook_stats.get("total_reps_given", 0),
            tier_advancements=playbook_stats.get("tier_advancements", 0),
            plays_practiced=playbook_stats.get("plays_practiced", 0),
        ),
        development_stats=DevelopmentPracticeStats(
            players_developed=dev_stats.get("players_developed", 0),
            total_points_gained=dev_stats.get("total_points_gained", 0.0),
            attributes_improved=dev_stats.get("attributes_improved", {}),
        ),
        game_prep_stats=GamePrepStats(
            opponent=prep_stats.get("opponent"),
            prep_level=prep_stats.get("prep_level", 0.0),
            scheme_bonus=prep_stats.get("scheme_bonus", 0.0),
            execution_bonus=prep_stats.get("execution_bonus", 0.0),
        ),
    )


@router.get("/franchise/{franchise_id}/playbook-mastery", response_model=PlaybookMasteryResponse)
async def get_playbook_mastery(franchise_id: UUID) -> PlaybookMasteryResponse:
    """
    Get playbook mastery data for all players on the user's team.

    Returns per-player, per-play mastery status:
    - UNLEARNED: Player doesn't know the play (-15% execution)
    - LEARNED: Player knows the play (normal execution)
    - MASTERED: Player has instinctive knowledge (+10% execution)

    Progress shows advancement toward the next tier (0.0-1.0).
    """
    from huddle.core.playbook.play_codes import ALL_PLAYS

    session = get_session_with_team(franchise_id)
    team = session.team

    # Get the team's playbook plays (or all plays if no playbook set)
    if team.playbook and hasattr(team.playbook, "get_all_play_codes"):
        playbook_codes = set(team.playbook.get_all_play_codes())
    else:
        # Default to common plays if no playbook
        playbook_codes = set(list(ALL_PLAYS.keys())[:20])

    players_mastery = []

    for player in team.roster.players.values():
        knowledge = team.get_player_knowledge(player.id)

        plays_info = []
        learned_count = 0
        mastered_count = 0

        for play_code in playbook_codes:
            play = ALL_PLAYS.get(play_code)
            if not play:
                continue

            # Check if player's position is involved in this play
            if player.position.value not in play.positions_involved:
                continue

            mastery = knowledge.get_mastery(play_code)

            if mastery.level.value == "learned":
                learned_count += 1
            elif mastery.level.value == "mastered":
                mastered_count += 1
                learned_count += 1  # Mastered counts as learned too

            plays_info.append(
                PlayMasteryInfo(
                    play_id=play_code,
                    play_name=play.name,
                    status=MasteryLevelSchema(mastery.level.value),
                    progress=mastery.progress,
                    reps=mastery.reps,
                )
            )

        if plays_info:  # Only include players with relevant plays
            players_mastery.append(
                PlayerPlaybookMastery(
                    player_id=str(player.id),
                    name=player.full_name,
                    position=player.position.value,
                    plays=plays_info,
                    learned_count=learned_count,
                    mastered_count=mastered_count,
                    total_plays=len(plays_info),
                )
            )

    return PlaybookMasteryResponse(
        team_abbr=team.abbreviation,
        players=players_mastery,
    )


@router.get("/franchise/{franchise_id}/development", response_model=DevelopmentResponse)
async def get_development_info(franchise_id: UUID) -> DevelopmentResponse:
    """
    Get development/potential info for all players on the user's team.

    Returns per-attribute potentials showing:
    - Current value
    - Potential ceiling
    - Growth room (how much the attribute can still improve)

    Players develop through practice and game experience.
    """
    from huddle.generators.potential import generate_all_potentials, calculate_overall_potential

    session = get_session_with_team(franchise_id)
    team = session.team

    players_dev = []

    for player in team.roster.players.values():
        # Check if player already has potentials stored
        existing_potentials = player.attributes.get_all_potentials()

        if not existing_potentials:
            # Generate potentials for this player (veteran tier)
            actual_potentials, _ = generate_all_potentials(
                player.attributes.to_dict(),
                tier="day3_late",  # Established players have lower ceilings
                scouted_percentage=100,  # We know our own players
            )
            # Store them on the player
            for key, value in actual_potentials.items():
                attr_name = key.replace("_potential", "")
                player.attributes.set_potential(attr_name, value)
            existing_potentials = player.attributes.get_all_potentials()

        # Build potential list
        potentials_list = []
        for attr_name, potential in existing_potentials.items():
            current = player.attributes.get(attr_name, 50)
            potentials_list.append(
                AttributePotential(
                    name=attr_name,
                    current=current,
                    potential=potential,
                    growth_room=max(0, potential - current),
                )
            )

        # Sort by growth room (most room to grow first)
        potentials_list.sort(key=lambda p: p.growth_room, reverse=True)

        # Calculate overall potential
        overall_pot = calculate_overall_potential(
            {f"{p.name}_potential": p.potential for p in potentials_list},
            player.position.value,
        )

        players_dev.append(
            PlayerDevelopmentInfo(
                player_id=str(player.id),
                name=player.full_name,
                position=player.position.value,
                overall=player.overall,
                overall_potential=overall_pot,
                potentials=potentials_list,
            )
        )

    # Sort by growth potential (biggest gap between overall and potential)
    players_dev.sort(key=lambda p: p.overall_potential - p.overall, reverse=True)

    return DevelopmentResponse(
        team_abbr=team.abbreviation,
        players=players_dev,
    )


@router.get("/franchise/{franchise_id}/weekly-development")
async def get_weekly_development(franchise_id: UUID) -> WeeklyDevelopmentResponse:
    """Get players who improved this week through practice.

    Returns only players who have gained attribute points this week,
    along with their specific gains. Resets each week.
    """
    session = get_session(franchise_id)

    data = session.service.get_weekly_development()
    return WeeklyDevelopmentResponse(
        week=data["week"],
        players=[PlayerWeeklyGain(**p) for p in data["players"]],
    )

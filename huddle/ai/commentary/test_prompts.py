"""
Commentary Prompt Testing

Test harness for play-by-play and color commentary prompts.
Creates realistic test plays and calls both prompt types.

Run with:
    python -m huddle.ai.commentary.test_prompts

Or with specific test:
    python -m huddle.ai.commentary.test_prompts --play routine
    python -m huddle.ai.commentary.test_prompts --play big_play
    python -m huddle.ai.commentary.test_prompts --play sack
    python -m huddle.ai.commentary.test_prompts --play touchdown
    python -m huddle.ai.commentary.test_prompts --play turnover

Add --live to call the actual Gemini API (requires GEMINI_API_KEY)
"""

import argparse
import asyncio
from datetime import datetime
from typing import Optional

from .schema import (
    PlayerRef,
    PlayConcept,
    DriveContext,
    GameSituation,
    EnrichedPlay,
    NarrativeType,
    NarrativeHook,
    MilestoneProximity,
    ActiveStreak,
    MatchupNote,
    NarrativeContext,
    CommentaryContext,
)
from .prompts import (
    build_play_by_play_prompt,
    build_color_prompt,
    serialize_play_for_prompt,
    serialize_narratives_for_prompt,
)


# =============================================================================
# MOCK DATA FACTORIES
# =============================================================================

def make_player(
    player_id: str,
    name: str,
    position: str,
    team: str,
    number: int,
    **stats
) -> PlayerRef:
    """Create a mock player reference."""
    return PlayerRef(
        player_id=player_id,
        name=name,
        position=position,
        team_abbrev=team,
        jersey_number=number,
        stats_today=stats,
    )


def make_situation(
    down: int = 2,
    distance: int = 7,
    field_position: str = "OPP 35",
    yards_to_goal: int = 35,
    quarter: int = 2,
    time_remaining: str = "5:42",
    time_remaining_seconds: int = 342,
    home_score: int = 14,
    away_score: int = 10,
    score_diff: int = 4,
    **flags
) -> GameSituation:
    """Create a mock game situation."""
    return GameSituation(
        quarter=quarter,
        time_remaining=time_remaining,
        time_remaining_seconds=time_remaining_seconds,
        down=down,
        distance=distance,
        field_position=field_position,
        yards_to_goal=yards_to_goal,
        home_score=home_score,
        away_score=away_score,
        score_differential=score_diff,
        is_red_zone=flags.get("is_red_zone", yards_to_goal <= 20),
        is_goal_to_go=flags.get("is_goal_to_go", yards_to_goal <= distance),
        is_two_minute_warning=flags.get("is_two_minute_warning", False),
        is_four_minute_offense=flags.get("is_four_minute_offense", False),
        is_hurry_up=flags.get("is_hurry_up", False),
        is_fourth_down=flags.get("is_fourth_down", down == 4),
        is_short_yardage=flags.get("is_short_yardage", distance <= 3),
        is_long_yardage=flags.get("is_long_yardage", distance >= 7),
        is_close_game=flags.get("is_close_game", abs(score_diff) <= 8),
        is_blowout=flags.get("is_blowout", abs(score_diff) >= 24),
        is_comeback_territory=flags.get("is_comeback_territory", False),
    )


def make_drive(
    play_number: int = 5,
    yards: float = 32,
    time: float = 180,
    starting_pos: str = "OWN 25",
    third_attempts: int = 1,
    third_conversions: int = 1,
    consecutive_firsts: int = 2,
    plays_since_negative: int = 5,
) -> DriveContext:
    """Create a mock drive context."""
    return DriveContext(
        play_number_in_drive=play_number,
        yards_this_drive=yards,
        time_this_drive=time,
        starting_field_position=starting_pos,
        third_down_attempts=third_attempts,
        third_down_conversions=third_conversions,
        consecutive_first_downs=consecutive_firsts,
        plays_since_negative=plays_since_negative,
    )


def make_narratives(
    hooks: Optional[list[NarrativeHook]] = None,
    milestones: Optional[list[MilestoneProximity]] = None,
    streaks: Optional[list[ActiveStreak]] = None,
    matchups: Optional[list[MatchupNote]] = None,
) -> NarrativeContext:
    """Create a mock narrative context."""
    return NarrativeContext(
        active_hooks=hooks or [],
        milestones_in_range=milestones or [],
        active_streaks=streaks or [],
        relevant_matchups=matchups or [],
        game_storylines=["division matchup", "playoff implications"],
        recently_mentioned={},
    )


# =============================================================================
# TEST SCENARIOS
# =============================================================================

def create_routine_completion() -> CommentaryContext:
    """
    Test 1: Routine completion
    2nd & 7, complete for 8 yards, first down
    """
    passer = make_player("qb1", "Patrick Mahomes", "QB", "KC", 15,
                         completions=18, attempts=24, yards=187)
    receiver = make_player("wr1", "Travis Kelce", "TE", "KC", 87,
                          receptions=6, yards=72, targets=8)
    tackler = make_player("db1", "Sauce Gardner", "CB", "NYJ", 1)

    play = EnrichedPlay(
        play_id="play_001",
        game_id="game_001",
        outcome="complete",
        yards_gained=8,
        passer=passer,
        receiver=receiver,
        ball_carrier=None,
        tackler=tackler,
        play_concept=PlayConcept(
            play_code="PASS_SLANT_RIGHT",
            play_type="pass",
            formation="shotgun",
            concept_name="slant_flat",
            route_tree={"wr1": "slant", "wr2": "flat"},
        ),
        situation=make_situation(down=2, distance=7, field_position="OPP 35"),
        drive_context=make_drive(play_number=5, yards=32),
        key_events=["clean_pocket", "quick_release"],
        play_duration=4.2,
        throw_time=2.1,
        air_yards=5,
        yards_after_catch=3,
        was_contested=False,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=False,
        resulted_in_first_down=True,
        resulted_in_touchdown=False,
        resulted_in_turnover=False,
    )

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.STREAK,
            priority=0.6,
            headline="Fifth straight completion",
            detail="Mahomes has now completed 5 consecutive passes for 42 yards",
            trigger_player_id="qb1",
            trigger_stat="consecutive_completions",
            trigger_value=5,
            discovered_at=datetime.now(),
            last_mentioned=None,
        )
    ]

    narratives = make_narratives(hooks=hooks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & 10: Run left, 3 yards",
            "2nd & 7: Incomplete deep right",
            "3rd & 7: Complete to Edwards-Helaire, 9 yards, first down",
        ],
        drive_summary="5 plays, 32 yards, 3:00",
        commentary_type="play_by_play",
        max_duration_seconds=3.0,
        energy_level="normal",
        suggested_focus=None,
        hooks_to_use=[],
    )


def create_big_play() -> CommentaryContext:
    """
    Test 2: Big play
    Deep pass, 45 yards, explosive
    """
    passer = make_player("qb1", "Joe Burrow", "QB", "CIN", 9,
                         completions=15, attempts=22, yards=198)
    receiver = make_player("wr1", "Ja'Marr Chase", "WR", "CIN", 1,
                          receptions=5, yards=112, targets=7)

    play = EnrichedPlay(
        play_id="play_002",
        game_id="game_001",
        outcome="complete",
        yards_gained=45,
        passer=passer,
        receiver=receiver,
        ball_carrier=None,
        tackler=None,
        play_concept=PlayConcept(
            play_code="PASS_FOUR_VERTS",
            play_type="pass",
            formation="shotgun",
            concept_name="four_verticals",
            route_tree={"wr1": "go", "wr2": "go", "wr3": "seam", "te1": "seam"},
        ),
        situation=make_situation(
            down=1, distance=10, field_position="OWN 30",
            yards_to_goal=70, quarter=3, time_remaining="8:15",
        ),
        drive_context=make_drive(play_number=1, yards=0),
        key_events=["max_protect", "pump_fake", "single_coverage_beat"],
        play_duration=5.8,
        throw_time=3.2,
        air_yards=38,
        yards_after_catch=7,
        was_contested=False,
        was_dropped=False,
        was_big_play=True,
        was_explosive=True,
        was_negative=False,
        resulted_in_first_down=True,
        resulted_in_touchdown=False,
        resulted_in_turnover=False,
    )

    milestones = [
        MilestoneProximity(
            player_id="wr1",
            player_name="Ja'Marr Chase",
            stat_name="receiving_yards",
            current_value=112,
            milestone_value=150,
            yards_needed=38,
            milestone_type="game",
            significance="150-yard game",
        )
    ]

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.MATCHUP,
            priority=0.8,
            headline="LSU reunion",
            detail="Burrow to Chase - the LSU connection strikes again, "
                   "just like their college days",
            trigger_player_id="wr1",
            trigger_stat=None,
            trigger_value=None,
            discovered_at=datetime.now(),
            last_mentioned=None,
        )
    ]

    narratives = make_narratives(hooks=hooks, milestones=milestones)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[],
        drive_summary="1 play, 45 yards, 0:06",
        commentary_type="play_by_play",
        max_duration_seconds=4.0,
        energy_level="excited",
        suggested_focus="matchup",
        hooks_to_use=["LSU reunion"],
    )


def create_sack() -> CommentaryContext:
    """
    Test 3: Sack
    3rd & long, QB goes down, loss of 8
    """
    passer = make_player("qb1", "Dak Prescott", "QB", "DAL", 4,
                         completions=12, attempts=19, yards=134, sacks=2)
    tackler = make_player("edge1", "Micah Parsons", "EDGE", "DAL", 11,
                         sacks=1.5, tackles=4)

    play = EnrichedPlay(
        play_id="play_003",
        game_id="game_001",
        outcome="sack",
        yards_gained=-8,
        passer=passer,
        receiver=None,
        ball_carrier=None,
        tackler=tackler,
        play_concept=PlayConcept(
            play_code="PASS_MESH",
            play_type="pass",
            formation="shotgun",
            concept_name="mesh_concept",
            route_tree={"wr1": "drag", "wr2": "drag"},
            protection="slide_right",
        ),
        situation=make_situation(
            down=3, distance=9, field_position="OPP 45",
            yards_to_goal=45, quarter=2, time_remaining="1:45",
            is_two_minute_warning=True,
        ),
        drive_context=make_drive(play_number=7, yards=28, consecutive_firsts=0),
        key_events=["pressure_level_high", "scramble_attempt", "tackle_for_loss"],
        play_duration=4.5,
        throw_time=None,
        air_yards=None,
        yards_after_catch=None,
        was_contested=False,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=True,
        resulted_in_first_down=False,
        resulted_in_touchdown=False,
        resulted_in_turnover=False,
    )

    streaks = [
        ActiveStreak(
            player_id="edge1",
            player_name="Micah Parsons",
            streak_type="games_with_sack",
            streak_value=4,
            is_positive=True,
            context="has at least half a sack in 4 straight games",
            career_best=6,
            season_best=4,
        )
    ]

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.STREAK,
            priority=0.75,
            headline="Parsons streak continues",
            detail="That's 4 straight games with a sack for Parsons, "
                   "2 away from his career best streak",
            trigger_player_id="edge1",
            trigger_stat="games_with_sack",
            trigger_value=4,
            discovered_at=datetime.now(),
            last_mentioned=None,
        )
    ]

    narratives = make_narratives(hooks=hooks, streaks=streaks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & 10: Run middle, 2 yards",
            "2nd & 8: Complete short right, 1 yard",
        ],
        drive_summary="7 plays, 28 yards, 3:15",
        commentary_type="play_by_play",
        max_duration_seconds=4.0,
        energy_level="tense",
        suggested_focus="streak",
        hooks_to_use=["Parsons streak continues"],
    )


def create_touchdown() -> CommentaryContext:
    """
    Test 4: Touchdown
    Red zone, TD pass, scoring play
    """
    passer = make_player("qb1", "Josh Allen", "QB", "BUF", 17,
                         completions=22, attempts=31, yards=267, touchdowns=3)
    receiver = make_player("wr1", "Stefon Diggs", "WR", "BUF", 14,
                          receptions=8, yards=94, touchdowns=2)

    play = EnrichedPlay(
        play_id="play_004",
        game_id="game_001",
        outcome="complete",
        yards_gained=12,
        passer=passer,
        receiver=receiver,
        ball_carrier=None,
        tackler=None,
        play_concept=PlayConcept(
            play_code="PASS_FADE_RED",
            play_type="pass",
            formation="shotgun",
            concept_name="fade_red_zone",
            route_tree={"wr1": "fade"},
        ),
        situation=make_situation(
            down=2, distance=8, field_position="OPP 12",
            yards_to_goal=12, quarter=4, time_remaining="3:22",
            home_score=24, away_score=28, score_diff=-4,
            is_red_zone=True,
        ),
        drive_context=make_drive(play_number=9, yards=73, consecutive_firsts=4),
        key_events=["back_shoulder_throw", "contested_catch", "touchdown"],
        play_duration=4.0,
        throw_time=2.8,
        air_yards=12,
        yards_after_catch=0,
        was_contested=True,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=False,
        resulted_in_first_down=True,
        resulted_in_touchdown=True,
        resulted_in_turnover=False,
    )

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.MILESTONE,
            priority=0.9,
            headline="Diggs' 10th TD",
            detail="That's Diggs' 10th receiving touchdown of the season, "
                   "joining elite company",
            trigger_player_id="wr1",
            trigger_stat="touchdowns",
            trigger_value=10,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
        NarrativeHook(
            narrative_type=NarrativeType.SITUATIONAL,
            priority=0.85,
            headline="Go-ahead score",
            detail="Bills take the lead with under 4 minutes to play",
            trigger_player_id=None,
            trigger_stat=None,
            trigger_value=None,
            discovered_at=datetime.now(),
            last_mentioned=None,
        )
    ]

    narratives = make_narratives(hooks=hooks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & 10: Complete to Knox, 15 yards",
            "1st & 10: Run left, 6 yards",
            "2nd & 4: Incomplete deep",
            "3rd & 4: Complete to Diggs, 12 yards, first down",
        ],
        drive_summary="9 plays, 73 yards, 4:38",
        commentary_type="play_by_play",
        max_duration_seconds=5.0,
        energy_level="excited",
        suggested_focus="milestone",
        hooks_to_use=["Diggs' 10th TD", "Go-ahead score"],
    )


def create_turnover() -> CommentaryContext:
    """
    Test 5: Turnover
    Interception, momentum shift
    """
    passer = make_player("qb1", "Russell Wilson", "QB", "DEN", 3,
                         completions=14, attempts=26, yards=156, interceptions=2)
    tackler = make_player("db1", "Trevon Diggs", "CB", "DAL", 7,
                         interceptions=1, passes_defended=2)

    play = EnrichedPlay(
        play_id="play_005",
        game_id="game_001",
        outcome="interception",
        yards_gained=0,
        passer=passer,
        receiver=None,
        ball_carrier=None,
        tackler=tackler,
        play_concept=PlayConcept(
            play_code="PASS_COMEBACK",
            play_type="pass",
            formation="shotgun",
            concept_name="comeback_route",
            route_tree={"wr1": "comeback"},
        ),
        situation=make_situation(
            down=3, distance=6, field_position="OPP 28",
            yards_to_goal=28, quarter=3, time_remaining="6:15",
            home_score=17, away_score=17, score_diff=0,
            is_red_zone=False,
        ),
        drive_context=make_drive(play_number=8, yards=47, consecutive_firsts=2),
        key_events=["tight_window", "ball_tipped", "interception"],
        play_duration=3.8,
        throw_time=2.5,
        air_yards=12,
        yards_after_catch=None,
        was_contested=True,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=True,
        resulted_in_first_down=False,
        resulted_in_touchdown=False,
        resulted_in_turnover=True,
    )

    matchups = [
        MatchupNote(
            matchup_type="player_vs_team",
            entity_a_id="qb1",
            entity_a_name="Russell Wilson",
            entity_b_id="team_dal",
            entity_b_name="Dallas",
            history_summary="3-1 record vs Dallas",
            key_stat="2 INTs in last meeting",
            narrative_angle="struggles against Dallas secondary",
        )
    ]

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.MATCHUP,
            priority=0.85,
            headline="Diggs strikes again",
            detail="The ball-hawking corner gets his 5th pick of the season",
            trigger_player_id="db1",
            trigger_stat="interceptions",
            trigger_value=5,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
        NarrativeHook(
            narrative_type=NarrativeType.STATISTICAL_ANOMALY,
            priority=0.7,
            headline="Red zone struggles",
            detail="Broncos have turned it over on 3 of their last 5 red zone trips",
            trigger_player_id=None,
            trigger_stat="red_zone_turnovers",
            trigger_value=3,
            discovered_at=datetime.now(),
            last_mentioned=None,
        )
    ]

    narratives = make_narratives(hooks=hooks, matchups=matchups)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & 10: Run middle, 4 yards",
            "2nd & 6: Complete underneath, 2 yards",
            "3rd & 4: Complete to Sutton, 9 yards, first down",
            "1st & 10: Run right, 3 yards",
        ],
        drive_summary="8 plays, 47 yards, 4:12",
        commentary_type="play_by_play",
        max_duration_seconds=5.0,
        energy_level="excited",
        suggested_focus="matchup",
        hooks_to_use=["Diggs strikes again"],
    )


# =============================================================================
# TEST RUNNERS
# =============================================================================

# =============================================================================
# FICTIONAL PLAYER SCENARIOS
# =============================================================================

def create_fictional_scramble_td() -> CommentaryContext:
    """
    Fictional: Rookie QB scramble touchdown
    4th & goal, QB keeps it, dives for the pylon
    """
    passer = make_player("qb_fic1", "Marcus Webb", "QB", "ATL", 7,
                         completions=19, attempts=28, yards=215, touchdowns=1,
                         rushing_yards=45, rushing_tds=1)
    tackler = make_player("lb_fic1", "DeShawn Carter", "LB", "NO", 54,
                         tackles=8, sacks=0.5)

    play = EnrichedPlay(
        play_id="play_fic_001",
        game_id="game_fic_001",
        outcome="rush_touchdown",
        yards_gained=3,
        passer=None,
        receiver=None,
        ball_carrier=passer,  # QB is the ball carrier on scramble
        tackler=tackler,
        play_concept=PlayConcept(
            play_code="PASS_ROLLOUT_RIGHT",
            play_type="run",  # Became a run
            formation="shotgun",
            concept_name="rollout_option",
            run_direction="right",
        ),
        situation=make_situation(
            down=4, distance=3, field_position="OPP 3",
            yards_to_goal=3, quarter=4, time_remaining="0:47",
            home_score=21, away_score=24, score_diff=-3,
            is_red_zone=True, is_goal_to_go=True, is_fourth_down=True,
        ),
        drive_context=make_drive(play_number=12, yards=75, consecutive_firsts=3),
        key_events=["coverage_tight", "scramble", "dive_for_pylon", "touchdown"],
        play_duration=6.2,
        throw_time=None,
        air_yards=None,
        yards_after_catch=None,
        was_contested=False,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=False,
        resulted_in_first_down=True,
        resulted_in_touchdown=True,
        resulted_in_turnover=False,
    )

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.PERSONNEL,
            priority=0.9,
            headline="Rookie moment",
            detail="Webb, the 3rd round pick out of Oregon State, with his first career rushing TD",
            trigger_player_id="qb_fic1",
            trigger_stat="rushing_touchdowns",
            trigger_value=1,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
        NarrativeHook(
            narrative_type=NarrativeType.SITUATIONAL,
            priority=0.95,
            headline="Game-tying score",
            detail="Falcons tie it up with under a minute to play",
            trigger_player_id=None,
            trigger_stat=None,
            trigger_value=None,
            discovered_at=datetime.now(),
            last_mentioned=None,
        )
    ]

    narratives = make_narratives(hooks=hooks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & Goal: Run middle, 1 yard",
            "2nd & Goal: Incomplete in end zone",
            "3rd & Goal: Complete to flat, 1 yard short",
        ],
        drive_summary="12 plays, 75 yards, 5:13",
        commentary_type="play_by_play",
        max_duration_seconds=5.0,
        energy_level="excited",
        suggested_focus="personnel",
        hooks_to_use=["Rookie moment", "Game-tying score"],
    )


def create_fictional_dropped_pass() -> CommentaryContext:
    """
    Fictional: Crucial dropped pass on 3rd down
    Wide open receiver drops easy conversion
    """
    passer = make_player("qb_fic2", "Tyler Raines", "QB", "JAX", 12,
                         completions=22, attempts=34, yards=248)
    receiver = make_player("wr_fic2", "Jaylen Foster", "WR", "JAX", 81,
                          receptions=4, yards=52, targets=9, drops=2)

    play = EnrichedPlay(
        play_id="play_fic_002",
        game_id="game_fic_001",
        outcome="incomplete",
        yards_gained=0,
        passer=passer,
        receiver=receiver,
        ball_carrier=None,
        tackler=None,
        play_concept=PlayConcept(
            play_code="PASS_CURL_FLAT",
            play_type="pass",
            formation="shotgun",
            concept_name="curl_flat",
            route_tree={"wr1": "curl", "rb1": "flat"},
        ),
        situation=make_situation(
            down=3, distance=5, field_position="OPP 42",
            yards_to_goal=42, quarter=3, time_remaining="4:22",
            home_score=10, away_score=17, score_diff=-7,
        ),
        drive_context=make_drive(play_number=6, yards=23, consecutive_firsts=1),
        key_events=["clean_pocket", "wide_open", "dropped_pass"],
        play_duration=3.8,
        throw_time=2.4,
        air_yards=7,
        yards_after_catch=None,
        was_contested=False,
        was_dropped=True,
        was_big_play=False,
        was_explosive=False,
        was_negative=False,
        resulted_in_first_down=False,
        resulted_in_touchdown=False,
        resulted_in_turnover=False,
    )

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.STATISTICAL_ANOMALY,
            priority=0.8,
            headline="Second drop today",
            detail="Foster has now dropped 2 of his 9 targets, both on third down",
            trigger_player_id="wr_fic2",
            trigger_stat="drops",
            trigger_value=2,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
    ]

    streaks = [
        ActiveStreak(
            player_id="wr_fic2",
            player_name="Jaylen Foster",
            streak_type="third_down_drops",
            streak_value=2,
            is_positive=False,
            context="has dropped his last 2 third-down targets",
            career_best=None,
            season_best=None,
        )
    ]

    narratives = make_narratives(hooks=hooks, streaks=streaks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & 10: Run right, 5 yards",
            "2nd & 5: Complete short, 3 yards",
            "3rd & 2: Run stuffed, no gain",
            "Punt",
            "1st & 10: Complete to Foster, 18 yards",
        ],
        drive_summary="6 plays, 23 yards, 2:45",
        commentary_type="play_by_play",
        max_duration_seconds=4.0,
        energy_level="normal",
        suggested_focus="statistical_anomaly",
        hooks_to_use=["Second drop today"],
    )


def create_fictional_goal_line_stand() -> CommentaryContext:
    """
    Fictional: Goal line stand - 4th & goal stuff
    Defense makes crucial stop at the 1-yard line
    """
    ball_carrier = make_player("rb_fic3", "Demetrius King", "RB", "DET", 28,
                               carries=22, yards=98, touchdowns=1)
    tackler = make_player("lb_fic3", "Marcus Thompson", "MLB", "GB", 52,
                         tackles=11, tfl=2)

    play = EnrichedPlay(
        play_id="play_fic_003",
        game_id="game_fic_002",
        outcome="rush_no_gain",
        yards_gained=0,
        passer=None,
        receiver=None,
        ball_carrier=ball_carrier,
        tackler=tackler,
        play_concept=PlayConcept(
            play_code="RUN_POWER_LEFT",
            play_type="run",
            formation="i_formation",
            concept_name="power",
            run_direction="left",
            blocking_scheme="power",
        ),
        situation=make_situation(
            down=4, distance=1, field_position="OPP 1",
            yards_to_goal=1, quarter=4, time_remaining="2:15",
            home_score=20, away_score=17, score_diff=3,
            is_red_zone=True, is_goal_to_go=True, is_fourth_down=True,
            is_short_yardage=True,
        ),
        drive_context=make_drive(play_number=11, yards=65, consecutive_firsts=2),
        key_events=["full_house_backfield", "met_in_hole", "tackle_for_loss", "turnover_on_downs"],
        play_duration=3.2,
        throw_time=None,
        air_yards=None,
        yards_after_catch=None,
        was_contested=False,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=False,  # No gain, not negative
        resulted_in_first_down=False,
        resulted_in_touchdown=False,
        resulted_in_turnover=False,  # Turnover on downs isn't a "turnover" stat
    )

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.SITUATIONAL,
            priority=0.95,
            headline="Goal line stand",
            detail="Packers defense holds at the 1-yard line, turnover on downs",
            trigger_player_id=None,
            trigger_stat=None,
            trigger_value=None,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
        NarrativeHook(
            narrative_type=NarrativeType.STREAK,
            priority=0.7,
            headline="Thompson's big day",
            detail="That's Thompson's 11th tackle and 2nd TFL of the game",
            trigger_player_id="lb_fic3",
            trigger_stat="tackles",
            trigger_value=11,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
    ]

    narratives = make_narratives(hooks=hooks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & Goal: Run middle, 2 yards",
            "2nd & Goal: Pass incomplete, thrown away",
            "3rd & Goal: Run right, 1 yard",
        ],
        drive_summary="11 plays, 65 yards, 5:45",
        commentary_type="play_by_play",
        max_duration_seconds=5.0,
        energy_level="tense",
        suggested_focus="situational",
        hooks_to_use=["Goal line stand", "Thompson's big day"],
    )


def create_fictional_hurry_up_td() -> CommentaryContext:
    """
    Fictional: Hurry-up offense touchdown
    No-huddle strike with seconds left in half
    """
    passer = make_player("qb_fic4", "Chris Nakamura", "QB", "SEA", 5,
                         completions=14, attempts=21, yards=178, touchdowns=2)
    receiver = make_player("wr_fic4", "Andre Williams", "WR", "SEA", 19,
                          receptions=6, yards=89, touchdowns=1)

    play = EnrichedPlay(
        play_id="play_fic_004",
        game_id="game_fic_002",
        outcome="complete",
        yards_gained=28,
        passer=passer,
        receiver=receiver,
        ball_carrier=None,
        tackler=None,
        play_concept=PlayConcept(
            play_code="PASS_SEAM_SHOT",
            play_type="pass",
            formation="shotgun_empty",
            concept_name="seam_shot",
            route_tree={"wr1": "seam", "wr2": "corner", "slot1": "post"},
        ),
        situation=make_situation(
            down=1, distance=10, field_position="OPP 28",
            yards_to_goal=28, quarter=2, time_remaining="0:08",
            home_score=14, away_score=10, score_diff=4,
            is_hurry_up=True,
        ),
        drive_context=make_drive(play_number=6, yards=47, time=55, consecutive_firsts=3),
        key_events=["no_huddle", "seam_route", "over_the_top", "touchdown"],
        play_duration=4.5,
        throw_time=2.8,
        air_yards=25,
        yards_after_catch=3,
        was_contested=False,
        was_dropped=False,
        was_big_play=True,
        was_explosive=False,
        was_negative=False,
        resulted_in_first_down=True,
        resulted_in_touchdown=True,
        resulted_in_turnover=False,
    )

    milestones = [
        MilestoneProximity(
            player_id="qb_fic4",
            player_name="Chris Nakamura",
            stat_name="passing_yards",
            current_value=206,
            milestone_value=250,
            yards_needed=44,
            milestone_type="game",
            significance="250-yard game",
        )
    ]

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.SITUATIONAL,
            priority=0.9,
            headline="Before the half",
            detail="Seahawks score with 8 seconds left to extend the lead going into halftime",
            trigger_player_id=None,
            trigger_stat=None,
            trigger_value=None,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
    ]

    narratives = make_narratives(hooks=hooks, milestones=milestones)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "Kickoff return to the 25",
            "1st & 10: Complete sideline, 15 yards, out of bounds",
            "1st & 10: Spike to stop clock",
            "2nd & 10: Complete middle, 12 yards",
            "1st & 10: Complete sideline, 20 yards, out of bounds",
        ],
        drive_summary="6 plays, 75 yards, 0:55",
        commentary_type="play_by_play",
        max_duration_seconds=5.0,
        energy_level="excited",
        suggested_focus="situational",
        hooks_to_use=["Before the half"],
    )


def create_fictional_strip_sack() -> CommentaryContext:
    """
    Fictional: Strip sack fumble recovery
    Defensive end forces fumble, defense recovers
    """
    passer = make_player("qb_fic5", "Brandon Mitchell", "QB", "CAR", 8,
                         completions=18, attempts=29, yards=201, fumbles=1)
    tackler = make_player("edge_fic5", "Terrence Okafor", "EDGE", "TB", 91,
                         sacks=2, forced_fumbles=1, tackles=5)

    play = EnrichedPlay(
        play_id="play_fic_005",
        game_id="game_fic_003",
        outcome="fumble_lost",
        yards_gained=-6,
        passer=passer,
        receiver=None,
        ball_carrier=None,
        tackler=tackler,
        play_concept=PlayConcept(
            play_code="PASS_LEVELS",
            play_type="pass",
            formation="shotgun",
            concept_name="levels_concept",
            route_tree={"wr1": "dig", "wr2": "shallow"},
            protection="6_man",
        ),
        situation=make_situation(
            down=2, distance=7, field_position="OPP 35",
            yards_to_goal=35, quarter=4, time_remaining="5:42",
            home_score=24, away_score=21, score_diff=3,
        ),
        drive_context=make_drive(play_number=7, yards=40, consecutive_firsts=2),
        key_events=["blind_side_hit", "strip_sack", "fumble", "defensive_recovery"],
        play_duration=3.1,
        throw_time=None,
        air_yards=None,
        yards_after_catch=None,
        was_contested=False,
        was_dropped=False,
        was_big_play=False,
        was_explosive=False,
        was_negative=True,
        resulted_in_first_down=False,
        resulted_in_touchdown=False,
        resulted_in_turnover=True,
    )

    hooks = [
        NarrativeHook(
            narrative_type=NarrativeType.MILESTONE,
            priority=0.85,
            headline="Okafor's double-digit sacks",
            detail="That's sack number 10 on the season for Okafor, entering elite company",
            trigger_player_id="edge_fic5",
            trigger_stat="sacks",
            trigger_value=10,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
        NarrativeHook(
            narrative_type=NarrativeType.SITUATIONAL,
            priority=0.9,
            headline="Momentum swing",
            detail="Bucs take over in plus territory with a chance to extend the lead",
            trigger_player_id=None,
            trigger_stat=None,
            trigger_value=None,
            discovered_at=datetime.now(),
            last_mentioned=None,
        ),
    ]

    narratives = make_narratives(hooks=hooks)

    return CommentaryContext(
        play=play,
        narratives=narratives,
        recent_plays_summary=[
            "1st & 10: Run left, 4 yards",
            "2nd & 6: Complete underneath, 8 yards, first down",
            "1st & 10: Complete deep left, 22 yards",
            "1st & 10: Run middle, 6 yards",
        ],
        drive_summary="7 plays, 40 yards, 3:18",
        commentary_type="play_by_play",
        max_duration_seconds=5.0,
        energy_level="excited",
        suggested_focus="milestone",
        hooks_to_use=["Okafor's double-digit sacks", "Momentum swing"],
    )


TEST_SCENARIOS = {
    # Real player scenarios
    "routine": ("Routine Completion", create_routine_completion),
    "big_play": ("Big Play - 45 Yard Bomb", create_big_play),
    "sack": ("Third Down Sack", create_sack),
    "touchdown": ("Red Zone Touchdown", create_touchdown),
    "turnover": ("Interception - Momentum Shift", create_turnover),
    # Fictional player scenarios
    "scramble_td": ("Fictional: Rookie Scramble TD", create_fictional_scramble_td),
    "dropped": ("Fictional: Crucial Dropped Pass", create_fictional_dropped_pass),
    "goal_line": ("Fictional: Goal Line Stand", create_fictional_goal_line_stand),
    "hurry_up": ("Fictional: Hurry-Up TD Before Half", create_fictional_hurry_up_td),
    "strip_sack": ("Fictional: Strip Sack Fumble", create_fictional_strip_sack),
}


def print_prompt_test(name: str, context: CommentaryContext):
    """Print the prompts for a test scenario (no API call)."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print("="*60)

    # Show serialized play
    print("\n--- Serialized Play ---")
    print(serialize_play_for_prompt(context.play))

    # Show narrative hooks
    print("\n--- Narrative Context ---")
    print(serialize_narratives_for_prompt(context.narratives))

    # Build and show play-by-play prompt
    pbp_system, pbp_user = build_play_by_play_prompt(context)
    print("\n--- Play-by-Play User Prompt ---")
    print(pbp_user)

    # Build and show color prompt (with mock play-by-play)
    mock_pbp = "[Play-by-play output would go here]"
    color_system, color_user = build_color_prompt(context, mock_pbp)
    print("\n--- Color Commentary User Prompt ---")
    print(color_user)


async def run_live_test(name: str, context: CommentaryContext):
    """Run a live test against the Gemini API."""
    from .generator import GeminiCommentaryGenerator

    print(f"\n{'='*60}")
    print(f"LIVE TEST: {name}")
    print("="*60)

    async with GeminiCommentaryGenerator() as generator:
        # Generate play-by-play
        print("\n--- Generating Play-by-Play ---")
        pbp_result = await generator.generate_play_by_play_with_metadata(context)
        print(f"Output: {pbp_result.text}")
        print(f"Latency: {pbp_result.latency_ms:.0f}ms")
        print(f"Tokens: {pbp_result.tokens_used}")

        # Generate color
        print("\n--- Generating Color Commentary ---")
        color_result = await generator.generate_color_with_metadata(context)
        print(f"Output: {color_result.text}")
        print(f"Latency: {color_result.latency_ms:.0f}ms")
        print(f"Tokens: {color_result.tokens_used}")

        # Summary
        total_latency = pbp_result.latency_ms + color_result.latency_ms
        total_tokens = pbp_result.tokens_used + color_result.tokens_used
        print(f"\n--- Summary ---")
        print(f"Total Latency: {total_latency:.0f}ms")
        print(f"Total Tokens: {total_tokens}")


def main():
    parser = argparse.ArgumentParser(description="Test commentary prompts")
    parser.add_argument(
        "--play",
        choices=list(TEST_SCENARIOS.keys()) + ["all"],
        default="all",
        help="Which test scenario to run",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the actual Gemini API (requires GEMINI_API_KEY)",
    )
    args = parser.parse_args()

    if args.play == "all":
        scenarios = list(TEST_SCENARIOS.items())
    else:
        scenarios = [(args.play, TEST_SCENARIOS[args.play])]

    for key, (name, factory) in scenarios:
        context = factory()

        if args.live:
            asyncio.run(run_live_test(name, context))
        else:
            print_prompt_test(name, context)


if __name__ == "__main__":
    main()

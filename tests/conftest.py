"""Shared pytest fixtures for Huddle tests."""

import pytest
from uuid import uuid4

from huddle.core.attributes import PlayerAttributes
from huddle.core.enums import (
    DefensiveScheme,
    PassType,
    PlayOutcome,
    PlayType,
    Position,
    RunType,
)
from huddle.core.models.field import DownState, FieldPosition
from huddle.core.models.game import (
    GameClock,
    GamePhase,
    GameState,
    PossessionState,
    ScoreState,
)
from huddle.core.models.play import DefensiveCall, PlayCall, PlayResult
from huddle.core.models.player import Player
from huddle.core.models.team import DepthChart, Roster, Team


# =============================================================================
# Player Fixtures
# =============================================================================


@pytest.fixture
def default_attributes() -> PlayerAttributes:
    """Create default player attributes (all 70s)."""
    attrs = PlayerAttributes()
    for attr in ["speed", "acceleration", "strength", "agility", "awareness",
                 "throw_power", "throw_accuracy_short", "throw_accuracy_mid",
                 "throw_accuracy_deep", "carrying", "catching", "route_running",
                 "run_blocking", "pass_blocking", "tackle", "hit_power",
                 "man_coverage", "zone_coverage", "kick_power", "kick_accuracy"]:
        attrs.set(attr, 70)
    return attrs


@pytest.fixture
def qb_player(default_attributes) -> Player:
    """Create a test quarterback."""
    return Player(
        id=uuid4(),
        first_name="Tom",
        last_name="Brady",
        position=Position.QB,
        attributes=default_attributes,
        age=25,
        jersey_number=12,
    )


@pytest.fixture
def rb_player(default_attributes) -> Player:
    """Create a test running back."""
    return Player(
        id=uuid4(),
        first_name="Derrick",
        last_name="Henry",
        position=Position.RB,
        attributes=default_attributes,
        age=27,
        jersey_number=22,
    )


@pytest.fixture
def wr_player(default_attributes) -> Player:
    """Create a test wide receiver."""
    return Player(
        id=uuid4(),
        first_name="Tyreek",
        last_name="Hill",
        position=Position.WR,
        attributes=default_attributes,
        age=28,
        jersey_number=10,
    )


@pytest.fixture
def defensive_player(default_attributes) -> Player:
    """Create a test defensive player (linebacker)."""
    return Player(
        id=uuid4(),
        first_name="Bobby",
        last_name="Wagner",
        position=Position.MLB,
        attributes=default_attributes,
        age=30,
        jersey_number=54,
    )


# =============================================================================
# Team Fixtures
# =============================================================================


@pytest.fixture
def empty_team() -> Team:
    """Create a team with no players."""
    return Team(
        id=uuid4(),
        name="Eagles",
        abbreviation="PHI",
        city="Philadelphia",
        primary_color="#004C54",
        secondary_color="#A5ACAF",
    )


@pytest.fixture
def basic_roster(qb_player, rb_player, wr_player) -> Roster:
    """Create a basic roster with a few key players."""
    roster = Roster()
    roster.add_player(qb_player)
    roster.add_player(rb_player)
    roster.add_player(wr_player)

    # Set depth chart
    roster.depth_chart.set("QB1", qb_player.id)
    roster.depth_chart.set("RB1", rb_player.id)
    roster.depth_chart.set("WR1", wr_player.id)

    return roster


@pytest.fixture
def home_team(basic_roster) -> Team:
    """Create a home team with roster."""
    team = Team(
        id=uuid4(),
        name="Eagles",
        abbreviation="PHI",
        city="Philadelphia",
        roster=basic_roster,
        primary_color="#004C54",
        secondary_color="#A5ACAF",
        run_tendency=0.45,
        aggression=0.6,
    )
    return team


@pytest.fixture
def away_team() -> Team:
    """Create an away team with basic roster."""
    roster = Roster()

    # Create some players
    qb = Player(first_name="Dak", last_name="Prescott", position=Position.QB)
    rb = Player(first_name="Ezekiel", last_name="Elliott", position=Position.RB)
    wr = Player(first_name="CeeDee", last_name="Lamb", position=Position.WR)

    roster.add_player(qb)
    roster.add_player(rb)
    roster.add_player(wr)
    roster.depth_chart.set("QB1", qb.id)
    roster.depth_chart.set("RB1", rb.id)
    roster.depth_chart.set("WR1", wr.id)

    return Team(
        id=uuid4(),
        name="Cowboys",
        abbreviation="DAL",
        city="Dallas",
        roster=roster,
        primary_color="#003594",
        secondary_color="#869397",
        run_tendency=0.55,
        aggression=0.4,
    )


# =============================================================================
# Field Position Fixtures
# =============================================================================


@pytest.fixture
def own_25() -> FieldPosition:
    """Ball at own 25 yard line."""
    return FieldPosition(25)


@pytest.fixture
def midfield() -> FieldPosition:
    """Ball at midfield."""
    return FieldPosition(50)


@pytest.fixture
def red_zone() -> FieldPosition:
    """Ball in red zone (opponent's 15)."""
    return FieldPosition(85)


@pytest.fixture
def goal_line() -> FieldPosition:
    """Ball at goal line (opponent's 1)."""
    return FieldPosition(99)


@pytest.fixture
def backed_up() -> FieldPosition:
    """Ball backed up at own 5."""
    return FieldPosition(5)


# =============================================================================
# Down State Fixtures
# =============================================================================


@pytest.fixture
def first_and_ten(own_25) -> DownState:
    """Standard 1st and 10 at own 25."""
    return DownState(down=1, yards_to_go=10, line_of_scrimmage=own_25)


@pytest.fixture
def third_and_short(midfield) -> DownState:
    """3rd and 2 at midfield."""
    return DownState(down=3, yards_to_go=2, line_of_scrimmage=midfield)


@pytest.fixture
def fourth_and_goal(goal_line) -> DownState:
    """4th and goal from the 1."""
    return DownState(down=4, yards_to_go=1, line_of_scrimmage=goal_line)


@pytest.fixture
def third_and_long(own_25) -> DownState:
    """3rd and 15 at own 25."""
    return DownState(down=3, yards_to_go=15, line_of_scrimmage=own_25)


# =============================================================================
# Game Clock Fixtures
# =============================================================================


@pytest.fixture
def start_of_game() -> GameClock:
    """Clock at start of game (Q1, 15:00)."""
    return GameClock(quarter=1, time_remaining_seconds=900)


@pytest.fixture
def two_minute_warning() -> GameClock:
    """Clock at two-minute warning in Q4."""
    return GameClock(quarter=4, time_remaining_seconds=120)


@pytest.fixture
def end_of_quarter() -> GameClock:
    """Clock at end of quarter."""
    return GameClock(quarter=1, time_remaining_seconds=0)


@pytest.fixture
def halftime_approaching() -> GameClock:
    """Clock with 30 seconds left in Q2."""
    return GameClock(quarter=2, time_remaining_seconds=30)


# =============================================================================
# Score State Fixtures
# =============================================================================


@pytest.fixture
def tied_game() -> ScoreState:
    """Tied game 14-14."""
    return ScoreState(home_score=14, away_score=14)


@pytest.fixture
def close_game() -> ScoreState:
    """Close game, home leading 21-17."""
    return ScoreState(home_score=21, away_score=17)


@pytest.fixture
def blowout() -> ScoreState:
    """Blowout game, home leading 42-10."""
    return ScoreState(home_score=42, away_score=10)


# =============================================================================
# Game State Fixtures
# =============================================================================


@pytest.fixture
def new_game_state(home_team, away_team) -> GameState:
    """Fresh game state ready to start."""
    state = GameState(
        phase=GamePhase.FIRST_QUARTER,
        clock=GameClock(quarter=1, time_remaining_seconds=900),
    )
    state.set_teams(home_team, away_team)
    state.possession.team_with_ball = home_team.id
    state.down_state = DownState(
        down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(25)
    )
    return state


@pytest.fixture
def mid_game_state(home_team, away_team) -> GameState:
    """Mid-game state (Q3, close game)."""
    state = GameState(
        phase=GamePhase.THIRD_QUARTER,
        clock=GameClock(quarter=3, time_remaining_seconds=450),
        score=ScoreState(home_score=17, away_score=14),
    )
    state.set_teams(home_team, away_team)
    state.possession.team_with_ball = away_team.id
    state.down_state = DownState(
        down=2, yards_to_go=7, line_of_scrimmage=FieldPosition(45)
    )
    return state


@pytest.fixture
def late_game_state(home_team, away_team) -> GameState:
    """Late game state (Q4, 2 minutes, close)."""
    state = GameState(
        phase=GamePhase.FOURTH_QUARTER,
        clock=GameClock(quarter=4, time_remaining_seconds=120),
        score=ScoreState(home_score=24, away_score=21),
    )
    state.set_teams(home_team, away_team)
    state.possession.team_with_ball = away_team.id
    state.down_state = DownState(
        down=1, yards_to_go=10, line_of_scrimmage=FieldPosition(35)
    )
    return state


# =============================================================================
# Play Call Fixtures
# =============================================================================


@pytest.fixture
def run_inside() -> PlayCall:
    """Inside run play call."""
    return PlayCall.run(RunType.INSIDE)


@pytest.fixture
def run_outside() -> PlayCall:
    """Outside run play call."""
    return PlayCall.run(RunType.OUTSIDE)


@pytest.fixture
def pass_short() -> PlayCall:
    """Short pass play call."""
    return PlayCall.pass_play(PassType.SHORT)


@pytest.fixture
def pass_deep() -> PlayCall:
    """Deep pass play call."""
    return PlayCall.pass_play(PassType.DEEP)


@pytest.fixture
def punt_call() -> PlayCall:
    """Punt play call."""
    return PlayCall.punt()


@pytest.fixture
def field_goal_call() -> PlayCall:
    """Field goal play call."""
    return PlayCall.field_goal()


# =============================================================================
# Defensive Call Fixtures
# =============================================================================


@pytest.fixture
def cover_3() -> DefensiveCall:
    """Cover 3 zone defense."""
    return DefensiveCall.cover_3()


@pytest.fixture
def man_coverage() -> DefensiveCall:
    """Man coverage defense."""
    return DefensiveCall.man()


@pytest.fixture
def blitz_5() -> DefensiveCall:
    """5-man blitz."""
    return DefensiveCall.blitz(5)


# =============================================================================
# Play Result Fixtures
# =============================================================================


@pytest.fixture
def completed_pass(pass_short, cover_3) -> PlayResult:
    """Completed short pass for 8 yards."""
    return PlayResult(
        play_call=pass_short,
        defensive_call=cover_3,
        outcome=PlayOutcome.COMPLETE,
        yards_gained=8,
        time_elapsed_seconds=6,
        description="Pass complete for 8 yards",
    )


@pytest.fixture
def rushing_play(run_inside, cover_3) -> PlayResult:
    """Rush for 4 yards."""
    return PlayResult(
        play_call=run_inside,
        defensive_call=cover_3,
        outcome=PlayOutcome.RUSH,
        yards_gained=4,
        time_elapsed_seconds=28,
        description="Rush for 4 yards",
    )


@pytest.fixture
def incomplete_pass(pass_deep, man_coverage) -> PlayResult:
    """Incomplete deep pass."""
    return PlayResult(
        play_call=pass_deep,
        defensive_call=man_coverage,
        outcome=PlayOutcome.INCOMPLETE,
        yards_gained=0,
        time_elapsed_seconds=5,
        clock_stopped=True,
        clock_stop_reason="incomplete",
        description="Pass incomplete",
    )


@pytest.fixture
def touchdown_play(run_inside, cover_3) -> PlayResult:
    """Touchdown run."""
    return PlayResult(
        play_call=run_inside,
        defensive_call=cover_3,
        outcome=PlayOutcome.TOUCHDOWN,
        yards_gained=5,
        time_elapsed_seconds=4,
        is_touchdown=True,
        points_scored=6,
        description="TOUCHDOWN! Rush for 5 yards",
    )


@pytest.fixture
def interception_play(pass_deep, cover_3) -> PlayResult:
    """Interception."""
    return PlayResult(
        play_call=pass_deep,
        defensive_call=cover_3,
        outcome=PlayOutcome.INTERCEPTION,
        yards_gained=0,
        time_elapsed_seconds=4,
        is_turnover=True,
        description="INTERCEPTED!",
    )


@pytest.fixture
def sack_play(pass_short, blitz_5) -> PlayResult:
    """Sack for loss of 7."""
    return PlayResult(
        play_call=pass_short,
        defensive_call=blitz_5,
        outcome=PlayOutcome.SACK,
        yards_gained=-7,
        time_elapsed_seconds=4,
        is_sack=True,
        description="SACKED for loss of 7 yards",
    )

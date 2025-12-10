"""
Admin API Router - League exploration and management.

Provides endpoints for viewing and exploring league data:
- League generation and retrieval
- Team listings and details
- Player search and details
- Standings and schedule
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from huddle.core.league import League, Division, Conference, NFL_TEAMS
from huddle.core.models.stats import GameLog, PlayerSeasonStats
from huddle.generators import generate_league, generate_league_with_schedule
from huddle.generators.player import generate_draft_class
from huddle.simulation import SeasonSimulator, SimulationMode
from huddle.simulation.draft import (
    Draft,
    DraftPick,
    DraftType,
    DraftPhase,
    create_nfl_draft,
    create_fantasy_draft,
)


router = APIRouter(prefix="/admin", tags=["admin"])

# In-memory storage (for demo purposes)
# In production, this would be a database
_active_league: Optional[League] = None
_active_draft: Optional[Draft] = None

# Position display order (familiar football ordering)
POSITION_ORDER = {
    # Offense - skill positions first
    "QB": 1, "RB": 2, "FB": 3, "WR": 4, "TE": 5,
    # Offensive line (left to right)
    "LT": 6, "LG": 7, "C": 8, "RG": 9, "RT": 10,
    # Defensive line
    "DE": 11, "DT": 12, "NT": 13,
    # Linebackers
    "MLB": 14, "ILB": 15, "OLB": 16,
    # Secondary
    "CB": 17, "FS": 18, "SS": 19,
    # Special teams
    "K": 20, "P": 21, "LS": 22,
}


# =============================================================================
# Pydantic Models
# =============================================================================


class LeagueSummary(BaseModel):
    """Summary of a league."""
    id: str
    name: str
    current_season: int
    current_week: int
    team_count: int
    total_players: int
    free_agent_count: int
    draft_class_size: int
    is_offseason: bool
    is_playoffs: bool


class TeamSummary(BaseModel):
    """Summary of a team."""
    id: str
    abbreviation: str
    name: str
    city: str
    full_name: str
    roster_size: int
    primary_color: str
    secondary_color: str
    division: str
    conference: str
    offense_rating: int
    defense_rating: int


class TeamDetail(TeamSummary):
    """Detailed team info including key players."""
    qb_name: Optional[str] = None
    qb_overall: Optional[int] = None
    top_players: list[dict] = Field(default_factory=list)


class PlayerSummary(BaseModel):
    """Summary of a player."""
    id: str
    first_name: str
    last_name: str
    full_name: str
    position: str
    overall: int
    potential: int
    age: int
    experience: int
    jersey_number: int
    team_abbr: Optional[str] = None


class PlayerDetail(PlayerSummary):
    """Detailed player info including all attributes."""
    height: str
    weight: int
    college: Optional[str] = None
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None
    years_on_team: int
    is_rookie: bool
    is_veteran: bool
    attributes: dict = Field(default_factory=dict)


class StandingEntry(BaseModel):
    """Single team standing."""
    rank: int
    abbreviation: str
    team_name: str
    wins: int
    losses: int
    ties: int
    record: str
    win_pct: float
    division_record: str
    points_for: int
    points_against: int
    point_diff: int


class DivisionStandings(BaseModel):
    """Standings for a division."""
    division: str
    conference: str
    teams: list[StandingEntry]


class GenerateLeagueRequest(BaseModel):
    """Request to generate a new league."""
    season: int = 2024
    name: str = "NFL"
    include_schedule: bool = True
    parity_mode: bool = False
    fantasy_draft: bool = False  # If True, start with empty rosters and run fantasy draft


class SimulateWeekRequest(BaseModel):
    """Request to simulate a specific week."""
    week: Optional[int] = Field(None, ge=1, le=22, description="Week to simulate. If None, simulates next week.")


class SimulateToWeekRequest(BaseModel):
    """Request to simulate up to a specific week."""
    target_week: int = Field(..., ge=1, le=18, description="Week to simulate up to (inclusive)")


class GameResultResponse(BaseModel):
    """Result of a single game."""
    game_id: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    winner: Optional[str]
    is_overtime: bool
    is_tie: bool


class WeekResultResponse(BaseModel):
    """Results from simulating a week."""
    week: int
    games: list[GameResultResponse]
    total_games: int


class PlayoffTeamResponse(BaseModel):
    """Playoff team info."""
    seed: int
    abbreviation: str
    team_name: str
    record: str
    win_pct: float
    is_division_winner: bool


class PlayoffPictureResponse(BaseModel):
    """Current playoff picture."""
    afc: list[PlayoffTeamResponse]
    nfc: list[PlayoffTeamResponse]


class PassingStatsResponse(BaseModel):
    """Passing statistics."""
    attempts: int
    completions: int
    yards: int
    touchdowns: int
    interceptions: int
    sacks: int
    completion_pct: float
    passer_rating: float


class RushingStatsResponse(BaseModel):
    """Rushing statistics."""
    attempts: int
    yards: int
    touchdowns: int
    fumbles_lost: int
    yards_per_carry: float
    longest: int


class ReceivingStatsResponse(BaseModel):
    """Receiving statistics."""
    targets: int
    receptions: int
    yards: int
    touchdowns: int
    yards_per_reception: float
    catch_pct: float


class DefensiveStatsResponse(BaseModel):
    """Defensive statistics."""
    tackles: int
    sacks: float
    interceptions: int
    passes_defended: int
    forced_fumbles: int
    fumble_recoveries: int


class PlayerSeasonStatsResponse(BaseModel):
    """Player season statistics."""
    player_id: str
    player_name: str
    team_abbr: str
    position: str
    games_played: int
    passing: Optional[PassingStatsResponse] = None
    rushing: Optional[RushingStatsResponse] = None
    receiving: Optional[ReceivingStatsResponse] = None
    defense: Optional[DefensiveStatsResponse] = None


class TeamGameStatsResponse(BaseModel):
    """Team game statistics."""
    team_abbr: str
    total_yards: int
    passing_yards: int
    rushing_yards: int
    first_downs: int
    turnovers: int
    penalties: int
    penalty_yards: int
    time_of_possession: str


class GameDetailResponse(BaseModel):
    """Detailed game information including stats."""
    game_id: str
    week: int
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    is_overtime: bool
    is_playoff: bool
    home_stats: TeamGameStatsResponse
    away_stats: TeamGameStatsResponse
    scoring_plays: list[dict]


class DepthChartEntry(BaseModel):
    """Single depth chart entry."""
    slot: str
    player_id: Optional[str]
    player_name: Optional[str]
    position: Optional[str]
    overall: Optional[int]


class DepthChartResponse(BaseModel):
    """Team depth chart."""
    team_abbr: str
    offense: list[DepthChartEntry]
    defense: list[DepthChartEntry]
    special_teams: list[DepthChartEntry]


class PlayoffBracketGame(BaseModel):
    """Single playoff game in bracket."""
    game_id: Optional[str]
    week: int
    round_name: str
    home_team: Optional[str]
    away_team: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    winner: Optional[str]
    is_played: bool


class PlayoffBracketResponse(BaseModel):
    """Full playoff bracket."""
    wild_card: list[PlayoffBracketGame]
    divisional: list[PlayoffBracketGame]
    conference: list[PlayoffBracketGame]
    super_bowl: Optional[PlayoffBracketGame]
    champion: Optional[str]


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/league/generate", response_model=LeagueSummary)
async def generate_new_league(request: GenerateLeagueRequest) -> LeagueSummary:
    """Generate a new 32-team NFL league."""
    global _active_league

    if request.include_schedule:
        _active_league = generate_league_with_schedule(
            season=request.season,
            name=request.name,
            parity_mode=request.parity_mode,
        )
    else:
        _active_league = generate_league(
            season=request.season,
            name=request.name,
            parity_mode=request.parity_mode,
        )

    # If fantasy draft mode, clear rosters and run fantasy draft
    if request.fantasy_draft:
        # Clear all team rosters
        for team in _active_league.teams.values():
            team.roster.players.clear()
            team.roster.depth_chart.slots.clear()

        # Generate large player pool (10 years of draft classes for variety)
        all_players = []
        for year in range(request.season - 9, request.season + 1):
            all_players.extend(generate_draft_class(year))

        # Create and run fantasy draft (53 rounds for full rosters)
        draft = create_fantasy_draft(
            team_abbrs=list(_active_league.teams.keys()),
            all_players=all_players,
            num_rounds=53,
        )

        # Simulate the full draft
        draft.simulate_full_draft(_active_league.teams, add_to_rosters=True)

        # Auto-fill depth charts now that rosters are complete
        for team in _active_league.teams.values():
            team.roster.auto_fill_depth_chart()

        # Clear draft class and free agents since we built fresh rosters
        _active_league.draft_class = []
        _active_league.free_agents = []

    return _league_to_summary(_active_league)


@router.get("/league", response_model=LeagueSummary)
async def get_league() -> LeagueSummary:
    """Get current league summary."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded. Generate one first.")
    return _league_to_summary(_active_league)


@router.get("/teams", response_model=list[TeamSummary])
async def list_teams(
    conference: Optional[str] = Query(None, description="Filter by conference (AFC/NFC)"),
    division: Optional[str] = Query(None, description="Filter by division"),
) -> list[TeamSummary]:
    """List all teams in the league."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    teams = list(_active_league.teams.values())

    # Filter by conference
    if conference:
        conf = Conference.AFC if conference.upper() == "AFC" else Conference.NFC
        teams = [t for t in teams if _active_league.get_conference_for_team(t.abbreviation) == conf]

    # Filter by division
    if division:
        div_map = {d.value.upper(): d for d in Division}
        if division.upper() in div_map:
            div = div_map[division.upper()]
            teams = [t for t in teams if _active_league.get_division_for_team(t.abbreviation) == div]

    return [_team_to_summary(t, _active_league) for t in teams]


@router.get("/teams/{abbreviation}", response_model=TeamDetail)
async def get_team(abbreviation: str) -> TeamDetail:
    """Get detailed info for a specific team."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    team = _active_league.get_team(abbreviation.upper())
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team {abbreviation} not found")

    return _team_to_detail(team, _active_league)


@router.get("/teams/{abbreviation}/roster", response_model=list[PlayerSummary])
async def get_team_roster(
    abbreviation: str,
    position: Optional[str] = Query(None, description="Filter by position"),
    sort_by: str = Query("depth_chart", description="Sort by: depth_chart, overall, age, name, position"),
) -> list[PlayerSummary]:
    """Get full roster for a team.

    Default sort is 'depth_chart' which orders by position (QB, RB, WR, TE, OL, DL, LB, DB, ST)
    and then by overall rating within each position.
    """
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    team = _active_league.get_team(abbreviation.upper())
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team {abbreviation} not found")

    players = list(team.roster.players.values())

    # Filter by position
    if position:
        players = [p for p in players if p.position.value.upper() == position.upper()]

    # Sort
    if sort_by == "depth_chart":
        # Sort by position order, then by overall within position (best first)
        players.sort(key=lambda p: (
            POSITION_ORDER.get(p.position.value, 99),
            -p.overall  # Negative for descending
        ))
    elif sort_by == "overall":
        players.sort(key=lambda p: p.overall, reverse=True)
    elif sort_by == "age":
        players.sort(key=lambda p: p.age)
    elif sort_by == "name":
        players.sort(key=lambda p: p.last_name)
    elif sort_by == "position":
        # Alphabetical position sort (legacy behavior)
        players.sort(key=lambda p: p.position.value)

    return [_player_to_summary(p, abbreviation.upper()) for p in players]


@router.get("/players/{player_id}", response_model=PlayerDetail)
async def get_player(player_id: str) -> PlayerDetail:
    """Get detailed info for a specific player."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    # Search all teams for the player
    for abbr, team in _active_league.teams.items():
        try:
            pid = UUID(player_id)
            player = team.roster.get_player(pid)
            if player:
                return _player_to_detail(player, abbr)
        except ValueError:
            pass

    # Check free agents
    for player in _active_league.free_agents:
        if str(player.id) == player_id:
            return _player_to_detail(player, None)

    raise HTTPException(status_code=404, detail="Player not found")


@router.get("/players", response_model=list[PlayerSummary])
async def search_players(
    position: Optional[str] = Query(None, description="Filter by position"),
    min_overall: int = Query(0, ge=0, le=99),
    max_overall: int = Query(99, ge=0, le=99),
    team: Optional[str] = Query(None, description="Filter by team abbreviation"),
    limit: int = Query(50, ge=1, le=200),
) -> list[PlayerSummary]:
    """Search players across all teams."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    results = []

    # Collect players from teams
    for abbr, t in _active_league.teams.items():
        if team and abbr.upper() != team.upper():
            continue

        for player in t.roster.players.values():
            if position and player.position.value.upper() != position.upper():
                continue
            if not (min_overall <= player.overall <= max_overall):
                continue
            results.append(_player_to_summary(player, abbr))

    # Sort by overall descending
    results.sort(key=lambda p: p.overall, reverse=True)

    return results[:limit]


@router.get("/free-agents", response_model=list[PlayerSummary])
async def get_free_agents(
    position: Optional[str] = Query(None),
    min_overall: int = Query(0, ge=0, le=99),
    limit: int = Query(50, ge=1, le=200),
) -> list[PlayerSummary]:
    """Get free agent pool."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    players = _active_league.free_agents

    if position:
        players = [p for p in players if p.position.value.upper() == position.upper()]

    players = [p for p in players if p.overall >= min_overall]
    players.sort(key=lambda p: p.overall, reverse=True)

    return [_player_to_summary(p, None) for p in players[:limit]]


@router.get("/draft-class", response_model=list[PlayerSummary])
async def get_draft_class(
    position: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=300),
) -> list[PlayerSummary]:
    """Get draft class prospects."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    players = _active_league.draft_class

    if position:
        players = [p for p in players if p.position.value.upper() == position.upper()]

    return [_player_to_summary(p, None) for p in players[:limit]]


@router.get("/standings", response_model=list[DivisionStandings])
async def get_standings(
    conference: Optional[str] = Query(None, description="Filter by conference (AFC/NFC)"),
) -> list[DivisionStandings]:
    """Get league standings by division."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    result = []

    for div in Division:
        # Filter by conference if specified
        if conference:
            conf = Conference.AFC if conference.upper() == "AFC" else Conference.NFC
            if div.conference != conf:
                continue

        standings = _active_league.get_division_standings(div)
        entries = []

        for rank, s in enumerate(standings, 1):
            team = _active_league.get_team(s.abbreviation)
            team_name = team.full_name if team else s.abbreviation

            entries.append(StandingEntry(
                rank=rank,
                abbreviation=s.abbreviation,
                team_name=team_name,
                wins=s.wins,
                losses=s.losses,
                ties=s.ties,
                record=s.record_string,
                win_pct=round(s.win_pct, 3),
                division_record=f"{s.division_wins}-{s.division_losses}",
                points_for=s.points_for,
                points_against=s.points_against,
                point_diff=s.point_diff,
            ))

        result.append(DivisionStandings(
            division=div.value,
            conference=div.conference.value,
            teams=entries,
        ))

    return result


@router.get("/schedule")
async def get_schedule(
    week: Optional[int] = Query(None, ge=1, le=22),
    team: Optional[str] = Query(None),
) -> list[dict]:
    """Get league schedule."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    games = _active_league.schedule

    if week:
        games = [g for g in games if g.week == week]

    if team:
        team = team.upper()
        games = [g for g in games if g.home_team_abbr == team or g.away_team_abbr == team]

    return [
        {
            "id": str(g.id),
            "week": g.week,
            "home_team": g.home_team_abbr,
            "away_team": g.away_team_abbr,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "is_played": g.is_played,
            "is_divisional": g.is_divisional,
            "is_conference": g.is_conference,
            "winner": g.winner_abbr,
        }
        for g in games
    ]


# =============================================================================
# Simulation Endpoints
# =============================================================================


@router.post("/simulate/week", response_model=WeekResultResponse)
async def simulate_week(request: SimulateWeekRequest) -> WeekResultResponse:
    """Simulate all games for a week."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    simulator = SeasonSimulator(_active_league, mode=SimulationMode.FAST)
    week_result = simulator.simulate_week(request.week)

    return WeekResultResponse(
        week=week_result.week,
        games=[
            GameResultResponse(
                game_id=str(g.game_id),
                home_team=g.home_team_abbr,
                away_team=g.away_team_abbr,
                home_score=g.home_score,
                away_score=g.away_score,
                winner=g.winner_abbr,
                is_overtime=g.is_overtime,
                is_tie=g.is_tie,
            )
            for g in week_result.games
        ],
        total_games=week_result.total_games,
    )


@router.post("/simulate/to-week", response_model=list[WeekResultResponse])
async def simulate_to_week(request: SimulateToWeekRequest) -> list[WeekResultResponse]:
    """Simulate from current week to target week (inclusive)."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    simulator = SeasonSimulator(_active_league, mode=SimulationMode.FAST)
    week_results = simulator.simulate_to_week(request.target_week)

    return [
        WeekResultResponse(
            week=wr.week,
            games=[
                GameResultResponse(
                    game_id=str(g.game_id),
                    home_team=g.home_team_abbr,
                    away_team=g.away_team_abbr,
                    home_score=g.home_score,
                    away_score=g.away_score,
                    winner=g.winner_abbr,
                    is_overtime=g.is_overtime,
                    is_tie=g.is_tie,
                )
                for g in wr.games
            ],
            total_games=wr.total_games,
        )
        for wr in week_results
    ]


@router.post("/simulate/season", response_model=list[WeekResultResponse])
async def simulate_full_season() -> list[WeekResultResponse]:
    """Simulate the entire regular season (weeks 1-18)."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    simulator = SeasonSimulator(_active_league, mode=SimulationMode.FAST)
    week_results = simulator.simulate_regular_season()

    return [
        WeekResultResponse(
            week=wr.week,
            games=[
                GameResultResponse(
                    game_id=str(g.game_id),
                    home_team=g.home_team_abbr,
                    away_team=g.away_team_abbr,
                    home_score=g.home_score,
                    away_score=g.away_score,
                    winner=g.winner_abbr,
                    is_overtime=g.is_overtime,
                    is_tie=g.is_tie,
                )
                for g in wr.games
            ],
            total_games=wr.total_games,
        )
        for wr in week_results
    ]


@router.get("/playoff-picture", response_model=PlayoffPictureResponse)
async def get_playoff_picture() -> PlayoffPictureResponse:
    """Get current playoff bracket for both conferences."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    afc_bracket = _active_league.get_playoff_bracket(Conference.AFC)
    nfc_bracket = _active_league.get_playoff_bracket(Conference.NFC)

    def to_response(standings: list, is_afc: bool) -> list[PlayoffTeamResponse]:
        result = []
        for i, s in enumerate(standings):
            team = _active_league.get_team(s.abbreviation)
            team_name = team.full_name if team else s.abbreviation
            result.append(PlayoffTeamResponse(
                seed=i + 1,
                abbreviation=s.abbreviation,
                team_name=team_name,
                record=s.record_string,
                win_pct=round(s.win_pct, 3),
                is_division_winner=i < 4,  # Seeds 1-4 are division winners
            ))
        return result

    return PlayoffPictureResponse(
        afc=to_response(afc_bracket, True),
        nfc=to_response(nfc_bracket, False),
    )


# =============================================================================
# Game Details & Stats Endpoints
# =============================================================================


@router.get("/games/{game_id}", response_model=GameDetailResponse)
async def get_game_detail(game_id: str) -> GameDetailResponse:
    """Get detailed game information including stats and plays."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    game_log = _active_league.game_logs.get(game_id)
    if not game_log:
        raise HTTPException(status_code=404, detail="Game not found or not yet played")

    return GameDetailResponse(
        game_id=str(game_log.game_id),
        week=game_log.week,
        home_team=game_log.home_team_abbr,
        away_team=game_log.away_team_abbr,
        home_score=game_log.home_score,
        away_score=game_log.away_score,
        is_overtime=game_log.is_overtime,
        is_playoff=game_log.is_playoff,
        home_stats=TeamGameStatsResponse(
            team_abbr=game_log.home_stats.team_abbr,
            total_yards=game_log.home_stats.total_yards,
            passing_yards=game_log.home_stats.passing_yards,
            rushing_yards=game_log.home_stats.rushing_yards,
            first_downs=game_log.home_stats.first_downs,
            turnovers=game_log.home_stats.turnovers,
            penalties=game_log.home_stats.penalties,
            penalty_yards=game_log.home_stats.penalty_yards,
            time_of_possession=game_log.home_stats.time_of_possession_display,
        ),
        away_stats=TeamGameStatsResponse(
            team_abbr=game_log.away_stats.team_abbr,
            total_yards=game_log.away_stats.total_yards,
            passing_yards=game_log.away_stats.passing_yards,
            rushing_yards=game_log.away_stats.rushing_yards,
            first_downs=game_log.away_stats.first_downs,
            turnovers=game_log.away_stats.turnovers,
            penalties=game_log.away_stats.penalties,
            penalty_yards=game_log.away_stats.penalty_yards,
            time_of_possession=game_log.away_stats.time_of_possession_display,
        ),
        scoring_plays=game_log.scoring_plays,
    )


@router.get("/games/{game_id}/plays")
async def get_game_plays(
    game_id: str,
    quarter: Optional[int] = Query(None, ge=1, le=5),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """Get play-by-play data for a game."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    game_log = _active_league.game_logs.get(game_id)
    if not game_log:
        raise HTTPException(status_code=404, detail="Game not found")

    plays = game_log.plays
    if quarter:
        plays = [p for p in plays if p.get('quarter') == quarter]

    return plays[offset:offset + limit]


@router.get("/games/{game_id}/stats")
async def get_game_player_stats(game_id: str) -> list[dict]:
    """Get all player stats for a game."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    game_log = _active_league.game_logs.get(game_id)
    if not game_log:
        raise HTTPException(status_code=404, detail="Game not found")

    return [stats.to_dict() for stats in game_log.player_stats.values()]


@router.get("/stats/leaders")
async def get_season_leaders(
    category: str = Query(..., description="passing, rushing, receiving, defense"),
    stat: str = Query(..., description="yards, touchdowns, interceptions, etc."),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict]:
    """Get season statistical leaders."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    valid_categories = ['passing', 'rushing', 'receiving', 'defense', 'kicking']
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Use: {valid_categories}")

    try:
        leaders = _active_league.get_season_leaders(category, stat, limit)
    except AttributeError:
        raise HTTPException(status_code=400, detail=f"Invalid stat '{stat}' for category '{category}'")

    return [
        {
            "rank": i + 1,
            "player_id": str(stats.player_id),
            "player_name": stats.player_name,
            "team_abbr": stats.team_abbr,
            "position": stats.position,
            "games_played": stats.games_played,
            "value": value,
        }
        for i, (stats, value) in enumerate(leaders)
    ]


@router.get("/stats/player/{player_id}", response_model=PlayerSeasonStatsResponse)
async def get_player_season_stats(player_id: str) -> PlayerSeasonStatsResponse:
    """Get season stats for a specific player."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    stats = _active_league.season_stats.get(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="No stats found for player")

    response = PlayerSeasonStatsResponse(
        player_id=str(stats.player_id),
        player_name=stats.player_name,
        team_abbr=stats.team_abbr,
        position=stats.position,
        games_played=stats.games_played,
    )

    # Add passing stats if any attempts
    if stats.passing.attempts > 0:
        response.passing = PassingStatsResponse(
            attempts=stats.passing.attempts,
            completions=stats.passing.completions,
            yards=stats.passing.yards,
            touchdowns=stats.passing.touchdowns,
            interceptions=stats.passing.interceptions,
            sacks=stats.passing.sacks,
            completion_pct=round(stats.passing.completion_pct, 1),
            passer_rating=round(stats.passing.passer_rating, 1),
        )

    # Add rushing stats if any attempts
    if stats.rushing.attempts > 0:
        response.rushing = RushingStatsResponse(
            attempts=stats.rushing.attempts,
            yards=stats.rushing.yards,
            touchdowns=stats.rushing.touchdowns,
            fumbles_lost=stats.rushing.fumbles_lost,
            yards_per_carry=round(stats.rushing.yards_per_carry, 1),
            longest=stats.rushing.longest,
        )

    # Add receiving stats if any targets
    if stats.receiving.targets > 0:
        response.receiving = ReceivingStatsResponse(
            targets=stats.receiving.targets,
            receptions=stats.receiving.receptions,
            yards=stats.receiving.yards,
            touchdowns=stats.receiving.touchdowns,
            yards_per_reception=round(stats.receiving.yards_per_reception, 1),
            catch_pct=round(stats.receiving.catch_pct, 1),
        )

    # Add defensive stats if any tackles
    if stats.defense.tackles > 0:
        response.defense = DefensiveStatsResponse(
            tackles=stats.defense.tackles,
            sacks=stats.defense.sacks,
            interceptions=stats.defense.interceptions,
            passes_defended=stats.defense.passes_defended,
            forced_fumbles=stats.defense.forced_fumbles,
            fumble_recoveries=stats.defense.fumble_recoveries,
        )

    return response


# =============================================================================
# Depth Chart Endpoints
# =============================================================================


@router.get("/teams/{abbreviation}/stats")
async def get_team_stats(abbreviation: str) -> dict:
    """Get season stats for all players on a team."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    team = _active_league.get_team(abbreviation.upper())
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Collect stats for players on this team
    passing = []
    rushing = []
    receiving = []
    defense = []

    for player_id_str, stats in _active_league.season_stats.items():
        if stats.team_abbr != abbreviation.upper():
            continue

        if stats.passing.attempts > 0:
            passing.append({
                "player_id": player_id_str,
                "player_name": stats.player_name,
                "position": stats.position,
                "games": stats.games_played,
                "attempts": stats.passing.attempts,
                "completions": stats.passing.completions,
                "yards": stats.passing.yards,
                "touchdowns": stats.passing.touchdowns,
                "interceptions": stats.passing.interceptions,
                "completion_pct": round(stats.passing.completion_pct, 1),
                "passer_rating": round(stats.passing.passer_rating, 1),
            })

        if stats.rushing.attempts > 0:
            rushing.append({
                "player_id": player_id_str,
                "player_name": stats.player_name,
                "position": stats.position,
                "games": stats.games_played,
                "attempts": stats.rushing.attempts,
                "yards": stats.rushing.yards,
                "touchdowns": stats.rushing.touchdowns,
                "yards_per_carry": round(stats.rushing.yards_per_carry, 1),
                "fumbles_lost": stats.rushing.fumbles_lost,
            })

        if stats.receiving.receptions > 0:
            receiving.append({
                "player_id": player_id_str,
                "player_name": stats.player_name,
                "position": stats.position,
                "games": stats.games_played,
                "receptions": stats.receiving.receptions,
                "targets": stats.receiving.targets,
                "yards": stats.receiving.yards,
                "touchdowns": stats.receiving.touchdowns,
                "yards_per_reception": round(stats.receiving.yards_per_reception, 1),
            })

        if stats.defense.tackles > 0:
            defense.append({
                "player_id": player_id_str,
                "player_name": stats.player_name,
                "position": stats.position,
                "games": stats.games_played,
                "tackles": stats.defense.tackles,
                "sacks": stats.defense.sacks,
                "interceptions": stats.defense.interceptions,
                "passes_defended": stats.defense.passes_defended,
                "forced_fumbles": stats.defense.forced_fumbles,
            })

    # Sort by primary stat
    passing.sort(key=lambda x: x["yards"], reverse=True)
    rushing.sort(key=lambda x: x["yards"], reverse=True)
    receiving.sort(key=lambda x: x["yards"], reverse=True)
    defense.sort(key=lambda x: x["tackles"], reverse=True)

    return {
        "team_abbr": abbreviation.upper(),
        "passing": passing,
        "rushing": rushing,
        "receiving": receiving,
        "defense": defense,
    }


@router.get("/teams/{abbreviation}/depth-chart", response_model=DepthChartResponse)
async def get_team_depth_chart(abbreviation: str) -> DepthChartResponse:
    """Get team's depth chart."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    team = _active_league.get_team(abbreviation.upper())
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    depth_chart = team.roster.depth_chart

    def get_entries(slots: list[str]) -> list[DepthChartEntry]:
        entries = []
        for slot in slots:
            player_id = depth_chart.slots.get(slot)
            if player_id:
                player = team.roster.get_player(player_id)
                entries.append(DepthChartEntry(
                    slot=slot,
                    player_id=str(player_id),
                    player_name=player.full_name if player else None,
                    position=player.position.value if player else None,
                    overall=player.overall if player else None,
                ))
            else:
                entries.append(DepthChartEntry(slot=slot, player_id=None, player_name=None, position=None, overall=None))
        return entries

    offense_slots = [
        'QB1', 'QB2', 'RB1', 'RB2', 'FB1',
        'WR1', 'WR2', 'WR3', 'WR4', 'TE1', 'TE2',
        'LT1', 'LG1', 'C1', 'RG1', 'RT1',
    ]
    defense_slots = [
        'DE1', 'DE2', 'DT1', 'DT2', 'NT1',
        'MLB1', 'MLB2', 'OLB1', 'OLB2', 'ILB1',
        'CB1', 'CB2', 'CB3', 'FS1', 'SS1',
    ]
    special_slots = ['K1', 'P1', 'LS1']

    return DepthChartResponse(
        team_abbr=abbreviation.upper(),
        offense=get_entries(offense_slots),
        defense=get_entries(defense_slots),
        special_teams=get_entries(special_slots),
    )


# =============================================================================
# Playoff Simulation Endpoints
# =============================================================================


@router.post("/simulate/playoffs")
async def simulate_playoffs() -> dict:
    """Simulate entire playoff bracket."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    if _active_league.current_week < 18:
        raise HTTPException(status_code=400, detail="Regular season must be complete (week 18)")

    simulator = SeasonSimulator(_active_league, mode=SimulationMode.FAST)
    results = simulator.simulate_playoffs()

    return {
        "wild_card": [
            {
                "home_team": g.home_team_abbr,
                "away_team": g.away_team_abbr,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "winner": g.winner_abbr,
            }
            for g in results['wild_card']
        ],
        "divisional": [
            {
                "home_team": g.home_team_abbr,
                "away_team": g.away_team_abbr,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "winner": g.winner_abbr,
            }
            for g in results['divisional']
        ],
        "conference": [
            {
                "home_team": g.home_team_abbr,
                "away_team": g.away_team_abbr,
                "home_score": g.home_score,
                "away_score": g.away_score,
                "winner": g.winner_abbr,
            }
            for g in results['conference']
        ],
        "super_bowl": {
            "home_team": results['super_bowl'].home_team_abbr,
            "away_team": results['super_bowl'].away_team_abbr,
            "home_score": results['super_bowl'].home_score,
            "away_score": results['super_bowl'].away_score,
            "winner": results['super_bowl'].winner_abbr,
        } if results['super_bowl'] else None,
        "champion": _active_league.champions.get(_active_league.current_season),
    }


@router.get("/playoff-bracket", response_model=PlayoffBracketResponse)
async def get_playoff_bracket() -> PlayoffBracketResponse:
    """Get current state of playoff bracket."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    def games_for_week(week: int, round_name: str) -> list[PlayoffBracketGame]:
        games = [g for g in _active_league.schedule if g.week == week and g.is_playoff]
        return [
            PlayoffBracketGame(
                game_id=str(g.id),
                week=g.week,
                round_name=round_name,
                home_team=g.home_team_abbr,
                away_team=g.away_team_abbr,
                home_score=g.home_score,
                away_score=g.away_score,
                winner=g.winner_abbr,
                is_played=g.is_played,
            )
            for g in games
        ]

    sb_games = games_for_week(22, "Super Bowl")

    return PlayoffBracketResponse(
        wild_card=games_for_week(19, "Wild Card"),
        divisional=games_for_week(20, "Divisional"),
        conference=games_for_week(21, "Conference Championship"),
        super_bowl=sb_games[0] if sb_games else None,
        champion=_active_league.champions.get(_active_league.current_season),
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _league_to_summary(league: League) -> LeagueSummary:
    """Convert League to summary."""
    return LeagueSummary(
        id=str(league.id),
        name=league.name,
        current_season=league.current_season,
        current_week=league.current_week,
        team_count=len(league.teams),
        total_players=league.total_players,
        free_agent_count=len(league.free_agents),
        draft_class_size=len(league.draft_class),
        is_offseason=league.is_offseason,
        is_playoffs=league.is_playoffs,
    )


def _team_to_summary(team, league: League) -> TeamSummary:
    """Convert Team to summary."""
    division = league.get_division_for_team(team.abbreviation)
    conference = league.get_conference_for_team(team.abbreviation)

    return TeamSummary(
        id=str(team.id),
        abbreviation=team.abbreviation,
        name=team.name,
        city=team.city,
        full_name=team.full_name,
        roster_size=team.roster.size,
        primary_color=team.primary_color,
        secondary_color=team.secondary_color,
        division=division.value if division else "Unknown",
        conference=conference.value if conference else "Unknown",
        offense_rating=team.calculate_offense_rating(),
        defense_rating=team.calculate_defense_rating(),
    )


def _team_to_detail(team, league: League) -> TeamDetail:
    """Convert Team to detail."""
    summary = _team_to_summary(team, league)

    qb = team.get_qb()
    top_players = sorted(
        team.roster.players.values(),
        key=lambda p: p.overall,
        reverse=True
    )[:10]

    return TeamDetail(
        **summary.model_dump(),
        qb_name=qb.full_name if qb else None,
        qb_overall=qb.overall if qb else None,
        top_players=[
            {
                "id": str(p.id),
                "name": p.full_name,
                "position": p.position.value,
                "overall": p.overall,
                "jersey": p.jersey_number,
            }
            for p in top_players
        ],
    )


def _player_to_summary(player, team_abbr: Optional[str]) -> PlayerSummary:
    """Convert Player to summary."""
    return PlayerSummary(
        id=str(player.id),
        first_name=player.first_name,
        last_name=player.last_name,
        full_name=player.full_name,
        position=player.position.value,
        overall=player.overall,
        potential=player.potential,
        age=player.age,
        experience=player.experience_years,
        jersey_number=player.jersey_number,
        team_abbr=team_abbr,
    )


def _player_to_detail(player, team_abbr: Optional[str]) -> PlayerDetail:
    """Convert Player to detail."""
    return PlayerDetail(
        id=str(player.id),
        first_name=player.first_name,
        last_name=player.last_name,
        full_name=player.full_name,
        position=player.position.value,
        overall=player.overall,
        potential=player.potential,
        age=player.age,
        experience=player.experience_years,
        jersey_number=player.jersey_number,
        team_abbr=team_abbr,
        height=player.height_display,
        weight=player.weight_lbs,
        college=player.college,
        draft_year=player.draft_year,
        draft_round=player.draft_round,
        draft_pick=player.draft_pick,
        years_on_team=player.years_on_team,
        is_rookie=player.is_rookie,
        is_veteran=player.is_veteran,
        attributes=player.attributes.to_dict(),
    )


# =============================================================================
# Draft Pydantic Models
# =============================================================================


class DraftPickResponse(BaseModel):
    """Response for a draft pick."""
    id: str
    round: int
    pick_number: int
    round_pick: int
    original_team: str
    current_team: str
    is_selected: bool
    was_traded: bool
    player_id: Optional[str] = None
    player_name: Optional[str] = None
    player_position: Optional[str] = None


class DraftStateResponse(BaseModel):
    """Response for current draft state."""
    id: str
    draft_type: str
    phase: str
    season: int
    num_rounds: int
    num_teams: int
    current_pick_index: int
    current_round: int
    picks_made: int
    picks_remaining: int
    is_user_pick: bool
    user_team: Optional[str] = None
    current_pick: Optional[DraftPickResponse] = None


class CreateDraftRequest(BaseModel):
    """Request to create a new draft."""
    draft_type: str = "nfl"  # "nfl" or "fantasy"
    num_rounds: int = 7
    user_team: Optional[str] = None


class MakePickRequest(BaseModel):
    """Request to make a draft pick."""
    player_id: str


class DraftResultResponse(BaseModel):
    """Response with draft results."""
    picks_made: list[DraftPickResponse]
    draft_complete: bool


# =============================================================================
# Draft Endpoints
# =============================================================================


@router.post("/draft/create")
async def create_draft(request: CreateDraftRequest) -> DraftStateResponse:
    """
    Create a new draft.

    For NFL draft: uses league's draft class and draft order
    For Fantasy draft: all players are available, random snake order
    """
    global _active_draft

    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    if request.draft_type == "fantasy":
        # Fantasy draft - all players from all rosters + free agents
        all_players = list(_active_league.free_agents)
        for team in _active_league.teams.values():
            all_players.extend(team.roster.players.values())

        _active_draft = create_fantasy_draft(
            team_abbrs=list(_active_league.teams.keys()),
            all_players=all_players,
            num_rounds=request.num_rounds,
            user_team=request.user_team,
        )

        # Clear rosters for fantasy draft
        for team in _active_league.teams.values():
            team.roster.players.clear()
            team.roster.depth_chart.slots.clear()
    else:
        # NFL draft - use draft class and standings-based order
        if not _active_league.draft_class:
            raise HTTPException(status_code=400, detail="No draft class available")

        # Use existing draft order or set from standings
        if not _active_league.draft_order:
            _active_league.set_draft_order(reverse_standings=True)

        _active_draft = create_nfl_draft(
            season=_active_league.current_season,
            team_order=_active_league.draft_order,
            draft_class=_active_league.draft_class,
            num_rounds=request.num_rounds,
            user_team=request.user_team,
        )

    return _draft_to_state_response(_active_draft)


@router.get("/draft/state")
async def get_draft_state() -> DraftStateResponse:
    """Get the current draft state."""
    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft in progress")

    return _draft_to_state_response(_active_draft)


@router.post("/draft/start")
async def start_draft() -> DraftStateResponse:
    """Start the draft."""
    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft created")

    _active_draft.start_draft()
    return _draft_to_state_response(_active_draft)


@router.post("/draft/pick")
async def make_draft_pick(request: MakePickRequest) -> DraftResultResponse:
    """
    Make a draft pick.

    If it's the user's turn, uses the specified player.
    """
    global _active_draft

    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft in progress")

    if _active_draft.phase != DraftPhase.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Draft not in progress")

    from uuid import UUID
    try:
        player_id = UUID(request.player_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid player ID")

    pick = _active_draft.make_pick(player_id)
    if pick is None:
        raise HTTPException(status_code=400, detail="Invalid pick - player not available")

    # Add player to team's roster
    if _active_league:
        team = _active_league.get_team(pick.current_team_abbr)
        if team:
            # Find the player from the recently removed list
            for p in list(_active_league.draft_class):
                if str(p.id) == request.player_id:
                    team.roster.add_player(p)
                    _active_league.draft_class.remove(p)
                    break

    return DraftResultResponse(
        picks_made=[_pick_to_response(pick)],
        draft_complete=_active_draft.phase == DraftPhase.COMPLETED,
    )


@router.post("/draft/simulate-to-user")
async def simulate_to_user_pick() -> DraftResultResponse:
    """
    Simulate AI picks until it's the user's turn.
    """
    global _active_draft

    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft in progress")

    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    if _active_draft.phase != DraftPhase.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Draft not in progress")

    picks = _active_draft.simulate_to_user_pick(_active_league.teams)

    # Add drafted players to rosters
    for pick in picks:
        if pick.player_id:
            team = _active_league.get_team(pick.current_team_abbr)
            if team:
                # Find and add player
                for p in list(_active_league.draft_class):
                    if p.id == pick.player_id:
                        team.roster.add_player(p)
                        _active_league.draft_class.remove(p)
                        break

    return DraftResultResponse(
        picks_made=[_pick_to_response(p) for p in picks],
        draft_complete=_active_draft.phase == DraftPhase.COMPLETED,
    )


@router.post("/draft/simulate-full")
async def simulate_full_draft() -> DraftResultResponse:
    """
    Simulate the entire draft with AI.
    """
    global _active_draft

    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft in progress")

    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    picks = _active_draft.simulate_full_draft(_active_league.teams)

    # Add drafted players to rosters
    for pick in picks:
        if pick.player_id:
            team = _active_league.get_team(pick.current_team_abbr)
            if team:
                for p in list(_active_league.draft_class):
                    if p.id == pick.player_id:
                        team.roster.add_player(p)
                        _active_league.draft_class.remove(p)
                        break

    return DraftResultResponse(
        picks_made=[_pick_to_response(p) for p in picks],
        draft_complete=_active_draft.phase == DraftPhase.COMPLETED,
    )


@router.get("/draft/picks")
async def get_draft_picks(
    team: Optional[str] = Query(None, description="Filter by team"),
    round_num: Optional[int] = Query(None, ge=1, le=15, alias="round"),
) -> list[DraftPickResponse]:
    """Get all draft picks, optionally filtered."""
    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft in progress")

    picks = _active_draft.picks

    if team:
        picks = [p for p in picks if p.current_team_abbr == team.upper()]

    if round_num:
        picks = [p for p in picks if p.round == round_num]

    return [_pick_to_response(p) for p in picks]


@router.get("/draft/available")
async def get_available_players(
    position: Optional[str] = Query(None, description="Filter by position"),
    limit: int = Query(50, ge=1, le=200),
) -> list[PlayerSummary]:
    """Get available players in the draft."""
    if _active_draft is None:
        raise HTTPException(status_code=404, detail="No draft in progress")

    players = _active_draft.get_best_available(position=position, limit=limit)
    return [_player_to_summary(p, None) for p in players]


@router.get("/draft/team/{abbreviation}/needs")
async def get_team_needs(abbreviation: str) -> dict:
    """Get a team's positional needs."""
    if _active_league is None:
        raise HTTPException(status_code=404, detail="No league loaded")

    team = _active_league.get_team(abbreviation.upper())
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    from huddle.simulation.draft import TeamNeeds
    needs = TeamNeeds.calculate_from_roster(team)

    return {
        "team": abbreviation.upper(),
        "needs": {pos: round(score, 2) for pos, score in needs.needs.items()},
    }


def _draft_to_state_response(draft: Draft) -> DraftStateResponse:
    """Convert Draft to response."""
    current_pick = draft.current_pick
    return DraftStateResponse(
        id=str(draft.id),
        draft_type=draft.draft_type.value,
        phase=draft.phase.value,
        season=draft.season,
        num_rounds=draft.num_rounds,
        num_teams=draft.num_teams,
        current_pick_index=draft.current_pick_index,
        current_round=draft.current_round,
        picks_made=draft.picks_made,
        picks_remaining=draft.picks_remaining,
        is_user_pick=draft.is_user_pick,
        user_team=draft.user_team_abbr,
        current_pick=_pick_to_response(current_pick) if current_pick else None,
    )


def _pick_to_response(pick: DraftPick) -> DraftPickResponse:
    """Convert DraftPick to response."""
    return DraftPickResponse(
        id=str(pick.id),
        round=pick.round,
        pick_number=pick.pick_number,
        round_pick=pick.round_pick,
        original_team=pick.original_team_abbr,
        current_team=pick.current_team_abbr,
        is_selected=pick.is_selected,
        was_traded=pick.was_traded,
        player_id=str(pick.player_id) if pick.player_id else None,
        player_name=pick.player_name,
        player_position=pick.player_position,
    )

"""
League Container and Management.

This module provides the League class - the top-level container for a
32-team NFL simulation. It manages:
- All 32 teams with rosters
- Division/Conference standings
- Free agent pool
- Draft class
- Schedule generation
- Season progression
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
import json
from pathlib import Path

from huddle.core.league.nfl_data import (
    Conference,
    Division,
    NFLTeamData,
    NFL_TEAMS,
    DIVISIONS_BY_CONFERENCE,
    get_teams_in_division,
    get_teams_in_conference,
)
from huddle.core.models.team import Team
from huddle.core.models.player import Player
from huddle.core.models.stats import GameLog, PlayerSeasonStats
from huddle.core.contracts import calculate_market_value, assign_contract

if TYPE_CHECKING:
    from huddle.core.transactions.transaction_log import TransactionLog
    from huddle.core.calendar.league_calendar import LeagueCalendar as DayCalendar
    from huddle.core.draft.picks import DraftPickInventory


@dataclass
class TeamStanding:
    """
    Standings record for a single team.

    Tracks wins, losses, ties and tiebreaker info for playoff seeding.
    """

    team_id: UUID
    abbreviation: str
    wins: int = 0
    losses: int = 0
    ties: int = 0

    # Tiebreaker stats
    division_wins: int = 0
    division_losses: int = 0
    conference_wins: int = 0
    conference_losses: int = 0
    points_for: int = 0
    points_against: int = 0

    # Strength of schedule (for tiebreakers)
    strength_of_victory: float = 0.0
    strength_of_schedule: float = 0.0

    @property
    def games_played(self) -> int:
        """Total games played."""
        return self.wins + self.losses + self.ties

    @property
    def win_pct(self) -> float:
        """Winning percentage."""
        if self.games_played == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / self.games_played

    @property
    def division_win_pct(self) -> float:
        """Division winning percentage."""
        div_games = self.division_wins + self.division_losses
        if div_games == 0:
            return 0.0
        return self.division_wins / div_games

    @property
    def point_diff(self) -> int:
        """Point differential."""
        return self.points_for - self.points_against

    @property
    def record_string(self) -> str:
        """Format record as string (e.g., '10-7' or '9-7-1')."""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "team_id": str(self.team_id),
            "abbreviation": self.abbreviation,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "division_wins": self.division_wins,
            "division_losses": self.division_losses,
            "conference_wins": self.conference_wins,
            "conference_losses": self.conference_losses,
            "points_for": self.points_for,
            "points_against": self.points_against,
            "strength_of_victory": self.strength_of_victory,
            "strength_of_schedule": self.strength_of_schedule,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeamStanding":
        """Create from dictionary."""
        return cls(
            team_id=UUID(data["team_id"]),
            abbreviation=data["abbreviation"],
            wins=data.get("wins", 0),
            losses=data.get("losses", 0),
            ties=data.get("ties", 0),
            division_wins=data.get("division_wins", 0),
            division_losses=data.get("division_losses", 0),
            conference_wins=data.get("conference_wins", 0),
            conference_losses=data.get("conference_losses", 0),
            points_for=data.get("points_for", 0),
            points_against=data.get("points_against", 0),
            strength_of_victory=data.get("strength_of_victory", 0.0),
            strength_of_schedule=data.get("strength_of_schedule", 0.0),
        )


@dataclass
class ScheduledGame:
    """
    A scheduled game between two teams.

    Can be in future (not played) or past (with result).
    """

    id: UUID = field(default_factory=uuid4)
    week: int = 0
    home_team_abbr: str = ""
    away_team_abbr: str = ""

    # Result (None if not played yet)
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    # Game type
    is_divisional: bool = False
    is_conference: bool = False
    is_playoff: bool = False

    @property
    def is_played(self) -> bool:
        """Check if game has been played."""
        return self.home_score is not None and self.away_score is not None

    @property
    def winner_abbr(self) -> Optional[str]:
        """Get winner abbreviation, or None if tie/not played."""
        if not self.is_played:
            return None
        if self.home_score > self.away_score:
            return self.home_team_abbr
        elif self.away_score > self.home_score:
            return self.away_team_abbr
        return None  # Tie

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "week": self.week,
            "home_team_abbr": self.home_team_abbr,
            "away_team_abbr": self.away_team_abbr,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "is_divisional": self.is_divisional,
            "is_conference": self.is_conference,
            "is_playoff": self.is_playoff,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledGame":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            week=data.get("week", 0),
            home_team_abbr=data.get("home_team_abbr", ""),
            away_team_abbr=data.get("away_team_abbr", ""),
            home_score=data.get("home_score"),
            away_score=data.get("away_score"),
            is_divisional=data.get("is_divisional", False),
            is_conference=data.get("is_conference", False),
            is_playoff=data.get("is_playoff", False),
        )


@dataclass
class League:
    """
    The top-level container for an NFL simulation.

    Contains all 32 teams, standings, schedule, free agents, and draft class.
    This is the "save file" - serializing this captures the entire league state.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = "NFL League"

    # Current state
    current_season: int = 2024
    current_week: int = 0  # 0 = offseason, 1-18 = regular season, 19+ = playoffs

    # Teams (keyed by abbreviation)
    teams: dict[str, Team] = field(default_factory=dict)

    # Standings (keyed by abbreviation)
    standings: dict[str, TeamStanding] = field(default_factory=dict)

    # Schedule
    schedule: list[ScheduledGame] = field(default_factory=list)

    # League-wide player pools
    free_agents: list[Player] = field(default_factory=list)
    draft_class: list[Player] = field(default_factory=list)

    # Draft order (list of team abbreviations)
    draft_order: list[str] = field(default_factory=list)

    # Historical data
    champions: dict[int, str] = field(default_factory=dict)  # year -> team abbr

    # Game logs (keyed by game_id string)
    game_logs: dict[str, GameLog] = field(default_factory=dict)

    # Season stats (keyed by player_id string)
    season_stats: dict[str, PlayerSeasonStats] = field(default_factory=dict)

    # Transaction log (tracks all roster moves, trades, signings)
    transactions: Optional["TransactionLog"] = None

    # Day-based calendar (tracks dates, phases, key events)
    calendar: Optional["DayCalendar"] = None

    # League-wide draft pick inventory (all picks across all teams)
    draft_picks: Optional["DraftPickInventory"] = None

    # ==========================================================================
    # Team Management
    # ==========================================================================

    def get_team(self, abbreviation: str) -> Optional[Team]:
        """Get a team by abbreviation."""
        return self.teams.get(abbreviation)

    def get_team_by_id(self, team_id: UUID) -> Optional[Team]:
        """Get a team by its UUID."""
        for team in self.teams.values():
            if team.id == team_id:
                return team
        return None

    def get_teams_in_division(self, division: Division) -> list[Team]:
        """Get all teams in a division."""
        nfl_teams = get_teams_in_division(division)
        return [
            self.teams[t.abbreviation]
            for t in nfl_teams
            if t.abbreviation in self.teams
        ]

    def get_teams_in_conference(self, conference: Conference) -> list[Team]:
        """Get all teams in a conference."""
        nfl_teams = get_teams_in_conference(conference)
        return [
            self.teams[t.abbreviation]
            for t in nfl_teams
            if t.abbreviation in self.teams
        ]

    def get_division_for_team(self, abbreviation: str) -> Optional[Division]:
        """Get the division a team belongs to."""
        nfl_data = NFL_TEAMS.get(abbreviation)
        if nfl_data:
            return nfl_data.division
        return None

    def get_conference_for_team(self, abbreviation: str) -> Optional[Conference]:
        """Get the conference a team belongs to."""
        division = self.get_division_for_team(abbreviation)
        if division:
            return division.conference
        return None

    # ==========================================================================
    # Standings
    # ==========================================================================

    def get_standing(self, abbreviation: str) -> Optional[TeamStanding]:
        """Get standings for a team."""
        return self.standings.get(abbreviation)

    def get_division_standings(self, division: Division) -> list[TeamStanding]:
        """Get standings for a division, sorted by record."""
        teams_in_div = get_teams_in_division(division)
        standings = [
            self.standings[t.abbreviation]
            for t in teams_in_div
            if t.abbreviation in self.standings
        ]
        return sorted(standings, key=lambda s: (-s.win_pct, -s.division_win_pct, -s.point_diff))

    def get_conference_standings(self, conference: Conference) -> list[TeamStanding]:
        """Get standings for a conference, sorted by record."""
        teams_in_conf = get_teams_in_conference(conference)
        standings = [
            self.standings[t.abbreviation]
            for t in teams_in_conf
            if t.abbreviation in self.standings
        ]
        return sorted(standings, key=lambda s: (-s.win_pct, -s.division_win_pct, -s.point_diff))

    def get_playoff_bracket(self, conference: Conference) -> list[TeamStanding]:
        """
        Get the 7 playoff teams for a conference.

        1-4 seeds: Division winners by record
        5-7 seeds: Best remaining records (wild cards)
        """
        # Get division winners
        divisions = DIVISIONS_BY_CONFERENCE[conference]
        division_winners: list[TeamStanding] = []

        for division in divisions:
            div_standings = self.get_division_standings(division)
            if div_standings:
                division_winners.append(div_standings[0])

        # Sort division winners by record
        division_winners.sort(key=lambda s: (-s.win_pct, -s.point_diff))

        # Get wild card teams (non-division winners with best records)
        wild_card_candidates = [
            s for s in self.get_conference_standings(conference)
            if s not in division_winners
        ]
        wild_cards = wild_card_candidates[:3]

        return division_winners + wild_cards

    def update_standings_from_game(self, game: ScheduledGame) -> None:
        """Update standings based on a completed game."""
        if not game.is_played:
            return

        home = self.standings.get(game.home_team_abbr)
        away = self.standings.get(game.away_team_abbr)

        if not home or not away:
            return

        # Update points
        home.points_for += game.home_score
        home.points_against += game.away_score
        away.points_for += game.away_score
        away.points_against += game.home_score

        # Update wins/losses
        if game.home_score > game.away_score:
            home.wins += 1
            away.losses += 1
            if game.is_divisional:
                home.division_wins += 1
                away.division_losses += 1
            if game.is_conference:
                home.conference_wins += 1
                away.conference_losses += 1
        elif game.away_score > game.home_score:
            away.wins += 1
            home.losses += 1
            if game.is_divisional:
                away.division_wins += 1
                home.division_losses += 1
            if game.is_conference:
                away.conference_wins += 1
                home.conference_losses += 1
        else:
            # Tie
            home.ties += 1
            away.ties += 1

    # ==========================================================================
    # Schedule
    # ==========================================================================

    def get_games_for_week(self, week: int) -> list[ScheduledGame]:
        """Get all games scheduled for a specific week."""
        return [g for g in self.schedule if g.week == week]

    def get_team_schedule(self, abbreviation: str) -> list[ScheduledGame]:
        """Get all games for a specific team."""
        return [
            g for g in self.schedule
            if g.home_team_abbr == abbreviation or g.away_team_abbr == abbreviation
        ]

    def get_next_game(self, abbreviation: str) -> Optional[ScheduledGame]:
        """Get the next unplayed game for a team."""
        team_games = self.get_team_schedule(abbreviation)
        for game in sorted(team_games, key=lambda g: g.week):
            if not game.is_played:
                return game
        return None

    # ==========================================================================
    # Free Agency & Draft
    # ==========================================================================

    def add_free_agent(self, player: Player) -> None:
        """Add a player to the free agent pool."""
        self.free_agents.append(player)

    def remove_free_agent(self, player_id: UUID) -> Optional[Player]:
        """Remove and return a player from the free agent pool."""
        for i, player in enumerate(self.free_agents):
            if player.id == player_id:
                return self.free_agents.pop(i)
        return None

    def sign_free_agent(
        self,
        player_id: UUID,
        team_abbr: str,
        salary: int = None,
        years: int = None,
        signing_bonus: int = None,
        enforce_cap: bool = True,
    ) -> tuple[bool, str]:
        """
        Sign a free agent to a team with contract terms.

        Args:
            player_id: The free agent's ID
            team_abbr: Team abbreviation to sign to
            salary: Annual salary in thousands (None = use market value)
            years: Contract length (None = use market value)
            signing_bonus: Bonus in thousands (None = use market value)
            enforce_cap: If True, reject signings that exceed cap

        Returns:
            Tuple of (success, message)
            - (True, "Signed {name}") on success
            - (False, "reason") on failure
        """
        if team_abbr not in self.teams:
            return (False, f"Team {team_abbr} not found")

        team = self.teams[team_abbr]

        # Find the player in free agents (don't remove yet)
        player = None
        for fa in self.free_agents:
            if fa.id == player_id:
                player = fa
                break

        if not player:
            return (False, "Player not found in free agents")

        # Calculate contract terms if not provided
        if salary is None or years is None:
            market = calculate_market_value(player)
            salary = salary or market.base_salary
            years = years or market.years
            signing_bonus = signing_bonus if signing_bonus is not None else market.signing_bonus

        # Cap enforcement - check if team can afford the salary
        if enforce_cap and not team.can_afford(salary):
            return (False, f"Team cannot afford ${salary:,}K salary (cap room: ${team.cap_room:,}K)")

        # Remove from free agents
        self.remove_free_agent(player_id)

        # Assign contract to player
        assign_contract(player, years=years, salary=salary, signing_bonus=signing_bonus)

        # Add to roster
        team.roster.add_player(player)

        # Update team financials
        team.financials.add_contract(salary)

        return (True, f"Signed {player.full_name} for {years}yr/${salary * years:,}K")

    def release_player(
        self,
        team_abbr: str,
        player_id: UUID,
        june_1_cut: bool = False,
    ) -> tuple[bool, str, int]:
        """
        Release a player from a team to free agency.

        Handles dead money from remaining signing bonus.

        Args:
            team_abbr: Team abbreviation
            player_id: Player to release
            june_1_cut: If True, spread dead money over 2 years (post-June 1)

        Returns:
            Tuple of (success, message, dead_money)
            - (True, "Released {name}", dead_money) on success
            - (False, "reason", 0) on failure
        """
        if team_abbr not in self.teams:
            return (False, f"Team {team_abbr} not found", 0)

        team = self.teams[team_abbr]
        player = team.roster.get_player(player_id)

        if not player:
            return (False, "Player not found on roster", 0)

        # Calculate dead money from remaining bonus
        dead_money = player.signing_bonus_remaining or 0
        salary = player.salary or 0
        player_name = player.full_name

        # Remove from roster
        team.roster.remove_player(player_id)

        # Update financials - remove salary, add dead money
        this_year_dead, next_year_dead = team.financials.cut_player(
            salary, dead_money, june_1_cut=june_1_cut
        )

        # Reset player contract info for free agency
        player.contract_years = None
        player.contract_year_remaining = None
        player.salary = None
        player.signing_bonus = None
        player.signing_bonus_remaining = None
        player.years_on_team = 0

        # Add to free agent pool
        self.add_free_agent(player)

        if dead_money > 0:
            if june_1_cut and next_year_dead > 0:
                return (
                    True,
                    f"Released {player_name} (June 1: ${this_year_dead:,}K this year, ${next_year_dead:,}K next year)",
                    this_year_dead,
                )
            else:
                return (True, f"Released {player_name} (${dead_money:,}K dead money)", dead_money)
        else:
            return (True, f"Released {player_name}", 0)

    def set_draft_class(self, players: list[Player]) -> None:
        """Set the draft class for the upcoming draft."""
        self.draft_class = players

    def draft_player(self, player_id: UUID, team_abbr: str) -> Optional[Player]:
        """Draft a player from the draft class to a team."""
        for i, player in enumerate(self.draft_class):
            if player.id == player_id:
                drafted = self.draft_class.pop(i)
                if team_abbr in self.teams:
                    self.teams[team_abbr].roster.add_player(drafted)
                return drafted
        return None

    # ==========================================================================
    # Game Logs & Stats
    # ==========================================================================

    def add_game_log(self, game_log: GameLog) -> None:
        """Add a game log and update season stats."""
        self.game_logs[str(game_log.game_id)] = game_log

        # Update season stats for each player
        for player_id_str, game_stats in game_log.player_stats.items():
            if player_id_str not in self.season_stats:
                self.season_stats[player_id_str] = PlayerSeasonStats(
                    player_id=game_stats.player_id,
                    player_name=game_stats.player_name,
                    team_abbr=game_stats.team_abbr,
                    position=game_stats.position,
                    season=self.current_season,
                )
            self.season_stats[player_id_str].add_game(game_stats)

    def get_game_log(self, game_id: UUID) -> Optional[GameLog]:
        """Get a game log by game ID."""
        return self.game_logs.get(str(game_id))

    def get_player_season_stats(self, player_id: UUID) -> Optional[PlayerSeasonStats]:
        """Get season stats for a player."""
        return self.season_stats.get(str(player_id))

    def get_team_game_logs(self, abbreviation: str) -> list[GameLog]:
        """Get all game logs for a team."""
        return [
            log for log in self.game_logs.values()
            if log.home_team_abbr == abbreviation or log.away_team_abbr == abbreviation
        ]

    def get_season_leaders(
        self,
        stat_category: str,
        stat_name: str,
        limit: int = 10,
    ) -> list[tuple[PlayerSeasonStats, int | float]]:
        """
        Get season leaders for a specific stat.

        Args:
            stat_category: Category (passing, rushing, receiving, defense, kicking)
            stat_name: Stat name within category (yards, touchdowns, etc.)
            limit: Number of leaders to return

        Returns:
            List of (PlayerSeasonStats, stat_value) tuples
        """
        results = []
        for stats in self.season_stats.values():
            category = getattr(stats, stat_category, None)
            if category:
                value = getattr(category, stat_name, 0)
                if value > 0:
                    results.append((stats, value))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    # ==========================================================================
    # Season Progression
    # ==========================================================================

    def advance_week(self) -> int:
        """Advance to the next week, returning the new week number."""
        self.current_week += 1
        return self.current_week

    def start_new_season(self) -> list[tuple[str, "Player"]]:
        """
        Start a new season - reset standings, age players, process contracts.

        Handles:
        - Incrementing season/week counters
        - Resetting standings
        - Aging all players
        - Decrementing contract years
        - Moving expired contracts to free agency
        - Processing team financials (cap increase, dead money rollover)

        Returns:
            List of (team_abbr, player) for players whose contracts expired
        """
        self.current_season += 1
        self.current_week = 0

        # Reset standings
        for abbr, team in self.teams.items():
            self.standings[abbr] = TeamStanding(
                team_id=team.id,
                abbreviation=abbr,
            )

        # Track players becoming free agents
        expiring_contracts: list[tuple[str, Player]] = []

        # Process team rosters
        for team in self.teams.values():
            players_to_remove = []

            for player in team.roster.players.values():
                # Age the player
                player.age += 1
                player.experience_years += 1
                player.years_on_team += 1

                # Process contract year
                if player.contract_year_remaining is not None:
                    player.contract_year_remaining -= 1

                    # Reduce remaining signing bonus (prorated portion used)
                    if player.signing_bonus_remaining and player.contract_years:
                        bonus_per_year = player.signing_bonus // player.contract_years
                        player.signing_bonus_remaining = max(
                            0, player.signing_bonus_remaining - bonus_per_year
                        )

                    # Check for expiring contract
                    if player.contract_year_remaining <= 0:
                        expiring_contracts.append((team.abbreviation, player))
                        players_to_remove.append(player.id)

            # Remove expired contracts from roster and move to free agency
            for player_id in players_to_remove:
                player = team.roster.remove_player(player_id)
                if player:
                    # Reset contract info
                    player.contract_years = None
                    player.contract_year_remaining = None
                    player.salary = None
                    player.signing_bonus = None
                    player.signing_bonus_remaining = None
                    player.years_on_team = 0
                    self.add_free_agent(player)

            # Process team financials (cap increase, dead money rollover)
            team.financials.new_season()

            # Recalculate total salary from remaining roster
            team.recalculate_financials()

        # Age free agents
        for player in self.free_agents:
            player.age += 1
            player.experience_years += 1

        # Clear schedule and season stats
        self.schedule = []
        self.game_logs = {}
        self.season_stats = {}

        return expiring_contracts

    def set_draft_order(self, reverse_standings: bool = True) -> None:
        """
        Set draft order based on standings.

        By default, worst teams pick first.
        """
        # Combine all standings
        all_standings = list(self.standings.values())

        if reverse_standings:
            # Worst to best (traditional NFL order)
            all_standings.sort(key=lambda s: (s.win_pct, s.point_diff))
        else:
            # Best to worst
            all_standings.sort(key=lambda s: (-s.win_pct, -s.point_diff))

        self.draft_order = [s.abbreviation for s in all_standings]

    # ==========================================================================
    # Serialization
    # ==========================================================================

    def to_dict(self) -> dict:
        """Convert the entire league to a dictionary for saving."""
        data = {
            "id": str(self.id),
            "name": self.name,
            "current_season": self.current_season,
            "current_week": self.current_week,
            "teams": {abbr: team.to_dict() for abbr, team in self.teams.items()},
            "standings": {abbr: s.to_dict() for abbr, s in self.standings.items()},
            "schedule": [g.to_dict() for g in self.schedule],
            "free_agents": [p.to_dict() for p in self.free_agents],
            "draft_class": [p.to_dict() for p in self.draft_class],
            "draft_order": self.draft_order,
            "champions": {str(y): abbr for y, abbr in self.champions.items()},
            "game_logs": {k: v.to_dict() for k, v in self.game_logs.items()},
            "season_stats": {k: v.to_dict() for k, v in self.season_stats.items()},
        }

        # Include optional systems if present
        if self.transactions:
            data["transactions"] = self.transactions.to_dict()
        if self.calendar:
            data["calendar"] = self.calendar.to_dict()
        if self.draft_picks:
            data["draft_picks"] = self.draft_picks.to_dict()

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "League":
        """Create a league from a dictionary (for loading saves)."""
        league = cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data.get("name", "NFL League"),
            current_season=data.get("current_season", 2024),
            current_week=data.get("current_week", 0),
        )

        # Load teams
        for abbr, team_data in data.get("teams", {}).items():
            league.teams[abbr] = Team.from_dict(team_data)

        # Load standings
        for abbr, standing_data in data.get("standings", {}).items():
            league.standings[abbr] = TeamStanding.from_dict(standing_data)

        # Load schedule
        league.schedule = [
            ScheduledGame.from_dict(g) for g in data.get("schedule", [])
        ]

        # Load free agents
        league.free_agents = [
            Player.from_dict(p) for p in data.get("free_agents", [])
        ]

        # Load draft class
        league.draft_class = [
            Player.from_dict(p) for p in data.get("draft_class", [])
        ]

        # Load draft order
        league.draft_order = data.get("draft_order", [])

        # Load champions
        league.champions = {
            int(y): abbr for y, abbr in data.get("champions", {}).items()
        }

        # Load game logs
        league.game_logs = {
            k: GameLog.from_dict(v) for k, v in data.get("game_logs", {}).items()
        }

        # Load season stats
        league.season_stats = {
            k: PlayerSeasonStats.from_dict(v) for k, v in data.get("season_stats", {}).items()
        }

        # Load transaction log if present
        if "transactions" in data:
            from huddle.core.transactions.transaction_log import TransactionLog
            league.transactions = TransactionLog.from_dict(data["transactions"])

        # Load day-based calendar if present
        if "calendar" in data:
            from huddle.core.calendar.league_calendar import LeagueCalendar as DayCalendar
            league.calendar = DayCalendar.from_dict(data["calendar"])

        # Load draft picks inventory if present
        if "draft_picks" in data:
            from huddle.core.draft.picks import DraftPickInventory
            league.draft_picks = DraftPickInventory.from_dict(data["draft_picks"])

        return league

    def save(self, path: Path) -> None:
        """Save the league to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "League":
        """Load a league from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    # ==========================================================================
    # League Info
    # ==========================================================================

    @property
    def is_offseason(self) -> bool:
        """Check if it's the offseason."""
        if self.calendar:
            from huddle.core.calendar.league_calendar import LeaguePeriod
            period = self.calendar.current_period
            return period in {
                LeaguePeriod.OFFSEASON_EARLY,
                LeaguePeriod.FREE_AGENCY,
                LeaguePeriod.DRAFT_PREP,
                LeaguePeriod.DRAFT,
                LeaguePeriod.POST_DRAFT,
                LeaguePeriod.OTAs,
                LeaguePeriod.TRAINING_CAMP,
            }
        return self.current_week == 0

    @property
    def is_regular_season(self) -> bool:
        """Check if it's the regular season (weeks 1-18)."""
        if self.calendar:
            from huddle.core.calendar.league_calendar import LeaguePeriod
            return self.calendar.current_period == LeaguePeriod.REGULAR_SEASON
        return 1 <= self.current_week <= 18

    @property
    def is_playoffs(self) -> bool:
        """Check if it's the playoffs (week 19+)."""
        if self.calendar:
            from huddle.core.calendar.league_calendar import LeaguePeriod
            return self.calendar.current_period in {
                LeaguePeriod.PLAYOFFS,
                LeaguePeriod.SUPER_BOWL,
            }
        return self.current_week >= 19

    @property
    def total_players(self) -> int:
        """Total number of players across all teams."""
        return sum(team.roster.size for team in self.teams.values())

    @property
    def current_date_display(self) -> str:
        """Get current date string from calendar."""
        if self.calendar:
            return self.calendar.current_date.strftime("%B %d, %Y")
        return f"Season {self.current_season}, Week {self.current_week}"

    @property
    def current_period_display(self) -> str:
        """Get current league period display string."""
        if self.calendar:
            period = self.calendar.current_period
            return period.name.replace("_", " ").title()
        if self.is_playoffs:
            return "Playoffs"
        if self.is_regular_season:
            return f"Week {self.current_week}"
        return "Offseason"

    def log_transaction(self, transaction_type: str, **kwargs) -> None:
        """Log a transaction if transaction log is enabled."""
        if self.transactions:
            from huddle.core.transactions.transaction_log import create_transaction
            txn = create_transaction(
                transaction_type=transaction_type,
                season=self.current_season,
                **kwargs
            )
            self.transactions.add_transaction(txn)

    def initialize_new_systems(self, year: int = None) -> None:
        """
        Initialize the new management systems for the league.

        Call this when creating a new league or upgrading an existing one.
        """
        year = year or self.current_season

        # Create transaction log
        if not self.transactions:
            from huddle.core.transactions.transaction_log import TransactionLog
            self.transactions = TransactionLog(league_id=str(self.id))

        # Create day-based calendar
        if not self.calendar:
            from huddle.core.calendar.league_calendar import LeagueCalendar, create_calendar_for_season
            self.calendar = create_calendar_for_season(year)

        # Create draft picks inventories for each team
        from huddle.core.draft.picks import DraftPickInventory, create_league_draft_picks
        for team in self.teams.values():
            if not team.draft_picks:
                team.draft_picks = DraftPickInventory(team_id=str(team.id))
                # Create picks for current year and next few years
                for draft_year in range(year, year + 4):
                    picks = create_league_draft_picks(str(team.id), draft_year)
                    team.draft_picks.picks.extend(picks)

        # Create league-wide pick inventory by aggregating all teams
        if not self.draft_picks:
            # The league's draft_picks stores all picks from all teams
            all_picks = []
            for team in self.teams.values():
                if team.draft_picks:
                    all_picks.extend(team.draft_picks.picks)
            # Use first team's ID as placeholder since league inventory needs one
            # In practice, league-level queries should iterate through teams
            if self.teams:
                first_team_id = str(next(iter(self.teams.values())).id)
                self.draft_picks = DraftPickInventory(team_id=first_team_id)
                self.draft_picks.picks = all_picks

    def __str__(self) -> str:
        return f"{self.name} ({self.current_season}, Week {self.current_week})"

    def __repr__(self) -> str:
        return f"League(name='{self.name}', teams={len(self.teams)}, season={self.current_season})"

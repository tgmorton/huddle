"""
Historical Simulation Runner.

Generates leagues with coherent history by simulating
multiple seasons of team operations before the player starts.

This creates:
- Realistic roster compositions with contract histories
- Draft pick ownership variations
- Team statuses that reflect actual performance
- Transaction logs showing how rosters were built
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, Callable
from uuid import UUID
import random

from huddle.core.calendar import LeagueCalendar, LeagueEvent, create_calendar_for_season
from huddle.core.league.league import League, ScheduledGame, TeamStanding
from huddle.core.league.nfl_data import NFL_TEAMS
from huddle.core.models.team import Team
from huddle.simulation.season import SeasonSimulator
from huddle.simulation.engine import SimulationMode
from huddle.generators.league import generate_nfl_schedule
from huddle.core.draft import (
    DraftPick,
    DraftPickInventory,
    DraftState,
    create_league_draft_picks,
    create_draft_order,
)
from huddle.core.transactions import (
    Transaction,
    TransactionLog,
    TransactionType,
    create_draft_transaction,
    create_signing_transaction,
    create_cut_transaction,
)
from huddle.core.contracts.contract import (
    Contract,
    create_rookie_contract,
    create_veteran_contract,
    create_minimum_contract,
)
from huddle.core.models.team_identity import (
    TeamStatus,
    TeamStatusState,
    generate_initial_team_status,
    evaluate_team_status,
)
from huddle.core.enums.positions import Position
from huddle.core.ai import (
    DraftAI,
    DraftAIConfig,
    RosterAI,
    FreeAgencyAI,
    TradeAI,
    TeamNeeds,
    calculate_team_needs,
    select_starters,
)
from huddle.core.ai.draft_ai import (
    MockDraft,
    MockDraftEntry,
    generate_mock_draft,
)
from huddle.core.ai.gm_archetypes import GMArchetype, GMProfile
from huddle.core.ai.position_planner import (
    PositionPlan,
    PositionNeed,
    AcquisitionPath,
    DraftProspect,
    create_position_plan,
    should_pursue_fa,
    update_plan_after_fa,
    update_plan_after_draft,
    get_draft_target,
)
from huddle.core.ai.trade_market import (
    TradeMarketConfig,
    TradeMarket,
    TeamTradeState,
    ExecutedTrade,
    simulate_trade_market,
    attempt_blockbuster_trade,
)


@dataclass
class TeamState:
    """Complete state of a team during simulation."""
    team_id: str
    team_name: str

    # Roster
    roster: list = field(default_factory=list)  # List of Player objects
    contracts: dict = field(default_factory=dict)  # player_id -> Contract

    # Assets
    pick_inventory: DraftPickInventory = None

    # Status
    status: TeamStatusState = None
    identity: object = None  # TeamIdentity

    # GM personality (affects draft/FA decisions)
    gm_archetype: GMArchetype = None

    # Offseason planning (HC09-style holistic approach)
    position_plan: PositionPlan = None

    # Season results
    wins: int = 0
    losses: int = 0
    made_playoffs: bool = False
    won_championship: bool = False

    # Financials
    salary_cap: int = 255_000
    cap_used: int = 0

    @property
    def win_pct(self) -> float:
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.5

    @property
    def cap_space(self) -> int:
        return self.salary_cap - self.cap_used

    def to_dict(self) -> dict:
        from huddle.core.models.player import Player
        from huddle.core.contracts.contract import Contract
        from huddle.core.models.team_identity import TeamIdentity

        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "roster": [p.to_dict() for p in self.roster],
            "contracts": {
                str(pid): c.to_dict() for pid, c in self.contracts.items()
            },
            "pick_inventory": self.pick_inventory.to_dict() if self.pick_inventory else None,
            "status": self.status.to_dict() if self.status else None,
            "identity": self.identity.to_dict() if hasattr(self.identity, 'to_dict') else None,
            "gm_archetype": self.gm_archetype.value if self.gm_archetype else None,
            "wins": self.wins,
            "losses": self.losses,
            "made_playoffs": self.made_playoffs,
            "won_championship": self.won_championship,
            "salary_cap": self.salary_cap,
            "cap_used": self.cap_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TeamState":
        from huddle.core.models.player import Player
        from huddle.core.contracts.contract import Contract
        from huddle.core.models.team_identity import TeamStatusState, TeamIdentity

        roster = [Player.from_dict(p) for p in data.get("roster", [])]
        contracts = {
            pid: Contract.from_dict(c) for pid, c in data.get("contracts", {}).items()
        }
        pick_inventory = (
            DraftPickInventory.from_dict(data["pick_inventory"])
            if data.get("pick_inventory") else None
        )
        status = (
            TeamStatusState.from_dict(data["status"])
            if data.get("status") else None
        )
        identity = (
            TeamIdentity.from_dict(data["identity"])
            if data.get("identity") else None
        )
        gm_archetype = (
            GMArchetype(data["gm_archetype"])
            if data.get("gm_archetype") else None
        )

        return cls(
            team_id=data["team_id"],
            team_name=data["team_name"],
            roster=roster,
            contracts=contracts,
            pick_inventory=pick_inventory,
            status=status,
            identity=identity,
            gm_archetype=gm_archetype,
            wins=data.get("wins", 0),
            losses=data.get("losses", 0),
            made_playoffs=data.get("made_playoffs", False),
            won_championship=data.get("won_championship", False),
            salary_cap=data.get("salary_cap", 255_000),
            cap_used=data.get("cap_used", 0),
        )


def get_nfl_team_data() -> list[dict]:
    """
    Convert NFL_TEAMS to the team_data format expected by HistoricalSimulator.

    Returns list of dicts with 'id', 'name', 'city', 'division', etc.
    """
    return [
        {
            "id": abbr,
            "name": team.name,
            "city": team.city,
            "division": team.division.value,
            "conference": team.division.conference.value,
            "primary_color": team.primary_color,
            "secondary_color": team.secondary_color,
            "stadium": team.stadium,
            "default_identity": team.default_identity,
        }
        for abbr, team in NFL_TEAMS.items()
    ]


@dataclass
class SimulationConfig:
    """Configuration for historical simulation."""
    # How many years to simulate
    years_to_simulate: int = 4

    # Starting season (simulation will end at this season)
    target_season: int = 2024

    # Number of teams
    num_teams: int = 32

    # Draft settings
    draft_rounds: int = 7

    # Simulation settings
    games_per_season: int = 17
    playoff_teams: int = 14

    # Speed settings
    verbose: bool = False
    progress_callback: Optional[Callable[[str], None]] = None


@dataclass
class SeasonSnapshot:
    """Snapshot of team standings at end of a season."""
    team_id: str
    team_name: str
    wins: int
    losses: int
    made_playoffs: bool
    won_championship: bool
    status: str

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "wins": self.wins,
            "losses": self.losses,
            "made_playoffs": self.made_playoffs,
            "won_championship": self.won_championship,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SeasonSnapshot":
        return cls(
            team_id=data["team_id"],
            team_name=data["team_name"],
            wins=data["wins"],
            losses=data["losses"],
            made_playoffs=data["made_playoffs"],
            won_championship=data["won_championship"],
            status=data["status"],
        )


@dataclass
class PlayerDevelopmentHistory:
    """Tracks a player's development over time."""
    player_id: str
    player_name: str
    position: str
    entries: list = field(default_factory=list)  # List of development entries by season

    def add_entry(self, entry: dict) -> None:
        """Add a development entry for a season."""
        self.entries.append(entry)

    def get_career_arc(self) -> list:
        """Get overall ratings over time for charting."""
        return [
            {"season": e["season"], "age": e["age_after"], "overall": e["overall_after"]}
            for e in self.entries
        ]

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "entries": self.entries,  # Already list of dicts
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerDevelopmentHistory":
        return cls(
            player_id=data["player_id"],
            player_name=data["player_name"],
            position=data["position"],
            entries=data.get("entries", []),
        )


@dataclass
class SimulationResult:
    """Results of historical simulation."""
    teams: dict  # team_id -> TeamState
    transaction_log: TransactionLog
    calendars: list  # LeagueCalendar per season
    draft_histories: dict  # year -> DraftState
    season_standings: dict = field(default_factory=dict)  # year -> list[SeasonSnapshot]

    # Development tracking
    development_histories: dict = field(default_factory=dict)  # player_id -> PlayerDevelopmentHistory

    # Blockbuster trades tracked during simulation
    blockbuster_trades: list = field(default_factory=list)

    # Summary
    seasons_simulated: int = 0
    total_transactions: int = 0

    def to_league(self, name: str = "NFL League") -> League:
        """
        Convert simulation results to a League object with full history.

        This creates a League ready for play with:
        - All teams with rosters, identities, statuses, and GM archetypes
        - Complete historical data (season_history, draft_history, player_development)
        - Transaction log
        - Calendar for current season

        Returns:
            League object with embedded historical data
        """
        from huddle.core.models.team import Team, Roster
        from huddle.core.models.team_identity import TeamFinancials
        from huddle.generators.player import generate_player

        # Find the final season from calendars
        final_season = max(c.season for c in self.calendars) if self.calendars else 2024

        league = League(
            name=name,
            current_season=final_season,
            current_week=0,  # Start in offseason
        )

        # Convert TeamState to Team for each team
        for team_id, team_state in self.teams.items():
            # Create roster from players
            roster = Roster()
            for player in team_state.roster:
                roster.add_player(player, assign_jersey=False)

            # Create Team with all historical sim data
            team = Team(
                name=team_state.team_name,
                abbreviation=team_id,
                city=team_state.team_name.split()[0] if team_state.team_name else team_id,
                roster=roster,
                financials=TeamFinancials(
                    salary_cap=team_state.salary_cap,
                    total_salary=team_state.cap_used,
                ),
                status=team_state.status,
                identity=team_state.identity,
                gm_archetype=team_state.gm_archetype.value if team_state.gm_archetype else None,
            )

            # Add draft picks inventory
            if team_state.pick_inventory:
                team.draft_picks = team_state.pick_inventory

            league.teams[team_id] = team

            # Initialize standings
            league.standings[team_id] = TeamStanding(
                team_id=team.id,
                abbreviation=team_id,
                wins=team_state.wins,
                losses=team_state.losses,
            )

        # Populate season_history from season_standings
        for year, snapshots in self.season_standings.items():
            league.season_history[year] = [
                {
                    "team_abbr": s.team_id,
                    "team_name": s.team_name,
                    "wins": s.wins,
                    "losses": s.losses,
                    "made_playoffs": s.made_playoffs,
                    "won_championship": s.won_championship,
                    "status": s.status,
                }
                for s in snapshots
            ]

            # Also populate champions
            for s in snapshots:
                if s.won_championship:
                    league.champions[year] = s.team_id

        # Populate draft_history from draft_histories
        for year, draft_state in self.draft_histories.items():
            league.draft_history[year] = []
            for pick in draft_state.picks:
                if pick.player:
                    league.draft_history[year].append({
                        "round": pick.round,
                        "pick": pick.pick_number,
                        "team_abbr": pick.team_id,
                        "player_id": str(pick.player.id),
                        "player_name": pick.player.full_name,
                        "position": pick.player.position.value,
                        "overall_at_draft": pick.player.overall,
                        "archetype": pick.player.player_archetype,
                    })

        # Populate player_development from development_histories
        for player_id, dev_history in self.development_histories.items():
            league.player_development[player_id] = [
                {
                    "season": entry.get("season"),
                    "age": entry.get("age_after"),
                    "overall_before": entry.get("overall_before"),
                    "overall_after": entry.get("overall_after"),
                    "change": entry.get("change", 0),
                }
                for entry in dev_history.entries
            ]

        # Populate blockbuster_trades
        league.blockbuster_trades = self.blockbuster_trades

        # Attach transaction log
        league.transactions = self.transaction_log

        # Attach the most recent calendar
        if self.calendars:
            league.calendar = self.calendars[-1]

        return league

    def to_dict(self) -> dict:
        """Serialize simulation result to dict for saving."""
        from huddle.core.calendar.league_calendar import LeagueCalendar

        return {
            "teams": {
                team_id: team_state.to_dict()
                for team_id, team_state in self.teams.items()
            },
            "transaction_log": self.transaction_log.to_dict(),
            "calendars": [cal.to_dict() for cal in self.calendars],
            "draft_histories": {
                str(year): draft_state.to_dict()
                for year, draft_state in self.draft_histories.items()
            },
            "season_standings": {
                str(year): [snapshot.to_dict() for snapshot in snapshots]
                for year, snapshots in self.season_standings.items()
            },
            "development_histories": {
                player_id: dev_history.to_dict()
                for player_id, dev_history in self.development_histories.items()
            },
            "blockbuster_trades": self.blockbuster_trades,  # Already list of dicts
            "seasons_simulated": self.seasons_simulated,
            "total_transactions": self.total_transactions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationResult":
        """Deserialize simulation result from dict."""
        from huddle.core.calendar.league_calendar import LeagueCalendar

        teams = {
            team_id: TeamState.from_dict(team_data)
            for team_id, team_data in data.get("teams", {}).items()
        }
        transaction_log = TransactionLog.from_dict(data.get("transaction_log", {}))
        calendars = [
            LeagueCalendar.from_dict(cal_data)
            for cal_data in data.get("calendars", [])
        ]
        draft_histories = {
            int(year): DraftState.from_dict(draft_data)
            for year, draft_data in data.get("draft_histories", {}).items()
        }
        season_standings = {
            int(year): [SeasonSnapshot.from_dict(s) for s in snapshots]
            for year, snapshots in data.get("season_standings", {}).items()
        }
        development_histories = {
            player_id: PlayerDevelopmentHistory.from_dict(dev_data)
            for player_id, dev_data in data.get("development_histories", {}).items()
        }

        return cls(
            teams=teams,
            transaction_log=transaction_log,
            calendars=calendars,
            draft_histories=draft_histories,
            season_standings=season_standings,
            development_histories=development_histories,
            blockbuster_trades=data.get("blockbuster_trades", []),
            seasons_simulated=data.get("seasons_simulated", 0),
            total_transactions=data.get("total_transactions", 0),
        )


class HistoricalSimulator:
    """
    Runs historical simulation to generate league state.

    Simulates multiple seasons of:
    - Offseason (free agency, draft, roster cuts)
    - Regular season (game results)
    - Playoffs (determine champions)

    All transactions are logged and rosters evolve naturally.
    """

    def __init__(
        self,
        config: SimulationConfig,
        player_generator: Callable,  # Function to generate players
        team_data: list,  # List of team info dicts
    ):
        self.config = config
        self.generate_players = player_generator
        self.team_data = team_data

        # State
        self.teams: dict[str, TeamState] = {}
        self.transaction_log: TransactionLog = None
        self.calendars: list[LeagueCalendar] = []
        self.draft_histories: dict[int, DraftState] = {}
        self.season_standings: dict[int, list[SeasonSnapshot]] = {}
        self.development_histories: dict[str, PlayerDevelopmentHistory] = {}
        self.blockbuster_trades: list[dict] = []  # Notable trades with details

        # Current simulation state
        self.current_season: int = 0
        self.current_calendar: LeagueCalendar = None

    @classmethod
    def create_with_nfl_teams(
        cls,
        config: SimulationConfig = None,
        player_generator: Callable = None,
    ) -> "HistoricalSimulator":
        """
        Create simulator with real NFL teams.

        Args:
            config: Simulation config (defaults to standard 4-year sim)
            player_generator: Function to generate players (defaults to generate_player)

        Returns:
            HistoricalSimulator ready to run with 32 NFL teams
        """
        from huddle.generators.player import generate_player

        if config is None:
            config = SimulationConfig()

        if player_generator is None:
            player_generator = generate_player

        return cls(
            config=config,
            player_generator=player_generator,
            team_data=get_nfl_team_data(),
        )

    def run(self) -> SimulationResult:
        """
        Run the full historical simulation.

        Returns SimulationResult with complete league state.
        """
        start_season = self.config.target_season - self.config.years_to_simulate

        self._log(f"Starting historical simulation from {start_season} to {self.config.target_season}")

        # Initialize league
        self._initialize_league(start_season)

        # Simulate each season
        for season in range(start_season, self.config.target_season + 1):
            self.current_season = season
            self._log(f"\n=== Simulating {season} Season ===")

            self._simulate_season(season)

        # Finalize
        self._log(f"\nSimulation complete. {len(self.transaction_log.transactions)} total transactions.")
        self._log(f"Tracked development for {len(self.development_histories)} players.")

        return SimulationResult(
            teams=self.teams,
            transaction_log=self.transaction_log,
            calendars=self.calendars,
            draft_histories=self.draft_histories,
            season_standings=self.season_standings,
            development_histories=self.development_histories,
            blockbuster_trades=self.blockbuster_trades,
            seasons_simulated=self.config.years_to_simulate + 1,
            total_transactions=len(self.transaction_log.transactions),
        )

    def _initialize_league(self, start_season: int):
        """Initialize league state for start of simulation."""
        self.transaction_log = TransactionLog(league_id="main")

        # Create teams
        for team_info in self.team_data:
            team_id = team_info["id"]

            # Initialize pick inventory
            picks = create_league_draft_picks(
                [team_id],
                start_season,
                years_ahead=3,
            )[team_id]

            # Initialize team status (random for first season)
            status = TeamStatusState(
                current_status=TeamStatus.UNKNOWN,
                status_since_season=start_season - 1,
            )

            # Assign random GM archetype for personality-based decisions
            gm_archetype = random.choice(list(GMArchetype))

            self.teams[team_id] = TeamState(
                team_id=team_id,
                team_name=team_info.get("name", team_id),
                pick_inventory=picks,
                status=status,
                identity=team_info.get("identity"),
                gm_archetype=gm_archetype,
            )

        # Generate initial rosters
        self._generate_initial_rosters(start_season)

    def _generate_initial_rosters(self, season: int):
        """
        Generate starting rosters for all teams within salary cap.

        Uses a cap-aware approach:
        1. Generate players for each position
        2. Assign contracts proportionally to fit within cap
        3. Ensure minimum roster requirements are met
        """
        self._log("Generating initial rosters...")

        for team_id, team in self.teams.items():
            # Generate players for each position
            roster = []

            # Position counts for initial roster (53 players total)
            position_counts = {
                "QB": 3, "RB": 4, "WR": 6, "TE": 3, "FB": 1,
                "LT": 2, "LG": 2, "C": 2, "RG": 2, "RT": 2,
                "DE": 4, "DT": 3,
                "OLB": 4, "ILB": 2, "MLB": 2,
                "CB": 5, "FS": 2, "SS": 2,
                "K": 1, "P": 1,
            }

            for position_str, count in position_counts.items():
                # Convert string to Position enum
                pos = Position(position_str)

                for i in range(count):
                    # Generate player with varied age
                    # First player at position tends to be older/more experienced
                    if i == 0:
                        age = random.randint(26, 32)
                    else:
                        age = random.randint(22, 28)

                    player = self.generate_players(
                        position=pos,
                        age=age,
                    )
                    roster.append(player)

            # Now assign contracts within cap budget
            contracts = self._assign_roster_contracts_within_cap(
                roster=roster,
                team_id=team_id,
                season=season,
                salary_cap=team.salary_cap,
                target_cap_usage=0.93,  # Target 93% cap usage (floor is 89%)
            )

            team.roster = roster
            team.contracts = contracts

            # Calculate cap usage
            team.cap_used = sum(c.cap_hit() for c in contracts.values())

    def _assign_roster_contracts_within_cap(
        self,
        roster: list,
        team_id: str,
        season: int,
        salary_cap: int = 255_000,
        target_cap_usage: float = 0.93,
    ) -> dict:
        """
        Assign contracts to roster players that fit within salary cap.

        Uses calibrated NFL market data from research/exports/contract_model.json.
        When total market values exceed cap budget, scales all contracts
        proportionally while maintaining relative differences.
        """
        from huddle.generators.calibration import calculate_contract_value

        contracts = {}
        budget = int(salary_cap * target_cap_usage)
        min_salary = 900  # ~$900K league minimum

        # Get calibrated market values for all players
        market_data = []
        for player in roster:
            cv = calculate_contract_value(
                position=player.position.value,
                overall=player.overall,
                age=player.age,
            )
            # Convert from millions to thousands
            market_salary = int(cv["apy_millions"] * 1000)
            market_data.append({
                "player": player,
                "salary": max(min_salary, market_salary),
                "years": cv["years"],
                "guaranteed_pct": cv["guaranteed_pct"],
                "tier": cv["tier"],
            })

        # Calculate total market value and scaling factor
        total_market = sum(md["salary"] for md in market_data)
        min_reserved = min_salary * len(roster)
        scalable_budget = budget - min_reserved
        scalable_market = total_market - min_reserved

        if scalable_market > 0 and total_market > budget:
            scale_factor = scalable_budget / scalable_market
        else:
            scale_factor = 1.0

        # Assign contracts to each player
        for md in market_data:
            player = md["player"]
            market_salary = md["salary"]

            # Scale salary if needed
            if scale_factor < 1.0:
                base_salary = min_salary + int((market_salary - min_salary) * scale_factor)
            else:
                base_salary = market_salary

            # Add variance
            base_salary = int(base_salary * random.uniform(0.9, 1.1))
            base_salary = max(min_salary, base_salary)

            # Determine contract type and years
            experience = max(0, player.age - 22)
            years = md["years"]

            if experience <= 4:
                contract_type = "rookie"
                years = max(1, 4 - experience)
            else:
                contract_type = "veteran"

            # Signing bonus from calibrated guaranteed percentage
            bonus_pct = md["guaranteed_pct"] * 0.5  # Half of guaranteed is signing bonus
            total_value_contract = base_salary * years
            signing_bonus = int(total_value_contract * bonus_pct)
            guaranteed = signing_bonus + base_salary  # First year guaranteed

            # Create contract
            if contract_type == "rookie" and experience < 4:
                # Use rookie contract with estimated pick
                pick_estimate = max(1, min(224, 32 + (4 - years) * 50))
                contract = create_rookie_contract(
                    player_id=str(player.id),
                    team_id=team_id,
                    pick_number=pick_estimate,
                    signed_date=date(season - experience, 4, 28),
                )
                # Advance to current year
                for _ in range(experience):
                    contract.advance_year()
            else:
                contract = create_veteran_contract(
                    player_id=str(player.id),
                    team_id=team_id,
                    total_years=years,
                    total_value=total_value_contract + signing_bonus,
                    guaranteed=guaranteed,
                    signing_bonus=signing_bonus,
                    signed_date=date(season - random.randint(0, years - 1), 3, 15),
                )

            contracts[str(player.id)] = contract

        return contracts

    def _simulate_season(self, season: int):
        """Simulate a complete season."""
        # Create calendar
        self.current_calendar = create_calendar_for_season(season)
        self.calendars.append(self.current_calendar)

        # 0. Create position plans for all teams (HC09-style holistic planning)
        # This determines each team's acquisition strategy BEFORE FA/Draft
        self._create_position_plans(season)

        # Advance to free agency
        self.current_calendar.advance_to_event(LeagueEvent.FREE_AGENCY_START)

        # 1. Free Agency (uses position plans for commitment-aware decisions)
        self._simulate_free_agency(season)

        # 1.5. Trades (commitment premiums affect valuations)
        self._simulate_trades(season)

        # 2. Draft (uses position plans for commitment-aware selection)
        self.current_calendar.advance_to_event(LeagueEvent.DRAFT_START)
        self._simulate_draft(season)

        # 3. Roster cuts
        self.current_calendar.advance_to_event(LeagueEvent.ROSTER_CUT_53)
        self._simulate_roster_cuts(season)

        # 4. Regular season
        self.current_calendar.advance_to_event(LeagueEvent.REGULAR_SEASON_START)
        self._simulate_regular_season(season)

        # 5. Playoffs
        self._simulate_playoffs(season)

        # 6. Apply player development (aging, growth/decline)
        self._apply_offseason_development(season)

        # 7. Update team statuses
        self._update_team_statuses(season)

        # 8. Handle expiring contracts
        self._handle_contract_expirations(season)

    def _create_position_plans(self, season: int):
        """
        Create HC09-style position plans for all teams before offseason.

        Each team decides for EACH position whether to:
        - KEEP_CURRENT: Current player is good enough
        - FREE_AGENCY: Target the FA market
        - DRAFT_EARLY/MID/LATE: Use a draft pick
        - TRADE: Pursue a trade
        - UNDECIDED: Still evaluating

        This affects commitment premiums in trades:
        - Team with #1 pick + elite QB prospect + DECIDED to draft QB
          values that pick at 1.4-1.6x market (harder to trade away)
        - UNDECIDED teams trade at market value
        """
        self._log(f"  Creating position plans for {season}...")

        # Generate draft class preview (for projection)
        # Teams need to know what prospects are available to plan
        draft_prospects = self._generate_draft_prospects(season)

        # Collect free agents preview
        fa_options = []
        for team in self.teams.values():
            expiring = [
                p for p in team.roster
                if str(p.id) in team.contracts and
                team.contracts[str(p.id)].is_expiring()
            ]
            for player in expiring:
                if random.random() < 0.35:  # 35% expected to hit FA
                    fa_options.append({
                        'player_id': str(player.id),
                        'position': player.position.value,
                        'overall': player.overall,
                        'asking_price': player.overall * 200,  # Rough estimate
                    })

        # Get draft order (based on previous season record)
        standings = sorted(
            self.teams.keys(),
            key=lambda t: self.teams[t].win_pct
        )

        # Create plan for each team
        for idx, team_id in enumerate(standings):
            team = self.teams[team_id]
            draft_position = idx + 1  # 1-indexed

            # Build roster info dict
            roster_info = {}
            for pos in ['QB', 'RB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT',
                        'DE', 'DT', 'OLB', 'ILB', 'CB', 'FS', 'SS']:
                players_at_pos = [p for p in team.roster if p.position.value == pos]
                if players_at_pos:
                    best = max(players_at_pos, key=lambda p: p.overall)
                    roster_info[pos] = {
                        'starter_overall': best.overall,
                        'depth_count': len(players_at_pos),
                    }
                else:
                    roster_info[pos] = {'starter_overall': 60, 'depth_count': 0}

            # Create the position plan
            gm_profile = GMProfile(archetype=team.gm_archetype or GMArchetype.BALANCED)

            team.position_plan = create_position_plan(
                team_id=team_id,
                gm_profile=gm_profile,
                draft_position=draft_position,
                cap_room=team.cap_space,
                roster=roster_info,
                draft_prospects=draft_prospects,
                fa_options=fa_options,
            )

    def _generate_draft_prospects(self, season: int) -> list[DraftProspect]:
        """
        Generate draft prospect previews for position planning.

        These are simplified projections used for planning, not actual players.
        """
        from uuid import uuid4

        prospects = []

        # Position distribution for elite prospects
        ELITE_POSITIONS = ['QB', 'DE', 'CB', 'WR', 'LT', 'DT']
        MID_POSITIONS = ['RB', 'TE', 'OLB', 'ILB', 'FS', 'SS', 'LG', 'RG', 'C', 'RT']

        pick_num = 1
        # Top 10 - elite prospects
        for i in range(10):
            pos = ELITE_POSITIONS[i % len(ELITE_POSITIONS)]
            prospects.append(DraftProspect(
                player_id=uuid4(),
                name=f"Top {pos} Prospect {i+1}",
                position=pos,
                grade=95 - i,  # 95, 94, 93...
                projected_round=1,
                projected_pick=pick_num,
            ))
            pick_num += 1

        # Picks 11-32 - good prospects
        for i in range(22):
            pos = (ELITE_POSITIONS + MID_POSITIONS)[i % len(ELITE_POSITIONS + MID_POSITIONS)]
            prospects.append(DraftProspect(
                player_id=uuid4(),
                name=f"Rd1 {pos} Prospect",
                position=pos,
                grade=85 - (i // 4),  # 85-80 range
                projected_round=1,
                projected_pick=pick_num,
            ))
            pick_num += 1

        # Rounds 2-3 prospects
        for rd in [2, 3]:
            for i in range(32):
                pos = (ELITE_POSITIONS + MID_POSITIONS)[i % len(ELITE_POSITIONS + MID_POSITIONS)]
                prospects.append(DraftProspect(
                    player_id=uuid4(),
                    name=f"Rd{rd} {pos} Prospect",
                    position=pos,
                    grade=78 - (rd * 3) - (i // 8),
                    projected_round=rd,
                    projected_pick=pick_num,
                ))
                pick_num += 1

        return prospects

    def _simulate_trades(self, season: int, config: Optional[TradeMarketConfig] = None):
        """
        Simulate trades using competitive market-based auction system.

        Replaces sequential trading with a simultaneous market where:
        1. All 32 teams participate equally
        2. Multiple teams can bid on the same asset
        3. Sellers pick the best offer, not the first acceptable one
        4. Trade volume determined by market demand, not arbitrary caps
        """
        self._log(f"  Simulating trades for {season}...")

        if config is None:
            config = TradeMarketConfig()

        # Generate draft prospects for trade valuation
        draft_prospects = self._generate_draft_prospects(season)

        # Convert TeamState objects to TeamTradeState for market system
        trade_states = self._create_trade_states()

        # =============================================================
        # Phase 0: Blockbuster Trades (10% chance per offseason)
        # =============================================================
        blockbuster = attempt_blockbuster_trade(
            teams=trade_states,
            season=season,
            config=config,
            draft_prospects=draft_prospects,
        )

        if blockbuster:
            self._execute_market_trade(blockbuster, season)
            self._log(f"    BLOCKBUSTER: {blockbuster}")
            self._record_blockbuster(blockbuster, season)

        # =============================================================
        # Market-Based Trading (all teams participate equally)
        # =============================================================
        def on_trade(trade: ExecutedTrade, round_num: int):
            """Callback for each executed trade."""
            self._execute_market_trade(trade, season)
            # Log trade details
            to_buyer = ", ".join(
                a.player_name or str(a.pick) for a in trade.assets_to_buyer[:2]
            )
            self._log(f"    Round {round_num}: {trade.seller_team_id} -> {trade.buyer_team_id}: {to_buyer}")

        executed_trades = simulate_trade_market(
            teams=trade_states,
            season=season,
            config=config,
            draft_prospects=draft_prospects,
            on_trade=on_trade,
        )

        # Summarize results
        total_trades = len(executed_trades) + (1 if blockbuster else 0)
        participating_teams = set()
        for trade in executed_trades:
            participating_teams.add(trade.seller_team_id)
            participating_teams.add(trade.buyer_team_id)
        if blockbuster:
            participating_teams.add(blockbuster.seller_team_id)
            participating_teams.add(blockbuster.buyer_team_id)

        self._log(f"    {total_trades} trades completed, {len(participating_teams)} teams participated")

    def _create_trade_states(self) -> dict[str, TeamTradeState]:
        """
        Convert TeamState objects to TeamTradeState for market system.

        This creates a lightweight wrapper that the trade market functions
        can operate on without circular imports.
        """
        trade_states = {}

        for team_id, team in self.teams.items():
            # Calculate needs
            needs = calculate_team_needs(team.roster)
            needs_dict = {
                p: needs.get_need(p) for p in [
                    "QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                    "DE", "DT", "OLB", "ILB", "CB", "FS", "SS"
                ]
            }

            # Get or create identity
            identity = team.identity
            if identity is None:
                from huddle.core.models.team_identity import TeamIdentity
                identity = TeamIdentity()

            trade_states[team_id] = TeamTradeState(
                team_id=team_id,
                roster=team.roster,
                contracts=team.contracts,
                pick_inventory=team.pick_inventory or DraftPickInventory(team_id=team_id),
                position_plan=team.position_plan,
                identity=identity,
                status=team.status or TeamStatusState(current_status=TeamStatus.REBUILDING),
                needs=needs_dict,
                gm_archetype=team.gm_archetype,
                salary_cap=team.salary_cap,
                cap_used=team.cap_used,
            )

        return trade_states

    def _execute_market_trade(self, trade: ExecutedTrade, season: int):
        """
        Execute a trade from the market system.

        Transfers players and picks between teams based on the ExecutedTrade record.
        """
        from huddle.core.ai.trade_ai import TradeAsset, TradeProposal

        seller = self.teams[trade.seller_team_id]
        buyer = self.teams[trade.buyer_team_id]

        # Transfer assets TO BUYER (from seller)
        for asset in trade.assets_to_buyer:
            if asset.asset_type == "player":
                player = next(
                    (p for p in seller.roster if str(p.id) == asset.player_id),
                    None
                )
                if player:
                    seller.roster.remove(player)
                    buyer.roster.append(player)
                    # Transfer contract
                    contract = seller.contracts.pop(asset.player_id, None)
                    if contract:
                        buyer.contracts[asset.player_id] = contract
                        cap_hit = contract.cap_hit() if hasattr(contract, 'cap_hit') else 0
                        seller.cap_used -= cap_hit
                        buyer.cap_used += cap_hit
            elif asset.asset_type == "pick" and asset.pick:
                asset.pick.current_team_id = buyer.team_id

        # Transfer assets TO SELLER (from buyer)
        for asset in trade.assets_to_seller:
            if asset.asset_type == "player":
                player = next(
                    (p for p in buyer.roster if str(p.id) == asset.player_id),
                    None
                )
                if player:
                    buyer.roster.remove(player)
                    seller.roster.append(player)
                    contract = buyer.contracts.pop(asset.player_id, None)
                    if contract:
                        seller.contracts[asset.player_id] = contract
                        cap_hit = contract.cap_hit() if hasattr(contract, 'cap_hit') else 0
                        buyer.cap_used -= cap_hit
                        seller.cap_used += cap_hit
            elif asset.asset_type == "pick" and asset.pick:
                asset.pick.current_team_id = seller.team_id

        # Log transaction
        self.transaction_log.add(Transaction(
            transaction_type=TransactionType.TRADE,
            team_id=seller.team_id,
            other_team_id=buyer.team_id,
            season=season,
            transaction_date=self.current_calendar.current_date,
        ))

    def _record_blockbuster(self, trade: ExecutedTrade, season: int):
        """Record a blockbuster trade for history tracking."""
        # Find player details
        player_asset = next(
            (a for a in trade.assets_to_buyer if a.asset_type == "player"),
            None
        )
        pick_assets = [a for a in trade.assets_to_seller if a.asset_type == "pick"]

        if player_asset:
            self.blockbuster_trades.append({
                "season": season,
                "type": "elite_player_for_picks",
                "player_name": player_asset.player_name,
                "player_position": player_asset.player_position,
                "player_overall": player_asset.player_overall,
                "from_team": trade.seller_team_id,
                "to_team": trade.buyer_team_id,
                "picks_received": len(pick_assets),
                "pick_details": [
                    {
                        "round": a.pick.round if a.pick else 0,
                        "year": a.pick.year if a.pick else season,
                        "value": a.value,
                    }
                    for a in pick_assets
                ],
            })

    def _execute_trade(self, team_from: 'TeamState', team_to: 'TeamState',
                       proposal: 'TradeProposal', season: int):
        """Execute a trade between two teams."""
        # Transfer players
        for asset in proposal.assets_requested:
            if asset.asset_type == "player":
                player = next((p for p in team_from.roster if str(p.id) == asset.player_id), None)
                if player:
                    team_from.roster.remove(player)
                    team_to.roster.append(player)
                    # Transfer contract
                    contract = team_from.contracts.pop(asset.player_id, None)
                    if contract:
                        team_to.contracts[asset.player_id] = contract
                        cap_hit = contract.cap_hit() if hasattr(contract, 'cap_hit') else 0
                        team_from.cap_used -= cap_hit
                        team_to.cap_used += cap_hit

        for asset in proposal.assets_offered:
            if asset.asset_type == "player":
                player = next((p for p in team_to.roster if str(p.id) == asset.player_id), None)
                if player:
                    team_to.roster.remove(player)
                    team_from.roster.append(player)
                    contract = team_to.contracts.pop(asset.player_id, None)
                    if contract:
                        team_from.contracts[asset.player_id] = contract
                        cap_hit = contract.cap_hit() if hasattr(contract, 'cap_hit') else 0
                        team_to.cap_used -= cap_hit
                        team_from.cap_used += cap_hit

        # Transfer picks
        for asset in proposal.assets_requested:
            if asset.asset_type == "pick" and asset.pick:
                asset.pick.current_team_id = team_to.team_id

        for asset in proposal.assets_offered:
            if asset.asset_type == "pick" and asset.pick:
                asset.pick.current_team_id = team_from.team_id

        # Log transaction (single log for the league)
        self.transaction_log.add(Transaction(
            transaction_type=TransactionType.TRADE,
            team_id=team_from.team_id,
            other_team_id=team_to.team_id,
            season=season,
            transaction_date=self.current_calendar.current_date,
        ))

    def _simulate_free_agency(self, season: int):
        """
        Simulate free agency with competitive bidding.

        Uses research-backed FreeAgencyAI for:
        - Position priority based on Calvetti framework
        - GM archetype personality-driven offers
        - FA premium for positions better to sign than draft (RB, CB)

        Target: Teams should reach 89-95% cap usage.
        """
        self._log(f"  Free agency {season}...")

        from huddle.core.contracts.market_value import calculate_market_value
        from huddle.core.ai import calculate_team_needs

        # Collect free agents (players with expiring contracts)
        free_agents = []
        for team in self.teams.values():
            expiring = [
                p for p in team.roster
                if str(p.id) in team.contracts and
                team.contracts[str(p.id)].is_expiring()
            ]
            # Some players re-sign with current team, some hit market
            for player in expiring:
                if random.random() < 0.35:  # 35% hit free agency
                    free_agents.append((player, team.team_id))

        # Sort FAs by value (best players sign first - realistic)
        free_agents.sort(key=lambda x: x[0].overall, reverse=True)

        # Process each free agent with competitive bidding
        for player, old_team_id in free_agents:
            # Calculate base market value
            market = calculate_market_value(player)

            # Find interested teams using FreeAgencyAI for evaluation
            interested_teams = []
            min_roster = 45
            min_salary = 900  # ~$900K league minimum

            for team in self.teams.values():
                if team.team_id == old_team_id:
                    continue  # Old team handled separately

                # Reserve cap for filling roster to minimum 45
                roster_spots_needed = max(0, min_roster - len(team.roster))
                cap_reserve = roster_spots_needed * min_salary

                # Check cap space - need room for this contract PLUS roster reserve
                available_for_fa = team.cap_space - cap_reserve
                if available_for_fa < market.cap_hit_year1:
                    continue

                # Check if team's position plan says to pursue this FA
                plan_aggression = 0.5  # Default moderate interest
                if team.position_plan:
                    pursue, aggression = should_pursue_fa(team.position_plan, {
                        'position': player.position.value,
                        'player_id': str(player.id),
                        'overall': player.overall,
                    })
                    if not pursue:
                        continue  # Plan says don't pursue this position via FA
                    plan_aggression = aggression

                # Use FreeAgencyAI for research-backed evaluation
                needs = calculate_team_needs(team.roster)
                fa_ai = FreeAgencyAI(
                    team_id=team.team_id,
                    team_identity=team.identity,
                    team_status=team.status,
                    cap_space=available_for_fa,
                    team_needs={p: needs.get_need(p) for p in [
                        "QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                        "DE", "DT", "OLB", "ILB", "CB", "FS", "SS"
                    ]},
                    gm_archetype=team.gm_archetype,
                )

                # Evaluate this free agent
                evaluation = fa_ai.evaluate_free_agent(player)
                position_need = needs.get_need(player.position.value)

                # Combine AI priority with plan aggression
                # High plan aggression = planned FA target = higher effective priority
                effective_priority = evaluation.priority * (0.7 + plan_aggression * 0.6)

                # Use AI priority score for interest determination
                if effective_priority > 0.3 or random.random() < 0.2:
                    interested_teams.append((team, effective_priority, position_need, fa_ai, plan_aggression))

            if not interested_teams:
                # No interest - player goes unsigned, remove from old team
                old_team = self.teams[old_team_id]
                old_team.roster = [p for p in old_team.roster if p.id != player.id]
                if str(player.id) in old_team.contracts:
                    del old_team.contracts[str(player.id)]
                continue

            # Competitive bidding - more interested teams = higher price
            num_bidders = len(interested_teams)
            competition_multiplier = 1.0 + min(0.3, num_bidders * 0.05)  # Up to 30% premium

            # Calculate final contract value FIRST
            final_value = int(market.total_value * competition_multiplier)
            years = market.years
            signing_bonus = int(final_value * 0.25)  # 25% signing bonus
            guaranteed = int(final_value * 0.45)  # 45% guaranteed

            # Create contract to get actual cap hit
            contract = create_veteran_contract(
                player_id=str(player.id),
                team_id="temp",  # Temp for calculation
                total_years=years,
                total_value=final_value,
                guaranteed=guaranteed,
                signing_bonus=signing_bonus,
                signed_date=self.current_calendar.current_date,
            )

            # Now find a team that can ACTUALLY afford this contract
            # Sort by interest and filter by actual cap space (including roster reserve)
            interested_teams.sort(key=lambda x: x[1] * random.uniform(0.8, 1.2), reverse=True)

            winning_team = None
            winning_fa_ai = None
            actual_cap_hit = contract.cap_hit()
            for team, priority, need, fa_ai, aggression in interested_teams:
                current_cap = sum(c.cap_hit() for c in team.contracts.values())
                # Reserve cap for filling roster to minimum 45
                roster_spots_needed = max(0, min_roster - len(team.roster) - 1)  # -1 since signing adds a player
                cap_reserve = roster_spots_needed * min_salary
                if current_cap + actual_cap_hit + cap_reserve <= team.salary_cap:
                    winning_team = team
                    winning_fa_ai = fa_ai
                    break

            if not winning_team:
                # No team can afford - player goes unsigned
                old_team = self.teams[old_team_id]
                old_team.roster = [p for p in old_team.roster if p.id != player.id]
                if str(player.id) in old_team.contracts:
                    del old_team.contracts[str(player.id)]
                continue

            # Update contract with actual team
            contract = create_veteran_contract(
                player_id=str(player.id),
                team_id=winning_team.team_id,
                total_years=years,
                total_value=final_value,
                guaranteed=guaranteed,
                signing_bonus=signing_bonus,
                signed_date=self.current_calendar.current_date,
            )

            # Update rosters
            old_team = self.teams[old_team_id]
            old_team.roster = [p for p in old_team.roster if p.id != player.id]
            if str(player.id) in old_team.contracts:
                del old_team.contracts[str(player.id)]

            winning_team.roster.append(player)
            winning_team.contracts[str(player.id)] = contract
            winning_team.cap_used = sum(c.cap_hit() for c in winning_team.contracts.values())

            # Update the team's position plan - position now filled via FA
            if winning_team.position_plan:
                update_plan_after_fa(winning_team.position_plan, {
                    'position': player.position.value,
                    'player_id': str(player.id),
                    'overall': player.overall,
                    'contract_value': final_value,
                })

            # Log transaction
            self.transaction_log.add(create_signing_transaction(
                team_id=winning_team.team_id,
                team_name=winning_team.team_name,
                player_id=str(player.id),
                player_name=player.full_name,
                player_position=player.position.value,
                contract_years=years,
                contract_value=final_value,
                contract_guaranteed=guaranteed,
                season=season,
                transaction_date=self.current_calendar.current_date,
            ))

    def _simulate_draft(self, season: int):
        """
        Simulate the draft with trade-up opportunities.

        Key enhancement: Mock draft consensus drives trade urgency.
        Teams trade up when "my guy will be gone before my pick."
        """
        self._log(f"  Draft {season}...")

        # Get trade config
        from huddle.core.ai.trade_market import TradeMarketConfig
        trade_config = TradeMarketConfig()

        # Generate draft class with realistic position distribution
        # Based on typical NFL draft classes
        DRAFT_CLASS_COUNTS = {
            # Offense (skill)
            "QB": 8,
            "RB": 10,
            "WR": 16,
            "TE": 8,
            # Offense (line) - realistic: ~24 total, not 50
            "LT": 5,
            "LG": 5,
            "C": 4,
            "RG": 5,
            "RT": 5,
            # Defense (front)
            "DE": 10,
            "DT": 8,
            # Defense (LB)
            "OLB": 8,
            "ILB": 6,
            "MLB": 4,
            # Defense (secondary)
            "CB": 14,
            "FS": 6,
            "SS": 6,
        }
        draft_class = []
        for position_str, count in DRAFT_CLASS_COUNTS.items():
            pos = Position(position_str)
            for _ in range(count):
                player = self.generate_players(
                    position=pos,
                    age=random.randint(21, 23),
                )
                draft_class.append(player)

        # Sort by overall (draft order proxy)
        draft_class.sort(key=lambda p: p.overall, reverse=True)

        # Get draft order (based on previous season record, reversed)
        standings = sorted(
            self.teams.keys(),
            key=lambda t: self.teams[t].win_pct
        )

        # Create draft state
        draft_state = create_draft_order(
            year=season,
            team_standings=standings,
            pick_inventories={t: self.teams[t].pick_inventory for t in self.teams},
            num_rounds=self.config.draft_rounds,
        )
        self.draft_histories[season] = draft_state

        # === NEW: Generate Mock Draft Consensus ===
        mock = generate_mock_draft(
            prospects=draft_class,
            teams=self.teams,
            noise_factor=trade_config.draft_mock_noise,
        )
        self._log(f"    Generated mock draft consensus for {len(draft_class)} prospects")

        # Track draft trades
        draft_trades_executed = 0
        drafted_player_ids = set()

        # Execute draft
        pick_number = 1
        available = list(draft_class)

        while not draft_state.is_complete and available:
            pick = draft_state.current_pick
            if not pick:
                break

            team = self.teams[pick.current_team_id]

            # === NEW: Check for trade-up interest from later teams ===
            trade_executed = False
            if (draft_trades_executed < trade_config.draft_max_trades_per_draft and
                pick_number % trade_config.draft_trade_check_frequency == 1):

                trade_executed = self._check_draft_trade_ups(
                    current_pick=pick,
                    pick_number=pick_number,
                    mock=mock,
                    available=available,
                    draft_state=draft_state,
                    trade_config=trade_config,
                    season=season,
                )

                if trade_executed:
                    draft_trades_executed += 1
                    # Pick ownership changed - re-get team on clock
                    team = self.teams[pick.current_team_id]
                    self._log(f"    Trade executed! Pick #{pick_number} now belongs to {team.team_name}")

            # Use full DraftAI for research-backed, GM-personality-aware selection
            needs = calculate_team_needs(team.roster)

            # Create DraftAI for this team
            draft_ai = DraftAI(
                team_id=team.team_id,
                team_identity=team.identity,
                team_status=team.status,
                team_needs=needs,
                gm_archetype=team.gm_archetype,
            )

            # Use position plan's draft board if available
            selected_player = None
            if team.position_plan:
                # Convert available players to DraftProspect format for get_draft_target
                # Calculate projected round from pick position
                current_round = (pick_number - 1) // len(self.teams) + 1
                available_prospects = [
                    DraftProspect(
                        player_id=str(p.id),
                        name=p.full_name,
                        position=p.position.value,
                        grade=p.overall,
                        projected_round=current_round,
                        projected_pick=pick_number,
                    )
                    for p in available
                ]
                target = get_draft_target(team.position_plan, available_prospects)
                if target:
                    # Find the actual player matching the target
                    selected_player = next(
                        (p for p in available if str(p.id) == str(target.player_id)),
                        None
                    )

            # Fall back to DraftAI if no plan target found
            if not selected_player:
                selected_player = draft_ai.select_player(available, pick_number)

            # Fallback if AI returns None (shouldn't happen)
            if not selected_player and available:
                selected_player = available[0]

            if not selected_player:
                break

            # Make selection
            pick.player_selected_id = str(selected_player.id)
            pick.selection_date = self.current_calendar.current_date
            pick.pick_number = pick_number

            # Create rookie contract
            contract = create_rookie_contract(
                player_id=str(selected_player.id),
                team_id=team.team_id,
                pick_number=pick_number,
                signed_date=self.current_calendar.current_date,
            )

            # Add to roster
            team.roster.append(selected_player)
            team.contracts[str(selected_player.id)] = contract
            team.cap_used += contract.cap_hit()

            # Track drafted player
            drafted_player_ids.add(str(selected_player.id))

            # Update the team's position plan - position now filled via draft
            if team.position_plan:
                update_plan_after_draft(team.position_plan, {
                    'position': selected_player.position.value,
                    'player_id': str(selected_player.id),
                    'overall': selected_player.overall,
                    'round': pick.round,
                    'pick': pick_number,
                })

            # Remove from available
            available.remove(selected_player)

            # Log transaction
            self.transaction_log.add(create_draft_transaction(
                team_id=team.team_id,
                team_name=team.team_name,
                player_id=str(selected_player.id),
                player_name=selected_player.full_name,
                player_position=selected_player.position.value,
                pick_number=pick_number,
                pick_round=pick.round,
                season=season,
                transaction_date=self.current_calendar.current_date,
            ))

            pick_number += 1
            draft_state.advance()

        # Log draft trade summary
        if draft_trades_executed > 0:
            self._log(f"    Draft trades: {draft_trades_executed}")

    def _check_draft_trade_ups(
        self,
        current_pick: DraftPick,
        pick_number: int,
        mock: MockDraft,
        available: list,
        draft_state: DraftState,
        trade_config: "TradeMarketConfig",
        season: int,
    ) -> bool:
        """
        Check if any team wants to trade up to the current pick.

        Returns True if a trade was executed (pick ownership changed).

        Logic:
        1. Get team currently on the clock
        2. Check if they're willing to trade down
        3. Find teams picking in next N spots that want to trade up
        4. Execute best trade if one exists
        """
        from huddle.core.draft.picks import get_pick_value

        current_team = self.teams[current_pick.current_team_id]

        # First, check if current team would even consider trading down
        # Get their best available evaluation
        needs = calculate_team_needs(current_team.roster)
        draft_ai = DraftAI(
            team_id=current_team.team_id,
            team_identity=current_team.identity,
            team_status=current_team.status,
            team_needs=needs,
            gm_archetype=current_team.gm_archetype,
        )

        if not available:
            return False

        # Get best available for current team
        rankings = draft_ai.rank_prospects(available[:30], pick_number)
        if not rankings:
            return False

        best_available = rankings[0]

        # Quick check: would current team trade down?
        # Skip detailed check if they definitely won't
        if best_available.raw_grade >= 90:
            # Elite talent - unlikely to trade down
            if random.random() > 0.15:  # 15% chance to still consider
                return False

        # Get upcoming picks that might want to trade up
        # DraftState stores picks in rounds[].order[]
        upcoming_picks = []
        overall_pick_num = 0
        for round_order in draft_state.rounds:
            for future_pick in round_order.order:
                overall_pick_num += 1
                if future_pick.player_selected_id:
                    continue  # Already used
                if overall_pick_num > pick_number and overall_pick_num <= pick_number + trade_config.draft_trade_up_range:
                    upcoming_picks.append((future_pick, overall_pick_num))

        if not upcoming_picks:
            return False

        # Find interested teams
        best_trade = None
        best_trade_value = 0

        for future_pick, future_pick_num in upcoming_picks[:10]:  # Check up to 10 teams
            later_team = self.teams.get(future_pick.current_team_id)
            if not later_team:
                continue

            # Skip if same team
            if later_team.team_id == current_team.team_id:
                continue

            # Create DraftAI for potential trading team
            later_needs = calculate_team_needs(later_team.roster)
            later_draft_ai = DraftAI(
                team_id=later_team.team_id,
                team_identity=later_team.identity,
                team_status=later_team.status,
                team_needs=later_needs,
                gm_archetype=later_team.gm_archetype,
            )

            # Does this team want to trade up?
            target_player = later_draft_ai.wants_to_trade_up_here(
                current_pick=pick_number,
                my_pick=future_pick_num,
                mock=mock,
                available=available,
                position_plan=later_team.position_plan,
                fall_probability=trade_config.draft_fall_probability,
            )

            if not target_player:
                continue

            # Generate trade package
            package_picks = later_draft_ai.generate_trade_up_package(
                target_pick=pick_number,
                my_pick=future_pick_num,
                inventory=later_team.pick_inventory,
                value_threshold=trade_config.draft_trade_value_threshold,
            )

            if not package_picks:
                continue

            # Calculate total package value (future pick + additional picks)
            future_pick_value = get_pick_value(future_pick_num)
            package_value = future_pick_value + sum(p.estimated_value for p in package_picks)

            # Current team evaluates the offer
            current_pick_value = get_pick_value(pick_number)
            accept, reason = draft_ai.evaluate_trade_down_offer(
                offered_picks=[future_pick] + package_picks,
                current_pick_value=current_pick_value,
                best_available=best_available,
                position_plan=current_team.position_plan,
                mock=mock,
            )

            if accept and package_value > best_trade_value:
                best_trade = {
                    'trading_up_team': later_team,
                    'trading_down_team': current_team,
                    'pick_acquired': current_pick,
                    'pick_given': future_pick,
                    'additional_picks': package_picks,
                    'target_player': target_player,
                    'package_value': package_value,
                    'reason': reason,
                }
                best_trade_value = package_value

        # Execute best trade if found
        if best_trade:
            self._execute_draft_trade(
                pick_acquired=best_trade['pick_acquired'],
                pick_given=best_trade['pick_given'],
                additional_picks=best_trade['additional_picks'],
                trading_up_team=best_trade['trading_up_team'],
                trading_down_team=best_trade['trading_down_team'],
                target_player=best_trade['target_player'],
                season=season,
            )
            return True

        return False

    def _execute_draft_trade(
        self,
        pick_acquired: DraftPick,
        pick_given: DraftPick,
        additional_picks: list,
        trading_up_team: "TeamState",
        trading_down_team: "TeamState",
        target_player: "Player",
        season: int,
    ):
        """
        Execute a draft day trade.

        Swaps pick ownership and logs the transaction.
        """
        # Swap pick ownership
        old_owner = pick_acquired.current_team_id
        pick_acquired.current_team_id = trading_up_team.team_id
        pick_given.current_team_id = trading_down_team.team_id

        # Transfer additional picks
        for pick in additional_picks:
            pick.current_team_id = trading_down_team.team_id

        # Log the trade transaction with DRAFT_TRADE type
        pick_details = [f"#{pick_given.pick_number or '?'} (Rd {pick_given.round})"]
        for p in additional_picks[:3]:
            pick_details.append(f"#{p.pick_number or '?'} (Rd {p.round})")

        self.transaction_log.add(Transaction(
            transaction_type=TransactionType.DRAFT_TRADE,
            team_id=trading_down_team.team_id,
            team_name=trading_down_team.team_name,
            other_team_id=trading_up_team.team_id,
            season=season,
            transaction_date=self.current_calendar.current_date,
            notes=f"Draft trade: {trading_up_team.team_name} trades up for pick #{pick_acquired.pick_number or '?'} "
                  f"targeting {target_player.full_name} ({target_player.position.value}). "
                  f"Sent: {', '.join(pick_details)}",
        ))

        self._log(f"      DRAFT TRADE: {trading_up_team.team_name} trades up to #{pick_acquired.pick_number or '?'} "
                  f"for {target_player.full_name}")

    def _simulate_roster_cuts(self, season: int):
        """Simulate roster cuts to 53."""
        self._log(f"  Roster cuts {season}...")

        for team in self.teams.values():
            while len(team.roster) > 53:
                # Find lowest value player
                team.roster.sort(key=lambda p: p.overall)
                cut_player = team.roster[0]

                # Remove from roster
                team.roster = team.roster[1:]

                # Handle contract
                if str(cut_player.id) in team.contracts:
                    contract = team.contracts[str(cut_player.id)]
                    dead_money = contract.dead_money_if_cut()
                    del team.contracts[str(cut_player.id)]

                    # Log transaction
                    self.transaction_log.add(create_cut_transaction(
                        team_id=team.team_id,
                        team_name=team.team_name,
                        player_id=str(cut_player.id),
                        player_name=cut_player.full_name,
                        player_position=cut_player.position.value,
                        season=season,
                        transaction_date=self.current_calendar.current_date,
                        dead_money=dead_money,
                    ))

    def _simulate_regular_season(self, season: int):
        """
        Simulate regular season games using the real game simulation engine.

        Creates a proper League object, generates schedule, and uses SeasonSimulator
        to play through all 18 weeks of games.
        """
        self._log(f"  Regular season {season}...")

        # Build a proper League object for simulation
        league = self._build_league_for_simulation(season)

        if not league:
            # Fallback to statistical simulation if league creation fails
            self._log("  Warning: Could not create league, using statistical simulation")
            self._simulate_regular_season_statistical(season)
            return

        # Generate schedule
        team_abbrs = list(league.teams.keys())
        schedule = generate_nfl_schedule(season, team_abbrs)
        league.schedule = schedule
        self._log(f"    Generated {len(schedule)} games")

        # Create simulator and run all games
        simulator = SeasonSimulator(league, mode=SimulationMode.FAST)

        # Simulate week by week
        for week in range(1, 19):
            week_result = simulator.simulate_week(week)
            if self.config.verbose and week_result.games:
                self._log(f"    Week {week}: {len(week_result.games)} games")

        # Extract results back to TeamState
        for team_id, team_state in self.teams.items():
            if team_id in league.standings:
                standing = league.standings[team_id]
                team_state.wins = standing.wins
                team_state.losses = standing.losses

        # Store league for playoff simulation
        self._simulation_league = league
        self._log(f"    Season complete")

    def _simulate_regular_season_statistical(self, season: int):
        """Fallback statistical simulation (used when real engine unavailable)."""
        for team in self.teams.values():
            avg_overall = sum(p.overall for p in team.roster) / len(team.roster) if team.roster else 50
            expected_wins = (avg_overall - 50) / 50 * 8 + 8.5
            actual_wins = int(expected_wins + random.gauss(0, 2.5))
            actual_wins = max(0, min(17, actual_wins))
            team.wins = actual_wins
            team.losses = self.config.games_per_season - actual_wins

    def _build_league_for_simulation(self, season: int) -> Optional[League]:
        """
        Build a proper League object from TeamState data for game simulation.

        Creates Team objects with Rosters containing the players.
        """
        try:
            league = League(
                name="Historical Simulation",
                current_season=season,
                current_week=0,
            )

            for team_id, team_state in self.teams.items():
                # Look up NFL team data if available
                nfl_data = NFL_TEAMS.get(team_id)

                if nfl_data:
                    team = Team(
                        name=nfl_data.name,
                        city=nfl_data.city,
                        abbreviation=nfl_data.abbreviation,
                        primary_color=nfl_data.primary_color,
                        secondary_color=nfl_data.secondary_color,
                    )
                else:
                    # Use generic team info
                    team = Team(
                        name=team_state.team_name,
                        city="City",
                        abbreviation=team_id,
                        primary_color="#333333",
                        secondary_color="#CCCCCC",
                    )

                # Add all players from TeamState roster
                for player in team_state.roster:
                    team.roster.add_player(player)

                # Auto-fill depth chart
                team.roster.auto_fill_depth_chart()

                # Add to league
                league.teams[team_id] = team
                league.standings[team_id] = TeamStanding(
                    team_id=team.id,
                    abbreviation=team_id,
                )

            return league

        except Exception as e:
            self._log(f"  Error building league: {e}")
            return None

    def _simulate_playoffs(self, season: int):
        """
        Simulate playoffs using the real playoff bracket simulation.

        Uses the league from regular season simulation if available,
        otherwise falls back to simplified playoff simulation.
        """
        self._log(f"  Playoffs {season}...")

        # Try to use real playoff simulation if we have the league
        league = getattr(self, '_simulation_league', None)

        if league and len(league.teams) == 32:
            # Use real playoff simulation with proper bracket
            try:
                simulator = SeasonSimulator(league, mode=SimulationMode.FAST)
                playoff_results = simulator.simulate_playoffs()

                # Extract playoff participants
                from huddle.core.league.nfl_data import Conference
                for conf in [Conference.AFC, Conference.NFC]:
                    bracket = league.get_playoff_bracket(conf)
                    for standing in bracket[:7]:  # Top 7 in each conference
                        if standing.abbreviation in self.teams:
                            self.teams[standing.abbreviation].made_playoffs = True

                # Find champion
                champion_abbr = league.champions.get(season)
                if champion_abbr and champion_abbr in self.teams:
                    self.teams[champion_abbr].won_championship = True
                    self._log(f"    Champion: {self.teams[champion_abbr].team_name}")
                    return

            except Exception as e:
                self._log(f"    Playoff simulation error: {e}, using simplified playoffs")

        # Fallback to simplified playoff simulation
        self._simulate_playoffs_simplified(season)

    def _simulate_playoffs_simplified(self, season: int):
        """Simplified playoff simulation (fallback for non-32-team leagues)."""
        standings = sorted(
            self.teams.values(),
            key=lambda t: (t.wins, random.random()),
            reverse=True
        )

        # Playoff spots scale with league size (roughly 40-44% of teams)
        num_teams = len(self.teams)
        actual_playoff_spots = min(
            self.config.playoff_teams,
            max(1, int(num_teams * 0.44))
        )

        playoff_teams = standings[:actual_playoff_spots]

        for team in playoff_teams:
            team.made_playoffs = True

        # Champion from top teams (higher seeds more likely)
        if playoff_teams:
            weights = [4, 3, 2, 1][:len(playoff_teams)]
            champion = random.choices(playoff_teams[:4], weights=weights[:len(playoff_teams)])[0]
            champion.won_championship = True
            self._log(f"    Champion: {champion.team_name}")

    def _update_team_statuses(self, season: int):
        """Update team statuses based on season results."""
        for team in self.teams.values():
            # Calculate roster metrics
            ages = [p.age for p in team.roster]
            avg_age = sum(ages) / len(ages) if ages else 26

            rookie_starters = sum(
                1 for p in team.roster[:22]  # Approximate starters
                if p.age <= 23
            )

            dead_money_pct = 0.05  # Simplified

            # Evaluate for status change
            new_status = evaluate_team_status(
                current_state=team.status,
                season=season,
                made_playoffs=team.made_playoffs,
                won_championship=team.won_championship,
                win_pct=team.win_pct,
                roster_avg_age=avg_age,
                rookie_starters=rookie_starters,
                dead_money_pct=dead_money_pct,
            )

            if new_status:
                self._log(f"    {team.team_name}: {team.status.current_status.name} -> {new_status.name}")
                team.status.transition_to(
                    new_status,
                    season,
                    trigger=f"Season {season} results",
                )

        # Capture season standings before resetting
        self._capture_season_standings(season)

        # Reset for next season (but keep final season stats)
        for team in self.teams.values():
            if season < self.config.target_season:
                team.wins = 0
                team.losses = 0
                team.made_playoffs = False
                team.won_championship = False

    def _apply_offseason_development(self, season: int):
        """
        Apply one year of development to all players in the league.

        This ages players, applies growth/decline curves, and tracks
        development history for each player.

        Args:
            season: The season just completed
        """
        from huddle.core.ai.development_curves import apply_offseason_development

        self._log(f"  Applying development for {season}...")

        players_developed = 0
        players_improved = 0
        players_declined = 0

        for team in self.teams.values():
            for player in team.roster:
                player_id = str(player.id)

                # Initialize development history if needed
                if player_id not in self.development_histories:
                    self.development_histories[player_id] = PlayerDevelopmentHistory(
                        player_id=player_id,
                        player_name=player.full_name,
                        position=player.position.value,
                    )

                # Apply development and get history entry
                entry = apply_offseason_development(player, season)
                self.development_histories[player_id].add_entry(entry)

                players_developed += 1
                if entry["change"] > 0:
                    players_improved += 1
                elif entry["change"] < 0:
                    players_declined += 1

        self._log(f"    {players_developed} players developed: {players_improved} improved, {players_declined} declined")

    def _handle_contract_expirations(self, season: int):
        """
        Handle end-of-season contract management.

        1. Advance all contracts to next year
        2. Handle expired contracts (re-sign or release)
        3. Ensure all rostered players have contracts
        4. Get team under salary cap if needed
        """
        from huddle.core.ai.cap_manager import CapManager

        for team in self.teams.values():
            # First, advance contracts and track expirations
            expired_player_ids = []
            for player_id, contract in list(team.contracts.items()):
                if not contract.advance_year():
                    expired_player_ids.append(player_id)

            # Create cap manager for this team
            cap_mgr = CapManager(
                team_id=team.team_id,
                roster=team.roster,
                contracts=team.contracts,
                salary_cap=team.salary_cap,
                team_status=team.status,
            )

            # Handle expired contracts - decide to re-sign or release
            for player_id in expired_player_ids:
                player = next((p for p in team.roster if str(p.id) == player_id), None)

                if player and cap_mgr._should_resign_player(player, team.contracts.get(player_id)):
                    # Re-sign with new contract
                    offer = cap_mgr.determine_offer(player)
                    if offer and offer["total_value"] + team.cap_used <= team.salary_cap:
                        new_contract = create_veteran_contract(
                            player_id=player_id,
                            team_id=team.team_id,
                            total_years=offer["years"],
                            total_value=offer["total_value"],
                            guaranteed=offer["guaranteed"],
                            signing_bonus=offer["signing_bonus"],
                            signed_date=self.current_calendar.current_date,
                        )
                        team.contracts[player_id] = new_contract
                    else:
                        # Can't afford - release
                        del team.contracts[player_id]
                        team.roster = [p for p in team.roster if str(p.id) != player_id]
                else:
                    # Release player
                    if player_id in team.contracts:
                        del team.contracts[player_id]
                    team.roster = [p for p in team.roster if str(p.id) != player_id]

            # Ensure all remaining roster players have contracts
            new_contracts = cap_mgr.ensure_all_players_have_contracts(
                self.current_calendar.current_date
            )
            for contract in new_contracts:
                team.contracts[contract.player_id] = contract

            # Get under cap if needed
            if cap_mgr.situation.is_over_cap:
                cuts = cap_mgr.get_under_cap(target_cushion=5_000)
                for player, dead_money in cuts:
                    # Log the cut
                    self.transaction_log.add(create_cut_transaction(
                        team_id=team.team_id,
                        team_name=team.team_name,
                        player_id=str(player.id),
                        player_name=player.full_name,
                        player_position=player.position.value,
                        cap_savings=team.contracts[str(player.id)].cap_savings_if_cut(),
                        dead_money=dead_money,
                        season=season,
                        transaction_date=self.current_calendar.current_date,
                    ))
                    # Remove player
                    team.roster = [p for p in team.roster if p.id != player.id]
                    if str(player.id) in team.contracts:
                        del team.contracts[str(player.id)]

            # Recalculate cap usage
            team.cap_used = sum(c.cap_hit() for c in team.contracts.values())

            # Fill roster to 53 if below (active roster requirement)
            target_roster = 53
            if len(team.roster) < target_roster:
                from huddle.core.contracts.market_value import calculate_market_value
                from huddle.core.ai import calculate_team_needs

                needed = target_roster - len(team.roster)
                needs = calculate_team_needs(team.roster)
                need_positions = sorted(
                    [(pos, needs.get_need(pos)) for pos in
                     ["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
                      "DE", "DT", "OLB", "ILB", "MLB", "CB", "FS", "SS"]],
                    key=lambda x: x[1],
                    reverse=True
                )

                # Sign replacement players at needed positions
                # Use market-rate contracts to spend cap (not just minimum)
                for i in range(needed):
                    pos_str = need_positions[i % len(need_positions)][0]
                    pos = Position(pos_str)

                    # Generate replacement player (varied quality)
                    new_player = self.generate_players(
                        position=pos,
                        age=random.randint(25, 31),
                    )

                    # Calculate market value and create appropriate contract
                    market = calculate_market_value(new_player)

                    # Check actual remaining cap space
                    current_cap_used = sum(c.cap_hit() for c in team.contracts.values())
                    remaining_cap = team.salary_cap - current_cap_used

                    # Try market rate contract first
                    market_contract = create_veteran_contract(
                        player_id=str(new_player.id),
                        team_id=team.team_id,
                        total_years=market.years,
                        total_value=market.total_value,
                        guaranteed=int(market.total_value * 0.3),
                        signing_bonus=market.signing_bonus,
                        signed_date=self.current_calendar.current_date,
                    )

                    min_contract = create_minimum_contract(
                        player_id=str(new_player.id),
                        team_id=team.team_id,
                        years=1,
                        player_experience=new_player.experience_years,
                        signed_date=self.current_calendar.current_date,
                    )

                    # Use market rate only if it fits under cap
                    if market_contract.cap_hit() <= remaining_cap:
                        contract = market_contract
                    elif min_contract.cap_hit() <= remaining_cap:
                        # Minimum contract if can't afford market
                        contract = min_contract
                    else:
                        # Can't afford anyone - skip
                        continue

                    team.roster.append(new_player)
                    team.contracts[str(new_player.id)] = contract

                    # Log the signing
                    self.transaction_log.add(create_signing_transaction(
                        team_id=team.team_id,
                        team_name=team.team_name,
                        player_id=str(new_player.id),
                        player_name=new_player.full_name,
                        player_position=pos_str,
                        contract_years=contract.years,
                        contract_value=contract.total_value,
                        contract_guaranteed=contract.total_guaranteed,
                        season=season,
                        transaction_date=self.current_calendar.current_date,
                    ))

                # Recalculate cap again
                team.cap_used = sum(c.cap_hit() for c in team.contracts.values())

            # Final cleanup: remove any orphan contracts (for players not on roster)
            roster_ids = {str(p.id) for p in team.roster}
            orphan_ids = [pid for pid in team.contracts.keys() if pid not in roster_ids]
            for pid in orphan_ids:
                del team.contracts[pid]

            # Final cap recalculation
            team.cap_used = sum(c.cap_hit() for c in team.contracts.values())

    def _capture_season_standings(self, season: int):
        """Capture standings snapshot at end of season."""
        standings = []
        for team in self.teams.values():
            standings.append(SeasonSnapshot(
                team_id=team.team_id,
                team_name=team.team_name,
                wins=team.wins,
                losses=team.losses,
                made_playoffs=team.made_playoffs,
                won_championship=team.won_championship,
                status=team.status.current_status.name if team.status else "UNKNOWN",
            ))
        # Sort by wins
        standings.sort(key=lambda s: (s.wins, -s.losses), reverse=True)
        self.season_standings[season] = standings

    def _log(self, message: str):
        """Log a message if verbose mode is on."""
        if self.config.verbose:
            print(message)
        if self.config.progress_callback:
            self.config.progress_callback(message)


def create_league_with_history(
    num_teams: int = 32,
    years_of_history: int = 4,
    target_season: int = 2024,
    player_generator: Callable = None,
    team_data: list = None,
    verbose: bool = False,
) -> SimulationResult:
    """
    Convenience function to create a league with simulated history.

    Args:
        num_teams: Number of teams in league
        years_of_history: How many years to simulate
        target_season: What season to end at
        player_generator: Function to generate players
        team_data: List of team info dicts
        verbose: Print progress

    Returns:
        SimulationResult with complete league state
    """
    if team_data is None:
        # Default team data
        team_data = [
            {"id": f"team_{i}", "name": f"Team {i}"}
            for i in range(num_teams)
        ]

    if player_generator is None:
        # Would need to import actual generator
        raise ValueError("player_generator function required")

    config = SimulationConfig(
        years_to_simulate=years_of_history,
        target_season=target_season,
        num_teams=num_teams,
        verbose=verbose,
    )

    simulator = HistoricalSimulator(
        config=config,
        player_generator=player_generator,
        team_data=team_data,
    )

    return simulator.run()

"""Team and roster models."""

from dataclasses import dataclass, field
from typing import Dict, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from huddle.core.enums import Position
from huddle.core.models.player import Player
from huddle.core.models.tendencies import TeamTendencies
from huddle.core.models.team_identity import TeamFinancials

if TYPE_CHECKING:
    from huddle.core.playbook import Playbook, PlayerPlayKnowledge
    from huddle.core.game_prep import GamePrepBonus
    from huddle.core.draft.picks import DraftPickInventory
    from huddle.core.models.team_identity import TeamStatusState, TeamIdentity


@dataclass
class DepthChart:
    """
    Manages position depth for a team.

    Maps depth chart slots (e.g., "WR1", "WR2") to player IDs.
    The slot name indicates position and depth (1 = starter).
    """

    slots: dict[str, UUID] = field(default_factory=dict)

    def set(self, slot: str, player_id: UUID) -> None:
        """Set a player at a depth chart slot."""
        self.slots[slot] = player_id

    def get(self, slot: str) -> Optional[UUID]:
        """Get player ID at a slot, or None if empty."""
        return self.slots.get(slot)

    def get_starter(self, position: str) -> Optional[UUID]:
        """Get the starter (depth 1) for a position."""
        return self.slots.get(f"{position}1")

    def get_all_at_position(self, position: str) -> list[UUID]:
        """Get all players at a position, ordered by depth."""
        result = []
        depth = 1
        while True:
            slot = f"{position}{depth}"
            player_id = self.slots.get(slot)
            if player_id is None:
                break
            result.append(player_id)
            depth += 1
        return result

    def get_starters(self, side: str = "offense") -> dict[str, UUID]:
        """
        Get all starters for offense or defense.

        Returns dict mapping slot name to player ID.
        """
        if side == "offense":
            slots = ["QB1", "RB1", "FB1", "WR1", "WR2", "WR3", "TE1", "LT1", "LG1", "C1", "RG1", "RT1"]
        elif side == "defense":
            slots = ["DE1", "DE2", "DT1", "DT2", "MLB1", "OLB1", "OLB2", "CB1", "CB2", "FS1", "SS1"]
        else:
            slots = ["K1", "P1", "LS1"]

        return {slot: pid for slot in slots if (pid := self.slots.get(slot)) is not None}

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for serialization."""
        return {slot: str(pid) for slot, pid in self.slots.items()}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "DepthChart":
        """Create from dictionary."""
        chart = cls()
        for slot, pid_str in data.items():
            chart.slots[slot] = UUID(pid_str)
        return chart


@dataclass
class Roster:
    """
    Full team roster with depth chart.

    Contains all players on the team and manages the depth chart.
    Handles jersey number assignment with tenure-based conflict resolution.
    """

    players: dict[UUID, Player] = field(default_factory=dict)
    depth_chart: DepthChart = field(default_factory=DepthChart)
    team_id: Optional[UUID] = None  # Set by Team to track which team owns this roster

    def add_player(self, player: Player, assign_jersey: bool = True) -> None:
        """
        Add a player to the roster.

        Args:
            player: Player to add
            assign_jersey: If True, automatically assign a jersey number
        """
        self.players[player.id] = player
        # Set team_id on player so they know which team they belong to
        if self.team_id:
            player.team_id = self.team_id

        if assign_jersey and player.jersey_number == 0:
            taken = self.get_taken_jersey_numbers()
            player.jersey_number = player.get_preferred_number(taken)

    def add_player_with_jersey_resolution(self, player: Player) -> tuple[bool, Optional[Player]]:
        """
        Add a player with jersey number conflict resolution.

        If the player wants a number that's taken, compares tenure.
        The player with more tenure keeps the number.

        Args:
            player: Player to add

        Returns:
            Tuple of (number_changed, displaced_player)
            - number_changed: True if incoming player had to change their number
            - displaced_player: Player who lost their number (if any)
        """
        self.players[player.id] = player
        # Set team_id on player so they know which team they belong to
        if self.team_id:
            player.team_id = self.team_id

        # If player has no preferences, just assign available number
        if not player.preferred_jersey_numbers:
            taken = self.get_taken_jersey_numbers()
            player.jersey_number = player.get_preferred_number(taken)
            return (False, None)

        # Try to get preferred number
        for preferred_num in player.preferred_jersey_numbers:
            current_holder = self.get_player_by_jersey(preferred_num)

            if current_holder is None:
                # Number is available!
                player.jersey_number = preferred_num
                return (False, None)

            # Number is taken - compare tenure
            if player.years_on_team > current_holder.years_on_team:
                # New player has more tenure (trade/signing of veteran)
                # Displace the current holder
                # First, give new player the number they want
                player.jersey_number = preferred_num
                # Then, give displaced player a new number (excluding the one we just assigned)
                taken = self.get_taken_jersey_numbers()  # Now includes new player's number
                current_holder.jersey_number = current_holder.get_preferred_number(taken)
                return (False, current_holder)

        # Couldn't get any preferred number, use fallback
        taken = self.get_taken_jersey_numbers()
        player.jersey_number = player.get_preferred_number(taken)
        return (True, None)

    def get_taken_jersey_numbers(self) -> set[int]:
        """Get all jersey numbers currently assigned on the roster."""
        return {p.jersey_number for p in self.players.values() if p.jersey_number > 0}

    def get_player_by_jersey(self, number: int) -> Optional[Player]:
        """Get the player wearing a specific jersey number."""
        for player in self.players.values():
            if player.jersey_number == number:
                return player
        return None

    def remove_player(self, player_id: UUID) -> Optional[Player]:
        """Remove a player from the roster."""
        player = self.players.pop(player_id, None)
        # Clear team_id when player is removed
        if player:
            player.team_id = None
        return player

    def get_player(self, player_id: UUID) -> Optional[Player]:
        """Get a player by ID."""
        return self.players.get(player_id)

    def get_starter(self, slot: str) -> Optional[Player]:
        """Get the starting player at a depth chart slot."""
        player_id = self.depth_chart.get(slot)
        if player_id:
            return self.players.get(player_id)
        return None

    def get_players_by_position(self, position: Position) -> list[Player]:
        """Get all players at a specific position."""
        return [p for p in self.players.values() if p.position == position]

    def get_offensive_starters(self) -> dict[str, Player]:
        """Get all offensive starters."""
        result = {}
        for slot, player_id in self.depth_chart.get_starters("offense").items():
            if player := self.players.get(player_id):
                result[slot] = player
        return result

    def get_defensive_starters(self) -> dict[str, Player]:
        """Get all defensive starters."""
        result = {}
        for slot, player_id in self.depth_chart.get_starters("defense").items():
            if player := self.players.get(player_id):
                result[slot] = player
        return result

    @property
    def size(self) -> int:
        """Number of players on roster."""
        return len(self.players)

    def calculate_total_salary(self) -> int:
        """
        Calculate total salary commitment from all players on roster.

        Returns salary in thousands (e.g., 150000 = $150M).
        """
        total = 0
        for player in self.players.values():
            if player.salary:
                total += player.salary
        return total

    def auto_fill_depth_chart(self) -> None:
        """
        Automatically populate the depth chart from roster players.

        Places players at their position slots sorted by overall rating.
        Best player at each position becomes the starter (depth 1).
        """
        # Group players by position
        by_position: dict[str, list[Player]] = {}
        for player in self.players.values():
            pos = player.position.value
            if pos not in by_position:
                by_position[pos] = []
            by_position[pos].append(player)

        # Sort each position by overall (best first)
        for pos in by_position:
            by_position[pos].sort(key=lambda p: p.overall, reverse=True)

        # Clear existing depth chart
        self.depth_chart.slots.clear()

        # Fill depth chart slots
        for pos, players in by_position.items():
            for depth, player in enumerate(players, start=1):
                slot = f"{pos}{depth}"
                self.depth_chart.set(slot, player.id)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = {
            "players": [p.to_dict() for p in self.players.values()],
            "depth_chart": self.depth_chart.to_dict(),
        }
        if self.team_id:
            data["team_id"] = str(self.team_id)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Roster":
        """Create from dictionary."""
        team_id = UUID(data["team_id"]) if data.get("team_id") else None
        roster = cls(team_id=team_id)
        for player_data in data.get("players", []):
            player = Player.from_dict(player_data)
            # Use assign_jersey=False since loaded players already have numbers
            roster.add_player(player, assign_jersey=False)
        if "depth_chart" in data:
            roster.depth_chart = DepthChart.from_dict(data["depth_chart"])
        return roster


@dataclass
class Team:
    """
    Represents a football team.

    Contains roster, identity info, AI tendencies, and salary cap state.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    abbreviation: str = ""
    city: str = ""
    roster: Roster = field(default_factory=Roster)

    # Team colors (for future UI)
    primary_color: str = "#000000"
    secondary_color: str = "#FFFFFF"

    # AI tendencies for all team decisions
    tendencies: TeamTendencies = field(default_factory=TeamTendencies)

    # Salary cap and financial state
    financials: TeamFinancials = field(default_factory=TeamFinancials)

    # Draft picks inventory (all picks owned, past trades, etc.)
    draft_picks: Optional["DraftPickInventory"] = None

    # Team status state (contending, rebuilding, etc.)
    status: Optional["TeamStatusState"] = None

    # Team identity (offensive/defensive scheme, philosophy)
    identity: Optional["TeamIdentity"] = None

    # GM archetype (affects draft/trade behavior)
    gm_archetype: Optional[str] = None  # e.g., "analytics_architect", "old_school"

    # Playbook system (play knowledge tracking)
    playbook: Optional["Playbook"] = None
    player_knowledge: Dict[UUID, "PlayerPlayKnowledge"] = field(default_factory=dict)

    # Game prep bonus (temporary, expires after game)
    game_prep_bonus: Optional["GamePrepBonus"] = None

    def __post_init__(self):
        """Ensure roster knows its team_id."""
        if self.roster:
            self.roster.team_id = self.id

    # Convenience properties for backward compatibility
    @property
    def run_tendency(self) -> float:
        return self.tendencies.run_tendency

    @property
    def aggression(self) -> float:
        return self.tendencies.aggression

    @property
    def blitz_tendency(self) -> float:
        return self.tendencies.blitz_tendency

    @property
    def full_name(self) -> str:
        """Full team name (e.g., 'New England Patriots')."""
        return f"{self.city} {self.name}"

    def get_starter(self, slot: str) -> Optional[Player]:
        """Get starting player at a depth chart slot."""
        return self.roster.get_starter(slot)

    def get_qb(self) -> Optional[Player]:
        """Get starting quarterback."""
        return self.roster.get_starter("QB1")

    def get_rb(self) -> Optional[Player]:
        """Get starting running back."""
        return self.roster.get_starter("RB1")

    def calculate_offense_rating(self) -> int:
        """Calculate overall offensive rating."""
        starters = self.roster.get_offensive_starters()
        if not starters:
            return 50
        return int(sum(p.overall for p in starters.values()) / len(starters))

    def calculate_defense_rating(self) -> int:
        """Calculate overall defensive rating."""
        starters = self.roster.get_defensive_starters()
        if not starters:
            return 50
        return int(sum(p.overall for p in starters.values()) / len(starters))

    def recalculate_financials(self) -> None:
        """
        Recalculate financial state from current roster.

        Call this after loading a team or making roster changes
        to ensure financials are in sync with actual player contracts.
        """
        self.financials.total_salary = self.roster.calculate_total_salary()

    @property
    def cap_room(self) -> int:
        """Available salary cap space."""
        return self.financials.cap_room

    @property
    def cap_used_pct(self) -> float:
        """Percentage of salary cap used."""
        return self.financials.cap_used_pct

    def can_afford(self, salary: int) -> bool:
        """Check if team can afford a contract with given salary."""
        return self.financials.can_sign(salary)

    @property
    def is_contending(self) -> bool:
        """Check if team is in a contending window."""
        if self.status:
            from huddle.core.models.team_identity import TeamStatus
            return self.status.current_status in {
                TeamStatus.DYNASTY,
                TeamStatus.CONTENDING,
                TeamStatus.WINDOW_CLOSING,
            }
        return False

    @property
    def is_rebuilding(self) -> bool:
        """Check if team is in a rebuild."""
        if self.status:
            from huddle.core.models.team_identity import TeamStatus
            return self.status.current_status == TeamStatus.REBUILDING
        return False

    def get_owned_picks(self, year: int) -> list:
        """Get all draft picks owned for a specific year."""
        if self.draft_picks:
            return [p for p in self.draft_picks.picks if p.year == year and p.current_team_id == str(self.id)]
        return []

    def get_traded_picks(self) -> list:
        """Get all picks traded away."""
        if self.draft_picks:
            return [p for p in self.draft_picks.picks if p.original_team_id == str(self.id) and p.current_team_id != str(self.id)]
        return []

    def get_player_knowledge(self, player_id: UUID) -> "PlayerPlayKnowledge":
        """
        Get or create play knowledge for a player.

        Args:
            player_id: The player's unique identifier

        Returns:
            PlayerPlayKnowledge for tracking play mastery
        """
        from huddle.core.playbook import PlayerPlayKnowledge

        if player_id not in self.player_knowledge:
            self.player_knowledge[player_id] = PlayerPlayKnowledge(player_id=player_id)
        return self.player_knowledge[player_id]

    def initialize_playbook(self) -> None:
        """
        Initialize the team's playbook with default plays.

        Call this when creating a new team or resetting their playbook.
        """
        from huddle.core.playbook import Playbook

        if self.playbook is None:
            self.playbook = Playbook.default(self.id)

    def clear_expired_prep(self, current_week: int) -> None:
        """
        Clear game prep bonus if the game has passed.

        Should be called after each game to clean up expired prep.

        Args:
            current_week: Current game week
        """
        if self.game_prep_bonus and self.game_prep_bonus.is_expired(current_week):
            self.game_prep_bonus = None

    def get_game_prep_bonus(self, opponent_id: UUID) -> float:
        """
        Get the game prep bonus multiplier for a specific opponent.

        Args:
            opponent_id: UUID of the opponent team

        Returns:
            Bonus multiplier (1.0 = no bonus)
        """
        if self.game_prep_bonus and self.game_prep_bonus.is_valid_for_opponent(opponent_id):
            return self.game_prep_bonus.get_total_bonus()
        return 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        data = {
            "id": str(self.id),
            "name": self.name,
            "abbreviation": self.abbreviation,
            "city": self.city,
            "roster": self.roster.to_dict(),
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "tendencies": self.tendencies.to_dict(),
            "financials": {
                "salary_cap": self.financials.salary_cap,
                "total_salary": self.financials.total_salary,
                "dead_money": self.financials.dead_money,
                "dead_money_next_year": self.financials.dead_money_next_year,
                "cap_penalties": self.financials.cap_penalties,
            },
        }

        # Include playbook if present
        if self.playbook:
            data["playbook"] = self.playbook.to_dict()

        # Include player knowledge if any
        if self.player_knowledge:
            data["player_knowledge"] = {
                str(pid): pk.to_dict()
                for pid, pk in self.player_knowledge.items()
            }

        # Include game prep bonus if present
        if self.game_prep_bonus:
            data["game_prep_bonus"] = self.game_prep_bonus.to_dict()

        # Include draft picks inventory if present
        if self.draft_picks:
            data["draft_picks"] = self.draft_picks.to_dict()

        # Include team status state if present
        if self.status:
            data["status"] = self.status.to_dict()

        # Include team identity if present
        if self.identity:
            data["identity"] = self.identity.to_dict()

        # Include GM archetype if present
        if self.gm_archetype:
            data["gm_archetype"] = self.gm_archetype

        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Team":
        """Create from dictionary."""
        # Handle legacy data format with individual tendency fields
        if "tendencies" in data:
            tendencies = TeamTendencies.from_dict(data["tendencies"])
        else:
            # Legacy format - create tendencies from old fields
            tendencies = TeamTendencies(
                run_tendency=data.get("run_tendency", 0.5),
                aggression=data.get("aggression", 0.5),
                blitz_tendency=data.get("blitz_tendency", 0.3),
            )

        # Load financials if present, otherwise create default
        if "financials" in data:
            fin_data = data["financials"]
            financials = TeamFinancials(
                salary_cap=fin_data.get("salary_cap", 255_000),
                total_salary=fin_data.get("total_salary", 0),
                dead_money=fin_data.get("dead_money", 0),
                dead_money_next_year=fin_data.get("dead_money_next_year", 0),
                cap_penalties=fin_data.get("cap_penalties", 0),
            )
        else:
            financials = TeamFinancials()

        # Load playbook if present
        playbook = None
        if "playbook" in data:
            from huddle.core.playbook import Playbook
            playbook = Playbook.from_dict(data["playbook"])

        # Load player knowledge if present
        player_knowledge: Dict[UUID, "PlayerPlayKnowledge"] = {}
        if "player_knowledge" in data:
            from huddle.core.playbook import PlayerPlayKnowledge
            for pid_str, pk_data in data["player_knowledge"].items():
                player_knowledge[UUID(pid_str)] = PlayerPlayKnowledge.from_dict(pk_data)

        # Load game prep bonus if present
        game_prep_bonus = None
        if "game_prep_bonus" in data:
            from huddle.core.game_prep import GamePrepBonus
            game_prep_bonus = GamePrepBonus.from_dict(data["game_prep_bonus"])

        # Load draft picks inventory if present
        draft_picks = None
        if "draft_picks" in data:
            from huddle.core.draft.picks import DraftPickInventory
            draft_picks = DraftPickInventory.from_dict(data["draft_picks"])

        # Load team status state if present
        status = None
        if "status" in data:
            from huddle.core.models.team_identity import TeamStatusState
            status = TeamStatusState.from_dict(data["status"])

        # Load team identity if present
        identity = None
        if "identity" in data:
            from huddle.core.models.team_identity import TeamIdentity
            identity = TeamIdentity.from_dict(data["identity"])

        # Load GM archetype if present
        gm_archetype = data.get("gm_archetype")

        team = cls(
            id=UUID(data["id"]) if "id" in data else uuid4(),
            name=data.get("name", ""),
            abbreviation=data.get("abbreviation", ""),
            city=data.get("city", ""),
            roster=Roster.from_dict(data.get("roster", {})),
            primary_color=data.get("primary_color", "#000000"),
            secondary_color=data.get("secondary_color", "#FFFFFF"),
            tendencies=tendencies,
            financials=financials,
            draft_picks=draft_picks,
            status=status,
            identity=identity,
            gm_archetype=gm_archetype,
            playbook=playbook,
            player_knowledge=player_knowledge,
            game_prep_bonus=game_prep_bonus,
        )

        # If no financials in data, calculate from roster
        if "financials" not in data:
            team.recalculate_financials()

        return team

    def __str__(self) -> str:
        return f"{self.full_name} ({self.abbreviation})"

    def __repr__(self) -> str:
        return f"Team(name='{self.full_name}', abbr='{self.abbreviation}')"

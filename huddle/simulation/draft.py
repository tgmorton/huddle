"""
Draft System.

Implements NFL-style draft with:
- 7 rounds, 32 picks per round (standard draft)
- Snake draft for fantasy mode
- AI draft logic using team tendencies
- Trade pick functionality
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from uuid import UUID, uuid4
import random

from huddle.core.models.player import Player
from huddle.core.models.team import Team
from huddle.core.models.tendencies import DraftStrategy, TeamTendencies
from huddle.core.enums import Position


class DraftType(Enum):
    """Type of draft."""
    NFL = "nfl"  # Standard NFL draft - worst to best order
    FANTASY = "fantasy"  # Snake draft - all players available
    SUPPLEMENTAL = "supplemental"  # Extra draft for special cases


class DraftPhase(Enum):
    """Current phase of the draft."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"


@dataclass
class DraftPick:
    """
    Represents a single draft pick.

    Can be traded between teams. Tracks original owner.
    """
    id: UUID = field(default_factory=uuid4)
    round: int = 1
    pick_number: int = 1  # Overall pick number (1-224 for 7-round NFL draft)
    round_pick: int = 1  # Pick within the round (1-32)
    original_team_abbr: str = ""  # Team that originally owned the pick
    current_team_abbr: str = ""  # Team that currently owns the pick
    player_id: Optional[UUID] = None  # Player selected with this pick
    player_name: Optional[str] = None
    player_position: Optional[str] = None

    @property
    def is_selected(self) -> bool:
        """Check if a player has been selected with this pick."""
        return self.player_id is not None

    @property
    def was_traded(self) -> bool:
        """Check if this pick was traded."""
        return self.original_team_abbr != self.current_team_abbr

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "round": self.round,
            "pick_number": self.pick_number,
            "round_pick": self.round_pick,
            "original_team_abbr": self.original_team_abbr,
            "current_team_abbr": self.current_team_abbr,
            "player_id": str(self.player_id) if self.player_id else None,
            "player_name": self.player_name,
            "player_position": self.player_position,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DraftPick":
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            round=data.get("round", 1),
            pick_number=data.get("pick_number", 1),
            round_pick=data.get("round_pick", 1),
            original_team_abbr=data.get("original_team_abbr", ""),
            current_team_abbr=data.get("current_team_abbr", ""),
            player_id=UUID(data["player_id"]) if data.get("player_id") else None,
            player_name=data.get("player_name"),
            player_position=data.get("player_position"),
        )


# Minimum roster requirements for a functional team
# Format: position -> minimum count required before drafting extras elsewhere
POSITION_MINIMUMS = {
    "QB": 2,    # Need starter + backup
    "RB": 2,    # Need starter + backup
    "WR": 4,    # Need 3 starters + depth
    "TE": 2,    # Need starter + backup
    "LT": 2, "LG": 2, "C": 2, "RG": 2, "RT": 2,  # OL depth
    "DE": 3,    # Two starters + rotation
    "DT": 3,    # Two starters + rotation
    "MLB": 2,   # Need starter + backup
    "OLB": 3,   # Two starters + rotation
    "CB": 4,    # Two starters + nickel + depth
    "FS": 2, "SS": 2,  # Safeties need depth
    "K": 1, "P": 1,    # Specialists
}


@dataclass
class TeamNeeds:
    """
    Tracks a team's positional needs for draft evaluation.

    Higher score = greater need at that position.
    """
    needs: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)  # Actual player counts

    def get_need(self, position: str) -> float:
        """Get need score for a position (0-1 scale)."""
        return self.needs.get(position, 0.5)

    def get_count(self, position: str) -> int:
        """Get current player count at a position."""
        return self.counts.get(position, 0)

    def set_need(self, position: str, score: float) -> None:
        """Set need score for a position."""
        self.needs[position] = max(0.0, min(1.0, score))

    def set_count(self, position: str, count: int) -> None:
        """Set player count at a position."""
        self.counts[position] = count

    def reduce_need(self, position: str, amount: float = 0.3) -> None:
        """Reduce need at a position (after drafting there)."""
        current = self.get_need(position)
        self.set_need(position, current - amount)
        # Also increment count
        self.counts[position] = self.counts.get(position, 0) + 1

    def is_below_minimum(self, position: str) -> bool:
        """Check if position is below minimum required count."""
        minimum = POSITION_MINIMUMS.get(position, 1)
        return self.get_count(position) < minimum

    def get_unfilled_positions(self) -> list[str]:
        """Get list of positions that haven't met their minimums."""
        unfilled = []
        for pos, minimum in POSITION_MINIMUMS.items():
            if self.get_count(pos) < minimum:
                unfilled.append(pos)
        return unfilled

    @classmethod
    def calculate_from_roster(cls, team: Team) -> "TeamNeeds":
        """
        Calculate team needs based on current roster.

        Positions with weak starters or no depth have higher need.
        Also tracks actual player counts for minimum requirements.
        """
        needs = cls()

        # Define ideal roster composition (starter count, ideal overall)
        position_targets = {
            "QB": (1, 85),  # Need 1 good QB (85+ ideal)
            "RB": (2, 78),  # Need 2 decent RBs
            "WR": (3, 80),  # Need 3 good WRs
            "TE": (1, 75),  # Need 1 decent TE
            "LT": (1, 80), "LG": (1, 75), "C": (1, 75), "RG": (1, 75), "RT": (1, 78),
            "DE": (2, 78),
            "DT": (2, 75),
            "MLB": (1, 78), "OLB": (2, 76), "ILB": (1, 75),
            "CB": (2, 80),
            "FS": (1, 76), "SS": (1, 76),
            "K": (1, 75), "P": (1, 75),
        }

        for position_str, (count_needed, ideal_overall) in position_targets.items():
            try:
                position = Position[position_str]
            except KeyError:
                continue

            players_at_pos = team.roster.get_players_by_position(position)
            players_at_pos.sort(key=lambda p: p.overall, reverse=True)

            # Track actual count
            needs.set_count(position_str, len(players_at_pos))

            # Calculate need based on quantity and quality
            if len(players_at_pos) < count_needed:
                # Missing players - high need
                need_score = 0.8 + (0.2 * (count_needed - len(players_at_pos)) / count_needed)
            elif not players_at_pos:
                need_score = 1.0
            else:
                # Have players - evaluate quality
                best_player = players_at_pos[0]
                quality_gap = (ideal_overall - best_player.overall) / 20  # Normalize
                need_score = max(0.2, min(0.8, 0.3 + quality_gap))

                # Factor in age for long-term needs
                if best_player.age >= 30:
                    need_score = min(1.0, need_score + 0.2)

            needs.set_need(position_str, need_score)

        return needs


@dataclass
class Draft:
    """
    Manages an NFL draft session.

    Handles pick order, player selection, and AI auto-picks.
    """
    id: UUID = field(default_factory=uuid4)
    draft_type: DraftType = DraftType.NFL
    phase: DraftPhase = DraftPhase.NOT_STARTED
    season: int = 2024

    # Configuration
    num_rounds: int = 7
    num_teams: int = 32

    # Draft state
    current_pick_index: int = 0  # Index into picks list
    picks: list[DraftPick] = field(default_factory=list)

    # Available players
    available_players: list[Player] = field(default_factory=list)

    # Team order (abbreviations) - first team picks first in round 1
    team_order: list[str] = field(default_factory=list)

    # User-controlled team (None = all AI)
    user_team_abbr: Optional[str] = None

    @property
    def current_pick(self) -> Optional[DraftPick]:
        """Get the current pick."""
        if 0 <= self.current_pick_index < len(self.picks):
            return self.picks[self.current_pick_index]
        return None

    @property
    def current_round(self) -> int:
        """Get the current round number."""
        pick = self.current_pick
        return pick.round if pick else 0

    @property
    def is_user_pick(self) -> bool:
        """Check if current pick belongs to user."""
        pick = self.current_pick
        return pick is not None and pick.current_team_abbr == self.user_team_abbr

    @property
    def picks_made(self) -> int:
        """Number of picks that have been made."""
        return sum(1 for p in self.picks if p.is_selected)

    @property
    def picks_remaining(self) -> int:
        """Number of picks remaining."""
        return len(self.picks) - self.picks_made

    def setup_draft_order(
        self,
        team_abbrs: list[str],
        standings_order: Optional[list[str]] = None,
    ) -> None:
        """
        Set up the draft order and create all picks.

        For NFL draft: worst team picks first
        For fantasy draft: random order with snake

        Args:
            team_abbrs: List of all team abbreviations
            standings_order: Optional ordered list (worst to best) for NFL draft
        """
        self.num_teams = len(team_abbrs)

        if self.draft_type == DraftType.FANTASY:
            # Random order for fantasy draft
            self.team_order = list(team_abbrs)
            random.shuffle(self.team_order)
        else:
            # Use standings order if provided, otherwise use as-is
            if standings_order:
                self.team_order = standings_order
            else:
                self.team_order = list(team_abbrs)

        # Create all picks
        self.picks = []
        pick_number = 1

        for round_num in range(1, self.num_rounds + 1):
            round_order = self.team_order.copy()

            # Snake draft for fantasy - reverse every other round
            if self.draft_type == DraftType.FANTASY and round_num % 2 == 0:
                round_order.reverse()

            for round_pick, team_abbr in enumerate(round_order, 1):
                pick = DraftPick(
                    round=round_num,
                    pick_number=pick_number,
                    round_pick=round_pick,
                    original_team_abbr=team_abbr,
                    current_team_abbr=team_abbr,
                )
                self.picks.append(pick)
                pick_number += 1

    def set_available_players(self, players: list[Player]) -> None:
        """Set the pool of available players."""
        self.available_players = list(players)
        # Sort by overall rating descending
        self.available_players.sort(key=lambda p: p.overall, reverse=True)

    def start_draft(self) -> None:
        """Start the draft."""
        if self.phase == DraftPhase.NOT_STARTED:
            self.phase = DraftPhase.IN_PROGRESS
            self.current_pick_index = 0

    def make_pick(self, player_id: UUID) -> Optional[DraftPick]:
        """
        Make a pick with the specified player.

        Args:
            player_id: ID of the player to draft

        Returns:
            The completed DraftPick, or None if invalid
        """
        if self.phase != DraftPhase.IN_PROGRESS:
            return None

        pick = self.current_pick
        if pick is None or pick.is_selected:
            return None

        # Find the player
        player = None
        player_index = -1
        for i, p in enumerate(self.available_players):
            if p.id == player_id:
                player = p
                player_index = i
                break

        if player is None:
            return None

        # Make the pick
        pick.player_id = player.id
        pick.player_name = player.full_name
        pick.player_position = player.position.value

        # Remove from available players
        self.available_players.pop(player_index)

        # Advance to next pick
        self.current_pick_index += 1

        # Check if draft is complete
        if self.current_pick_index >= len(self.picks):
            self.phase = DraftPhase.COMPLETED

        return pick

    def get_best_available(
        self,
        position: Optional[str] = None,
        limit: int = 10,
    ) -> list[Player]:
        """
        Get the best available players.

        Args:
            position: Optional position filter
            limit: Max players to return

        Returns:
            List of best available players
        """
        if position:
            try:
                pos = Position[position]
                filtered = [p for p in self.available_players if p.position == pos]
            except KeyError:
                filtered = self.available_players
        else:
            filtered = self.available_players

        return filtered[:limit]

    def ai_make_pick(
        self,
        team: Team,
        team_needs: Optional[TeamNeeds] = None,
    ) -> Optional[DraftPick]:
        """
        Make an AI pick based on team tendencies.

        In fantasy drafts, enforces position minimums - teams must fill
        required positions before drafting extras at other positions.

        Args:
            team: The team making the pick
            team_needs: Optional pre-calculated needs

        Returns:
            The completed DraftPick
        """
        if not self.available_players:
            return None

        pick = self.current_pick
        if pick is None or pick.current_team_abbr != team.abbreviation:
            return None

        # Calculate needs if not provided
        if team_needs is None:
            team_needs = TeamNeeds.calculate_from_roster(team)

        tendencies = team.tendencies

        # Get positions that still need filling (below minimums)
        unfilled_positions = team_needs.get_unfilled_positions()

        # Build candidate pool based on draft type and team needs
        candidates: dict[UUID, Player] = {}

        # Group available players by position
        by_position: dict[str, list[Player]] = {}
        for player in self.available_players:
            pos = player.position.value
            if pos not in by_position:
                by_position[pos] = []
            by_position[pos].append(player)

        # In fantasy drafts, enforce position minimums
        if self.draft_type == DraftType.FANTASY and unfilled_positions:
            # ONLY consider players at positions that need filling
            for pos in unfilled_positions:
                if pos in by_position:
                    # Add best 5 available at each unfilled position
                    for player in by_position[pos][:5]:
                        candidates[player.id] = player
        else:
            # Normal draft logic - consider overall BPA + positional best
            # Add overall top 30
            for player in self.available_players[:30]:
                candidates[player.id] = player

            # Add best 3 available at each position
            for pos, players in by_position.items():
                for player in players[:3]:
                    candidates[player.id] = player

        # If no candidates found (unlikely), fall back to BPA
        if not candidates:
            for player in self.available_players[:10]:
                candidates[player.id] = player

        # Evaluate each candidate
        player_scores: list[tuple[Player, float]] = []

        for player in candidates.values():
            pos = player.position.value

            score = tendencies.evaluate_player_fit(
                player_overall=player.overall,
                player_position=pos,
                team_need_score=team_needs.get_need(pos),
            )

            # In fantasy drafts, give bonus to positions further below minimum
            if self.draft_type == DraftType.FANTASY and pos in unfilled_positions:
                minimum = POSITION_MINIMUMS.get(pos, 1)
                current = team_needs.get_count(pos)
                shortage = minimum - current
                # More shortage = higher priority (e.g., 0/4 WRs > 1/2 QBs)
                shortage_bonus = shortage * 3.0
                score += shortage_bonus

            # Consider potential for early picks
            if pick.round <= 2 and player.potential > player.overall:
                upside_bonus = (player.potential - player.overall) * 0.3
                score += upside_bonus

            player_scores.append((player, score))

        # Sort by score and pick the best
        player_scores.sort(key=lambda x: x[1], reverse=True)

        if player_scores:
            selected_player = player_scores[0][0]

            # Add some randomness to not always pick #1
            if len(player_scores) >= 3 and random.random() < 0.15:
                # 15% chance to pick from top 3 instead of always #1
                selected_player = random.choice([ps[0] for ps in player_scores[:3]])

            return self.make_pick(selected_player.id)

        return None

    def simulate_to_user_pick(
        self,
        teams: dict[str, Team],
    ) -> list[DraftPick]:
        """
        Simulate AI picks until it's the user's turn.

        Args:
            teams: Dict of team abbreviation to Team

        Returns:
            List of picks made
        """
        picks_made = []

        while self.phase == DraftPhase.IN_PROGRESS:
            if self.is_user_pick:
                break

            pick = self.current_pick
            if pick is None:
                break

            team = teams.get(pick.current_team_abbr)
            if team is None:
                break

            result = self.ai_make_pick(team)
            if result:
                picks_made.append(result)
            else:
                break

        return picks_made

    def simulate_full_draft(
        self,
        teams: dict[str, Team],
        add_to_rosters: bool = True,
    ) -> list[DraftPick]:
        """
        Simulate the entire draft with AI.

        Args:
            teams: Dict of team abbreviation to Team
            add_to_rosters: If True, add drafted players to team rosters during
                           simulation (important for fantasy drafts so needs update)

        Returns:
            List of all picks made
        """
        # Start the draft if not already started
        if self.phase == DraftPhase.NOT_STARTED:
            self.start_draft()

        picks_made = []

        # Cache team needs - will be updated after each pick if adding to rosters
        team_needs_cache: dict[str, TeamNeeds] = {}
        for abbr, team in teams.items():
            team_needs_cache[abbr] = TeamNeeds.calculate_from_roster(team)

        # Temporarily remove user team to let AI pick everything
        saved_user = self.user_team_abbr
        self.user_team_abbr = None

        # Build a lookup of available players by ID for roster additions
        available_by_id = {p.id: p for p in self.available_players}

        while self.phase == DraftPhase.IN_PROGRESS:
            pick = self.current_pick
            if pick is None:
                break

            team = teams.get(pick.current_team_abbr)
            if team is None:
                self.current_pick_index += 1
                continue

            # Use cached needs for this team
            result = self.ai_make_pick(team, team_needs_cache.get(pick.current_team_abbr))
            if result:
                picks_made.append(result)

                # Add player to roster and update needs cache
                if add_to_rosters and result.player_id:
                    player = available_by_id.get(result.player_id)
                    if player:
                        team.roster.add_player(player, assign_jersey=True)
                        # Recalculate needs for this team
                        team_needs_cache[pick.current_team_abbr] = TeamNeeds.calculate_from_roster(team)

        self.user_team_abbr = saved_user
        return picks_made

    def get_team_picks(self, team_abbr: str) -> list[DraftPick]:
        """Get all picks for a team."""
        return [p for p in self.picks if p.current_team_abbr == team_abbr]

    def get_team_selections(self, team_abbr: str) -> list[DraftPick]:
        """Get all completed selections for a team."""
        return [p for p in self.picks if p.current_team_abbr == team_abbr and p.is_selected]

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "draft_type": self.draft_type.value,
            "phase": self.phase.value,
            "season": self.season,
            "num_rounds": self.num_rounds,
            "num_teams": self.num_teams,
            "current_pick_index": self.current_pick_index,
            "picks": [p.to_dict() for p in self.picks],
            "available_players": [p.to_dict() for p in self.available_players],
            "team_order": self.team_order,
            "user_team_abbr": self.user_team_abbr,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Draft":
        draft = cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            draft_type=DraftType(data.get("draft_type", "nfl")),
            phase=DraftPhase(data.get("phase", "not_started")),
            season=data.get("season", 2024),
            num_rounds=data.get("num_rounds", 7),
            num_teams=data.get("num_teams", 32),
            current_pick_index=data.get("current_pick_index", 0),
            team_order=data.get("team_order", []),
            user_team_abbr=data.get("user_team_abbr"),
        )
        draft.picks = [DraftPick.from_dict(p) for p in data.get("picks", [])]
        draft.available_players = [
            Player.from_dict(p) for p in data.get("available_players", [])
        ]
        return draft


def create_nfl_draft(
    season: int,
    team_order: list[str],
    draft_class: list[Player],
    num_rounds: int = 7,
    user_team: Optional[str] = None,
) -> Draft:
    """
    Create a standard NFL draft.

    Args:
        season: Draft year
        team_order: Teams in draft order (worst to best)
        draft_class: Available players
        num_rounds: Number of rounds (default 7)
        user_team: Optional user-controlled team

    Returns:
        Configured Draft ready to start
    """
    draft = Draft(
        draft_type=DraftType.NFL,
        season=season,
        num_rounds=num_rounds,
        user_team_abbr=user_team,
    )
    draft.setup_draft_order(team_order)
    draft.set_available_players(draft_class)
    return draft


def create_fantasy_draft(
    team_abbrs: list[str],
    all_players: list[Player],
    num_rounds: int = 53,
    user_team: Optional[str] = None,
) -> Draft:
    """
    Create a fantasy-style snake draft.

    In fantasy draft mode, ALL players are available (not just rookies).
    Default is 53 rounds to fill a complete NFL roster.
    Teams start with empty rosters and build from scratch.

    Args:
        team_abbrs: Participating teams
        all_players: All available players (from all rosters + free agents)
        num_rounds: Number of rounds
        user_team: User-controlled team

    Returns:
        Configured Draft for fantasy mode
    """
    draft = Draft(
        draft_type=DraftType.FANTASY,
        num_rounds=num_rounds,
        user_team_abbr=user_team,
    )
    draft.setup_draft_order(team_abbrs)
    draft.set_available_players(all_players)
    return draft

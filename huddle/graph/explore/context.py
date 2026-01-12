"""
Context generation for AI commentary and narratives.

This module generates "Context Cards" - structured fragments of information
that can be used by the fast generation layer for commentary.

The "slow" agentic layer explores the graph and produces context cards.
The "fast" layer consumes these cards to generate fluent commentary.
"""

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from huddle.graph.connection import get_graph, is_graph_enabled
from huddle.graph.explore.tools import (
    get_player_context,
    get_team_context,
    get_matchup_context,
)

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Types of context cards."""
    PLAYER = "player"
    TEAM = "team"
    MATCHUP = "matchup"
    HISTORY = "history"
    NARRATIVE = "narrative"
    SITUATION = "situation"
    STATISTIC = "statistic"


@dataclass
class ContextCard:
    """
    A structured fragment of context for commentary generation.

    Context cards are the output of the "slow" exploration layer and
    the input to the "fast" generation layer.
    """
    id: str
    type: ContextType
    topic: str  # Short topic label (e.g., "Jalen Hurts", "PHI vs DAL")
    content: str  # The actual context/insight
    relevance: float = 0.5  # 0-1 how relevant to current moment
    ttl_seconds: int = 300  # Time-to-live (some context stales)
    source_entities: list[str] = field(default_factory=list)  # Entity IDs
    tags: list[str] = field(default_factory=list)  # For filtering
    created_at: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """Check if this context card has expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        d["type"] = self.type.value
        return d


@dataclass
class ContextQueue:
    """
    A queue of context cards for the generation layer.

    The exploration layer populates this queue. The generation layer
    consumes relevant cards based on current game state.
    """
    cards: list[ContextCard] = field(default_factory=list)
    max_size: int = 100

    def add(self, card: ContextCard) -> None:
        """Add a context card, removing expired ones."""
        # Remove expired cards
        self.cards = [c for c in self.cards if not c.is_expired()]

        # Add new card
        self.cards.append(card)

        # Trim to max size, keeping highest relevance
        if len(self.cards) > self.max_size:
            self.cards.sort(key=lambda c: c.relevance, reverse=True)
            self.cards = self.cards[:self.max_size]

    def get_relevant(
        self,
        context_type: Optional[ContextType] = None,
        tags: Optional[list[str]] = None,
        min_relevance: float = 0.0,
        limit: int = 5,
    ) -> list[ContextCard]:
        """
        Get relevant context cards for the current moment.

        Args:
            context_type: Filter by type
            tags: Filter by tags (any match)
            min_relevance: Minimum relevance score
            limit: Maximum cards to return

        Returns:
            List of relevant context cards
        """
        # Remove expired
        self.cards = [c for c in self.cards if not c.is_expired()]

        # Filter
        filtered = self.cards
        if context_type:
            filtered = [c for c in filtered if c.type == context_type]
        if tags:
            filtered = [c for c in filtered if any(t in c.tags for t in tags)]
        if min_relevance > 0:
            filtered = [c for c in filtered if c.relevance >= min_relevance]

        # Sort by relevance and return top N
        filtered.sort(key=lambda c: c.relevance, reverse=True)
        return filtered[:limit]

    def clear(self) -> None:
        """Clear all context cards."""
        self.cards = []


class ContextGenerator:
    """
    Generates context cards by exploring the graph.

    This is the "slow" process that runs continuously during games,
    building up context for the "fast" generation layer.
    """

    def __init__(self, queue: Optional[ContextQueue] = None):
        self.queue = queue or ContextQueue()

    def generate_player_context(
        self,
        player_identifier: str,
        relevance: float = 0.5,
    ) -> list[ContextCard]:
        """
        Generate context cards about a player.

        Returns multiple cards covering different aspects:
        - Basic info and career phase
        - Recent performance trend
        - Notable narratives
        - Interesting stats
        """
        cards = []

        result = get_player_context(player_identifier)
        if not result.success:
            return cards

        data = result.data
        player = data.get("player", {}).get("properties", {})
        name = player.get("name", player_identifier)

        # Card 1: Basic player context
        team_name = data.get("team", {}).get("properties", {}).get("name", "Unknown")
        position = player.get("position", "?")
        overall = player.get("overall", "?")
        age = player.get("age", "?")

        cards.append(ContextCard(
            id=f"player_basic_{player.get('id', name)}",
            type=ContextType.PLAYER,
            topic=name,
            content=f"{name} is a {age}-year-old {position} for the {team_name}. Rated {overall} overall.",
            relevance=relevance,
            ttl_seconds=600,
            source_entities=[player.get("id", "")],
            tags=["player", "basic", position],
        ))

        # Card 2: Career phase
        career = data.get("career_phase", {})
        if career:
            phase = career.get("phase", "unknown")
            trajectory = career.get("trajectory", "unknown")

            phase_descriptions = {
                "rookie": "in their rookie season, full of potential",
                "rising": "a rising star, still improving",
                "peak": "at the peak of their career",
                "declining": "past their prime but still productive",
                "twilight": "in the twilight of their career",
            }

            desc = phase_descriptions.get(phase, "at an unknown career stage")

            cards.append(ContextCard(
                id=f"player_career_{player.get('id', name)}",
                type=ContextType.PLAYER,
                topic=f"{name} Career",
                content=f"{name} is {desc}. Their performance trajectory is {trajectory}.",
                relevance=relevance * 0.8,
                ttl_seconds=1800,  # Career phase doesn't change quickly
                source_entities=[player.get("id", "")],
                tags=["player", "career", phase],
            ))

        # Card 3: Narratives
        for narrative in data.get("narratives", []):
            n_props = narrative.get("properties", {})
            cards.append(ContextCard(
                id=f"narrative_{n_props.get('id', 'unknown')}",
                type=ContextType.NARRATIVE,
                topic=n_props.get("title", "Storyline"),
                content=n_props.get("description", "Active storyline"),
                relevance=relevance * n_props.get("intensity", 0.5),
                ttl_seconds=300,
                source_entities=[player.get("id", "")],
                tags=["narrative", n_props.get("type", "unknown")],
            ))

        # Add all cards to queue
        for card in cards:
            self.queue.add(card)

        return cards

    def generate_team_context(
        self,
        team_identifier: str,
        relevance: float = 0.5,
    ) -> list[ContextCard]:
        """Generate context cards about a team."""
        cards = []

        result = get_team_context(team_identifier)
        if not result.success:
            return cards

        data = result.data
        team = data.get("team", {}).get("properties", {})
        name = team.get("name", team_identifier)
        abbr = team.get("abbr", "???")

        # Card 1: Team record and status
        record = data.get("record", {})
        wins = record.get("wins", 0)
        losses = record.get("losses", 0)

        cards.append(ContextCard(
            id=f"team_record_{abbr}",
            type=ContextType.TEAM,
            topic=name,
            content=f"The {name} are {wins}-{losses} this season.",
            relevance=relevance,
            ttl_seconds=3600,
            source_entities=[team.get("id", "")],
            tags=["team", "record", abbr],
        ))

        # Card 2: Tendencies
        run_tendency = team.get("run_tendency", 0.5)
        if run_tendency > 0.6:
            tendency_desc = "a run-heavy team that likes to control the clock"
        elif run_tendency < 0.4:
            tendency_desc = "an aggressive passing team that likes to air it out"
        else:
            tendency_desc = "a balanced offense that keeps defenses guessing"

        cards.append(ContextCard(
            id=f"team_tendency_{abbr}",
            type=ContextType.TEAM,
            topic=f"{abbr} Style",
            content=f"The {name} are {tendency_desc}.",
            relevance=relevance * 0.7,
            ttl_seconds=1800,
            source_entities=[team.get("id", "")],
            tags=["team", "tendency", abbr],
        ))

        # Card 3: Star players
        roster = data.get("roster", [])
        if roster:
            top_player = roster[0].get("properties", {})
            star_name = top_player.get("name", "Unknown")
            star_pos = top_player.get("position", "?")
            star_ovr = top_player.get("overall", "?")

            cards.append(ContextCard(
                id=f"team_star_{abbr}",
                type=ContextType.PLAYER,
                topic=f"{abbr} Star",
                content=f"{star_name} ({star_pos}, {star_ovr} OVR) is the {name}'s top player.",
                relevance=relevance * 0.6,
                ttl_seconds=600,
                source_entities=[team.get("id", ""), top_player.get("id", "")],
                tags=["team", "star", abbr],
            ))

        for card in cards:
            self.queue.add(card)

        return cards

    def generate_matchup_context(
        self,
        team_a: str,
        team_b: str,
        relevance: float = 0.7,
    ) -> list[ContextCard]:
        """Generate context cards about a matchup."""
        cards = []

        result = get_matchup_context(team_a, team_b, "team")
        if not result.success:
            return cards

        data = result.data
        entity_a = data.get("entity_a", {}).get("properties", {})
        entity_b = data.get("entity_b", {}).get("properties", {})
        name_a = entity_a.get("name", team_a)
        name_b = entity_b.get("name", team_b)

        # Card 1: Matchup overview
        h2h_games = data.get("head_to_head_games", [])

        if h2h_games:
            cards.append(ContextCard(
                id=f"matchup_{team_a}_{team_b}",
                type=ContextType.MATCHUP,
                topic=f"{name_a} vs {name_b}",
                content=f"The {name_a} and {name_b} have met {len(h2h_games)} times recently.",
                relevance=relevance,
                ttl_seconds=3600,
                source_entities=[entity_a.get("id", ""), entity_b.get("id", "")],
                tags=["matchup", team_a, team_b],
            ))
        else:
            cards.append(ContextCard(
                id=f"matchup_{team_a}_{team_b}",
                type=ContextType.MATCHUP,
                topic=f"{name_a} vs {name_b}",
                content=f"First meeting between the {name_a} and {name_b} this season.",
                relevance=relevance * 0.5,
                ttl_seconds=3600,
                source_entities=[entity_a.get("id", ""), entity_b.get("id", "")],
                tags=["matchup", team_a, team_b],
            ))

        for card in cards:
            self.queue.add(card)

        return cards

    def generate_game_situation_context(
        self,
        quarter: int,
        time_remaining: str,
        score_diff: int,
        down: int,
        yards_to_go: int,
        field_position: int,
        relevance: float = 0.8,
    ) -> list[ContextCard]:
        """
        Generate context cards about the current game situation.

        This provides situational awareness for commentary.
        """
        cards = []

        # Card 1: Game state
        if score_diff > 14:
            game_state = "a blowout"
        elif score_diff > 7:
            game_state = "a comfortable lead"
        elif score_diff > 0:
            game_state = "a close game"
        elif score_diff == 0:
            game_state = "tied"
        elif score_diff > -7:
            game_state = "trailing slightly"
        else:
            game_state = "in a deep hole"

        cards.append(ContextCard(
            id=f"situation_q{quarter}_{time_remaining}",
            type=ContextType.SITUATION,
            topic="Game State",
            content=f"Q{quarter} {time_remaining} - This is {game_state}.",
            relevance=relevance,
            ttl_seconds=30,  # Situation changes fast
            tags=["situation", "score"],
        ))

        # Card 2: Down and distance
        if down == 4:
            if yards_to_go <= 2 and field_position > 50:
                situation = "a crucial short-yardage situation - do they go for it?"
            elif field_position > 60:
                situation = "fourth down in field goal range"
            else:
                situation = "fourth down - likely a punt"
        elif down == 3 and yards_to_go > 7:
            situation = "third and long - passing situation"
        elif down == 1:
            situation = "first down - full playbook available"
        else:
            situation = f"{down}{'st' if down == 1 else 'nd' if down == 2 else 'rd' if down == 3 else 'th'} and {yards_to_go}"

        cards.append(ContextCard(
            id=f"situation_down_{down}_{yards_to_go}",
            type=ContextType.SITUATION,
            topic="Down & Distance",
            content=f"It's {situation}.",
            relevance=relevance * 0.9,
            ttl_seconds=20,
            tags=["situation", "down"],
        ))

        for card in cards:
            self.queue.add(card)

        return cards


# Singleton context queue for the game
_game_context_queue: Optional[ContextQueue] = None


def get_game_context_queue() -> ContextQueue:
    """Get the global game context queue."""
    global _game_context_queue
    if _game_context_queue is None:
        _game_context_queue = ContextQueue()
    return _game_context_queue


def reset_game_context() -> None:
    """Reset the game context queue (e.g., at game start)."""
    global _game_context_queue
    _game_context_queue = ContextQueue()

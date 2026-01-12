"""
Computed properties module.

Calculates derived properties for graph nodes:
- Player career phase (rising/peak/declining)
- Performance trends
- Matchup analysis
- Narrative detection

These properties add "intelligence" to the graph - the AI exploration
layer can query these computed values rather than raw data.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from huddle.graph.connection import GraphConnection, get_graph, is_graph_enabled
from huddle.graph.schema import NodeLabels, RelTypes
from huddle.graph.sync.base import SyncResult, sync_entity

logger = logging.getLogger(__name__)


# ============================================================================
# CAREER PHASE
# ============================================================================

@dataclass
class CareerPhase:
    """A player's career phase classification."""
    phase: str  # "rookie", "rising", "peak", "declining", "twilight"
    confidence: float  # 0-1 confidence in classification
    peak_age_estimate: int  # Estimated age of peak
    years_from_peak: int  # Negative = before peak, positive = after
    trajectory: str  # "ascending", "plateau", "descending"


# Position-specific peak ages (from NFL research)
POSITION_PEAK_AGES = {
    "QB": 29,
    "RB": 26,
    "WR": 27,
    "TE": 28,
    "LT": 28, "LG": 28, "C": 28, "RG": 28, "RT": 28,
    "DE": 27, "DT": 27, "NT": 27,
    "MLB": 27, "ILB": 27, "OLB": 27,
    "CB": 27,
    "FS": 28, "SS": 28,
    "K": 32, "P": 32,
}


def calculate_career_phase(
    player: Any,
    recent_stats: Optional[list[dict]] = None,
) -> CareerPhase:
    """
    Calculate a player's career phase based on age, experience, and performance.

    Args:
        player: Player object with age, position, experience
        recent_stats: Optional list of recent game/season stats for trajectory

    Returns:
        CareerPhase with classification and metadata
    """
    position = player.position.value if hasattr(player.position, "value") else str(player.position)
    peak_age = POSITION_PEAK_AGES.get(position, 28)

    age = player.age
    experience = player.experience_years

    years_from_peak = age - peak_age

    # Classify phase
    if experience <= 1:
        phase = "rookie"
        confidence = 0.95
        trajectory = "ascending"
    elif years_from_peak < -3:
        phase = "rising"
        confidence = 0.8
        trajectory = "ascending"
    elif -3 <= years_from_peak <= 2:
        phase = "peak"
        confidence = 0.7
        trajectory = "plateau"
    elif 2 < years_from_peak <= 5:
        phase = "declining"
        confidence = 0.75
        trajectory = "descending"
    else:
        phase = "twilight"
        confidence = 0.85
        trajectory = "descending"

    # Adjust confidence based on available stats
    if recent_stats:
        # TODO: Analyze actual performance trend to adjust confidence
        pass

    return CareerPhase(
        phase=phase,
        confidence=confidence,
        peak_age_estimate=peak_age,
        years_from_peak=years_from_peak,
        trajectory=trajectory,
    )


def sync_player_career_phase(
    player: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Calculate and sync a player's career phase to the graph.
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    phase = calculate_career_phase(player)

    properties = {
        "career_phase": phase.phase,
        "career_phase_confidence": phase.confidence,
        "peak_age_estimate": phase.peak_age_estimate,
        "years_from_peak": phase.years_from_peak,
        "trajectory": phase.trajectory,
    }

    return sync_entity(NodeLabels.PLAYER, player.id, properties, graph)


# ============================================================================
# PERFORMANCE TRENDS
# ============================================================================

@dataclass
class PerformanceTrend:
    """A player's performance trend over recent games."""
    player_id: str
    window: int  # Number of games in window
    direction: str  # "improving", "stable", "declining"
    magnitude: float  # How strong the trend is (0-1)
    key_stats: dict  # Stats that drove the classification
    hot_streak: bool  # Currently on a hot streak?
    cold_streak: bool  # Currently on a cold streak?


def calculate_performance_trend(
    player_id: str,
    game_stats: list[dict],
    window: int = 5,
) -> PerformanceTrend:
    """
    Calculate performance trend from recent game stats.

    Args:
        player_id: Player's ID
        game_stats: List of game stats dicts (most recent first)
        window: Number of games to analyze

    Returns:
        PerformanceTrend with direction and key stats
    """
    if not game_stats or len(game_stats) < 2:
        return PerformanceTrend(
            player_id=player_id,
            window=len(game_stats) if game_stats else 0,
            direction="stable",
            magnitude=0.0,
            key_stats={},
            hot_streak=False,
            cold_streak=False,
        )

    # Take the window
    recent = game_stats[:window]
    n = len(recent)

    # Calculate key stats averages for first half vs second half of window
    first_half = recent[n // 2:]
    second_half = recent[:n // 2]

    def avg_stat(games: list, stat: str) -> float:
        values = [g.get(stat, 0) for g in games if stat in g]
        return sum(values) / len(values) if values else 0

    # Compare key stats
    key_stats = {}
    trends = []

    for stat in ["passing_yards", "rushing_yards", "receiving_yards", "tackles", "sacks"]:
        old_avg = avg_stat(first_half, stat)
        new_avg = avg_stat(second_half, stat)

        if old_avg > 0:
            pct_change = (new_avg - old_avg) / old_avg
            key_stats[stat] = {"old": old_avg, "new": new_avg, "change": pct_change}
            trends.append(pct_change)

    # Determine overall direction
    if not trends:
        direction = "stable"
        magnitude = 0.0
    else:
        avg_trend = sum(trends) / len(trends)
        magnitude = abs(avg_trend)

        if avg_trend > 0.1:
            direction = "improving"
        elif avg_trend < -0.1:
            direction = "declining"
        else:
            direction = "stable"

    # Detect streaks (simple: 3+ consecutive good/bad games)
    # TODO: More sophisticated streak detection
    hot_streak = False
    cold_streak = False

    return PerformanceTrend(
        player_id=player_id,
        window=n,
        direction=direction,
        magnitude=min(magnitude, 1.0),
        key_stats=key_stats,
        hot_streak=hot_streak,
        cold_streak=cold_streak,
    )


def sync_performance_trend(
    player_id: str,
    trend: PerformanceTrend,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """Sync a calculated performance trend to the graph."""
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    properties = {
        "trend_direction": trend.direction,
        "trend_magnitude": trend.magnitude,
        "trend_window": trend.window,
        "hot_streak": trend.hot_streak,
        "cold_streak": trend.cold_streak,
    }

    return sync_entity(NodeLabels.PLAYER, player_id, properties, graph)


# ============================================================================
# MATCHUP ANALYSIS
# ============================================================================

@dataclass
class MatchupAnalysis:
    """Analysis of head-to-head matchup between two players."""
    player_a_id: str
    player_b_id: str
    games_faced: int
    player_a_edge: float  # -1 to 1 (negative = B has edge)
    key_factor: str  # What determines the matchup
    narrative_significance: str  # Why this matchup matters


def calculate_matchup(
    player_a_id: str,
    player_b_id: str,
    head_to_head_stats: list[dict],
) -> MatchupAnalysis:
    """
    Calculate matchup analysis between two players.

    Args:
        player_a_id: First player's ID
        player_b_id: Second player's ID
        head_to_head_stats: Stats from games where both played

    Returns:
        MatchupAnalysis with edge calculation
    """
    if not head_to_head_stats:
        return MatchupAnalysis(
            player_a_id=player_a_id,
            player_b_id=player_b_id,
            games_faced=0,
            player_a_edge=0.0,
            key_factor="insufficient_data",
            narrative_significance="First meeting",
        )

    games = len(head_to_head_stats)

    # TODO: Calculate actual edge based on stats
    # For now, return neutral
    return MatchupAnalysis(
        player_a_id=player_a_id,
        player_b_id=player_b_id,
        games_faced=games,
        player_a_edge=0.0,
        key_factor="experience",
        narrative_significance=f"Met {games} times before",
    )


# ============================================================================
# TEAM HEAD-TO-HEAD
# ============================================================================

@dataclass
class HeadToHead:
    """Head-to-head record between two teams."""
    team_a_id: str
    team_b_id: str
    team_a_abbr: str
    team_b_abbr: str
    games_played: int
    team_a_wins: int
    team_b_wins: int
    ties: int
    point_differential: int  # Team A's perspective
    streak: str  # "A3" = Team A won last 3, "B2" = Team B won last 2
    is_rivalry: bool
    rivalry_intensity: str  # "division", "conference", "historic"


def calculate_head_to_head(
    team_a: Any,
    team_b: Any,
    games: list[dict],
) -> HeadToHead:
    """
    Calculate head-to-head record between two teams.
    """
    team_a_wins = 0
    team_b_wins = 0
    ties = 0
    point_diff = 0

    for game in games:
        a_score = game.get("team_a_score", 0)
        b_score = game.get("team_b_score", 0)
        point_diff += (a_score - b_score)

        if a_score > b_score:
            team_a_wins += 1
        elif b_score > a_score:
            team_b_wins += 1
        else:
            ties += 1

    # Determine streak (simplified)
    streak = "none"
    if games:
        last_game = games[0]
        if last_game.get("team_a_score", 0) > last_game.get("team_b_score", 0):
            streak = "A1"
        else:
            streak = "B1"

    # Check if division rivals
    from huddle.graph.sync.teams import get_division_for_team
    div_a = get_division_for_team(team_a.abbreviation if hasattr(team_a, "abbreviation") else str(team_a))
    div_b = get_division_for_team(team_b.abbreviation if hasattr(team_b, "abbreviation") else str(team_b))
    is_division_rival = div_a == div_b and div_a is not None

    return HeadToHead(
        team_a_id=str(team_a.id if hasattr(team_a, "id") else team_a),
        team_b_id=str(team_b.id if hasattr(team_b, "id") else team_b),
        team_a_abbr=team_a.abbreviation if hasattr(team_a, "abbreviation") else str(team_a),
        team_b_abbr=team_b.abbreviation if hasattr(team_b, "abbreviation") else str(team_b),
        games_played=len(games),
        team_a_wins=team_a_wins,
        team_b_wins=team_b_wins,
        ties=ties,
        point_differential=point_diff,
        streak=streak,
        is_rivalry=is_division_rival,
        rivalry_intensity="division" if is_division_rival else "none",
    )


# ============================================================================
# NARRATIVE DETECTION
# ============================================================================

@dataclass
class Narrative:
    """A detected narrative/storyline in the game world."""
    id: str
    type: str  # "rivalry", "comeback", "streak", "milestone", "breakout", "decline"
    title: str
    description: str
    participants: list[str]  # Player/team IDs involved
    start_date: Optional[datetime]
    is_active: bool
    intensity: float  # 0-1 how significant


def detect_narratives(
    player: Optional[Any] = None,
    team: Optional[Any] = None,
    recent_events: Optional[list[dict]] = None,
) -> list[Narrative]:
    """
    Detect active narratives involving a player or team.

    Args:
        player: Optional player to analyze
        team: Optional team to analyze
        recent_events: Recent game events for context

    Returns:
        List of detected narratives
    """
    narratives = []

    if player:
        # Check for milestone narratives
        if hasattr(player, "experience_years"):
            if player.experience_years == 1:
                narratives.append(Narrative(
                    id=f"{player.id}_rookie_season",
                    type="milestone",
                    title="Rookie Season",
                    description=f"{player.full_name}'s first NFL season",
                    participants=[str(player.id)],
                    start_date=None,
                    is_active=True,
                    intensity=0.6,
                ))

        # Check for career phase narratives
        phase = calculate_career_phase(player)
        if phase.phase == "twilight":
            narratives.append(Narrative(
                id=f"{player.id}_twilight",
                type="decline",
                title="Career Twilight",
                description=f"{player.full_name} in the twilight of their career",
                participants=[str(player.id)],
                start_date=None,
                is_active=True,
                intensity=0.7,
            ))

    # TODO: Add more narrative detection
    # - Winning/losing streaks
    # - Comeback stories
    # - Rivalry games
    # - Statistical milestones

    return narratives


def sync_narratives(
    narratives: list[Narrative],
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """Sync detected narratives to the graph."""
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    result = SyncResult(success=True)

    for narrative in narratives:
        properties = {
            "type": narrative.type,
            "title": narrative.title,
            "description": narrative.description,
            "is_active": narrative.is_active,
            "intensity": narrative.intensity,
        }

        r = sync_entity(NodeLabels.NARRATIVE, narrative.id, properties, graph)
        result = result + r

        # Create INVOLVED_IN relationships for participants
        for participant_id in narrative.participants:
            # Try to link as player first, then as team
            query = """
            MATCH (n:Narrative {id: $narrative_id})
            OPTIONAL MATCH (p:Player {id: $participant_id})
            OPTIONAL MATCH (t:Team {id: $participant_id})
            WITH n, COALESCE(p, t) as participant
            WHERE participant IS NOT NULL
            MERGE (participant)-[r:INVOLVED_IN]->(n)
            RETURN r
            """
            try:
                graph.run_write(query, {
                    "narrative_id": narrative.id,
                    "participant_id": participant_id,
                })
                result.relationships_created += 1
            except Exception as e:
                result.errors.append(str(e))

    return result


# ============================================================================
# BATCH COMPUTED PROPERTY SYNC
# ============================================================================

def sync_all_computed_properties(
    league: Any,
    graph: Optional[GraphConnection] = None,
) -> SyncResult:
    """
    Calculate and sync all computed properties for a league.

    This is expensive - run periodically or after significant changes.
    """
    graph = graph or get_graph()

    if not is_graph_enabled():
        return SyncResult(success=True)

    logger.info("Syncing all computed properties...")
    result = SyncResult(success=True)

    # Sync career phases for all players
    for team in league.teams.values():
        for player in team.roster.players.values():
            r = sync_player_career_phase(player, graph)
            result = result + r

            # Detect and sync narratives
            narratives = detect_narratives(player=player)
            if narratives:
                r = sync_narratives(narratives, graph)
                result = result + r

    logger.info(
        f"Computed properties synced: {result.nodes_created} nodes, "
        f"{result.relationships_created} relationships"
    )

    return result

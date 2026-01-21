"""
Commentary System Schema

Three-layer architecture for transforming raw play data into commentary-ready context.

Layer 1: Raw Play (exists in simulation)
Layer 2: Enriched Play (deterministic derivation)
Layer 3: Narrative Context (agent-discovered)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# =============================================================================
# LAYER 2: ENRICHED PLAY CONTEXT
# Derived deterministically from existing game state + lookups
# =============================================================================

@dataclass
class PlayerRef:
    """Resolved player reference with name and context."""
    player_id: str
    name: str
    position: str
    team_abbrev: str
    jersey_number: int

    # Quick stats context (today's game)
    stats_today: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"receptions": 5, "yards": 67, "targets": 8}


@dataclass
class PlayConcept:
    """What was called and why it matters."""
    play_code: str              # Raw code from playbook
    play_type: str              # "pass", "run", "screen", "play_action"
    formation: str              # "shotgun", "under_center", "pistol"
    concept_name: Optional[str] # "slant_flat", "hb_dive", "four_verticals"

    # Pass-specific
    route_tree: Optional[Dict[str, str]] = None  # {receiver_id: "slant", ...}
    protection: Optional[str] = None              # "max_protect", "slide_left"

    # Run-specific
    run_direction: Optional[str] = None           # "left", "right", "middle"
    blocking_scheme: Optional[str] = None         # "zone", "power", "counter"


@dataclass
class DriveContext:
    """Current drive state for context."""
    play_number_in_drive: int
    yards_this_drive: float
    time_this_drive: float          # seconds
    starting_field_position: str    # "OWN 25"

    # Efficiency
    third_down_attempts: int
    third_down_conversions: int

    # Momentum indicators
    consecutive_first_downs: int
    plays_since_negative: int       # plays since a loss of yards


@dataclass
class GameSituation:
    """Situational context that shapes commentary tone."""
    # Core state
    quarter: int
    time_remaining: str             # "2:34"
    time_remaining_seconds: int

    down: int
    distance: int
    field_position: str             # "OPP 35"
    yards_to_goal: int

    # Score context
    home_score: int
    away_score: int
    score_differential: int         # From perspective of offense

    # Situational flags
    is_red_zone: bool
    is_goal_to_go: bool
    is_two_minute_warning: bool
    is_four_minute_offense: bool    # Protecting lead late
    is_hurry_up: bool
    is_fourth_down: bool
    is_short_yardage: bool          # 3 or fewer
    is_long_yardage: bool           # 7 or more

    # Game phase
    is_close_game: bool             # Within one score
    is_blowout: bool                # 3+ scores
    is_comeback_territory: bool     # Down big but time remains


@dataclass
class EnrichedPlay:
    """
    Layer 2: Deterministically enriched play data.

    Built from: PlayResult + GameState + Roster lookups + PlayCode mapping
    """
    # Identifiers
    play_id: str
    game_id: str

    # Result basics (from PlayResult)
    outcome: str                    # "complete", "incomplete", "sack", etc.
    yards_gained: float

    # Resolved participants
    passer: Optional[PlayerRef]
    receiver: Optional[PlayerRef]
    ball_carrier: Optional[PlayerRef]
    tackler: Optional[PlayerRef]

    # What was called
    play_concept: PlayConcept

    # Context
    situation: GameSituation
    drive_context: DriveContext

    # Key moments from tick events (extracted)
    key_events: List[str]           # ["pressure_level_high", "scramble", "throw_on_run"]

    # Timing
    play_duration: float            # seconds
    throw_time: Optional[float]     # seconds from snap

    # Passing detail
    air_yards: Optional[float]
    yards_after_catch: Optional[float]
    was_contested: bool
    was_dropped: bool

    # Derived flags
    was_big_play: bool              # 20+ pass, 10+ run
    was_explosive: bool             # 40+ yards
    was_negative: bool              # Loss of yards
    resulted_in_first_down: bool
    resulted_in_touchdown: bool
    resulted_in_turnover: bool


# =============================================================================
# LAYER 3: NARRATIVE CONTEXT
# Discovered by agentic exploration - not derivable from single play
# =============================================================================

class NarrativeType(Enum):
    """Categories of narrative hooks."""
    STATISTICAL_ANOMALY = "statistical_anomaly"     # Unusual pattern
    MILESTONE = "milestone"                          # Record/achievement proximity
    STREAK = "streak"                                # Hot/cold streak
    MATCHUP = "matchup"                              # Player vs player story
    HISTORICAL = "historical"                        # Past game reference
    STORYLINE = "storyline"                          # Season-long narrative
    SITUATIONAL = "situational"                      # Game situation significance
    PERSONNEL = "personnel"                          # Injury, debut, return


@dataclass
class NarrativeHook:
    """
    A single narrative element discovered by the agent.

    These are the building blocks of color commentary.
    """
    narrative_type: NarrativeType
    priority: float                 # 0.0 - 1.0, how important/interesting

    # The hook itself
    headline: str                   # Short: "Third drop today"
    detail: str                     # Longer: "Cooper has now dropped 3 of his 8 targets..."

    # What triggered it
    trigger_player_id: Optional[str]
    trigger_stat: Optional[str]     # "drops", "rushing_yards", etc.
    trigger_value: Optional[Any]

    # Freshness
    discovered_at: datetime
    last_mentioned: Optional[datetime]  # Avoid repetition
    mention_count: int = 0


@dataclass
class MilestoneProximity:
    """Tracking approach to significant numbers."""
    player_id: str
    player_name: str

    stat_name: str                  # "rushing_yards", "career_touchdowns"
    current_value: int
    milestone_value: int            # 100, 1000, etc.
    yards_needed: int

    milestone_type: str             # "game", "season", "career"
    significance: str               # "100 yard game", "1000 yard season"


@dataclass
class ActiveStreak:
    """Hot or cold streak in progress."""
    player_id: str
    player_name: str

    streak_type: str                # "completions", "catches", "games_with_td"
    streak_value: int               # Length of streak
    is_positive: bool               # Hot (good) or cold (bad)

    context: str                    # "has completed his last 8 passes"

    # Historical comparison
    career_best: Optional[int]
    season_best: Optional[int]


@dataclass
class MatchupNote:
    """Player vs player or team vs team history."""
    matchup_type: str               # "player_vs_player", "player_vs_team", "team_vs_team"

    entity_a_id: str
    entity_a_name: str
    entity_b_id: str
    entity_b_name: str

    history_summary: str            # "2-0 in last two meetings"
    key_stat: Optional[str]         # "has allowed 0 TDs in coverage"

    narrative_angle: str            # "revenge game", "former teammates", "division rival"


@dataclass
class NarrativeContext:
    """
    Layer 3: Agent-discovered narrative elements.

    Built by: Background agent exploring stats, history, patterns
    Updated: Continuously during game, cached between plays
    """
    # Active hooks relevant to current situation
    active_hooks: List[NarrativeHook]

    # Milestone tracking
    milestones_in_range: List[MilestoneProximity]

    # Streaks
    active_streaks: List[ActiveStreak]

    # Matchup notes
    relevant_matchups: List[MatchupNote]

    # Pre-computed storylines for this game
    game_storylines: List[str]      # ["rivalry game", "playoff implications", ...]

    # What we've already said (avoid repetition)
    recently_mentioned: Dict[str, datetime]  # hook_id -> last_mentioned


# =============================================================================
# COMBINED: COMMENTARY CONTEXT PACKAGE
# What gets sent to the generative model
# =============================================================================

@dataclass
class CommentaryContext:
    """
    The complete context package for generating commentary.

    This is what the generative model receives.
    """
    # The play itself (Layer 2)
    play: EnrichedPlay

    # Narrative elements (Layer 3)
    narratives: NarrativeContext

    # Recent history (for continuity)
    recent_plays_summary: List[str]     # Last 3-5 plays, one-line each
    drive_summary: str                   # "7 plays, 45 yards, 3:20"

    # Commentary constraints
    commentary_type: str                 # "play_by_play", "color", "analysis"
    max_duration_seconds: float          # How long they have to talk
    energy_level: str                    # "normal", "excited", "tense"

    # What to emphasize (agent's recommendation)
    suggested_focus: Optional[str]       # "milestone_proximity", "matchup", etc.
    hooks_to_use: List[str]              # IDs of narrative hooks to weave in


# =============================================================================
# BUILDER INTERFACES
# How each layer gets constructed
# =============================================================================

class Layer2Builder:
    """
    Builds EnrichedPlay from raw simulation data.

    Dependencies:
    - PlayResult (from simulation)
    - GameState (from game manager)
    - Roster (for player lookups)
    - Playbook (for play concept mapping)
    """

    def build(
        self,
        play_result: Any,           # PlayResult from orchestrator
        game_state: Any,            # GameState
        roster: Any,                # Team rosters for lookup
        play_code: str,             # What was called
    ) -> EnrichedPlay:
        """Transform raw play into enriched play."""
        raise NotImplementedError


class Layer3Agent:
    """
    Discovers narrative context through exploration.

    This runs asynchronously, continuously updating NarrativeContext.

    Explores:
    - Player stats (game, season, career)
    - Historical matchups
    - Statistical patterns
    - Milestone proximity
    - Storylines from graph database
    """

    async def update_context(
        self,
        enriched_play: EnrichedPlay,
        current_context: NarrativeContext,
    ) -> NarrativeContext:
        """Update narrative context after a play."""
        raise NotImplementedError

    async def discover_pregame_narratives(
        self,
        home_team_id: str,
        away_team_id: str,
    ) -> NarrativeContext:
        """Build initial narrative context before game starts."""
        raise NotImplementedError


class CommentaryGenerator:
    """
    Generates commentary from context.

    This is the fast, generative layer.
    Could be prompted LLM or fine-tuned model.
    """

    async def generate_play_by_play(
        self,
        context: CommentaryContext,
    ) -> str:
        """Quick, reactive play description."""
        raise NotImplementedError

    async def generate_color(
        self,
        context: CommentaryContext,
    ) -> str:
        """Narrative-rich color commentary."""
        raise NotImplementedError

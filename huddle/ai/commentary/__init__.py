"""
Commentary System

Three-layer architecture for generating ESPN-style broadcast commentary.

Layer 1: Raw Play (simulation events)
Layer 2: Enriched Play (deterministic derivation)
Layer 3: Narrative Context (agent-discovered)
"""

from .schema import (
    # Layer 2 - Enriched
    PlayerRef,
    PlayConcept,
    DriveContext,
    GameSituation,
    EnrichedPlay,

    # Layer 3 - Narrative
    NarrativeType,
    NarrativeHook,
    MilestoneProximity,
    ActiveStreak,
    MatchupNote,
    NarrativeContext,

    # Combined
    CommentaryContext,

    # Builder interfaces
    Layer2Builder,
    Layer3Agent,
    CommentaryGenerator,
)

from .client import (
    GeminiClient,
    GeminiClientError,
    GeminiRateLimitError,
    GeminiAPIError,
    GenerationResult,
    generate_with_gemini,
)

from .generator import (
    GeminiCommentaryGenerator,
    CommentaryResult,
)

from .prompts import (
    build_play_by_play_prompt,
    build_color_prompt,
    serialize_play_for_prompt,
    serialize_narratives_for_prompt,
    PLAY_BY_PLAY_SYSTEM,
    COLOR_COMMENTARY_SYSTEM,
)

__all__ = [
    # Schema - Layer 2
    "PlayerRef",
    "PlayConcept",
    "DriveContext",
    "GameSituation",
    "EnrichedPlay",
    # Schema - Layer 3
    "NarrativeType",
    "NarrativeHook",
    "MilestoneProximity",
    "ActiveStreak",
    "MatchupNote",
    "NarrativeContext",
    # Schema - Combined
    "CommentaryContext",
    # Schema - Interfaces
    "Layer2Builder",
    "Layer3Agent",
    "CommentaryGenerator",
    # Client
    "GeminiClient",
    "GeminiClientError",
    "GeminiRateLimitError",
    "GeminiAPIError",
    "GenerationResult",
    "generate_with_gemini",
    # Generator
    "GeminiCommentaryGenerator",
    "CommentaryResult",
    # Prompts
    "build_play_by_play_prompt",
    "build_color_prompt",
    "serialize_play_for_prompt",
    "serialize_narratives_for_prompt",
    "PLAY_BY_PLAY_SYSTEM",
    "COLOR_COMMENTARY_SYSTEM",
]

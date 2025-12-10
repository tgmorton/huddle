"""Content generators."""

from huddle.generators.player import (
    generate_player,
    generate_team,
    generate_team_with_identity,
    generate_rookie,
    generate_draft_class,
)
from huddle.generators.league import (
    generate_league,
    generate_league_with_schedule,
    generate_nfl_team,
    generate_preseason_league,
)

__all__ = [
    # Player generation
    "generate_player",
    "generate_team",
    "generate_team_with_identity",
    "generate_rookie",
    "generate_draft_class",
    # League generation
    "generate_league",
    "generate_league_with_schedule",
    "generate_nfl_team",
    "generate_preseason_league",
]

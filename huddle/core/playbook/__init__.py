"""
Playbook System.

HC09-style play knowledge tracking where players progress from
UNLEARNED → LEARNED → MASTERED for each play in the team's playbook.

Key Components:
- PlayCode: Individual play definitions with complexity and position requirements
- Playbook: Team's active play selection
- PlayMastery: Per-player, per-play knowledge state
- PlayerPlayKnowledge: All play knowledge for a player
- Learning functions: Practice reps, decay, team readiness

Example usage:
    from huddle.core.playbook import (
        Playbook,
        PlayerPlayKnowledge,
        MasteryLevel,
        apply_practice_rep,
        calculate_learning_rate,
    )

    # Create team playbook
    playbook = Playbook.default(team_id=team.id)

    # Track player knowledge
    knowledge = PlayerPlayKnowledge(player_id=player.id)

    # Practice a play
    mastery = knowledge.get_mastery("RUN_POWER")
    advanced = apply_practice_rep(player, mastery, play_complexity=2)

    # Check execution modifier
    modifier = knowledge.get_execution_modifier("RUN_POWER")
    # Returns 0.85 (unlearned), 1.0 (learned), or 1.1 (mastered)
"""

from huddle.core.playbook.play_codes import (
    PlayCategory,
    PlayCode,
    OFFENSIVE_PLAYS,
    DEFENSIVE_PLAYS,
    ALL_PLAYS,
    DEFAULT_OFFENSIVE_PLAYBOOK,
    DEFAULT_DEFENSIVE_PLAYBOOK,
    get_play,
    get_plays_for_position,
    get_offensive_plays,
    get_defensive_plays,
    OL_POSITIONS,
    SKILL_POSITIONS,
    PASS_CATCHERS,
    ALL_OFFENSE,
    ALL_DEFENSE,
)

from huddle.core.playbook.knowledge import (
    MasteryLevel,
    PlayMastery,
    PlayerPlayKnowledge,
    MASTERY_MODIFIERS,
)

from huddle.core.playbook.playbook import Playbook

from huddle.core.playbook.learning import (
    calculate_learning_rate,
    calculate_decay_rate,
    apply_practice_rep,
    apply_decay,
    apply_game_rep,
    practice_plays,
    apply_weekly_decay,
    get_team_play_readiness,
    estimate_reps_to_learn,
    BASE_LEARNING_RATE,
    MASTERED_WEEKLY_DECAY,
    LEARNED_WEEKLY_DECAY,
)


__all__ = [
    # Play Codes
    "PlayCategory",
    "PlayCode",
    "OFFENSIVE_PLAYS",
    "DEFENSIVE_PLAYS",
    "ALL_PLAYS",
    "DEFAULT_OFFENSIVE_PLAYBOOK",
    "DEFAULT_DEFENSIVE_PLAYBOOK",
    "get_play",
    "get_plays_for_position",
    "get_offensive_plays",
    "get_defensive_plays",
    "OL_POSITIONS",
    "SKILL_POSITIONS",
    "PASS_CATCHERS",
    "ALL_OFFENSE",
    "ALL_DEFENSE",
    # Knowledge
    "MasteryLevel",
    "PlayMastery",
    "PlayerPlayKnowledge",
    "MASTERY_MODIFIERS",
    # Playbook
    "Playbook",
    # Learning
    "calculate_learning_rate",
    "calculate_decay_rate",
    "apply_practice_rep",
    "apply_decay",
    "apply_game_rep",
    "practice_plays",
    "apply_weekly_decay",
    "get_team_play_readiness",
    "estimate_reps_to_learn",
    "BASE_LEARNING_RATE",
    "MASTERED_WEEKLY_DECAY",
    "LEARNED_WEEKLY_DECAY",
]

"""
Play Learning Mechanics.

Implements the HC09-style learning system where players progress
from UNLEARNED → LEARNED → MASTERED based on practice and decay
over time if plays aren't used.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

from huddle.core.playbook.knowledge import MasteryLevel, PlayMastery, PlayerPlayKnowledge
from huddle.core.playbook.play_codes import ALL_PLAYS, PlayCode

if TYPE_CHECKING:
    from huddle.core.models.player import Player


# =============================================================================
# Learning Constants
# =============================================================================

# Base progress per practice rep for average player (LEARNING=50) on complexity 3
BASE_LEARNING_RATE = 0.10

# Decay rates (per week, for average player)
MASTERED_WEEKLY_DECAY = 0.05   # 5% per week for mastered plays
LEARNED_WEEKLY_DECAY = 0.10    # 10% per week for learned plays

# When dropping from MASTERED to LEARNED, retain this much progress
TIER_DROP_RETENTION = 0.8


# =============================================================================
# Learning Rate Calculation
# =============================================================================

def calculate_learning_rate(player: "Player", play_complexity: int) -> float:
    """
    Calculate how fast a player learns based on their LEARNING attribute.

    The LEARNING attribute (typically 30-90) determines how quickly
    a player progresses through mastery tiers.

    Args:
        player: The player learning the play
        play_complexity: Play complexity 1-5 (1=easy, 5=complex)

    Returns:
        Progress per practice rep (0.0-1.0 scale)
        With 10 reps, an average player learns a complexity-3 play.

    Examples:
        - LEARNING 50, complexity 3: 0.10 per rep (10 reps to learn)
        - LEARNING 90, complexity 3: 0.18 per rep (6 reps to learn)
        - LEARNING 30, complexity 5: 0.03 per rep (33 reps to learn)
    """
    learning_attr = player.attributes.get("learning", 50)

    # Learning attribute modifier
    # 50 = 1.0x (baseline)
    # 90 = 1.8x (fast learner)
    # 30 = 0.6x (slow learner)
    learning_mod = learning_attr / 50.0

    # Complexity modifier
    # 1 (easy) = 1.5x faster
    # 3 (medium) = 1.0x baseline
    # 5 (complex) = 0.5x slower
    complexity_mod = 1.0 + (3 - play_complexity) * 0.25

    return BASE_LEARNING_RATE * learning_mod * complexity_mod


def calculate_decay_rate(
    player: "Player",
    mastery: PlayMastery,
    days: int,
) -> float:
    """
    Calculate knowledge decay for a play over time.

    Players forget plays they don't practice. High LEARNING attribute
    and game reps slow decay.

    Args:
        player: The player
        mastery: Current mastery state
        days: Days since last practice

    Returns:
        Total decay to subtract from progress
    """
    learning_attr = player.attributes.get("learning", 50)

    # High learning = slower decay (better memory)
    decay_resistance = learning_attr / 100.0  # 0.3-0.9 range typically

    # Game reps slow decay (muscle memory from real games)
    # Each game rep reduces decay by 5%, up to 50% reduction
    game_bonus = min(0.5, mastery.game_reps * 0.05)

    # Base weekly decay rate
    if mastery.level == MasteryLevel.MASTERED:
        weekly_decay = MASTERED_WEEKLY_DECAY
    else:
        weekly_decay = LEARNED_WEEKLY_DECAY

    # Apply modifiers
    effective_weekly_decay = weekly_decay * (1 - decay_resistance) * (1 - game_bonus)

    # Convert to daily and multiply by days
    daily_decay = effective_weekly_decay / 7
    return daily_decay * days


# =============================================================================
# Learning Functions
# =============================================================================

def apply_practice_rep(
    player: "Player",
    mastery: PlayMastery,
    play_complexity: int,
    practice_time: Optional[datetime] = None,
) -> bool:
    """
    Apply one practice rep to a player's play knowledge.

    Increases progress based on learning rate. If progress reaches 1.0,
    advances to the next tier.

    Args:
        player: The player practicing
        mastery: The play mastery to update (modified in place)
        play_complexity: Complexity of the play (1-5)
        practice_time: When the practice occurred (default: now)

    Returns:
        True if the player advanced a tier (learned or mastered)
    """
    if practice_time is None:
        practice_time = datetime.now()

    # Don't add progress if already mastered
    if mastery.level == MasteryLevel.MASTERED:
        mastery.last_practiced = practice_time
        mastery.reps += 1
        return False

    # Calculate and apply progress
    rate = calculate_learning_rate(player, play_complexity)
    mastery.progress += rate
    mastery.reps += 1
    mastery.last_practiced = practice_time

    # Check for tier advancement
    advanced = False
    if mastery.progress >= 1.0:
        if mastery.level == MasteryLevel.UNLEARNED:
            mastery.level = MasteryLevel.LEARNED
            mastery.progress = 0.0  # Reset for next tier
            advanced = True
        elif mastery.level == MasteryLevel.LEARNED:
            mastery.level = MasteryLevel.MASTERED
            mastery.progress = 1.0  # Cap at mastered
            advanced = True

    return advanced


def apply_decay(
    player: "Player",
    mastery: PlayMastery,
    current_time: Optional[datetime] = None,
) -> bool:
    """
    Apply knowledge decay for an unpracticed play.

    Calculates decay based on time since last practice and applies it.
    If progress drops below 0, player drops a tier.

    Args:
        player: The player
        mastery: The play mastery to update (modified in place)
        current_time: Current time for decay calculation (default: now)

    Returns:
        True if the player dropped a tier
    """
    if current_time is None:
        current_time = datetime.now()

    # Can't decay if unlearned or never practiced
    if mastery.level == MasteryLevel.UNLEARNED:
        return False
    if mastery.last_practiced is None:
        return False

    # Calculate days since practice
    delta = current_time - mastery.last_practiced
    days = delta.days + (delta.seconds / 86400)  # Include partial days

    if days <= 0:
        return False

    # Calculate and apply decay
    decay = calculate_decay_rate(player, mastery, int(days))
    mastery.progress -= decay

    # Check for tier drop
    dropped = False
    if mastery.progress < 0:
        if mastery.level == MasteryLevel.MASTERED:
            mastery.level = MasteryLevel.LEARNED
            mastery.progress = TIER_DROP_RETENTION  # Partial retention
            dropped = True
        elif mastery.level == MasteryLevel.LEARNED:
            mastery.level = MasteryLevel.UNLEARNED
            mastery.progress = 0.0
            dropped = True

    return dropped


def apply_game_rep(mastery: PlayMastery) -> None:
    """
    Record that a play was called in a game.

    Game reps slow decay and help retain knowledge.

    Args:
        mastery: The play mastery to update (modified in place)
    """
    mastery.game_reps += 1


# =============================================================================
# Batch Operations
# =============================================================================

def practice_plays(
    player: "Player",
    knowledge: PlayerPlayKnowledge,
    play_codes: List[str],
    reps_per_play: int = 1,
    practice_time: Optional[datetime] = None,
) -> Dict[str, bool]:
    """
    Practice multiple plays for a player.

    Args:
        player: The player practicing
        knowledge: Player's knowledge state (modified in place)
        play_codes: List of play codes to practice
        reps_per_play: Number of reps for each play
        practice_time: When the practice occurred

    Returns:
        Dict mapping play_code to whether player advanced a tier
    """
    advancements = {}

    for play_code in play_codes:
        play = ALL_PLAYS.get(play_code)
        if not play:
            continue

        # Skip if player's position isn't involved
        # (This check should be done by caller, but adding safety)

        mastery = knowledge.get_mastery(play_code)
        advanced = False

        for _ in range(reps_per_play):
            if apply_practice_rep(player, mastery, play.complexity, practice_time):
                advanced = True

        advancements[play_code] = advanced

    return advancements


def apply_weekly_decay(
    player: "Player",
    knowledge: PlayerPlayKnowledge,
    playbook_codes: set[str],
    current_time: Optional[datetime] = None,
) -> List[str]:
    """
    Apply decay to all plays in a playbook.

    Should be called periodically (e.g., at end of each week).

    Args:
        player: The player
        knowledge: Player's knowledge state (modified in place)
        playbook_codes: Set of play codes in the team's playbook
        current_time: Current time for decay calculation

    Returns:
        List of play codes where player dropped a tier
    """
    dropped = []

    for play_code in playbook_codes:
        if play_code in knowledge.plays:
            mastery = knowledge.plays[play_code]
            if apply_decay(player, mastery, current_time):
                dropped.append(play_code)

    return dropped


# =============================================================================
# Team Readiness
# =============================================================================

def get_team_play_readiness(
    players: List["Player"],
    play_code: str,
    knowledge_map: Dict[str, PlayerPlayKnowledge],
) -> float:
    """
    Calculate how ready a group of players is to execute a play.

    Averages the execution modifiers of all relevant players.

    Args:
        players: List of players involved in the play
        play_code: The play to check
        knowledge_map: Dict mapping player_id (as string) to their knowledge

    Returns:
        Average execution modifier (0.85-1.1 range typically)
    """
    if not players:
        return 1.0

    play = ALL_PLAYS.get(play_code)
    if not play:
        return 1.0

    # Filter to players whose position is involved
    relevant_players = [
        p for p in players
        if p.position.value in play.positions_involved
    ]

    if not relevant_players:
        return 1.0

    total_mod = 0.0
    for player in relevant_players:
        knowledge = knowledge_map.get(str(player.id))
        if knowledge:
            total_mod += knowledge.get_execution_modifier(play_code)
        else:
            # No knowledge = unlearned
            total_mod += 0.85

    return total_mod / len(relevant_players)


def estimate_reps_to_learn(
    player: "Player",
    play_code: str,
    target_level: MasteryLevel = MasteryLevel.LEARNED,
) -> int:
    """
    Estimate how many practice reps needed to reach a mastery level.

    Useful for showing players how long it will take to learn plays.

    Args:
        player: The player
        play_code: The play to learn
        target_level: Target mastery level

    Returns:
        Estimated number of reps needed
    """
    play = ALL_PLAYS.get(play_code)
    if not play:
        return 0

    rate = calculate_learning_rate(player, play.complexity)
    if rate <= 0:
        return 999  # Would never learn

    if target_level == MasteryLevel.LEARNED:
        # Need to go 0 -> 1.0 progress
        return int(1.0 / rate) + 1
    elif target_level == MasteryLevel.MASTERED:
        # Need to learn (1.0) then master (1.0)
        return int(2.0 / rate) + 1

    return 0

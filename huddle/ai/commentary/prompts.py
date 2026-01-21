"""
Commentary Prompt Templates

Prompt templates and serialization functions for play-by-play and color commentary.
Uses Gemini Flash API for generation.
"""

from typing import Optional

from .schema import (
    CommentaryContext,
    EnrichedPlay,
    NarrativeContext,
    NarrativeHook,
)


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

PLAY_BY_PLAY_SYSTEM = """You are a professional NFL play-by-play announcer. Your job is to describe
what just happened on the field in a clear, energetic, broadcast-ready style.

Guidelines:
- Be concise: 1-2 sentences max
- Lead with the action, then the result
- Use present tense for immediacy ("fires", "breaks", "goes")
- Include player names and jersey numbers naturally
- Match energy to the play (routine vs explosive)
- Never editorialize or add analysis - just describe

Examples of good play-by-play:
- "Mahomes fires to Kelce at the 30, first down Chiefs."
- "Handoff to Henry, cuts left, breaks a tackle at the 40, still going... finally brought down at the 28. Gain of 15."
- "Pass is... INTERCEPTED! Diggs picks it off at the goal line!"
"""

COLOR_COMMENTARY_SYSTEM = """You are a veteran NFL color commentator with deep knowledge of the game.
Your job is to add insight, context, and narrative to what just happened.

Guidelines:
- Build on what the play-by-play announcer just said (don't repeat the play description)
- Connect this moment to larger narratives (streaks, milestones, matchups)
- Offer tactical insight when relevant (why a play worked/failed)
- Keep it conversational but professional
- 2-4 sentences, natural broadcast rhythm
- Use narrative hooks provided - weave them in naturally
- Vary your openings (don't always start with "You know..." or "And...")

What makes great color commentary:
- Timing awareness ("That's huge with under two minutes left")
- Pattern recognition ("That's the third time they've gone to Kelce on third down")
- Historical context ("He hasn't dropped one all season until today")
- Matchup insight ("Watch how Jefferson keeps winning against single coverage")
"""


# =============================================================================
# SERIALIZATION FUNCTIONS
# =============================================================================

def serialize_play_for_prompt(play: EnrichedPlay) -> str:
    """Serialize play details for prompt context."""
    lines = []

    # Play type and outcome
    play_type = play.play_concept.play_type
    if play_type == "pass":
        if play.outcome == "complete":
            action = f"Pass complete to #{play.receiver.jersey_number} {play.receiver.name}" if play.receiver else "Pass complete"
        elif play.outcome == "incomplete":
            action = "Pass incomplete"
        elif play.outcome == "interception":
            action = "INTERCEPTION"
        elif play.outcome == "sack":
            action = f"SACK on {play.passer.name}" if play.passer else "SACK"
        else:
            action = f"Pass - {play.outcome}"
    elif play_type == "run":
        carrier = f"#{play.ball_carrier.jersey_number} {play.ball_carrier.name}" if play.ball_carrier else "Ball carrier"
        direction = play.play_concept.run_direction or ""
        action = f"Run {direction} by {carrier}".strip()
    else:
        action = f"{play_type.title()}"

    lines.append(f"Play: {action}")
    lines.append(f"Outcome: {play.outcome}")
    lines.append(f"Yards: {play.yards_gained:+.0f}")

    # Key participants
    participants = []
    if play.passer:
        participants.append(f"Passer: #{play.passer.jersey_number} {play.passer.name}")
    if play.receiver:
        participants.append(f"Receiver: #{play.receiver.jersey_number} {play.receiver.name}")
    if play.ball_carrier and play.play_concept.play_type == "run":
        participants.append(f"Runner: #{play.ball_carrier.jersey_number} {play.ball_carrier.name}")
    if play.tackler:
        participants.append(f"Tackler: #{play.tackler.jersey_number} {play.tackler.name}")
    if participants:
        lines.append("Key players: " + ", ".join(participants))

    # Key moments
    if play.key_events:
        lines.append(f"Key moments: {', '.join(play.key_events)}")

    # Passing details
    if play.play_concept.play_type == "pass" and play.outcome == "complete":
        details = []
        if play.air_yards is not None:
            details.append(f"air yards: {play.air_yards:.0f}")
        if play.yards_after_catch is not None:
            details.append(f"YAC: {play.yards_after_catch:.0f}")
        if play.was_contested:
            details.append("contested catch")
        if details:
            lines.append(f"Pass details: {', '.join(details)}")

    # Result flags
    flags = []
    if play.resulted_in_touchdown:
        flags.append("TOUCHDOWN")
    if play.resulted_in_first_down and not play.resulted_in_touchdown:
        flags.append("First down")
    if play.resulted_in_turnover:
        flags.append("TURNOVER")
    if play.was_explosive:
        flags.append("EXPLOSIVE PLAY")
    elif play.was_big_play:
        flags.append("Big play")
    if play.was_negative:
        flags.append("Loss of yards")
    if flags:
        lines.append(f"Result: {', '.join(flags)}")

    return "\n".join(lines)


def serialize_situation_for_prompt(play: EnrichedPlay) -> str:
    """Serialize game situation for prompt context."""
    sit = play.situation
    lines = []

    # Down and distance
    lines.append(f"Situation: {sit.down} & {sit.distance} at the {sit.field_position}")
    lines.append(f"Game: Q{sit.quarter}, {sit.time_remaining}")
    lines.append(f"Score: Home {sit.home_score}, Away {sit.away_score}")

    # Situational flags
    flags = []
    if sit.is_red_zone:
        flags.append("Red zone")
    if sit.is_goal_to_go:
        flags.append("Goal to go")
    if sit.is_two_minute_warning:
        flags.append("Two-minute warning")
    if sit.is_four_minute_offense:
        flags.append("Four-minute offense")
    if sit.is_hurry_up:
        flags.append("Hurry-up")
    if sit.is_fourth_down:
        flags.append("Fourth down")
    if flags:
        lines.append(f"Situation flags: {', '.join(flags)}")

    # Game context
    if sit.is_close_game:
        lines.append("Game context: Close game")
    elif sit.is_blowout:
        lines.append("Game context: Blowout")
    elif sit.is_comeback_territory:
        lines.append("Game context: Comeback territory")

    return "\n".join(lines)


def serialize_drive_for_prompt(play: EnrichedPlay) -> str:
    """Serialize drive context for prompt."""
    dc = play.drive_context
    lines = [
        f"Drive: Play #{dc.play_number_in_drive}",
        f"Drive progress: {dc.yards_this_drive:.0f} yards, started at {dc.starting_field_position}",
        f"Third downs: {dc.third_down_conversions}/{dc.third_down_attempts}",
    ]

    if dc.consecutive_first_downs > 1:
        lines.append(f"Momentum: {dc.consecutive_first_downs} consecutive first downs")
    if dc.plays_since_negative > 5:
        lines.append(f"Momentum: {dc.plays_since_negative} plays without negative yardage")

    return "\n".join(lines)


def serialize_narratives_for_prompt(
    narratives: NarrativeContext,
    hooks_to_use: Optional[list[str]] = None,
) -> str:
    """Serialize narrative hooks for color commentary prompt."""
    lines = []

    # Filter to requested hooks or use all high-priority ones
    hooks: list[NarrativeHook] = []
    if hooks_to_use:
        hooks = [h for h in narratives.active_hooks if h.headline in hooks_to_use]
    else:
        # Use top 3 by priority
        hooks = sorted(narratives.active_hooks, key=lambda h: h.priority, reverse=True)[:3]

    if hooks:
        lines.append("Narrative hooks to consider:")
        for hook in hooks:
            priority_label = "HIGH" if hook.priority > 0.7 else "MED" if hook.priority > 0.4 else "LOW"
            lines.append(f"- [{priority_label}] {hook.headline}: {hook.detail}")

    # Milestone proximity
    if narratives.milestones_in_range:
        lines.append("\nMilestones nearby:")
        for m in narratives.milestones_in_range[:2]:  # Top 2
            lines.append(f"- {m.player_name}: {m.yards_needed} yards from {m.significance}")

    # Active streaks
    if narratives.active_streaks:
        lines.append("\nActive streaks:")
        for s in narratives.active_streaks[:2]:
            streak_type = "hot" if s.is_positive else "cold"
            lines.append(f"- {s.player_name} ({streak_type}): {s.context}")

    # Matchup notes
    if narratives.relevant_matchups:
        lines.append("\nMatchup notes:")
        for m in narratives.relevant_matchups[:1]:
            lines.append(f"- {m.entity_a_name} vs {m.entity_b_name}: {m.narrative_angle}")

    return "\n".join(lines) if lines else "No specific narrative hooks for this play."


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_play_by_play_prompt(context: CommentaryContext) -> tuple[str, str]:
    """
    Build system and user prompts for play-by-play commentary.

    Returns:
        tuple[str, str]: (system_prompt, user_prompt)
    """
    play = context.play
    sit = play.situation

    # Build user prompt
    user_lines = [
        serialize_situation_for_prompt(play),
        "",
        serialize_play_for_prompt(play),
    ]

    # Add recent context if available
    if context.recent_plays_summary:
        user_lines.append("")
        user_lines.append("Recent plays:")
        for summary in context.recent_plays_summary[-3:]:
            user_lines.append(f"- {summary}")

    user_lines.append("")
    user_lines.append("Generate play-by-play call:")

    return PLAY_BY_PLAY_SYSTEM, "\n".join(user_lines)


def build_color_prompt(
    context: CommentaryContext,
    play_by_play: str,
) -> tuple[str, str]:
    """
    Build system and user prompts for color commentary.

    Args:
        context: Full commentary context
        play_by_play: The play-by-play call just generated

    Returns:
        tuple[str, str]: (system_prompt, user_prompt)
    """
    play = context.play
    sit = play.situation
    dc = play.drive_context

    # Score differential description
    diff = sit.score_differential
    if diff > 0:
        score_desc = f"leading by {diff}"
    elif diff < 0:
        score_desc = f"trailing by {abs(diff)}"
    else:
        score_desc = "tied"

    # Build user prompt
    user_lines = [
        f'Play just called: "{play_by_play}"',
        "",
        "Context:",
        f"- Situation: {sit.down} & {sit.distance}, {sit.field_position}, Q{sit.quarter} {sit.time_remaining}",
        f"- Score: Offense {score_desc}",
        f"- Drive: {dc.play_number_in_drive} plays, {dc.yards_this_drive:.0f} yards",
        "",
    ]

    # Add narrative context
    narrative_text = serialize_narratives_for_prompt(
        context.narratives,
        context.hooks_to_use if context.hooks_to_use else None,
    )
    user_lines.append(narrative_text)

    # Add guidance
    user_lines.append("")
    if context.suggested_focus:
        user_lines.append(f"Suggested focus: {context.suggested_focus}")
    user_lines.append(f"Energy level: {context.energy_level}")
    user_lines.append("")
    user_lines.append("Generate color commentary (2-4 sentences):")

    return COLOR_COMMENTARY_SYSTEM, "\n".join(user_lines)

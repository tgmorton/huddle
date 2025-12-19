"""
Player Approval System.

HC09-style approval tracking where player decisions affect morale and performance.
Each player has an approval rating (0-100) toward the coaching staff that affects:
- On-field performance modifiers
- Trade request likelihood
- Holdout risk

Approval is affected by:
- Depth chart changes (promotions/demotions)
- Team success (win/loss streaks)
- Contract negotiations
- Weekly drift toward baseline
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from huddle.core.models.player import Player


# =============================================================================
# Constants
# =============================================================================

# Approval thresholds
APPROVAL_MOTIVATED = 80      # Performance bonus threshold
APPROVAL_NEUTRAL = 50        # Baseline/default approval
APPROVAL_UNHAPPY = 40        # Trade request risk threshold
APPROVAL_DISGRUNTLED = 25    # Holdout risk threshold

# Performance modifiers at each tier
PERFORMANCE_MOTIVATED = 1.05     # +5% when highly motivated
PERFORMANCE_NEUTRAL = 1.0        # Normal
PERFORMANCE_UNHAPPY = 0.97       # -3% when unhappy
PERFORMANCE_DISGRUNTLED = 0.92   # -8% when disgruntled

# Weekly drift
BASELINE_APPROVAL = 50.0
DRIFT_RATE = 0.05  # 5% toward baseline per week


class ApprovalEvent(Enum):
    """Events that affect player approval."""
    # Depth chart events
    PROMOTED_STARTER = "promoted_starter"      # Became starter
    PROMOTED_BACKUP = "promoted_backup"        # Moved up in depth
    DEMOTED_BACKUP = "demoted_backup"          # Lost starting job
    DEMOTED_DEEP = "demoted_deep"              # Buried in depth chart

    # Team performance
    WIN = "win"
    LOSS = "loss"
    WIN_STREAK = "win_streak"
    LOSE_STREAK = "lose_streak"

    # Contract events
    CONTRACT_EXTENDED = "contract_extended"
    CONTRACT_DISPUTE = "contract_dispute"

    # Personal events
    PUBLIC_PRAISE = "public_praise"
    PUBLIC_CRITICISM = "public_criticism"

    # Game performance events (individual)
    BIG_PLAY_HERO = "big_play_hero"            # Made a game-changing play
    TD_CELEBRATION = "td_celebration"          # Scored and celebrated
    CRITICAL_DROP = "critical_drop"            # Dropped crucial pass
    COSTLY_TURNOVER = "costly_turnover"        # Fumble/INT at bad time
    GAME_WINNING_DRIVE = "game_winning_drive"  # Led clutch drive
    BLOWN_ASSIGNMENT = "blown_assignment"      # Gave up big play

    # Game aftermath events (team-wide)
    BIG_WIN = "big_win"                        # Significant team victory
    TOUGH_LOSS = "tough_loss"                  # Painful team defeat
    PLAYOFF_ELIMINATION = "playoff_elimination"  # Season ended
    PLAYOFF_ADVANCEMENT = "playoff_advancement"  # Moving on in playoffs
    DIVISION_CLINCH = "division_clinch"        # Clinched division title
    BLOWOUT_WIN = "blowout_win"                # Dominant victory
    BLOWOUT_LOSS = "blowout_loss"              # Embarrassing defeat


# Base impact values for each event (before personality modifiers)
EVENT_IMPACTS = {
    # Depth chart events
    ApprovalEvent.PROMOTED_STARTER: 15.0,
    ApprovalEvent.PROMOTED_BACKUP: 8.0,
    ApprovalEvent.DEMOTED_BACKUP: -12.0,
    ApprovalEvent.DEMOTED_DEEP: -20.0,

    # Team performance
    ApprovalEvent.WIN: 2.0,
    ApprovalEvent.LOSS: -2.0,
    ApprovalEvent.WIN_STREAK: 5.0,
    ApprovalEvent.LOSE_STREAK: -5.0,

    # Contract events
    ApprovalEvent.CONTRACT_EXTENDED: 20.0,
    ApprovalEvent.CONTRACT_DISPUTE: -15.0,

    # Personal events
    ApprovalEvent.PUBLIC_PRAISE: 10.0,
    ApprovalEvent.PUBLIC_CRITICISM: -12.0,

    # Game performance events (individual) - from Events Catalog
    ApprovalEvent.BIG_PLAY_HERO: 12.0,        # +8 to +15, use midpoint
    ApprovalEvent.TD_CELEBRATION: 7.0,         # +5 to +10
    ApprovalEvent.CRITICAL_DROP: -8.0,         # -5 to -12
    ApprovalEvent.COSTLY_TURNOVER: -15.0,      # -10 to -20
    ApprovalEvent.GAME_WINNING_DRIVE: 20.0,    # +15 to +25
    ApprovalEvent.BLOWN_ASSIGNMENT: -7.0,      # -5 to -10

    # Game aftermath events (team-wide) - from Events Catalog
    ApprovalEvent.BIG_WIN: 7.0,                # +5 to +10
    ApprovalEvent.TOUGH_LOSS: -7.0,            # -5 to -10
    ApprovalEvent.PLAYOFF_ELIMINATION: -15.0,  # -10 to -20
    ApprovalEvent.PLAYOFF_ADVANCEMENT: 12.0,   # Excitement of moving on
    ApprovalEvent.DIVISION_CLINCH: 10.0,       # Achievement feeling
    ApprovalEvent.BLOWOUT_WIN: 10.0,           # Domination feels good
    ApprovalEvent.BLOWOUT_LOSS: -12.0,         # Embarrassment hurts
}


# Events that are performance-related (get personality modifiers)
GAME_PERFORMANCE_EVENTS = {
    ApprovalEvent.BIG_PLAY_HERO,
    ApprovalEvent.TD_CELEBRATION,
    ApprovalEvent.CRITICAL_DROP,
    ApprovalEvent.COSTLY_TURNOVER,
    ApprovalEvent.GAME_WINNING_DRIVE,
    ApprovalEvent.BLOWN_ASSIGNMENT,
}

# Events that apply to the whole team
TEAM_WIDE_EVENTS = {
    ApprovalEvent.BIG_WIN,
    ApprovalEvent.TOUGH_LOSS,
    ApprovalEvent.PLAYOFF_ELIMINATION,
    ApprovalEvent.PLAYOFF_ADVANCEMENT,
    ApprovalEvent.DIVISION_CLINCH,
    ApprovalEvent.BLOWOUT_WIN,
    ApprovalEvent.BLOWOUT_LOSS,
}


# =============================================================================
# PlayerApproval Dataclass
# =============================================================================

@dataclass
class PlayerApproval:
    """
    Tracks a player's approval of the coaching staff.

    Approval affects:
    - Performance: motivated players get bonuses, unhappy players suffer penalties
    - Trade requests: low approval leads to trade demands
    - Holdouts: very low approval can cause contract holdouts
    """

    player_id: UUID
    approval: float = BASELINE_APPROVAL
    trend: float = 0.0  # Recent change direction (+/-)
    grievances: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        """Clamp approval to valid range."""
        self.approval = max(0.0, min(100.0, self.approval))

    def get_performance_modifier(self) -> float:
        """
        Get performance modifier based on current approval.

        Returns:
            Multiplier for player performance (0.92 to 1.05)
        """
        if self.approval >= APPROVAL_MOTIVATED:
            return PERFORMANCE_MOTIVATED
        elif self.approval >= APPROVAL_NEUTRAL:
            return PERFORMANCE_NEUTRAL
        elif self.approval >= APPROVAL_DISGRUNTLED:
            return PERFORMANCE_UNHAPPY
        else:
            return PERFORMANCE_DISGRUNTLED

    def get_mood_description(self) -> str:
        """Get text description of player's mood."""
        if self.approval >= APPROVAL_MOTIVATED:
            return "Motivated"
        elif self.approval >= 60:
            return "Content"
        elif self.approval >= APPROVAL_NEUTRAL:
            return "Neutral"
        elif self.approval >= APPROVAL_UNHAPPY:
            return "Unhappy"
        elif self.approval >= APPROVAL_DISGRUNTLED:
            return "Frustrated"
        else:
            return "Disgruntled"

    def is_trade_candidate(self) -> bool:
        """Check if player may request a trade."""
        return self.approval < APPROVAL_UNHAPPY

    def is_holdout_risk(self) -> bool:
        """Check if player may hold out of practice/games."""
        return self.approval < APPROVAL_DISGRUNTLED

    def apply_change(self, amount: float, reason: Optional[str] = None) -> float:
        """
        Apply an approval change.

        Args:
            amount: Change amount (positive or negative)
            reason: Optional reason to record in grievances

        Returns:
            New approval value
        """
        old_approval = self.approval
        self.approval = max(0.0, min(100.0, self.approval + amount))

        # Track trend (exponential moving average)
        self.trend = 0.7 * self.trend + 0.3 * amount

        # Record significant negative events as grievances
        if amount < -10 and reason:
            self.grievances.append(reason)
            # Keep only recent grievances
            if len(self.grievances) > 5:
                self.grievances = self.grievances[-5:]

        self.last_updated = datetime.now()

        return self.approval

    def apply_weekly_drift(self, team_winning: bool = False, team_losing: bool = False) -> float:
        """
        Apply weekly drift toward baseline.

        Approval naturally moves toward 50 over time.
        Team success/failure affects the effective baseline.

        Args:
            team_winning: Team is on a winning streak
            team_losing: Team is on a losing streak

        Returns:
            New approval value
        """
        # Calculate drift toward baseline
        diff = BASELINE_APPROVAL - self.approval
        change = diff * DRIFT_RATE

        # Team success/failure affects drift
        if team_winning:
            change += 1.0  # Winning cures many ills
        elif team_losing:
            change -= 1.0  # Losing breeds discontent

        return self.apply_change(change)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "player_id": str(self.player_id),
            "approval": self.approval,
            "trend": self.trend,
            "grievances": self.grievances,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlayerApproval":
        """Create from dictionary."""
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])

        return cls(
            player_id=UUID(data["player_id"]),
            approval=data.get("approval", BASELINE_APPROVAL),
            trend=data.get("trend", 0.0),
            grievances=data.get("grievances", []),
            last_updated=last_updated,
        )


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_approval_change(
    player: "Player",
    event: ApprovalEvent,
    magnitude: float = 1.0,
) -> float:
    """
    Calculate approval change for an event, applying personality modifiers.

    Args:
        player: The player affected
        event: The type of event
        magnitude: Multiplier for event impact (e.g., 2.0 for "much worse" demotion)

    Returns:
        Approval change amount (positive or negative)
    """
    base_impact = EVENT_IMPACTS.get(event, 0.0) * magnitude

    if base_impact == 0:
        return 0.0

    # Apply personality modifiers if player has personality
    if player.personality:
        from huddle.core.personality import Trait

        sensitivity = player.personality.get_morale_sensitivity()

        if base_impact > 0:
            # Positive events
            if player.personality.prefers_praise():
                base_impact *= 1.3  # Responds well to good news
        else:
            # Negative events
            if player.personality.prefers_criticism():
                base_impact *= 0.7  # Takes criticism well
            else:
                base_impact *= sensitivity  # Sensitive players react more strongly

        # Special handling for game performance events
        # DRAMATIC = 1.5x amplification, LEVEL_HEADED = 0.6x dampening
        if event in GAME_PERFORMANCE_EVENTS:
            # DRAMATIC players feel everything more intensely during games
            if player.personality.is_trait_strong(Trait.DRAMATIC):
                base_impact *= 1.5

            # LEVEL_HEADED players stay emotionally stable
            if player.personality.is_trait_strong(Trait.LEVEL_HEADED):
                base_impact *= 0.6

            # COMPETITIVE players feel losses harder but wins feel great
            if player.personality.is_trait_strong(Trait.COMPETITIVE):
                if base_impact < 0:
                    base_impact *= 1.2  # Losses sting more
                else:
                    base_impact *= 1.1  # Wins feel sweeter

        # Additional trait modifiers for demotions
        if event in (ApprovalEvent.DEMOTED_BACKUP, ApprovalEvent.DEMOTED_DEEP):
            # Ambitious players especially upset by demotions
            if player.personality.is_trait_strong(Trait.AMBITIOUS):
                base_impact *= 1.2

            # Competitive players hate losing their spot
            if player.personality.is_trait_strong(Trait.COMPETITIVE):
                base_impact *= 1.15

            # Team players are more understanding
            if player.personality.is_trait_strong(Trait.TEAM_PLAYER):
                base_impact *= 0.85

            # Loyal players give benefit of the doubt
            if player.personality.is_trait_strong(Trait.LOYAL):
                base_impact *= 0.9

    # Age modifier for demotions (applies regardless of personality)
    if event in (ApprovalEvent.DEMOTED_BACKUP, ApprovalEvent.DEMOTED_DEEP):
        # Veterans take demotions harder
        if player.age >= 28:
            base_impact *= 1.3

    return base_impact


def apply_approval_event(
    player: "Player",
    event: ApprovalEvent,
    magnitude: float = 1.0,
    reason: Optional[str] = None,
) -> float:
    """
    Apply an approval event to a player.

    Creates PlayerApproval if player doesn't have one.

    Args:
        player: The player affected
        event: The type of event
        magnitude: Multiplier for event impact
        reason: Optional reason string

    Returns:
        New approval value
    """
    # Ensure player has approval tracking
    if not hasattr(player, 'approval') or player.approval is None:
        player.approval = PlayerApproval(player_id=player.id)

    # Calculate personality-adjusted change
    change = calculate_approval_change(player, event, magnitude)

    # Apply the change
    return player.approval.apply_change(change, reason)


def get_depth_chart_event(old_depth: int, new_depth: int) -> Optional[ApprovalEvent]:
    """
    Determine the approval event for a depth chart change.

    Args:
        old_depth: Previous depth position (1 = starter)
        new_depth: New depth position

    Returns:
        ApprovalEvent or None if no significant change
    """
    if new_depth == old_depth:
        return None

    # Promotion (lower number = higher on depth chart)
    if new_depth < old_depth:
        if new_depth == 1:
            return ApprovalEvent.PROMOTED_STARTER
        else:
            return ApprovalEvent.PROMOTED_BACKUP

    # Demotion
    else:
        if old_depth == 1:
            return ApprovalEvent.DEMOTED_BACKUP  # Lost starting job
        elif new_depth >= 3:
            return ApprovalEvent.DEMOTED_DEEP    # Buried in depth chart
        else:
            return ApprovalEvent.DEMOTED_BACKUP  # Minor demotion


def create_player_approval(player_id: UUID, initial_approval: float = BASELINE_APPROVAL) -> PlayerApproval:
    """
    Create a new PlayerApproval instance.

    Args:
        player_id: The player's UUID
        initial_approval: Starting approval value (default 50)

    Returns:
        New PlayerApproval instance
    """
    return PlayerApproval(
        player_id=player_id,
        approval=initial_approval,
        last_updated=datetime.now(),
    )


# =============================================================================
# Post-Game Event Functions
# =============================================================================

def apply_team_event(
    players: List["Player"],
    event: ApprovalEvent,
    magnitude: float = 1.0,
    reason: Optional[str] = None,
) -> Dict[UUID, float]:
    """
    Apply a team-wide event to multiple players.

    Args:
        players: List of players to affect
        event: The team event type
        magnitude: Multiplier for event impact
        reason: Optional reason string

    Returns:
        Dict mapping player_id -> new approval value
    """
    results = {}
    for player in players:
        new_approval = apply_approval_event(player, event, magnitude, reason)
        results[player.id] = new_approval
    return results


def determine_game_aftermath_event(
    score_diff: int,
    is_playoff: bool = False,
    is_division_clinch: bool = False,
    is_elimination: bool = False,
) -> ApprovalEvent:
    """
    Determine the appropriate team-wide event based on game result.

    Args:
        score_diff: Point differential (positive = win)
        is_playoff: Whether this was a playoff game
        is_division_clinch: Whether this game clinched division
        is_elimination: Whether this loss ends the season

    Returns:
        Appropriate ApprovalEvent for team-wide application
    """
    if is_elimination:
        return ApprovalEvent.PLAYOFF_ELIMINATION

    if is_division_clinch:
        return ApprovalEvent.DIVISION_CLINCH

    if is_playoff and score_diff > 0:
        return ApprovalEvent.PLAYOFF_ADVANCEMENT

    # Regular game results based on score differential
    if score_diff > 0:
        if score_diff >= 21:
            return ApprovalEvent.BLOWOUT_WIN
        elif score_diff >= 7:
            return ApprovalEvent.BIG_WIN
        else:
            return ApprovalEvent.WIN
    else:
        if score_diff <= -21:
            return ApprovalEvent.BLOWOUT_LOSS
        elif score_diff <= -7:
            return ApprovalEvent.TOUGH_LOSS
        else:
            return ApprovalEvent.LOSS


def apply_post_game_morale(
    players: List["Player"],
    score_diff: int,
    is_playoff: bool = False,
    is_division_clinch: bool = False,
    is_elimination: bool = False,
    individual_performances: Optional[Dict[UUID, ApprovalEvent]] = None,
) -> Dict[UUID, float]:
    """
    Apply post-game morale updates to a team.

    Applies team-wide event to all players, then individual performance
    events to specific players.

    Args:
        players: List of players on the team
        score_diff: Point differential (positive = win)
        is_playoff: Whether this was a playoff game
        is_division_clinch: Whether this game clinched division
        is_elimination: Whether this loss ends the season
        individual_performances: Optional dict of player_id -> performance event
            (e.g., {uuid: ApprovalEvent.BIG_PLAY_HERO})

    Returns:
        Dict mapping player_id -> final approval value

    Example:
        # Apply post-game morale after a 14-point win
        results = apply_post_game_morale(
            players=team.roster,
            score_diff=14,  # Won by 14
            individual_performances={
                qb.id: ApprovalEvent.GAME_WINNING_DRIVE,
                rb.id: ApprovalEvent.BIG_PLAY_HERO,
                cb.id: ApprovalEvent.BLOWN_ASSIGNMENT,
            }
        )
    """
    results = {}

    # 1. Determine and apply team-wide event
    team_event = determine_game_aftermath_event(
        score_diff=score_diff,
        is_playoff=is_playoff,
        is_division_clinch=is_division_clinch,
        is_elimination=is_elimination,
    )

    for player in players:
        apply_approval_event(player, team_event)
        results[player.id] = player.approval.approval if player.approval else BASELINE_APPROVAL

    # 2. Apply individual performance events on top
    if individual_performances:
        for player in players:
            if player.id in individual_performances:
                perf_event = individual_performances[player.id]
                apply_approval_event(player, perf_event)
                results[player.id] = player.approval.approval

    return results


def get_individual_performance_events(
    game_stats: Dict[UUID, dict],
) -> Dict[UUID, List[ApprovalEvent]]:
    """
    Analyze game stats to determine individual performance events.

    This is a helper that can be customized based on how game stats are tracked.
    The implementation converts raw stats into approval events.

    Args:
        game_stats: Dict of player_id -> stat dict
            Expected stat keys: touchdowns, turnovers, big_plays, blown_plays

    Returns:
        Dict mapping player_id -> list of ApprovalEvent to apply

    Example:
        stats = {
            qb_id: {"touchdowns": 3, "turnovers": 0, "big_plays": 2},
            wr_id: {"touchdowns": 2, "drops": 1},
            cb_id: {"turnovers_forced": 0, "blown_plays": 2},
        }
        events = get_individual_performance_events(stats)
        # events[qb_id] = [ApprovalEvent.TD_CELEBRATION, ApprovalEvent.BIG_PLAY_HERO]
    """
    results = {}

    for player_id, stats in game_stats.items():
        events = []

        # Touchdowns
        tds = stats.get("touchdowns", 0)
        if tds >= 1:
            events.append(ApprovalEvent.TD_CELEBRATION)
        if tds >= 3:  # Multi-TD game is heroic
            events.append(ApprovalEvent.BIG_PLAY_HERO)

        # Big plays
        big_plays = stats.get("big_plays", 0)
        if big_plays >= 2:
            events.append(ApprovalEvent.BIG_PLAY_HERO)

        # Game winning drive (QB-specific typically)
        if stats.get("game_winning_drive", False):
            events.append(ApprovalEvent.GAME_WINNING_DRIVE)

        # Negative events
        turnovers = stats.get("turnovers", 0)
        if turnovers >= 1:
            events.append(ApprovalEvent.COSTLY_TURNOVER)

        drops = stats.get("drops", 0) + stats.get("critical_drops", 0)
        if drops >= 1:
            events.append(ApprovalEvent.CRITICAL_DROP)

        blown_plays = stats.get("blown_plays", 0) + stats.get("blown_assignments", 0)
        if blown_plays >= 2:
            events.append(ApprovalEvent.BLOWN_ASSIGNMENT)

        if events:
            results[player_id] = events

    return results

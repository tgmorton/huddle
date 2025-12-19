"""Game-level state that persists across plays.

Tracks information that affects AI decision-making across plays within a game:
- Play history for tendency detection
- Player confidence/momentum
- Game situation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class PlayRecord:
    """Record of a single play."""
    play_type: str         # "run", "pass", "screen", "play_action"
    success: bool          # Did the play gain positive yards / first down
    yards: int             # Yards gained/lost
    timestamp: float = 0.0 # When the play occurred

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class PlayHistory:
    """Track recent plays for tendency analysis.

    Used by defensive brains to detect offensive tendencies and bias
    their reads accordingly. Implements recency bias - recent plays
    affect how defenders interpret ambiguous reads.
    """
    recent_plays: List[PlayRecord] = field(default_factory=list)
    max_history: int = 10

    def record_play(self, play_type: str, success: bool, yards: int) -> None:
        """Record a completed play.

        Args:
            play_type: Type of play ("run", "pass", "screen", "play_action")
            success: Whether the play was successful
            yards: Yards gained/lost
        """
        self.recent_plays.append(PlayRecord(
            play_type=play_type,
            success=success,
            yards=yards,
        ))
        if len(self.recent_plays) > self.max_history:
            self.recent_plays.pop(0)

    def get_tendency(self, last_n: int = 5) -> dict:
        """Calculate run/pass tendency from recent plays.

        Returns:
            {
                'run_bias': float,   # -0.15 to +0.15, positive = run-heavy
                'pass_bias': float,  # -0.15 to +0.15, positive = pass-heavy
                'run_count': int,
                'pass_count': int,
            }
        """
        recent = self.recent_plays[-last_n:] if self.recent_plays else []
        if not recent:
            return {
                'run_bias': 0.0,
                'pass_bias': 0.0,
                'run_count': 0,
                'pass_count': 0,
            }

        runs = sum(1 for p in recent if p.play_type == 'run')
        passes = sum(1 for p in recent if p.play_type in ('pass', 'play_action'))

        total = len(recent)
        run_pct = runs / total
        pass_pct = passes / total

        # Bias is deviation from 50/50, scaled to max ±0.15
        return {
            'run_bias': (run_pct - 0.5) * 0.3,   # Max ±0.15 bias
            'pass_bias': (pass_pct - 0.5) * 0.3,
            'run_count': runs,
            'pass_count': passes,
        }

    def get_recent_big_plays_against(self, min_yards: int = 15) -> int:
        """Count recent big plays (for defensive aggression adjustment).

        Args:
            min_yards: Minimum yards for a "big play"

        Returns:
            Count of big plays in recent history
        """
        return sum(1 for p in self.recent_plays[-5:] if p.yards >= min_yards)

    def clear(self) -> None:
        """Clear history (e.g., at start of new game)."""
        self.recent_plays.clear()


@dataclass
class GameSituation:
    """Current game situation for context-aware decisions.

    Affects things like ball security, aggressiveness, clock management.
    """
    quarter: int = 1
    time_remaining: float = 900.0  # Seconds remaining in quarter
    score_differential: int = 0    # Positive = winning
    timeouts_remaining: int = 3
    is_two_minute_warning: bool = False

    @property
    def is_close_game(self) -> bool:
        """Is the game within one score?"""
        return abs(self.score_differential) <= 8

    @property
    def is_late_game(self) -> bool:
        """Is it late in the 4th quarter with a close game?"""
        return self.quarter == 4 and self.time_remaining < 300 and self.is_close_game

    @property
    def should_protect_ball(self) -> bool:
        """Should ballcarrier prioritize ball security?"""
        # Protect when winning close in 4th, or always in red zone when ahead
        if self.quarter == 4 and self.score_differential > 0:
            return True
        return False

    @property
    def should_be_aggressive(self) -> bool:
        """Should take more risks?"""
        # Be aggressive when losing late
        if self.quarter >= 3 and self.score_differential < -8:
            return True
        return False

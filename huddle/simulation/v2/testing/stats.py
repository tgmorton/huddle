"""Statistical analysis for simulation testing.

Aggregates metrics across multiple scenario runs to identify
patterns and verify behavior is realistic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import defaultdict
import statistics

from .scenario import ScenarioResult
from .logger import PlayLogger


@dataclass
class PlayStats:
    """Statistics from a single play."""
    # Timing
    duration: float = 0.0
    time_to_throw: Optional[float] = None
    time_in_air: Optional[float] = None

    # Route stats
    route_depth_at_break: Optional[float] = None
    separation_at_break: Optional[float] = None
    separation_at_catch: Optional[float] = None
    max_separation: float = 0.0
    min_separation: float = float("inf")

    # Coverage stats
    db_reaction_time: Optional[float] = None  # Time to react to break
    db_speed_through_break: Optional[float] = None

    # Pass stats
    throw_distance: Optional[float] = None
    throw_accuracy: Optional[float] = None  # 0-1
    catch_result: Optional[str] = None  # complete/incomplete/int

    # Movement stats
    receiver_top_speed: float = 0.0
    db_top_speed: float = 0.0
    receiver_total_distance: float = 0.0

    @classmethod
    def from_logger(
        cls,
        logger: PlayLogger,
        receiver_id: str = "WR1",
        defender_id: str = "CB1",
    ) -> PlayStats:
        """Extract stats from a play log."""
        stats = PlayStats()

        if not logger.ticks:
            return stats

        stats.duration = logger.ticks[-1].time

        # Track positions over time
        prev_r_pos = None
        prev_d_pos = None

        for tick in logger.ticks:
            # Find receiver and defender
            r_snap = None
            d_snap = None
            for p in tick.offense:
                if p.id == receiver_id:
                    r_snap = p
            for p in tick.defense:
                if p.id == defender_id:
                    d_snap = p

            if r_snap:
                stats.receiver_top_speed = max(stats.receiver_top_speed, r_snap.speed)
                if prev_r_pos:
                    from ..core.vec2 import Vec2
                    dist = Vec2(r_snap.pos[0] - prev_r_pos[0],
                               r_snap.pos[1] - prev_r_pos[1]).length()
                    stats.receiver_total_distance += dist
                prev_r_pos = r_snap.pos

            if d_snap:
                stats.db_top_speed = max(stats.db_top_speed, d_snap.speed)
                prev_d_pos = d_snap.pos

            # Separation
            if r_snap and d_snap:
                from ..core.vec2 import Vec2
                r_pos = Vec2(r_snap.pos[0], r_snap.pos[1])
                d_pos = Vec2(d_snap.pos[0], d_snap.pos[1])
                sep = r_pos.distance_to(d_pos)
                stats.max_separation = max(stats.max_separation, sep)
                stats.min_separation = min(stats.min_separation, sep)

        # Extract from events
        for event in logger.events:
            if event.type.value == "throw":
                stats.time_to_throw = event.time
            elif event.type.value == "catch":
                stats.catch_result = "complete"
                if stats.time_to_throw:
                    stats.time_in_air = event.time - stats.time_to_throw
            elif event.type.value == "incomplete":
                stats.catch_result = "incomplete"
            elif event.type.value == "interception":
                stats.catch_result = "interception"
            elif event.type.value == "route_break":
                stats.route_depth_at_break = event.data.get("depth")

        return stats


@dataclass
class AggregateStats:
    """Aggregated statistics across multiple plays."""
    play_count: int = 0

    # Completion rates
    completions: int = 0
    incompletions: int = 0
    interceptions: int = 0

    # Separation (yards)
    avg_separation_at_catch: float = 0.0
    avg_max_separation: float = 0.0
    avg_min_separation: float = 0.0

    # Timing (seconds)
    avg_time_to_throw: float = 0.0
    avg_time_in_air: float = 0.0

    # Speed (yards/sec)
    avg_receiver_top_speed: float = 0.0
    avg_db_top_speed: float = 0.0

    # Distributions (for analysis)
    separation_distribution: List[float] = field(default_factory=list)
    completion_by_separation: Dict[str, int] = field(default_factory=dict)

    def completion_rate(self) -> float:
        """Calculate completion percentage."""
        total = self.completions + self.incompletions + self.interceptions
        if total == 0:
            return 0.0
        return self.completions / total

    def interception_rate(self) -> float:
        """Calculate interception percentage."""
        total = self.completions + self.incompletions + self.interceptions
        if total == 0:
            return 0.0
        return self.interceptions / total

    def format_report(self) -> str:
        """Format a human-readable report."""
        lines = [
            "=" * 50,
            "AGGREGATE STATISTICS",
            f"Plays analyzed: {self.play_count}",
            "=" * 50,
            "",
            "COMPLETION RATES:",
            f"  Completions: {self.completions} ({self.completion_rate():.1%})",
            f"  Incompletions: {self.incompletions}",
            f"  Interceptions: {self.interceptions} ({self.interception_rate():.1%})",
            "",
            "SEPARATION (yards):",
            f"  Avg at catch: {self.avg_separation_at_catch:.2f}",
            f"  Avg max: {self.avg_max_separation:.2f}",
            f"  Avg min: {self.avg_min_separation:.2f}",
            "",
            "TIMING (seconds):",
            f"  Avg time to throw: {self.avg_time_to_throw:.2f}",
            f"  Avg ball in air: {self.avg_time_in_air:.2f}",
            "",
            "SPEED (yards/sec):",
            f"  Avg receiver top speed: {self.avg_receiver_top_speed:.1f}",
            f"  Avg DB top speed: {self.avg_db_top_speed:.1f}",
        ]

        return "\n".join(lines)


def aggregate_stats(results: List[ScenarioResult]) -> AggregateStats:
    """Aggregate statistics from multiple scenario results."""
    agg = AggregateStats()
    agg.play_count = len(results)

    if not results:
        return agg

    # Collect individual stats
    all_stats = []
    for result in results:
        if result.logger:
            stats = PlayStats.from_logger(result.logger)
            all_stats.append(stats)

            # Count outcomes
            if stats.catch_result == "complete":
                agg.completions += 1
            elif stats.catch_result == "incomplete":
                agg.incompletions += 1
            elif stats.catch_result == "interception":
                agg.interceptions += 1

            # Track separation distribution
            if stats.max_separation > 0:
                agg.separation_distribution.append(stats.max_separation)

    if not all_stats:
        return agg

    # Calculate averages
    def safe_avg(values: List[float]) -> float:
        valid = [v for v in values if v is not None and v > 0]
        return statistics.mean(valid) if valid else 0.0

    agg.avg_max_separation = safe_avg([s.max_separation for s in all_stats])
    agg.avg_min_separation = safe_avg([s.min_separation for s in all_stats
                                       if s.min_separation < float("inf")])
    agg.avg_time_to_throw = safe_avg([s.time_to_throw for s in all_stats])
    agg.avg_time_in_air = safe_avg([s.time_in_air for s in all_stats])
    agg.avg_receiver_top_speed = safe_avg([s.receiver_top_speed for s in all_stats])
    agg.avg_db_top_speed = safe_avg([s.db_top_speed for s in all_stats])

    return agg


# =============================================================================
# Analysis helpers
# =============================================================================

def analyze_route_execution(logger: PlayLogger, receiver_id: str = "WR1") -> Dict[str, Any]:
    """Analyze how well a route was executed."""
    analysis = {
        "total_distance": 0.0,
        "top_speed": 0.0,
        "time_to_break": None,
        "depth_at_break": None,
        "phases": [],
    }

    prev_pos = None
    for tick in logger.ticks:
        for p in tick.offense:
            if p.id == receiver_id:
                analysis["top_speed"] = max(analysis["top_speed"], p.speed)
                if prev_pos:
                    from ..core.vec2 import Vec2
                    dist = Vec2(p.pos[0] - prev_pos[0], p.pos[1] - prev_pos[1]).length()
                    analysis["total_distance"] += dist
                prev_pos = p.pos

    # Extract from events
    for event in logger.events:
        if event.type.value == "route_break" and event.player_id == receiver_id:
            analysis["time_to_break"] = event.time
            analysis["depth_at_break"] = event.data.get("depth")

    return analysis


def analyze_coverage_performance(
    logger: PlayLogger,
    receiver_id: str = "WR1",
    defender_id: str = "CB1",
) -> Dict[str, Any]:
    """Analyze how well coverage was executed."""
    analysis = {
        "initial_cushion": None,
        "separation_at_break": None,
        "separation_at_catch": None,
        "max_separation": 0.0,
        "min_separation": float("inf"),
        "reaction_delay_ticks": None,
    }

    # Get separation over time
    separations = logger.get_separation_over_time(receiver_id, defender_id)
    if separations:
        analysis["initial_cushion"] = separations[0][1]
        analysis["max_separation"] = max(s[1] for s in separations)
        analysis["min_separation"] = min(s[1] for s in separations)

    # Find break time
    break_time = None
    for event in logger.events:
        if event.type.value == "route_break" and event.player_id == receiver_id:
            break_time = event.time
            # Find separation at this time
            for time, sep in separations:
                if abs(time - break_time) < 0.1:
                    analysis["separation_at_break"] = sep
                    break

    return analysis


def compare_attribute_impact(
    results_by_attribute: Dict[int, List[ScenarioResult]],
    attribute_name: str,
) -> str:
    """Compare how an attribute affects outcomes."""
    lines = [
        f"ATTRIBUTE IMPACT ANALYSIS: {attribute_name}",
        "=" * 50,
    ]

    for attr_value, results in sorted(results_by_attribute.items()):
        agg = aggregate_stats(results)
        lines.append(
            f"{attribute_name}={attr_value}: "
            f"Comp%={agg.completion_rate():.1%}, "
            f"Avg Sep={agg.avg_max_separation:.1f}yd, "
            f"n={agg.play_count}"
        )

    return "\n".join(lines)

#!/usr/bin/env python3
"""
V2 Simulation Verification Test Script

Tests:
1. Phase transition bug fix - run several games, confirm no crashes
2. Run game variance - check if blocking quality affects outcomes
3. Aggregate stats collection (completion rate, sack rate, yards per play, TD rate)

Run: python verify_v2_fixes.py
"""

import sys
sys.path.insert(0, '.')

import asyncio
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Import simulation components
from huddle.api.routers.v2_sim import (
    session_manager, V2SimSession, SimulationConfig, PlayerConfig,
    create_run_play_session, create_pass_play_session, run_play_to_completion,
    drive_manager, StartDriveRequest, DriveState, Drive, DriveStatus,
)
from huddle.simulation.v2.core.phases import PlayPhase
from huddle.simulation.v2.resolution.blocking import get_play_blocking_quality


@dataclass
class PlayResult:
    """Result of a single play."""
    play_type: str  # "run" or "pass"
    outcome: str  # "complete", "incomplete", "interception", "sack", "tackle"
    yards_gained: int
    blocking_quality: Optional[str] = None  # For run plays
    is_touchdown: bool = False
    is_turnover: bool = False
    phase_crash: bool = False  # Did we hit a phase transition error?


@dataclass
class DriveResults:
    """Results from a full drive."""
    plays: List[PlayResult] = field(default_factory=list)
    total_yards: int = 0
    result: str = ""  # "touchdown", "turnover", "turnover_on_downs", "punt"


@dataclass
class GameStats:
    """Aggregate stats from multiple plays."""
    # Counts
    total_plays: int = 0
    run_plays: int = 0
    pass_plays: int = 0

    # Outcomes
    completions: int = 0
    incompletions: int = 0
    interceptions: int = 0
    sacks: int = 0
    run_stuffs: int = 0  # Runs for loss
    run_no_gains: int = 0  # Runs for 0 yards
    touchdowns: int = 0

    # Yards
    total_yards: int = 0
    pass_yards: int = 0
    run_yards: int = 0
    run_yards_list: List[int] = field(default_factory=list)

    # Blocking quality breakdown (run plays)
    great_blocks: int = 0
    avg_blocks: int = 0
    poor_blocks: int = 0
    yards_by_blocking: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))

    # Phase crashes (should be 0 after fix)
    phase_crashes: int = 0

    def add_play(self, result: PlayResult):
        """Add a play result to the stats."""
        self.total_plays += 1

        if result.phase_crash:
            self.phase_crashes += 1

        if result.play_type == "run":
            self.run_plays += 1
            self.run_yards += result.yards_gained
            self.run_yards_list.append(result.yards_gained)
            self.total_yards += result.yards_gained

            if result.yards_gained < 0:
                self.run_stuffs += 1
            elif result.yards_gained == 0:
                self.run_no_gains += 1

            if result.blocking_quality:
                if result.blocking_quality == "great":
                    self.great_blocks += 1
                elif result.blocking_quality == "poor":
                    self.poor_blocks += 1
                else:
                    self.avg_blocks += 1
                self.yards_by_blocking[result.blocking_quality].append(result.yards_gained)

        else:  # pass
            self.pass_plays += 1

            if result.outcome == "complete":
                self.completions += 1
                self.pass_yards += result.yards_gained
                self.total_yards += result.yards_gained
            elif result.outcome == "incomplete":
                self.incompletions += 1
            elif result.outcome == "interception":
                self.interceptions += 1
            elif result.outcome == "sack":
                self.sacks += 1
                self.total_yards += result.yards_gained  # Negative

        if result.is_touchdown:
            self.touchdowns += 1

    def completion_rate(self) -> float:
        """Calculate pass completion percentage."""
        attempts = self.completions + self.incompletions + self.interceptions
        if attempts == 0:
            return 0.0
        return 100.0 * self.completions / attempts

    def sack_rate(self) -> float:
        """Calculate sack rate per dropback."""
        dropbacks = self.pass_plays
        if dropbacks == 0:
            return 0.0
        return 100.0 * self.sacks / dropbacks

    def yards_per_play(self) -> float:
        """Calculate yards per play."""
        if self.total_plays == 0:
            return 0.0
        return self.total_yards / self.total_plays

    def run_ypc(self) -> float:
        """Calculate rushing yards per carry."""
        if self.run_plays == 0:
            return 0.0
        return self.run_yards / self.run_plays

    def stuff_rate(self) -> float:
        """Calculate percentage of runs for loss."""
        if self.run_plays == 0:
            return 0.0
        return 100.0 * self.run_stuffs / self.run_plays

    def no_gain_rate(self) -> float:
        """Calculate percentage of runs for 0 yards."""
        if self.run_plays == 0:
            return 0.0
        return 100.0 * self.run_no_gains / self.run_plays


async def run_single_play(play_type: str = "run", concept: str = None) -> PlayResult:
    """Run a single play and return results."""
    try:
        if play_type == "run":
            concept = concept or random.choice([
                "inside_zone_right", "inside_zone_left",
                "outside_zone_right", "outside_zone_left",
                "power_right", "power_left",
            ])
            session = await create_run_play_session(concept, "cover_3")
        else:
            concept = concept or random.choice([
                "mesh", "smash", "four_verts", "slants", "curls",
            ])
            session = await create_pass_play_session(concept, "cover_3")

        # Run play to completion
        result = await run_play_to_completion(session)

        # Get blocking quality AFTER the play runs (it's set at snap)
        blocking_quality = None
        if play_type == "run":
            blocking_quality = getattr(session.orchestrator, '_play_blocking_quality', 'average')

        return PlayResult(
            play_type=play_type,
            outcome=result.get("outcome", "unknown"),
            yards_gained=result.get("yards_gained", 0),
            blocking_quality=blocking_quality,
            is_touchdown=result.get("is_touchdown", False),
            is_turnover=result.get("is_turnover", False),
            phase_crash=False,
        )

    except Exception as e:
        error_msg = str(e)
        is_phase_crash = "Invalid transition" in error_msg or "phase" in error_msg.lower()

        if is_phase_crash:
            print(f"  ** PHASE CRASH: {error_msg[:80]}")
        else:
            print(f"  ** ERROR: {error_msg[:80]}")

        return PlayResult(
            play_type=play_type,
            outcome="error",
            yards_gained=0,
            phase_crash=is_phase_crash,
        )


async def run_game_simulation(num_plays: int = 20) -> GameStats:
    """Run a full game simulation with mixed play types."""
    stats = GameStats()

    for i in range(num_plays):
        # Mix of run (50%) and pass (50%) plays
        play_type = "run" if random.random() < 0.5 else "pass"
        result = await run_single_play(play_type)
        stats.add_play(result)

    return stats


async def run_focused_run_test(num_plays: int = 100) -> GameStats:
    """Run focused test on run plays to analyze variance."""
    stats = GameStats()

    concepts = [
        "inside_zone_right", "inside_zone_left",
        "outside_zone_right", "outside_zone_left",
        "power_right", "power_left",
    ]

    for i in range(num_plays):
        concept = concepts[i % len(concepts)]
        result = await run_single_play("run", concept)
        stats.add_play(result)

        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{num_plays} run plays completed...")

    return stats


def print_report(stats: GameStats, title: str = "SIMULATION RESULTS"):
    """Print formatted stats report."""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    print(f"\nTotal Plays: {stats.total_plays}")
    print(f"  Run plays: {stats.run_plays}")
    print(f"  Pass plays: {stats.pass_plays}")

    print(f"\nPhase Crashes: {stats.phase_crashes}")
    if stats.phase_crashes > 0:
        print("  ** WARNING: Phase transition bugs detected! **")
    else:
        print("  Phase transition fix VERIFIED - no crashes")

    print(f"\n--- PASSING STATS ---")
    if stats.pass_plays > 0:
        print(f"  Completion Rate: {stats.completion_rate():.1f}% ({stats.completions}/{stats.completions + stats.incompletions + stats.interceptions})")
        print(f"  Sack Rate: {stats.sack_rate():.1f}% ({stats.sacks} sacks)")
        print(f"  Interceptions: {stats.interceptions}")
    else:
        print("  No pass plays")

    print(f"\n--- RUSHING STATS ---")
    if stats.run_plays > 0:
        print(f"  Yards Per Carry: {stats.run_ypc():.2f} (target: 4.5)")
        print(f"  Stuff Rate (loss): {stats.stuff_rate():.1f}% (target: 8.7%)")
        print(f"  No Gain Rate: {stats.no_gain_rate():.1f}% (target: 8.4%)")

        # Distribution
        if stats.run_yards_list:
            yards = stats.run_yards_list
            negative = sum(1 for y in yards if y < 0)
            zero = sum(1 for y in yards if y == 0)
            short = sum(1 for y in yards if 1 <= y <= 3)
            medium = sum(1 for y in yards if 4 <= y <= 6)
            good = sum(1 for y in yards if 7 <= y <= 9)
            explosive = sum(1 for y in yards if y >= 10)
            big = sum(1 for y in yards if y >= 20)

            n = len(yards)
            print(f"\n  Run Distribution:")
            print(f"    Loss (<0): {100*negative/n:.1f}% (target: 8.7%)")
            print(f"    No gain (0): {100*zero/n:.1f}% (target: 8.4%)")
            print(f"    Short (1-3): {100*short/n:.1f}% (target: 36.4%)")
            print(f"    Medium (4-6): {100*medium/n:.1f}% (target: 24.1%)")
            print(f"    Good (7-9): {100*good/n:.1f}% (target: 10.8%)")
            print(f"    Explosive (10+): {100*explosive/n:.1f}% (target: 11.6%)")
            print(f"    Big Play (20+): {100*big/n:.1f}% (target: 2.5%)")

            print(f"\n    Min: {min(yards)}, Max: {max(yards)}, Mean: {statistics.mean(yards):.1f}, Median: {statistics.median(yards):.0f}")
    else:
        print("  No run plays")

    print(f"\n--- BLOCKING QUALITY IMPACT ---")
    if stats.run_plays > 0:
        print(f"  Great blocks: {stats.great_blocks} ({100*stats.great_blocks/stats.run_plays:.1f}%)")
        print(f"  Average blocks: {stats.avg_blocks} ({100*stats.avg_blocks/stats.run_plays:.1f}%)")
        print(f"  Poor blocks: {stats.poor_blocks} ({100*stats.poor_blocks/stats.run_plays:.1f}%)")

        for quality in ["great", "average", "poor"]:
            yards = stats.yards_by_blocking.get(quality, [])
            if yards:
                print(f"\n  {quality.capitalize()} blocking:")
                print(f"    Count: {len(yards)}")
                print(f"    Avg yards: {statistics.mean(yards):.1f}")
                print(f"    Min/Max: {min(yards)}/{max(yards)}")
                stuffs = sum(1 for y in yards if y < 0)
                print(f"    Stuffs: {stuffs} ({100*stuffs/len(yards):.1f}%)")

    print(f"\n--- OVERALL ---")
    print(f"  Yards Per Play: {stats.yards_per_play():.2f}")
    print(f"  Touchdowns: {stats.touchdowns}")

    print()


async def main():
    """Main test runner."""
    print()
    print("#" * 70)
    print("# V2 SIMULATION VERIFICATION TEST")
    print("#" * 70)

    # Test 1: Phase transition stability (run several games)
    print("\n[TEST 1] Phase Transition Stability Test")
    print("-" * 50)
    print("Running 3 games with 30 plays each to verify no crashes...")

    total_crashes = 0
    total_plays = 0

    for game_num in range(3):
        print(f"\n  Game {game_num + 1}:")
        stats = await run_game_simulation(num_plays=30)
        total_crashes += stats.phase_crashes
        total_plays += stats.total_plays
        print(f"    Plays: {stats.total_plays}, Crashes: {stats.phase_crashes}")

    print(f"\n  RESULT: {total_crashes} crashes in {total_plays} plays")
    if total_crashes == 0:
        print("  PASS - Phase transition bug appears FIXED")
    else:
        print("  FAIL - Phase transition bugs still occurring!")

    # Test 2: Run game variance analysis
    print("\n\n[TEST 2] Run Game Variance Analysis")
    print("-" * 50)
    print("Running 100 focused run plays to analyze blocking impact...")

    run_stats = await run_focused_run_test(num_plays=100)
    print_report(run_stats, "RUN GAME VARIANCE ANALYSIS")

    # Analyze correlation between blocking quality and yards
    print("\n[ANALYSIS] Blocking Quality Correlation")
    print("-" * 50)

    great_yards = run_stats.yards_by_blocking.get("great", [])
    avg_yards = run_stats.yards_by_blocking.get("average", [])
    poor_yards = run_stats.yards_by_blocking.get("poor", [])

    if great_yards and avg_yards and poor_yards:
        great_mean = statistics.mean(great_yards)
        avg_mean = statistics.mean(avg_yards)
        poor_mean = statistics.mean(poor_yards)

        print(f"  Great blocking avg: {great_mean:.1f} yards")
        print(f"  Average blocking avg: {avg_mean:.1f} yards")
        print(f"  Poor blocking avg: {poor_mean:.1f} yards")

        if great_mean > avg_mean > poor_mean:
            print("\n  PASS - Blocking quality correctly affects yards!")
        else:
            print("\n  WARNING - Blocking quality correlation unexpected")

    # Key metrics summary
    print("\n\n[SUMMARY] Key Metrics vs NFL Targets")
    print("=" * 70)

    ypc = run_stats.run_ypc()
    stuff = run_stats.stuff_rate()

    print(f"  Yards Per Carry: {ypc:.2f} (target: 4.5, was: 7.45)")
    print(f"  Stuff Rate: {stuff:.1f}% (target: 8.7%)")

    if 3.5 <= ypc <= 5.5:
        print("\n  YPC: IMPROVED - within reasonable range of target")
    else:
        print(f"\n  YPC: NEEDS WORK - {'too high' if ypc > 5.5 else 'too low'}")

    if stuff >= 5.0:
        print("  Stuffs: IMPROVED - seeing negative plays")
    else:
        print("  Stuffs: NEEDS WORK - not enough stuffs")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

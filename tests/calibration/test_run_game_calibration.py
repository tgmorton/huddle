"""Run Game Calibration Tests.

Tests run game simulation output against NFL targets from research data.

NFL Targets (44,545 plays analyzed):
- Mean: 4.5 yards
- Median: 3.0 yards
- Stuff rate (loss): 8.7%
- No gain: 8.4%
- Short (1-3): 36.4%
- Medium (4-6): 24.1%
- Good (7-9): 10.8%
- Explosive (10+): 11.6%
- Big play (20+): 2.5%
"""

import asyncio
import sys
sys.path.insert(0, '/Users/thomasmorton/huddle')

import numpy as np
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Any

from huddle.api.routers.v2_sim import (
    drive_manager, StartDriveRequest, RunPlayRequest,
    start_drive, run_drive_play
)


# =============================================================================
# NFL Calibration Targets
# =============================================================================

NFL_TARGETS = {
    # Overall distribution
    "mean_yards": 4.5,
    "median_yards": 3.0,

    # Outcome buckets (percentages)
    "stuff_rate": 8.7,      # Loss of yards
    "no_gain_rate": 8.4,    # 0 yards
    "short_rate": 36.4,     # 1-3 yards
    "medium_rate": 24.1,    # 4-6 yards
    "good_rate": 10.8,      # 7-9 yards
    "explosive_rate": 11.6, # 10+ yards
    "big_play_rate": 2.5,   # 20+ yards

    # Tolerance for passing tests
    "tolerance": {
        "mean_yards": 1.0,      # +/- 1 yard
        "median_yards": 1.0,    # +/- 1 yard
        "stuff_rate": 5.0,      # +/- 5%
        "no_gain_rate": 5.0,
        "short_rate": 10.0,
        "medium_rate": 10.0,
        "good_rate": 5.0,
        "explosive_rate": 5.0,
        "big_play_rate": 2.0,
    }
}

# By gap targets
NFL_GAP_TARGETS = {
    "end": {"mean": 5.4, "median": 4},
    "guard": {"mean": 4.2, "median": 3},
    "tackle": {"mean": 4.4, "median": 3},
}


@dataclass
class RunResult:
    """Single run play result."""
    yards: int
    concept: str
    is_touchdown: bool = False
    is_first_down: bool = False


@dataclass
class CalibrationReport:
    """Calibration test results."""
    total_plays: int
    results: List[RunResult]

    # Computed metrics
    mean_yards: float = 0.0
    median_yards: float = 0.0
    std_yards: float = 0.0

    # Distribution buckets
    stuff_rate: float = 0.0
    no_gain_rate: float = 0.0
    short_rate: float = 0.0
    medium_rate: float = 0.0
    good_rate: float = 0.0
    explosive_rate: float = 0.0
    big_play_rate: float = 0.0

    def compute_metrics(self):
        """Compute all metrics from results."""
        if not self.results:
            return

        yards = [r.yards for r in self.results]
        n = len(yards)

        self.mean_yards = np.mean(yards)
        self.median_yards = np.median(yards)
        self.std_yards = np.std(yards)

        # Bucket counts
        self.stuff_rate = 100 * sum(1 for y in yards if y < 0) / n
        self.no_gain_rate = 100 * sum(1 for y in yards if y == 0) / n
        self.short_rate = 100 * sum(1 for y in yards if 1 <= y <= 3) / n
        self.medium_rate = 100 * sum(1 for y in yards if 4 <= y <= 6) / n
        self.good_rate = 100 * sum(1 for y in yards if 7 <= y <= 9) / n
        self.explosive_rate = 100 * sum(1 for y in yards if y >= 10) / n
        self.big_play_rate = 100 * sum(1 for y in yards if y >= 20) / n

    def compare_to_nfl(self) -> Dict[str, Dict[str, float]]:
        """Compare metrics to NFL targets."""
        comparisons = {}

        metrics = [
            "mean_yards", "median_yards", "stuff_rate", "no_gain_rate",
            "short_rate", "medium_rate", "good_rate", "explosive_rate", "big_play_rate"
        ]

        for metric in metrics:
            actual = getattr(self, metric)
            target = NFL_TARGETS[metric]
            tolerance = NFL_TARGETS["tolerance"][metric]
            diff = actual - target
            within_tolerance = abs(diff) <= tolerance

            comparisons[metric] = {
                "actual": actual,
                "target": target,
                "diff": diff,
                "tolerance": tolerance,
                "pass": within_tolerance,
            }

        return comparisons

    def print_report(self):
        """Print formatted calibration report."""
        print("=" * 70)
        print("RUN GAME CALIBRATION REPORT")
        print("=" * 70)
        print(f"Total plays: {self.total_plays}")
        print()

        # Distribution
        yards = [r.yards for r in self.results]
        print("YARDS DISTRIBUTION:")
        print(f"  Min: {min(yards)}, Max: {max(yards)}")
        print(f"  Mean: {self.mean_yards:.2f} (NFL: {NFL_TARGETS['mean_yards']})")
        print(f"  Median: {self.median_yards:.1f} (NFL: {NFL_TARGETS['median_yards']})")
        print(f"  Std Dev: {self.std_yards:.2f}")
        print()

        # Comparison table
        print("COMPARISON TO NFL TARGETS:")
        print("-" * 70)
        print(f"{'Metric':<20} {'Actual':>10} {'Target':>10} {'Diff':>10} {'Status':>10}")
        print("-" * 70)

        comparisons = self.compare_to_nfl()
        for metric, data in comparisons.items():
            status = "PASS" if data["pass"] else "FAIL"
            status_str = f"[{status}]"

            if "rate" in metric:
                print(f"{metric:<20} {data['actual']:>9.1f}% {data['target']:>9.1f}% {data['diff']:>+9.1f}% {status_str:>10}")
            else:
                print(f"{metric:<20} {data['actual']:>10.2f} {data['target']:>10.1f} {data['diff']:>+10.2f} {status_str:>10}")

        print("-" * 70)

        # Pass/fail summary
        passed = sum(1 for d in comparisons.values() if d["pass"])
        total = len(comparisons)
        print(f"RESULT: {passed}/{total} metrics within tolerance")
        print()

        # Histogram
        print("HISTOGRAM:")
        buckets = Counter()
        for y in yards:
            if y < 0:
                buckets["loss"] += 1
            elif y == 0:
                buckets["0"] += 1
            elif y <= 3:
                buckets["1-3"] += 1
            elif y <= 6:
                buckets["4-6"] += 1
            elif y <= 9:
                buckets["7-9"] += 1
            elif y <= 19:
                buckets["10-19"] += 1
            else:
                buckets["20+"] += 1

        max_count = max(buckets.values()) if buckets else 1
        for bucket in ["loss", "0", "1-3", "4-6", "7-9", "10-19", "20+"]:
            count = buckets.get(bucket, 0)
            pct = 100 * count / len(yards)
            bar_len = int(40 * count / max_count)
            bar = "#" * bar_len
            print(f"  {bucket:>5}: {bar:<40} {count:>4} ({pct:>5.1f}%)")


async def run_calibration_test(
    num_plays: int = 200,
    concepts: List[str] = None,
) -> CalibrationReport:
    """Run calibration test with specified number of plays.

    Args:
        num_plays: Number of run plays to simulate
        concepts: List of run concepts to use (cycles through them)

    Returns:
        CalibrationReport with all results and metrics
    """
    if concepts is None:
        # Default: mix of inside and outside zone
        concepts = [
            "inside_zone_right",
            "inside_zone_left",
            "outside_zone_right",
            "outside_zone_left",
            "power_right",
            "power_left",
        ]

    results = []
    plays_run = 0
    concept_idx = 0

    print(f"Running {num_plays} plays...")

    while plays_run < num_plays:
        # Start a new drive at the 25
        request = StartDriveRequest(starting_yard_line=25)
        drive_state = await start_drive(request)
        drive_id = drive_state.drive_id

        # Run plays until drive ends or we have enough
        while plays_run < num_plays:
            concept = concepts[concept_idx % len(concepts)]
            concept_idx += 1

            request = RunPlayRequest(
                drive_id=drive_id,
                play_type="run",
                run_concept=concept,
            )

            try:
                result = await run_drive_play(request)
                play_result = result["play_result"]
                drive_state_dict = result["drive_state"]

                yards = play_result.get("yards_gained", 0)

                results.append(RunResult(
                    yards=yards,
                    concept=concept,
                    is_touchdown=play_result.get("is_touchdown", False),
                    is_first_down=play_result.get("is_first_down", False),
                ))

                plays_run += 1

                if plays_run % 50 == 0:
                    print(f"  {plays_run}/{num_plays} plays completed...")

                # End drive if not active
                if drive_state_dict["status"] != "active":
                    break

            except Exception as e:
                print(f"Error on play {plays_run}: {e}")
                break

    print(f"Completed {len(results)} plays")

    report = CalibrationReport(
        total_plays=len(results),
        results=results,
    )
    report.compute_metrics()

    return report


async def run_concept_breakdown(num_plays_per_concept: int = 50) -> Dict[str, CalibrationReport]:
    """Run calibration broken down by run concept.

    Returns dict of concept -> CalibrationReport
    """
    concepts = [
        "inside_zone_right",
        "inside_zone_left",
        "outside_zone_right",
        "outside_zone_left",
        "power_right",
        "power_left",
        "counter_left",
        "dive_right",
    ]

    reports = {}

    for concept in concepts:
        print(f"\nTesting {concept}...")
        report = await run_calibration_test(
            num_plays=num_plays_per_concept,
            concepts=[concept],
        )
        reports[concept] = report
        print(f"  Mean: {report.mean_yards:.1f}, Median: {report.median_yards:.0f}")

    return reports


async def main():
    """Run full calibration suite."""
    print("=" * 70)
    print("RUN GAME CALIBRATION SUITE")
    print("=" * 70)
    print()

    # Overall calibration
    print("PHASE 1: Overall Run Game Calibration")
    print("-" * 70)
    report = await run_calibration_test(num_plays=300)
    report.print_report()

    # Concept breakdown
    print("\n" + "=" * 70)
    print("PHASE 2: By Concept Breakdown")
    print("=" * 70)

    concept_reports = await run_concept_breakdown(num_plays_per_concept=30)

    print("\nCONCEPT SUMMARY:")
    print("-" * 50)
    print(f"{'Concept':<25} {'Mean':>8} {'Median':>8} {'Stuff%':>8}")
    print("-" * 50)

    for concept, rpt in concept_reports.items():
        print(f"{concept:<25} {rpt.mean_yards:>8.1f} {rpt.median_yards:>8.0f} {rpt.stuff_rate:>7.1f}%")

    print()
    print("=" * 70)
    print("CALIBRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

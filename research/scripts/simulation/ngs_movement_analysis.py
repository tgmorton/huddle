"""NGS Tracking Data Movement Analysis.

Analyzes NFL Next Gen Stats tracking data to extract realistic movement
parameters for calibrating the V2 simulation.

Data source: https://github.com/asonty/ngs_highlights
- 562 plays from 2017-2019 seasons
- 10 FPS frame-by-frame tracking
- x, y, speed, orientation, direction for all players

Exports:
- Speed distributions by position
- Acceleration profiles
- Direction change (cut) patterns
- Route timing benchmarks
- Play duration statistics
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math

import pandas as pd
import numpy as np

# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "ngs_highlights" / "play_data"
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports" / "reference" / "simulation"

# Position groupings for analysis
POSITION_GROUPS = {
    "QB": ["QB"],
    "RB": ["RB", "FB"],
    "WR": ["WR"],
    "TE": ["TE"],
    "OL": ["T", "G", "C", "OT", "OG"],
    "DL": ["DT", "DE", "NT"],
    "LB": ["LB", "OLB", "ILB", "MLB"],
    "CB": ["CB"],
    "S": ["S", "SS", "FS"],
}

def get_position_group(position: str) -> str:
    """Map specific position to group."""
    for group, positions in POSITION_GROUPS.items():
        if position in positions:
            return group
    return "OTHER"


# =============================================================================
# Data Loading
# =============================================================================

def load_play(filepath: Path) -> pd.DataFrame:
    """Load a single play's tracking data."""
    df = pd.read_csv(filepath, sep='\t')
    df['position_group'] = df['position'].apply(get_position_group)
    return df


def load_all_plays(limit: Optional[int] = None) -> List[pd.DataFrame]:
    """Load all plays from the data directory."""
    plays = []
    files = sorted(DATA_DIR.glob("*.tsv"))
    if limit:
        files = files[:limit]

    for f in files:
        try:
            df = load_play(f)
            df['source_file'] = f.name
            plays.append(df)
        except Exception as e:
            print(f"Error loading {f.name}: {e}")

    return plays


# =============================================================================
# Speed Analysis
# =============================================================================

@dataclass
class SpeedStats:
    """Speed statistics for a position group."""
    position_group: str
    sample_size: int
    max_speed_mean: float
    max_speed_std: float
    max_speed_p50: float
    max_speed_p90: float
    max_speed_p99: float
    cruise_speed_mean: float  # Average speed when moving (>1 yd/s)
    acceleration_mean: float  # yards/sec^2 to reach cruise


def analyze_speeds(plays: List[pd.DataFrame]) -> Dict[str, SpeedStats]:
    """Analyze speed distributions by position group."""
    # Collect max speeds per player per play
    max_speeds = defaultdict(list)
    cruise_speeds = defaultdict(list)
    accelerations = defaultdict(list)

    for play_df in plays:
        # Group by player within this play
        for (player_name, pos_group), player_df in play_df.groupby(['displayName', 'position_group']):
            if pos_group == "OTHER":
                continue

            speeds = player_df['s'].values

            # Max speed this play
            max_speed = speeds.max()
            if max_speed > 0:
                max_speeds[pos_group].append(max_speed)

            # Cruise speed (average when moving)
            moving = speeds[speeds > 1.0]
            if len(moving) > 5:
                cruise_speeds[pos_group].append(moving.mean())

            # Acceleration (frames to go from <1 to >3 yd/s)
            for i in range(len(speeds) - 1):
                if speeds[i] < 1.0 and speeds[i+1] >= 1.0:
                    # Find time to reach 3+ yd/s
                    for j in range(i+1, min(i+30, len(speeds))):
                        if speeds[j] >= 3.0:
                            frames = j - i
                            accel = 3.0 / (frames * 0.1)  # yd/s^2
                            accelerations[pos_group].append(accel)
                            break

    results = {}
    for pos_group in POSITION_GROUPS.keys():
        speeds = max_speeds.get(pos_group, [])
        if len(speeds) < 10:
            continue

        speeds_arr = np.array(speeds)
        cruise_arr = np.array(cruise_speeds.get(pos_group, [0]))
        accel_arr = np.array(accelerations.get(pos_group, [0]))

        results[pos_group] = SpeedStats(
            position_group=pos_group,
            sample_size=len(speeds),
            max_speed_mean=float(speeds_arr.mean()),
            max_speed_std=float(speeds_arr.std()),
            max_speed_p50=float(np.percentile(speeds_arr, 50)),
            max_speed_p90=float(np.percentile(speeds_arr, 90)),
            max_speed_p99=float(np.percentile(speeds_arr, 99)),
            cruise_speed_mean=float(cruise_arr.mean()) if len(cruise_arr) > 0 else 0,
            acceleration_mean=float(accel_arr.mean()) if len(accel_arr) > 0 else 0,
        )

    return results


# =============================================================================
# Direction Change Analysis
# =============================================================================

@dataclass
class CutStats:
    """Direction change (cut) statistics."""
    position_group: str
    sample_size: int
    cut_angle_mean: float  # Average cut angle in degrees
    cut_angle_p90: float
    speed_retention: float  # Speed after cut / speed before cut
    frames_to_recover: float  # Frames to regain pre-cut speed


def analyze_cuts(plays: List[pd.DataFrame]) -> Dict[str, CutStats]:
    """Analyze direction changes by position group."""
    cuts = defaultdict(list)

    for play_df in plays:
        for (player_name, pos_group), player_df in play_df.groupby(['displayName', 'position_group']):
            if pos_group == "OTHER":
                continue

            dirs = player_df['dir'].values
            speeds = player_df['s'].values

            # Find significant direction changes while moving fast
            for i in range(2, len(dirs) - 5):
                if speeds[i] < 3.0:  # Only count cuts at speed
                    continue

                # Calculate direction change
                dir_before = dirs[i-2:i].mean()
                dir_after = dirs[i+1:i+3].mean()

                # Handle wraparound at 360
                angle_diff = abs(dir_after - dir_before)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                # Significant cut = 30+ degrees
                if angle_diff >= 30:
                    speed_before = speeds[i-1]
                    speed_after = speeds[i+1]
                    retention = speed_after / speed_before if speed_before > 0 else 1

                    # Find frames to recover speed
                    frames_to_recover = 10  # default
                    for j in range(i+1, min(i+20, len(speeds))):
                        if speeds[j] >= speed_before * 0.95:
                            frames_to_recover = j - i
                            break

                    cuts[pos_group].append({
                        'angle': angle_diff,
                        'retention': retention,
                        'frames_to_recover': frames_to_recover,
                    })

    results = {}
    for pos_group in POSITION_GROUPS.keys():
        cut_data = cuts.get(pos_group, [])
        if len(cut_data) < 10:
            continue

        angles = [c['angle'] for c in cut_data]
        retentions = [c['retention'] for c in cut_data]
        recoveries = [c['frames_to_recover'] for c in cut_data]

        results[pos_group] = CutStats(
            position_group=pos_group,
            sample_size=len(cut_data),
            cut_angle_mean=float(np.mean(angles)),
            cut_angle_p90=float(np.percentile(angles, 90)),
            speed_retention=float(np.mean(retentions)),
            frames_to_recover=float(np.mean(recoveries)),
        )

    return results


# =============================================================================
# Play Duration Analysis
# =============================================================================

@dataclass
class PlayDurationStats:
    """Play duration statistics."""
    play_type: str
    sample_size: int
    snap_to_end_mean: float  # seconds
    snap_to_end_std: float
    snap_to_end_p50: float
    snap_to_end_p90: float


def analyze_play_durations(plays: List[pd.DataFrame]) -> Dict[str, PlayDurationStats]:
    """Analyze play durations by type."""
    durations = defaultdict(list)

    for play_df in plays:
        play_type = play_df['playType'].iloc[0]

        # Find snap and end events
        events = play_df[play_df['event'].notna()][['frame', 'event']].drop_duplicates()

        snap_frame = None
        end_frame = None

        for _, row in events.iterrows():
            if row['event'] == 'ball_snap':
                snap_frame = row['frame']
            elif row['event'] in ['tackle', 'touchdown', 'out_of_bounds', 'pass_outcome_incomplete', 'fumble']:
                end_frame = row['frame']

        if snap_frame is not None and end_frame is not None and end_frame > snap_frame:
            duration_secs = (end_frame - snap_frame) * 0.1
            durations[play_type].append(duration_secs)

    results = {}
    for play_type, times in durations.items():
        if len(times) < 5:
            continue

        times_arr = np.array(times)
        results[play_type] = PlayDurationStats(
            play_type=play_type,
            sample_size=len(times),
            snap_to_end_mean=float(times_arr.mean()),
            snap_to_end_std=float(times_arr.std()),
            snap_to_end_p50=float(np.percentile(times_arr, 50)),
            snap_to_end_p90=float(np.percentile(times_arr, 90)),
        )

    return results


# =============================================================================
# Route Timing Analysis (WR specific)
# =============================================================================

@dataclass
class RouteTimingStats:
    """Route timing benchmarks for receivers."""
    sample_size: int
    snap_to_5yds_mean: float  # seconds to reach 5 yards downfield
    snap_to_10yds_mean: float
    snap_to_15yds_mean: float
    snap_to_break_mean: float  # seconds to first major direction change
    break_depth_mean: float  # yards downfield at break


def analyze_route_timing(plays: List[pd.DataFrame]) -> RouteTimingStats:
    """Analyze receiver route timing from passing plays."""
    passing_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_pass']

    snap_to_5 = []
    snap_to_10 = []
    snap_to_15 = []
    snap_to_break = []
    break_depths = []

    for play_df in passing_plays:
        # Find snap frame
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Get receivers
        receivers = play_df[play_df['position_group'] == 'WR']['displayName'].unique()

        for wr_name in receivers:
            wr_df = play_df[play_df['displayName'] == wr_name].copy()
            wr_df = wr_df[wr_df['frame'] >= snap_frame].sort_values('frame')

            if len(wr_df) < 10:
                continue

            # Get starting position (at snap)
            start_x = wr_df['x'].iloc[0]
            start_y = wr_df['y'].iloc[0]

            # Determine direction (left or right based on play direction)
            play_dir = play_df['playDirection'].iloc[0]

            # Track depth milestones
            for i, row in wr_df.iterrows():
                frames_since_snap = row['frame'] - snap_frame

                # Calculate downfield distance
                if play_dir == 'left':
                    depth = start_x - row['x']
                else:
                    depth = row['x'] - start_x

                # 5 yard milestone
                if depth >= 5 and len(snap_to_5) < len(passing_plays) * 3:
                    snap_to_5.append(frames_since_snap * 0.1)
                    break

            # Similar for 10, 15 yards...
            for i, row in wr_df.iterrows():
                frames_since_snap = row['frame'] - snap_frame
                if play_dir == 'left':
                    depth = start_x - row['x']
                else:
                    depth = row['x'] - start_x

                if depth >= 10:
                    snap_to_10.append(frames_since_snap * 0.1)
                    break

            for i, row in wr_df.iterrows():
                frames_since_snap = row['frame'] - snap_frame
                if play_dir == 'left':
                    depth = start_x - row['x']
                else:
                    depth = row['x'] - start_x

                if depth >= 15:
                    snap_to_15.append(frames_since_snap * 0.1)
                    break

            # Find break point (significant direction change)
            dirs = wr_df['dir'].values
            xs = wr_df['x'].values
            frames = wr_df['frame'].values

            for i in range(5, len(dirs) - 2):
                dir_before = dirs[i-3:i].mean()
                dir_after = dirs[i:i+3].mean()

                angle_diff = abs(dir_after - dir_before)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                if angle_diff >= 45:  # Significant break
                    snap_to_break.append((frames[i] - snap_frame) * 0.1)
                    if play_dir == 'left':
                        break_depths.append(start_x - xs[i])
                    else:
                        break_depths.append(xs[i] - start_x)
                    break

    return RouteTimingStats(
        sample_size=len(passing_plays),
        snap_to_5yds_mean=float(np.mean(snap_to_5)) if snap_to_5 else 0,
        snap_to_10yds_mean=float(np.mean(snap_to_10)) if snap_to_10 else 0,
        snap_to_15yds_mean=float(np.mean(snap_to_15)) if snap_to_15 else 0,
        snap_to_break_mean=float(np.mean(snap_to_break)) if snap_to_break else 0,
        break_depth_mean=float(np.mean(break_depths)) if break_depths else 0,
    )


# =============================================================================
# Pursuit Analysis (Defenders)
# =============================================================================

@dataclass
class PursuitStats:
    """Defender pursuit statistics."""
    position_group: str
    sample_size: int
    pursuit_speed_mean: float  # Speed when chasing ball carrier
    pursuit_angle_efficiency: float  # How direct is the pursuit (1.0 = perfect)
    closing_speed_mean: float  # Rate of closing distance to ball carrier


def analyze_pursuit(plays: List[pd.DataFrame]) -> Dict[str, PursuitStats]:
    """Analyze defender pursuit patterns on rushing plays."""
    rush_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_rush']

    pursuit_data = defaultdict(list)

    for play_df in rush_plays:
        # Find ball carrier (RB typically)
        rbs = play_df[play_df['position_group'] == 'RB']['displayName'].unique()
        if len(rbs) == 0:
            continue

        ball_carrier = rbs[0]
        bc_df = play_df[play_df['displayName'] == ball_carrier]

        # Find snap frame
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Analyze each defender
        defenders = play_df[play_df['position_group'].isin(['LB', 'CB', 'S', 'DL'])]

        for def_name in defenders['displayName'].unique():
            def_df = play_df[play_df['displayName'] == def_name]
            pos_group = def_df['position_group'].iloc[0]

            # Get frames after snap
            def_df = def_df[def_df['frame'] >= snap_frame].sort_values('frame')
            bc_frames = bc_df[bc_df['frame'] >= snap_frame].sort_values('frame')

            if len(def_df) < 10 or len(bc_frames) < 10:
                continue

            # Calculate pursuit metrics
            pursuit_speeds = []
            closing_speeds = []

            for i in range(len(def_df) - 1):
                frame = def_df.iloc[i]['frame']

                # Find ball carrier position at same frame
                bc_at_frame = bc_frames[bc_frames['frame'] == frame]
                if len(bc_at_frame) == 0:
                    continue

                bc_x, bc_y = bc_at_frame['x'].iloc[0], bc_at_frame['y'].iloc[0]
                def_x, def_y = def_df.iloc[i]['x'], def_df.iloc[i]['y']
                def_speed = def_df.iloc[i]['s']

                dist = math.sqrt((bc_x - def_x)**2 + (bc_y - def_y)**2)

                # Next frame distance
                if i + 1 < len(def_df):
                    next_frame = def_df.iloc[i+1]['frame']
                    bc_next = bc_frames[bc_frames['frame'] == next_frame]
                    if len(bc_next) > 0:
                        next_def_x, next_def_y = def_df.iloc[i+1]['x'], def_df.iloc[i+1]['y']
                        next_bc_x, next_bc_y = bc_next['x'].iloc[0], bc_next['y'].iloc[0]
                        next_dist = math.sqrt((next_bc_x - next_def_x)**2 + (next_bc_y - next_def_y)**2)

                        closing_speed = (dist - next_dist) / 0.1  # yd/s

                        if def_speed > 2.0:  # Only when actually pursuing
                            pursuit_speeds.append(def_speed)
                            closing_speeds.append(closing_speed)

            if pursuit_speeds:
                pursuit_data[pos_group].append({
                    'pursuit_speed': np.mean(pursuit_speeds),
                    'closing_speed': np.mean(closing_speeds),
                })

    results = {}
    for pos_group in ['LB', 'CB', 'S', 'DL']:
        data = pursuit_data.get(pos_group, [])
        if len(data) < 10:
            continue

        pursuit_speeds = [d['pursuit_speed'] for d in data]
        closing_speeds = [d['closing_speed'] for d in data]

        results[pos_group] = PursuitStats(
            position_group=pos_group,
            sample_size=len(data),
            pursuit_speed_mean=float(np.mean(pursuit_speeds)),
            pursuit_angle_efficiency=0.0,  # TODO: Calculate
            closing_speed_mean=float(np.mean(closing_speeds)),
        )

    return results


# =============================================================================
# Main Analysis
# =============================================================================

def run_analysis(limit: Optional[int] = None):
    """Run all analyses and export results."""
    print(f"Loading plays from {DATA_DIR}...")
    plays = load_all_plays(limit=limit)
    print(f"Loaded {len(plays)} plays")

    print("\nAnalyzing speeds...")
    speed_stats = analyze_speeds(plays)

    print("Analyzing direction changes...")
    cut_stats = analyze_cuts(plays)

    print("Analyzing play durations...")
    duration_stats = analyze_play_durations(plays)

    print("Analyzing route timing...")
    route_stats = analyze_route_timing(plays)

    print("Analyzing pursuit patterns...")
    pursuit_stats = analyze_pursuit(plays)

    # Build export
    export = {
        "meta": {
            "source": "ngs_highlights (github.com/asonty/ngs_highlights)",
            "plays_analyzed": len(plays),
            "seasons": "2017-2019",
            "frame_rate": 10,
            "description": "NFL Next Gen Stats tracking data analysis for movement calibration",
        },
        "speed_by_position": {
            pos: {
                "sample_size": s.sample_size,
                "max_speed_mean_yps": round(s.max_speed_mean, 2),
                "max_speed_mean_mph": round(s.max_speed_mean * 2.045, 1),
                "max_speed_std": round(s.max_speed_std, 2),
                "max_speed_p50_yps": round(s.max_speed_p50, 2),
                "max_speed_p90_yps": round(s.max_speed_p90, 2),
                "max_speed_p99_yps": round(s.max_speed_p99, 2),
                "cruise_speed_mean_yps": round(s.cruise_speed_mean, 2),
                "acceleration_mean_yps2": round(s.acceleration_mean, 2),
            }
            for pos, s in speed_stats.items()
        },
        "direction_change_by_position": {
            pos: {
                "sample_size": s.sample_size,
                "cut_angle_mean_deg": round(s.cut_angle_mean, 1),
                "cut_angle_p90_deg": round(s.cut_angle_p90, 1),
                "speed_retention_ratio": round(s.speed_retention, 3),
                "frames_to_recover_speed": round(s.frames_to_recover, 1),
                "seconds_to_recover_speed": round(s.frames_to_recover * 0.1, 2),
            }
            for pos, s in cut_stats.items()
        },
        "play_duration_by_type": {
            ptype: {
                "sample_size": s.sample_size,
                "snap_to_end_mean_sec": round(s.snap_to_end_mean, 2),
                "snap_to_end_std_sec": round(s.snap_to_end_std, 2),
                "snap_to_end_p50_sec": round(s.snap_to_end_p50, 2),
                "snap_to_end_p90_sec": round(s.snap_to_end_p90, 2),
            }
            for ptype, s in duration_stats.items()
        },
        "route_timing": {
            "sample_size": route_stats.sample_size,
            "snap_to_5yds_mean_sec": round(route_stats.snap_to_5yds_mean, 2),
            "snap_to_10yds_mean_sec": round(route_stats.snap_to_10yds_mean, 2),
            "snap_to_15yds_mean_sec": round(route_stats.snap_to_15yds_mean, 2),
            "snap_to_break_mean_sec": round(route_stats.snap_to_break_mean, 2),
            "break_depth_mean_yds": round(route_stats.break_depth_mean, 1),
        },
        "pursuit_by_position": {
            pos: {
                "sample_size": s.sample_size,
                "pursuit_speed_mean_yps": round(s.pursuit_speed_mean, 2),
                "pursuit_speed_mean_mph": round(s.pursuit_speed_mean * 2.045, 1),
                "closing_speed_mean_yps": round(s.closing_speed_mean, 2),
            }
            for pos, s in pursuit_stats.items()
        },
        "implementation_notes": {
            "speed_units": "Speeds in yards/second (multiply by 2.045 for mph)",
            "frame_rate": "Data captured at 10 FPS, so 1 frame = 0.1 seconds",
            "direction": "0 degrees = upfield, increases clockwise",
            "calibration_targets": [
                "V2 simulation should match position max speeds within 5%",
                "Route timing should match snap_to_Xyds benchmarks",
                "Cut speed retention should be ~70-80% immediately after cut",
                "Pursuit closing speed indicates tackle likelihood",
            ],
        },
    }

    # Print summary
    print("\n" + "="*60)
    print("SPEED BY POSITION (yards/second)")
    print("="*60)
    for pos, stats in sorted(speed_stats.items(), key=lambda x: -x[1].max_speed_mean):
        print(f"{pos:4s}: max={stats.max_speed_mean:.2f} yps ({stats.max_speed_mean*2.045:.1f} mph), "
              f"cruise={stats.cruise_speed_mean:.2f} yps, accel={stats.acceleration_mean:.1f} yps²")

    print("\n" + "="*60)
    print("PLAY DURATION BY TYPE")
    print("="*60)
    for ptype, stats in duration_stats.items():
        print(f"{ptype:25s}: mean={stats.snap_to_end_mean:.1f}s, p90={stats.snap_to_end_p90:.1f}s (n={stats.sample_size})")

    print("\n" + "="*60)
    print("ROUTE TIMING (WR)")
    print("="*60)
    print(f"Snap to 5 yards:  {route_stats.snap_to_5yds_mean:.2f}s")
    print(f"Snap to 10 yards: {route_stats.snap_to_10yds_mean:.2f}s")
    print(f"Snap to 15 yards: {route_stats.snap_to_15yds_mean:.2f}s")
    print(f"Snap to break:    {route_stats.snap_to_break_mean:.2f}s at {route_stats.break_depth_mean:.1f} yards depth")

    print("\n" + "="*60)
    print("DIRECTION CHANGE (CUTS)")
    print("="*60)
    for pos, stats in cut_stats.items():
        print(f"{pos:4s}: avg cut={stats.cut_angle_mean:.0f}°, "
              f"speed retention={stats.speed_retention:.1%}, "
              f"recovery={stats.frames_to_recover*0.1:.2f}s")

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "ngs_movement_calibration.json"

    with open(export_path, 'w') as f:
        json.dump(export, f, indent=2)

    print(f"\nExported to {export_path}")

    return export


if __name__ == "__main__":
    run_analysis()

"""NGS Detailed Movement Analysis - Routes, Momentum, OL/DL.

Enhanced analysis focusing on:
1. Route trajectories - actual path shapes receivers run
2. Momentum - mass-adjusted speed changes, inertia effects
3. OL/DL engagement - blocking patterns and shed timing

Data source: https://github.com/asonty/ngs_highlights
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "ngs_highlights" / "play_data"
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports" / "reference" / "simulation"

# Estimated player weights by position (lbs) for momentum calculations
POSITION_WEIGHTS = {
    "QB": 220,
    "RB": 215,
    "FB": 245,
    "WR": 195,
    "TE": 250,
    "T": 315,
    "G": 315,
    "C": 305,
    "OT": 315,
    "OG": 315,
    "DT": 305,
    "DE": 270,
    "NT": 325,
    "LB": 240,
    "OLB": 240,
    "ILB": 245,
    "MLB": 245,
    "CB": 195,
    "S": 205,
    "SS": 210,
    "FS": 200,
}

def get_weight(position: str) -> float:
    """Get estimated weight for position."""
    return POSITION_WEIGHTS.get(position, 220)


# =============================================================================
# Data Loading
# =============================================================================

def load_play(filepath: Path) -> pd.DataFrame:
    """Load a single play's tracking data."""
    df = pd.read_csv(filepath, sep='\t', low_memory=False)
    return df


def load_plays_by_type(play_type: str, limit: Optional[int] = None) -> List[pd.DataFrame]:
    """Load plays of a specific type."""
    plays = []
    files = sorted(DATA_DIR.glob("*.tsv"))

    for f in files:
        try:
            df = load_play(f)
            if df['playType'].iloc[0] == play_type:
                df['source_file'] = f.name
                plays.append(df)
                if limit and len(plays) >= limit:
                    break
        except Exception as e:
            continue

    return plays


# =============================================================================
# Route Trajectory Analysis
# =============================================================================

@dataclass
class RouteTrajectory:
    """A single route's trajectory data."""
    player_name: str
    route_type: str  # inferred from shape
    total_distance: float
    max_depth: float
    lateral_movement: float
    frames: List[Tuple[float, float]]  # (x, y) positions relative to snap
    velocities: List[float]
    break_frame: Optional[int]
    break_angle: Optional[float]


def classify_route(trajectory: List[Tuple[float, float]], play_dir: str) -> str:
    """Classify route type based on trajectory shape."""
    if len(trajectory) < 10:
        return "unknown"

    # Get relative positions
    start = trajectory[0]
    end = trajectory[-1]

    # Calculate depth and lateral movement
    if play_dir == 'left':
        depth = start[0] - end[0]
        lateral = end[1] - start[1]
    else:
        depth = end[0] - start[0]
        lateral = end[1] - start[1]

    # Find break point (largest direction change)
    max_angle_change = 0
    break_idx = 0
    for i in range(5, len(trajectory) - 5):
        # Vector before
        v1 = (trajectory[i][0] - trajectory[i-5][0], trajectory[i][1] - trajectory[i-5][1])
        # Vector after
        v2 = (trajectory[i+5][0] - trajectory[i][0], trajectory[i+5][1] - trajectory[i][1])

        # Angle between vectors
        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)

        if mag1 > 0.1 and mag2 > 0.1:
            cos_angle = max(-1, min(1, dot / (mag1 * mag2)))
            angle = math.degrees(math.acos(cos_angle))
            if angle > max_angle_change:
                max_angle_change = angle
                break_idx = i

    # Classify based on characteristics
    if depth < 5:
        if abs(lateral) < 3:
            return "flat"
        return "screen"
    elif depth < 8:
        if max_angle_change < 30:
            return "slant" if abs(lateral) > 3 else "hitch"
        return "quick_out"
    elif depth < 15:
        if max_angle_change > 60:
            if lateral > 5:
                return "out"
            elif lateral < -5:
                return "in"
            return "curl"
        return "dig"
    else:
        if max_angle_change > 45:
            if abs(lateral) > 8:
                return "corner" if lateral > 0 else "post"
            return "comeback"
        return "go"


def analyze_routes(plays: List[pd.DataFrame]) -> Dict[str, List[RouteTrajectory]]:
    """Extract route trajectories from passing plays."""
    routes_by_type = defaultdict(list)

    for play_df in plays:
        # Find snap frame
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        play_dir = play_df['playDirection'].iloc[0]

        # Get receivers
        receivers = play_df[play_df['position'].isin(['WR', 'TE'])]['displayName'].unique()

        for rec_name in receivers:
            rec_df = play_df[play_df['displayName'] == rec_name].copy()
            rec_df = rec_df[rec_df['frame'] >= snap_frame].sort_values('frame')

            if len(rec_df) < 20:
                continue

            # Get starting position
            start_x = rec_df['x'].iloc[0]
            start_y = rec_df['y'].iloc[0]

            # Build trajectory (relative to start)
            trajectory = []
            velocities = []

            for _, row in rec_df.iterrows():
                rel_x = row['x'] - start_x
                rel_y = row['y'] - start_y
                trajectory.append((rel_x, rel_y))
                velocities.append(row['s'])

            # Calculate metrics
            total_dist = sum(math.sqrt((trajectory[i][0] - trajectory[i-1][0])**2 +
                                        (trajectory[i][1] - trajectory[i-1][1])**2)
                            for i in range(1, len(trajectory)))

            if play_dir == 'left':
                max_depth = max(-t[0] for t in trajectory)
                lateral = trajectory[-1][1] - trajectory[0][1]
            else:
                max_depth = max(t[0] for t in trajectory)
                lateral = trajectory[-1][1] - trajectory[0][1]

            # Find break
            break_frame = None
            break_angle = None
            dirs = rec_df['dir'].values

            for i in range(10, len(dirs) - 5):
                dir_before = np.mean(dirs[i-5:i])
                dir_after = np.mean(dirs[i:i+5])

                angle_diff = abs(dir_after - dir_before)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                if angle_diff > 45:
                    break_frame = i
                    break_angle = angle_diff
                    break

            # Classify route
            route_type = classify_route(trajectory, play_dir)

            route = RouteTrajectory(
                player_name=rec_name,
                route_type=route_type,
                total_distance=total_dist,
                max_depth=max_depth,
                lateral_movement=lateral,
                frames=trajectory[:50],  # First 5 seconds
                velocities=velocities[:50],
                break_frame=break_frame,
                break_angle=break_angle,
            )

            routes_by_type[route_type].append(route)

    return routes_by_type


# =============================================================================
# Momentum Analysis
# =============================================================================

@dataclass
class MomentumProfile:
    """Momentum characteristics by position."""
    position: str
    avg_weight_lbs: float
    max_momentum: float  # lbs * yds/s
    momentum_at_contact: float  # typical momentum when hitting
    deceleration_rate: float  # momentum loss per second when cutting
    time_to_max_momentum: float  # seconds


def analyze_momentum(plays: List[pd.DataFrame]) -> Dict[str, MomentumProfile]:
    """Analyze momentum patterns by position."""
    momentum_data = defaultdict(list)

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        for player_name in play_df['displayName'].unique():
            player_df = play_df[play_df['displayName'] == player_name]
            player_df = player_df[player_df['frame'] >= snap_frame].sort_values('frame')

            if len(player_df) < 10:
                continue

            position = player_df['position'].iloc[0]
            if pd.isna(position):
                continue

            weight = get_weight(position)
            speeds = player_df['s'].values

            # Calculate momentum (weight * speed)
            momenta = weight * speeds

            # Find max momentum and when it occurs
            max_momentum = momenta.max()
            max_frame = np.argmax(momenta)
            time_to_max = max_frame * 0.1

            # Find deceleration during cuts (speed drops > 1 yd/s in 0.3s)
            decel_rates = []
            for i in range(3, len(speeds)):
                speed_drop = speeds[i-3] - speeds[i]
                if speed_drop > 1.0:  # Significant deceleration
                    decel_rate = (momenta[i-3] - momenta[i]) / 0.3
                    decel_rates.append(decel_rate)

            momentum_data[position].append({
                'weight': weight,
                'max_momentum': max_momentum,
                'time_to_max': time_to_max,
                'decel_rate': np.mean(decel_rates) if decel_rates else 0,
            })

    results = {}
    for position, data in momentum_data.items():
        if len(data) < 10:
            continue

        results[position] = MomentumProfile(
            position=position,
            avg_weight_lbs=np.mean([d['weight'] for d in data]),
            max_momentum=np.mean([d['max_momentum'] for d in data]),
            momentum_at_contact=np.percentile([d['max_momentum'] for d in data], 75),
            deceleration_rate=np.mean([d['decel_rate'] for d in data]),
            time_to_max_momentum=np.mean([d['time_to_max'] for d in data]),
        )

    return results


# =============================================================================
# OL/DL Engagement Analysis
# =============================================================================

@dataclass
class BlockEngagement:
    """Single blocking engagement data."""
    ol_position: str
    dl_position: str
    initial_distance: float
    contact_frame: int
    engagement_duration: int  # frames
    ol_displacement: float  # yards pushed back
    dl_penetration: float  # yards gained by DL
    shed_occurred: bool
    shed_frame: Optional[int]


@dataclass
class OLDLStats:
    """OL/DL engagement statistics."""
    sample_size: int
    avg_contact_frame: float  # frames after snap
    avg_engagement_duration: float  # frames
    avg_ol_displacement: float  # yards
    avg_dl_penetration: float  # yards
    shed_rate: float  # % of engagements where DL sheds block
    avg_shed_time: float  # frames to shed


def analyze_ol_dl(plays: List[pd.DataFrame]) -> Dict[str, OLDLStats]:
    """Analyze OL/DL blocking engagements."""
    engagements = []

    ol_positions = ['T', 'G', 'C', 'OT', 'OG']
    dl_positions = ['DT', 'DE', 'NT']

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Get OL and DL players
        ol_players = play_df[play_df['position'].isin(ol_positions)]['displayName'].unique()
        dl_players = play_df[play_df['position'].isin(dl_positions)]['displayName'].unique()

        for ol_name in ol_players:
            ol_df = play_df[play_df['displayName'] == ol_name]
            ol_df = ol_df[ol_df['frame'] >= snap_frame].sort_values('frame')

            if len(ol_df) < 10:
                continue

            ol_pos = ol_df['position'].iloc[0]
            ol_start_x = ol_df['x'].iloc[0]
            ol_start_y = ol_df['y'].iloc[0]

            # Find nearest DL at snap
            for dl_name in dl_players:
                dl_df = play_df[play_df['displayName'] == dl_name]
                dl_df = dl_df[dl_df['frame'] >= snap_frame].sort_values('frame')

                if len(dl_df) < 10:
                    continue

                dl_pos = dl_df['position'].iloc[0]
                dl_start_x = dl_df['x'].iloc[0]
                dl_start_y = dl_df['y'].iloc[0]

                initial_dist = math.sqrt((ol_start_x - dl_start_x)**2 +
                                          (ol_start_y - dl_start_y)**2)

                # Only analyze if they start close (likely matched up)
                if initial_dist > 3.0:
                    continue

                # Track engagement
                contact_frame = None
                shed_frame = None
                min_dist = initial_dist

                for frame_idx in range(min(len(ol_df), len(dl_df))):
                    ol_x = ol_df.iloc[frame_idx]['x']
                    ol_y = ol_df.iloc[frame_idx]['y']
                    dl_x = dl_df.iloc[frame_idx]['x']
                    dl_y = dl_df.iloc[frame_idx]['y']

                    dist = math.sqrt((ol_x - dl_x)**2 + (ol_y - dl_y)**2)

                    # Contact when very close
                    if dist < 1.5 and contact_frame is None:
                        contact_frame = frame_idx

                    # Track minimum distance
                    if dist < min_dist:
                        min_dist = dist

                    # Shed when distance increases after being close
                    if contact_frame and dist > 3.0 and shed_frame is None:
                        shed_frame = frame_idx

                if contact_frame is not None:
                    # Calculate displacements
                    contact_ol_x = ol_df.iloc[contact_frame]['x']
                    final_ol_x = ol_df.iloc[-1]['x']
                    ol_displacement = abs(final_ol_x - contact_ol_x)

                    contact_dl_x = dl_df.iloc[contact_frame]['x']
                    final_dl_x = dl_df.iloc[-1]['x']

                    # DL penetration = movement toward backfield
                    play_dir = play_df['playDirection'].iloc[0]
                    if play_dir == 'left':
                        dl_penetration = contact_dl_x - final_dl_x
                    else:
                        dl_penetration = final_dl_x - contact_dl_x

                    engagements.append(BlockEngagement(
                        ol_position=ol_pos,
                        dl_position=dl_pos,
                        initial_distance=initial_dist,
                        contact_frame=contact_frame,
                        engagement_duration=len(ol_df) - contact_frame,
                        ol_displacement=ol_displacement,
                        dl_penetration=max(0, dl_penetration),
                        shed_occurred=shed_frame is not None,
                        shed_frame=shed_frame,
                    ))

    if not engagements:
        return {}

    # Aggregate stats
    contact_frames = [e.contact_frame for e in engagements]
    durations = [e.engagement_duration for e in engagements]
    ol_displacements = [e.ol_displacement for e in engagements]
    dl_penetrations = [e.dl_penetration for e in engagements]
    shed_times = [e.shed_frame - e.contact_frame for e in engagements
                  if e.shed_occurred and e.shed_frame]

    return {
        "all": OLDLStats(
            sample_size=len(engagements),
            avg_contact_frame=np.mean(contact_frames),
            avg_engagement_duration=np.mean(durations),
            avg_ol_displacement=np.mean(ol_displacements),
            avg_dl_penetration=np.mean(dl_penetrations),
            shed_rate=sum(1 for e in engagements if e.shed_occurred) / len(engagements),
            avg_shed_time=np.mean(shed_times) if shed_times else 0,
        )
    }


# =============================================================================
# Main Analysis
# =============================================================================

def run_detailed_analysis():
    """Run detailed analysis and export results."""
    print("Loading passing plays for route analysis...")
    passing_plays = load_plays_by_type('play_type_pass', limit=200)
    print(f"Loaded {len(passing_plays)} passing plays")

    print("Loading rushing plays for OL/DL analysis...")
    rushing_plays = load_plays_by_type('play_type_rush', limit=100)
    print(f"Loaded {len(rushing_plays)} rushing plays")

    all_plays = passing_plays + rushing_plays

    print("\nAnalyzing route trajectories...")
    routes = analyze_routes(passing_plays)

    print("Analyzing momentum profiles...")
    momentum = analyze_momentum(all_plays)

    print("Analyzing OL/DL engagements...")
    ol_dl = analyze_ol_dl(rushing_plays)

    # Build export
    export = {
        "meta": {
            "source": "ngs_highlights detailed analysis",
            "passing_plays": len(passing_plays),
            "rushing_plays": len(rushing_plays),
        },
        "route_trajectories": {
            route_type: {
                "count": len(routes_list),
                "avg_depth": round(np.mean([r.max_depth for r in routes_list]), 1),
                "avg_lateral": round(np.mean([r.lateral_movement for r in routes_list]), 1),
                "avg_total_distance": round(np.mean([r.total_distance for r in routes_list]), 1),
                "avg_break_frame": round(np.mean([r.break_frame for r in routes_list if r.break_frame]), 1) if any(r.break_frame for r in routes_list) else None,
                "avg_break_angle": round(np.mean([r.break_angle for r in routes_list if r.break_angle]), 1) if any(r.break_angle for r in routes_list) else None,
                "example_trajectory": [
                    {"x": round(p[0], 2), "y": round(p[1], 2)}
                    for p in routes_list[0].frames[:30]
                ] if routes_list else [],
                "example_velocities": [round(v, 2) for v in routes_list[0].velocities[:30]] if routes_list else [],
            }
            for route_type, routes_list in routes.items()
            if len(routes_list) >= 3
        },
        "momentum_by_position": {
            pos: {
                "avg_weight_lbs": round(m.avg_weight_lbs, 0),
                "max_momentum_lbs_yps": round(m.max_momentum, 0),
                "momentum_at_contact_lbs_yps": round(m.momentum_at_contact, 0),
                "deceleration_rate_lbs_yps2": round(m.deceleration_rate, 0),
                "time_to_max_momentum_sec": round(m.time_to_max_momentum, 2),
            }
            for pos, m in momentum.items()
        },
        "ol_dl_engagements": {
            matchup: {
                "sample_size": stats.sample_size,
                "avg_contact_time_sec": round(stats.avg_contact_frame * 0.1, 2),
                "avg_engagement_duration_sec": round(stats.avg_engagement_duration * 0.1, 2),
                "avg_ol_displacement_yds": round(stats.avg_ol_displacement, 2),
                "avg_dl_penetration_yds": round(stats.avg_dl_penetration, 2),
                "shed_rate": round(stats.shed_rate, 3),
                "avg_shed_time_sec": round(stats.avg_shed_time * 0.1, 2),
            }
            for matchup, stats in ol_dl.items()
        },
        "implementation_notes": {
            "route_trajectories": "x/y coordinates relative to snap position, sampled at 10 FPS",
            "momentum": "Calculated as weight_lbs * speed_yps, useful for contact resolution",
            "ol_dl": "Contact = within 1.5 yards, Shed = separation > 3 yards after contact",
            "calibration_targets": [
                "Route break timing should match avg_break_frame (~1.5-2.5 sec after snap)",
                "Speed at break should drop to ~60-70% then recover",
                "OL should absorb initial contact, DL penetration averages 1-2 yards",
                "Block shed takes ~1-2 seconds on average",
                "Heavier players have more momentum, harder to redirect",
            ],
        },
    }

    # Print summary
    print("\n" + "="*60)
    print("ROUTE TYPES FOUND")
    print("="*60)
    for route_type, routes_list in sorted(routes.items(), key=lambda x: -len(x[1])):
        if len(routes_list) >= 3:
            avg_depth = np.mean([r.max_depth for r in routes_list])
            avg_break = np.mean([r.break_frame for r in routes_list if r.break_frame]) if any(r.break_frame for r in routes_list) else 0
            print(f"{route_type:12s}: n={len(routes_list):3d}, avg_depth={avg_depth:.1f} yds, "
                  f"break_frame={avg_break:.0f} ({avg_break*0.1:.1f}s)")

    print("\n" + "="*60)
    print("MOMENTUM BY POSITION")
    print("="*60)
    for pos in ['RB', 'WR', 'TE', 'LB', 'DT', 'DE']:
        if pos in momentum:
            m = momentum[pos]
            print(f"{pos:4s}: weight={m.avg_weight_lbs:.0f}lbs, "
                  f"max_momentum={m.max_momentum:.0f} lbs·yps, "
                  f"time_to_max={m.time_to_max_momentum:.2f}s")

    print("\n" + "="*60)
    print("OL/DL ENGAGEMENT STATS")
    print("="*60)
    if 'all' in ol_dl:
        s = ol_dl['all']
        print(f"Sample size: {s.sample_size}")
        print(f"Contact time after snap: {s.avg_contact_frame * 0.1:.2f}s")
        print(f"Engagement duration: {s.avg_engagement_duration * 0.1:.2f}s")
        print(f"OL displacement: {s.avg_ol_displacement:.2f} yards")
        print(f"DL penetration: {s.avg_dl_penetration:.2f} yards")
        print(f"Shed rate: {s.shed_rate:.1%}")
        print(f"Time to shed: {s.avg_shed_time * 0.1:.2f}s")

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "ngs_detailed_movement.json"

    with open(export_path, 'w') as f:
        json.dump(export, f, indent=2)

    print(f"\nExported to {export_path}")

    return export


if __name__ == "__main__":
    run_detailed_analysis()

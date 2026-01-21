"""NGS Physics Analysis - Movement Curvature, Momentum, Jukes, OL/DL.

Deep analysis of player movement physics for V2 simulation calibration:
1. Path curvature - how sharply players can turn at speed
2. Juke/move detection - sudden direction changes and speed effects
3. Momentum dynamics - how mass affects direction changes
4. OL/DL engagement - blocking physics over short time windows
5. Post-catch movement - YAC momentum and evasion patterns

Data source: https://github.com/asonty/ngs_highlights
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings

import pandas as pd
import numpy as np
from scipy import signal
from scipy.ndimage import gaussian_filter1d

warnings.filterwarnings('ignore')

# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "ngs_highlights" / "play_data"
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports" / "reference" / "simulation"

FRAME_RATE = 10  # FPS
DT = 0.1  # seconds per frame

# Position weights (lbs)
POSITION_WEIGHTS = {
    "QB": 220, "RB": 215, "FB": 245, "WR": 195, "TE": 250,
    "T": 315, "G": 315, "C": 305, "OT": 315, "OG": 315,
    "DT": 305, "DE": 270, "NT": 325,
    "LB": 240, "OLB": 240, "ILB": 245, "MLB": 245,
    "CB": 195, "S": 205, "SS": 210, "FS": 200,
}

POSITION_GROUPS = {
    "QB": ["QB"], "RB": ["RB", "FB"], "WR": ["WR"], "TE": ["TE"],
    "OL": ["T", "G", "C", "OT", "OG"],
    "DL": ["DT", "DE", "NT"],
    "LB": ["LB", "OLB", "ILB", "MLB"],
    "CB": ["CB"], "S": ["S", "SS", "FS"],
}

def get_position_group(pos: str) -> str:
    for group, positions in POSITION_GROUPS.items():
        if pos in positions:
            return group
    return "OTHER"

def get_weight(pos: str) -> float:
    return POSITION_WEIGHTS.get(pos, 220)


# =============================================================================
# Data Loading
# =============================================================================

def load_all_plays(limit: Optional[int] = None) -> List[pd.DataFrame]:
    """Load all plays."""
    plays = []
    files = sorted(DATA_DIR.glob("*.tsv"))
    if limit:
        files = files[:limit]

    for f in files:
        try:
            # Skip index file
            if 'index' in f.name.lower():
                continue
            df = pd.read_csv(f, sep='\t', low_memory=False)
            # Verify it has required columns
            if 'event' not in df.columns or 'frame' not in df.columns:
                continue
            df['source_file'] = f.name
            plays.append(df)
        except:
            continue
    return plays


# =============================================================================
# Curvature Analysis
# =============================================================================

def compute_curvature(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Compute path curvature at each point.

    Curvature κ = |x'y'' - y'x''| / (x'² + y'²)^(3/2)

    Returns curvature in radians per yard (1/radius of curvature).
    """
    # Smooth the path slightly to reduce noise
    x_smooth = gaussian_filter1d(x, sigma=1)
    y_smooth = gaussian_filter1d(y, sigma=1)

    # First derivatives (velocity)
    dx = np.gradient(x_smooth, DT)
    dy = np.gradient(y_smooth, DT)

    # Second derivatives (acceleration)
    ddx = np.gradient(dx, DT)
    ddy = np.gradient(dy, DT)

    # Curvature formula
    numerator = np.abs(dx * ddy - dy * ddx)
    denominator = (dx**2 + dy**2)**1.5

    # Avoid division by zero
    curvature = np.where(denominator > 0.01, numerator / denominator, 0)

    return curvature


def compute_turn_rate(directions: np.ndarray) -> np.ndarray:
    """Compute rate of direction change (degrees per second)."""
    # Handle wraparound at 360
    dir_diff = np.diff(directions)
    dir_diff = np.where(dir_diff > 180, dir_diff - 360, dir_diff)
    dir_diff = np.where(dir_diff < -180, dir_diff + 360, dir_diff)

    turn_rate = np.abs(dir_diff) / DT  # degrees per second
    return np.concatenate([[0], turn_rate])


@dataclass
class CurvatureStats:
    """Curvature statistics for a position."""
    position_group: str
    sample_size: int
    # Curvature while running (speed > 3 yps)
    curvature_mean: float  # 1/yards (inverse of turn radius)
    curvature_p50: float
    curvature_p90: float
    curvature_p99: float
    # Turn rate
    turn_rate_mean: float  # degrees/second
    turn_rate_max_mean: float
    # Speed vs curvature relationship
    curvature_at_max_speed: float
    max_curvature_at_speed: Dict[str, float]  # speed bucket -> max curvature


def analyze_curvature(plays: List[pd.DataFrame]) -> Dict[str, CurvatureStats]:
    """Analyze path curvature by position."""
    curvature_data = defaultdict(lambda: {
        'curvatures': [], 'turn_rates': [], 'max_turn_rates': [],
        'curvature_at_max_speed': [], 'speed_curvature_pairs': []
    })

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        for player_name in play_df['displayName'].unique():
            player_df = play_df[play_df['displayName'] == player_name]
            player_df = player_df[player_df['frame'] >= snap_frame].sort_values('frame')

            if len(player_df) < 20:
                continue

            pos = player_df['position'].iloc[0]
            if pd.isna(pos):
                continue
            pos_group = get_position_group(pos)
            if pos_group == "OTHER":
                continue

            x = player_df['x'].values
            y = player_df['y'].values
            speeds = player_df['s'].values
            directions = player_df['dir'].values

            # Compute curvature
            curvature = compute_curvature(x, y)
            turn_rate = compute_turn_rate(directions)

            # Only count when moving (speed > 3 yps)
            moving_mask = speeds > 3.0
            if moving_mask.sum() < 5:
                continue

            moving_curvature = curvature[moving_mask]
            moving_turn_rate = turn_rate[moving_mask]
            moving_speeds = speeds[moving_mask]

            curvature_data[pos_group]['curvatures'].extend(moving_curvature)
            curvature_data[pos_group]['turn_rates'].extend(moving_turn_rate)
            curvature_data[pos_group]['max_turn_rates'].append(moving_turn_rate.max())

            # Curvature at max speed
            max_speed_idx = np.argmax(speeds)
            if max_speed_idx > 0 and max_speed_idx < len(curvature) - 1:
                curvature_data[pos_group]['curvature_at_max_speed'].append(curvature[max_speed_idx])

            # Speed-curvature pairs for relationship analysis
            for s, c in zip(moving_speeds, moving_curvature):
                curvature_data[pos_group]['speed_curvature_pairs'].append((s, c))

    results = {}
    for pos_group, data in curvature_data.items():
        curvatures = np.array(data['curvatures'])
        turn_rates = np.array(data['turn_rates'])

        if len(curvatures) < 100:
            continue

        # Compute max curvature at different speed buckets
        speed_curvature = defaultdict(list)
        for s, c in data['speed_curvature_pairs']:
            if s < 4:
                speed_curvature['slow_0-4'].append(c)
            elif s < 6:
                speed_curvature['medium_4-6'].append(c)
            elif s < 8:
                speed_curvature['fast_6-8'].append(c)
            else:
                speed_curvature['sprint_8+'].append(c)

        max_curvature_by_speed = {
            bucket: float(np.percentile(curves, 95)) if curves else 0
            for bucket, curves in speed_curvature.items()
        }

        results[pos_group] = CurvatureStats(
            position_group=pos_group,
            sample_size=len(curvatures),
            curvature_mean=float(np.mean(curvatures)),
            curvature_p50=float(np.percentile(curvatures, 50)),
            curvature_p90=float(np.percentile(curvatures, 90)),
            curvature_p99=float(np.percentile(curvatures, 99)),
            turn_rate_mean=float(np.mean(turn_rates)),
            turn_rate_max_mean=float(np.mean(data['max_turn_rates'])) if data['max_turn_rates'] else 0,
            curvature_at_max_speed=float(np.mean(data['curvature_at_max_speed'])) if data['curvature_at_max_speed'] else 0,
            max_curvature_at_speed=max_curvature_by_speed,
        )

    return results


# =============================================================================
# Juke/Move Detection
# =============================================================================

@dataclass
class JukeEvent:
    """A detected juke/move."""
    frame: int
    position: str
    speed_before: float
    speed_during: float
    speed_after: float
    direction_change: float  # degrees
    duration_frames: int
    speed_retention: float  # speed_after / speed_before
    lateral_displacement: float  # yards moved sideways


@dataclass
class JukeStats:
    """Juke/move statistics by position."""
    position_group: str
    total_jukes: int
    jukes_per_play: float
    avg_direction_change: float
    avg_speed_before: float
    avg_speed_during: float  # Speed at moment of juke
    avg_speed_after: float
    avg_speed_retention: float
    avg_recovery_time_sec: float
    avg_lateral_displacement: float
    # By intensity
    small_cuts_30_60: Dict[str, float]  # 30-60 degree cuts
    medium_cuts_60_90: Dict[str, float]  # 60-90 degree cuts
    hard_cuts_90_plus: Dict[str, float]  # 90+ degree cuts


def detect_jukes(plays: List[pd.DataFrame]) -> Dict[str, JukeStats]:
    """Detect and analyze jukes/moves by position."""
    jukes_by_position = defaultdict(list)
    plays_by_position = defaultdict(int)

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        for player_name in play_df['displayName'].unique():
            player_df = play_df[play_df['displayName'] == player_name]
            player_df = player_df[player_df['frame'] >= snap_frame].sort_values('frame')

            if len(player_df) < 15:
                continue

            pos = player_df['position'].iloc[0]
            if pd.isna(pos):
                continue
            pos_group = get_position_group(pos)
            if pos_group == "OTHER":
                continue

            plays_by_position[pos_group] += 1

            speeds = player_df['s'].values
            directions = player_df['dir'].values
            x = player_df['x'].values
            y = player_df['y'].values
            frames = player_df['frame'].values

            # Detect jukes: rapid direction change while moving fast
            i = 5
            while i < len(directions) - 10:
                # Must be moving fast (>4 yps)
                if speeds[i] < 4.0:
                    i += 1
                    continue

                # Look for direction change over 3-5 frames
                dir_before = np.mean(directions[i-3:i])
                dir_after = np.mean(directions[i+2:i+5])

                dir_change = abs(dir_after - dir_before)
                if dir_change > 180:
                    dir_change = 360 - dir_change

                # Significant juke = 30+ degrees while moving fast
                if dir_change >= 30:
                    # Find speed minimum during juke
                    speed_window = speeds[i-2:i+5]
                    min_speed_idx = np.argmin(speed_window)
                    speed_during = speed_window[min_speed_idx]

                    speed_before = np.mean(speeds[i-3:i])

                    # Find speed recovery
                    speed_after = speed_before  # default
                    recovery_frames = 10
                    for j in range(i+3, min(i+20, len(speeds))):
                        if speeds[j] >= speed_before * 0.9:
                            speed_after = speeds[j]
                            recovery_frames = j - i
                            break
                    else:
                        speed_after = np.mean(speeds[i+5:i+10]) if i+10 < len(speeds) else speeds[-1]

                    # Lateral displacement
                    lateral = abs(y[i+5] - y[i-2]) if i+5 < len(y) else 0

                    juke = JukeEvent(
                        frame=int(frames[i]),
                        position=pos_group,
                        speed_before=float(speed_before),
                        speed_during=float(speed_during),
                        speed_after=float(speed_after),
                        direction_change=float(dir_change),
                        duration_frames=recovery_frames,
                        speed_retention=float(speed_after / speed_before) if speed_before > 0 else 1,
                        lateral_displacement=float(lateral),
                    )
                    jukes_by_position[pos_group].append(juke)

                    # Skip ahead to avoid double-counting
                    i += 8
                else:
                    i += 1

    results = {}
    for pos_group, jukes in jukes_by_position.items():
        if len(jukes) < 10:
            continue

        # Categorize by intensity
        small_cuts = [j for j in jukes if 30 <= j.direction_change < 60]
        medium_cuts = [j for j in jukes if 60 <= j.direction_change < 90]
        hard_cuts = [j for j in jukes if j.direction_change >= 90]

        def cut_stats(cuts):
            if not cuts:
                return {"count": 0, "avg_speed_retention": 0, "avg_recovery_sec": 0}
            return {
                "count": len(cuts),
                "avg_speed_retention": round(np.mean([c.speed_retention for c in cuts]), 3),
                "avg_speed_drop": round(1 - np.mean([c.speed_during / c.speed_before for c in cuts if c.speed_before > 0]), 3),
                "avg_recovery_sec": round(np.mean([c.duration_frames for c in cuts]) * DT, 2),
            }

        results[pos_group] = JukeStats(
            position_group=pos_group,
            total_jukes=len(jukes),
            jukes_per_play=len(jukes) / max(plays_by_position[pos_group], 1),
            avg_direction_change=float(np.mean([j.direction_change for j in jukes])),
            avg_speed_before=float(np.mean([j.speed_before for j in jukes])),
            avg_speed_during=float(np.mean([j.speed_during for j in jukes])),
            avg_speed_after=float(np.mean([j.speed_after for j in jukes])),
            avg_speed_retention=float(np.mean([j.speed_retention for j in jukes])),
            avg_recovery_time_sec=float(np.mean([j.duration_frames for j in jukes]) * DT),
            avg_lateral_displacement=float(np.mean([j.lateral_displacement for j in jukes])),
            small_cuts_30_60=cut_stats(small_cuts),
            medium_cuts_60_90=cut_stats(medium_cuts),
            hard_cuts_90_plus=cut_stats(hard_cuts),
        )

    return results


# =============================================================================
# OL/DL Engagement Physics
# =============================================================================

@dataclass
class EngagementPhysics:
    """Physics of a single OL/DL engagement."""
    ol_position: str
    dl_position: str
    # Pre-contact
    closing_speed: float  # relative velocity at contact
    dl_momentum_at_contact: float
    ol_momentum_at_contact: float
    # Contact phase (first 1 second)
    contact_duration_sec: float
    ol_displacement_1sec: float  # how far OL pushed back in first second
    dl_penetration_1sec: float  # how far DL got in first second
    # Sustained phase
    avg_ol_velocity: float  # during engagement
    avg_dl_velocity: float
    # Outcome
    winner: str  # 'OL' or 'DL' based on net displacement


@dataclass
class OLDLPhysicsStats:
    """Aggregate OL/DL physics statistics."""
    sample_size: int
    # Contact
    avg_closing_speed: float
    avg_dl_momentum_at_contact: float
    avg_ol_momentum_at_contact: float
    # First second outcomes
    avg_ol_displacement_1sec: float
    avg_dl_penetration_1sec: float
    ol_win_rate: float  # % where OL holds ground
    # Velocity during engagement
    avg_ol_velocity_engaged: float
    avg_dl_velocity_engaged: float
    # By matchup type
    interior_stats: Dict[str, float]  # G/C vs DT
    edge_stats: Dict[str, float]  # T vs DE


def analyze_ol_dl_physics(plays: List[pd.DataFrame]) -> OLDLPhysicsStats:
    """Analyze OL/DL engagement physics."""
    engagements = []

    ol_positions = {'T', 'G', 'C', 'OT', 'OG'}
    dl_positions = {'DT', 'DE', 'NT'}

    rush_plays = [p for p in plays if p['playType'].iloc[0] in ['play_type_rush', 'play_type_pass']]

    for play_df in rush_plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        play_dir = play_df['playDirection'].iloc[0]

        # Get all OL and DL
        ol_players = play_df[play_df['position'].isin(ol_positions)]['displayName'].unique()
        dl_players = play_df[play_df['position'].isin(dl_positions)]['displayName'].unique()

        for ol_name in ol_players:
            ol_df = play_df[play_df['displayName'] == ol_name].sort_values('frame')
            ol_at_snap = ol_df[ol_df['frame'] == snap_frame]
            if len(ol_at_snap) == 0:
                continue

            ol_pos = ol_df['position'].iloc[0]
            ol_weight = get_weight(ol_pos)
            ol_snap_x = ol_at_snap['x'].iloc[0]
            ol_snap_y = ol_at_snap['y'].iloc[0]

            # Find closest DL at snap
            best_dl = None
            best_dist = float('inf')

            for dl_name in dl_players:
                dl_df = play_df[play_df['displayName'] == dl_name].sort_values('frame')
                dl_at_snap = dl_df[dl_df['frame'] == snap_frame]
                if len(dl_at_snap) == 0:
                    continue

                dl_snap_x = dl_at_snap['x'].iloc[0]
                dl_snap_y = dl_at_snap['y'].iloc[0]

                dist = math.sqrt((ol_snap_x - dl_snap_x)**2 + (ol_snap_y - dl_snap_y)**2)

                if dist < best_dist and dist < 2.5:  # Must be lined up close
                    best_dist = dist
                    best_dl = dl_name

            if best_dl is None:
                continue

            dl_df = play_df[play_df['displayName'] == best_dl].sort_values('frame')
            dl_pos = dl_df['position'].iloc[0]
            dl_weight = get_weight(dl_pos)

            # Get post-snap data (first 2 seconds = 20 frames)
            ol_post = ol_df[(ol_df['frame'] >= snap_frame) & (ol_df['frame'] <= snap_frame + 20)]
            dl_post = dl_df[(dl_df['frame'] >= snap_frame) & (dl_df['frame'] <= snap_frame + 20)]

            if len(ol_post) < 10 or len(dl_post) < 10:
                continue

            # Find contact frame (when distance is minimum)
            ol_xs = ol_post['x'].values
            ol_ys = ol_post['y'].values
            ol_speeds = ol_post['s'].values

            dl_xs = dl_post['x'].values
            dl_ys = dl_post['y'].values
            dl_speeds = dl_post['s'].values

            # Align frames
            min_len = min(len(ol_xs), len(dl_xs))
            ol_xs, ol_ys, ol_speeds = ol_xs[:min_len], ol_ys[:min_len], ol_speeds[:min_len]
            dl_xs, dl_ys, dl_speeds = dl_xs[:min_len], dl_ys[:min_len], dl_speeds[:min_len]

            distances = np.sqrt((ol_xs - dl_xs)**2 + (ol_ys - dl_ys)**2)
            contact_frame_idx = np.argmin(distances)

            if contact_frame_idx < 2 or contact_frame_idx >= min_len - 10:
                continue

            # Closing speed (relative velocity toward each other)
            if contact_frame_idx > 0:
                ol_vx = (ol_xs[contact_frame_idx] - ol_xs[contact_frame_idx-1]) / DT
                ol_vy = (ol_ys[contact_frame_idx] - ol_ys[contact_frame_idx-1]) / DT
                dl_vx = (dl_xs[contact_frame_idx] - dl_xs[contact_frame_idx-1]) / DT
                dl_vy = (dl_ys[contact_frame_idx] - dl_ys[contact_frame_idx-1]) / DT

                # Closing speed = component of relative velocity along line between them
                dx = dl_xs[contact_frame_idx] - ol_xs[contact_frame_idx]
                dy = dl_ys[contact_frame_idx] - ol_ys[contact_frame_idx]
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0:
                    rel_vx = dl_vx - ol_vx
                    rel_vy = dl_vy - ol_vy
                    closing_speed = abs(rel_vx * dx/dist + rel_vy * dy/dist)
                else:
                    closing_speed = 0
            else:
                closing_speed = 0

            # Momentum at contact
            ol_momentum = ol_weight * ol_speeds[contact_frame_idx]
            dl_momentum = dl_weight * dl_speeds[contact_frame_idx]

            # Displacement in first 10 frames (1 second) after contact
            end_idx = min(contact_frame_idx + 10, min_len - 1)

            ol_displacement = ol_xs[end_idx] - ol_xs[contact_frame_idx]
            dl_displacement = dl_xs[end_idx] - dl_xs[contact_frame_idx]

            # Adjust for play direction (positive = toward offense's goal)
            if play_dir == 'left':
                ol_pushed_back = ol_displacement  # positive = pushed back
                dl_penetration = -dl_displacement  # negative x = penetration
            else:
                ol_pushed_back = -ol_displacement
                dl_penetration = dl_displacement

            # Average velocity during engagement
            avg_ol_vel = np.mean(ol_speeds[contact_frame_idx:end_idx])
            avg_dl_vel = np.mean(dl_speeds[contact_frame_idx:end_idx])

            # Winner: who gained ground?
            winner = 'DL' if dl_penetration > ol_pushed_back else 'OL'

            engagement = EngagementPhysics(
                ol_position=ol_pos,
                dl_position=dl_pos,
                closing_speed=closing_speed,
                dl_momentum_at_contact=dl_momentum,
                ol_momentum_at_contact=ol_momentum,
                contact_duration_sec=1.0,
                ol_displacement_1sec=ol_pushed_back,
                dl_penetration_1sec=dl_penetration,
                avg_ol_velocity=avg_ol_vel,
                avg_dl_velocity=avg_dl_vel,
                winner=winner,
            )
            engagements.append(engagement)

    if not engagements:
        return None

    # Aggregate stats
    interior = [e for e in engagements if e.ol_position in ['G', 'C', 'OG'] and e.dl_position in ['DT', 'NT']]
    edge = [e for e in engagements if e.ol_position in ['T', 'OT'] and e.dl_position == 'DE']

    def matchup_stats(engs):
        if not engs:
            return {"count": 0}
        return {
            "count": len(engs),
            "avg_ol_displacement": round(np.mean([e.ol_displacement_1sec for e in engs]), 2),
            "avg_dl_penetration": round(np.mean([e.dl_penetration_1sec for e in engs]), 2),
            "ol_win_rate": round(sum(1 for e in engs if e.winner == 'OL') / len(engs), 3),
        }

    return OLDLPhysicsStats(
        sample_size=len(engagements),
        avg_closing_speed=float(np.mean([e.closing_speed for e in engagements])),
        avg_dl_momentum_at_contact=float(np.mean([e.dl_momentum_at_contact for e in engagements])),
        avg_ol_momentum_at_contact=float(np.mean([e.ol_momentum_at_contact for e in engagements])),
        avg_ol_displacement_1sec=float(np.mean([e.ol_displacement_1sec for e in engagements])),
        avg_dl_penetration_1sec=float(np.mean([e.dl_penetration_1sec for e in engagements])),
        ol_win_rate=sum(1 for e in engagements if e.winner == 'OL') / len(engagements),
        avg_ol_velocity_engaged=float(np.mean([e.avg_ol_velocity for e in engagements])),
        avg_dl_velocity_engaged=float(np.mean([e.avg_dl_velocity for e in engagements])),
        interior_stats=matchup_stats(interior),
        edge_stats=matchup_stats(edge),
    )


# =============================================================================
# Post-Catch Movement Analysis
# =============================================================================

@dataclass
class PostCatchStats:
    """Post-catch (YAC) movement statistics."""
    sample_size: int
    avg_speed_at_catch: float
    avg_speed_1sec_after: float
    avg_max_speed_after: float
    avg_direction_changes: int  # jukes after catch
    avg_yac_yards: float
    # Momentum
    avg_momentum_at_catch: float
    momentum_retention_1sec: float
    # Evasion success
    evaded_first_defender_rate: float


def analyze_post_catch(plays: List[pd.DataFrame]) -> PostCatchStats:
    """Analyze receiver movement after catch."""
    passing_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_pass']

    catch_events = []

    for play_df in passing_plays:
        # Find catch event
        catch_rows = play_df[play_df['event'].isin(['pass_outcome_caught', 'catch'])]
        if len(catch_rows) == 0:
            # Look for first_contact as proxy for catch
            catch_rows = play_df[play_df['event'] == 'first_contact']
        if len(catch_rows) == 0:
            continue

        catch_frame = catch_rows['frame'].iloc[0]

        # Find receivers
        receivers = play_df[play_df['position'].isin(['WR', 'TE', 'RB'])]

        for rec_name in receivers['displayName'].unique():
            rec_df = play_df[play_df['displayName'] == rec_name].sort_values('frame')

            # Get data around catch
            at_catch = rec_df[rec_df['frame'] == catch_frame]
            after_catch = rec_df[(rec_df['frame'] > catch_frame) & (rec_df['frame'] <= catch_frame + 30)]

            if len(at_catch) == 0 or len(after_catch) < 5:
                continue

            pos = rec_df['position'].iloc[0]
            weight = get_weight(pos)

            speed_at_catch = at_catch['s'].iloc[0]

            # Skip if not moving much (probably not the receiver)
            if speed_at_catch < 2:
                continue

            speeds_after = after_catch['s'].values
            dirs_after = after_catch['dir'].values
            x_after = after_catch['x'].values

            speed_1sec = speeds_after[min(9, len(speeds_after)-1)]
            max_speed = speeds_after.max()

            # Count direction changes (jukes)
            dir_changes = 0
            for i in range(3, len(dirs_after) - 3):
                d1 = np.mean(dirs_after[i-3:i])
                d2 = np.mean(dirs_after[i:i+3])
                change = abs(d2 - d1)
                if change > 180:
                    change = 360 - change
                if change > 30:
                    dir_changes += 1

            # YAC (approximate from x displacement)
            yac = abs(x_after[-1] - x_after[0]) if len(x_after) > 1 else 0

            # Momentum
            momentum_at_catch = weight * speed_at_catch
            momentum_1sec = weight * speed_1sec

            catch_events.append({
                'speed_at_catch': speed_at_catch,
                'speed_1sec': speed_1sec,
                'max_speed': max_speed,
                'dir_changes': dir_changes,
                'yac': yac,
                'momentum_at_catch': momentum_at_catch,
                'momentum_1sec': momentum_1sec,
            })

    if not catch_events:
        return None

    return PostCatchStats(
        sample_size=len(catch_events),
        avg_speed_at_catch=float(np.mean([e['speed_at_catch'] for e in catch_events])),
        avg_speed_1sec_after=float(np.mean([e['speed_1sec'] for e in catch_events])),
        avg_max_speed_after=float(np.mean([e['max_speed'] for e in catch_events])),
        avg_direction_changes=int(np.mean([e['dir_changes'] for e in catch_events])),
        avg_yac_yards=float(np.mean([e['yac'] for e in catch_events])),
        avg_momentum_at_catch=float(np.mean([e['momentum_at_catch'] for e in catch_events])),
        momentum_retention_1sec=float(np.mean([e['momentum_1sec']/e['momentum_at_catch'] for e in catch_events if e['momentum_at_catch'] > 0])),
        evaded_first_defender_rate=0.0,  # Would need defender tracking
    )


# =============================================================================
# Main
# =============================================================================

def run_physics_analysis():
    """Run all physics analyses."""
    print("Loading plays...")
    plays = load_all_plays(limit=None)  # Load all
    print(f"Loaded {len(plays)} plays")

    print("\nAnalyzing path curvature...")
    curvature_stats = analyze_curvature(plays)

    print("Detecting jukes/moves...")
    juke_stats = detect_jukes(plays)

    print("Analyzing OL/DL physics...")
    ol_dl_stats = analyze_ol_dl_physics(plays)

    print("Analyzing post-catch movement...")
    post_catch_stats = analyze_post_catch(plays)

    # Build export
    export = {
        "meta": {
            "source": "ngs_highlights physics analysis",
            "plays_analyzed": len(plays),
            "frame_rate_fps": FRAME_RATE,
        },
        "curvature_by_position": {
            pos: {
                "sample_size": s.sample_size,
                "curvature_mean_inv_yds": round(s.curvature_mean, 4),
                "curvature_p90_inv_yds": round(s.curvature_p90, 4),
                "turn_radius_mean_yds": round(1/s.curvature_mean, 1) if s.curvature_mean > 0.001 else 999,
                "turn_radius_min_p90_yds": round(1/s.curvature_p90, 1) if s.curvature_p90 > 0.001 else 999,
                "turn_rate_mean_deg_sec": round(s.turn_rate_mean, 1),
                "turn_rate_max_mean_deg_sec": round(s.turn_rate_max_mean, 1),
                "max_curvature_by_speed": {
                    k: round(v, 4) for k, v in s.max_curvature_at_speed.items()
                },
            }
            for pos, s in curvature_stats.items()
        },
        "jukes_by_position": {
            pos: {
                "total_jukes": s.total_jukes,
                "jukes_per_play": round(s.jukes_per_play, 2),
                "avg_direction_change_deg": round(s.avg_direction_change, 1),
                "avg_speed_before_yps": round(s.avg_speed_before, 2),
                "avg_speed_during_yps": round(s.avg_speed_during, 2),
                "avg_speed_retention": round(s.avg_speed_retention, 3),
                "avg_recovery_time_sec": round(s.avg_recovery_time_sec, 2),
                "avg_lateral_displacement_yds": round(s.avg_lateral_displacement, 2),
                "small_cuts_30_60": s.small_cuts_30_60,
                "medium_cuts_60_90": s.medium_cuts_60_90,
                "hard_cuts_90_plus": s.hard_cuts_90_plus,
            }
            for pos, s in juke_stats.items()
        },
        "ol_dl_physics": {
            "sample_size": ol_dl_stats.sample_size if ol_dl_stats else 0,
            "avg_closing_speed_yps": round(ol_dl_stats.avg_closing_speed, 2) if ol_dl_stats else 0,
            "avg_dl_momentum_at_contact": round(ol_dl_stats.avg_dl_momentum_at_contact, 0) if ol_dl_stats else 0,
            "avg_ol_momentum_at_contact": round(ol_dl_stats.avg_ol_momentum_at_contact, 0) if ol_dl_stats else 0,
            "avg_ol_displacement_1sec_yds": round(ol_dl_stats.avg_ol_displacement_1sec, 2) if ol_dl_stats else 0,
            "avg_dl_penetration_1sec_yds": round(ol_dl_stats.avg_dl_penetration_1sec, 2) if ol_dl_stats else 0,
            "ol_win_rate": round(ol_dl_stats.ol_win_rate, 3) if ol_dl_stats else 0,
            "avg_velocity_while_engaged": {
                "ol_yps": round(ol_dl_stats.avg_ol_velocity_engaged, 2) if ol_dl_stats else 0,
                "dl_yps": round(ol_dl_stats.avg_dl_velocity_engaged, 2) if ol_dl_stats else 0,
            },
            "interior_matchups": ol_dl_stats.interior_stats if ol_dl_stats else {},
            "edge_matchups": ol_dl_stats.edge_stats if ol_dl_stats else {},
        } if ol_dl_stats else {},
        "post_catch_movement": {
            "sample_size": post_catch_stats.sample_size if post_catch_stats else 0,
            "avg_speed_at_catch_yps": round(post_catch_stats.avg_speed_at_catch, 2) if post_catch_stats else 0,
            "avg_speed_1sec_after_yps": round(post_catch_stats.avg_speed_1sec_after, 2) if post_catch_stats else 0,
            "avg_max_speed_after_yps": round(post_catch_stats.avg_max_speed_after, 2) if post_catch_stats else 0,
            "avg_direction_changes_after": post_catch_stats.avg_direction_changes if post_catch_stats else 0,
            "avg_yac_yards": round(post_catch_stats.avg_yac_yards, 1) if post_catch_stats else 0,
            "avg_momentum_at_catch": round(post_catch_stats.avg_momentum_at_catch, 0) if post_catch_stats else 0,
            "momentum_retention_1sec": round(post_catch_stats.momentum_retention_1sec, 3) if post_catch_stats else 0,
        } if post_catch_stats else {},
        "implementation_notes": {
            "curvature": "Inverse of turn radius in yards. Higher = tighter turns. Use max_curvature_by_speed to limit turn sharpness at high speeds.",
            "turn_rate": "Degrees per second of direction change. Limit this based on speed for realistic movement.",
            "jukes": "Sudden direction changes. Speed drops during juke, recovers in 0.5-1.0 sec. Heavier players have lower speed retention.",
            "ol_dl": "Contact physics. DL penetration vs OL displacement determines run lane. Momentum at contact matters.",
            "post_catch": "Receivers maintain ~90% momentum after catch. Average 1-2 direction changes during YAC.",
            "calibration_formula": {
                "max_turn_rate": "base_turn_rate * (1 - speed/max_speed)^0.5",
                "speed_during_cut": "speed_before * (1 - cut_angle/180 * 0.3)",
                "momentum_effect": "heavier players: slower cuts, harder to redirect",
            },
        },
    }

    # Print summary
    print("\n" + "="*70)
    print("CURVATURE BY POSITION (turn radius in yards)")
    print("="*70)
    for pos, s in sorted(curvature_stats.items(), key=lambda x: -x[1].turn_rate_max_mean):
        radius = 1/s.curvature_p90 if s.curvature_p90 > 0.001 else 999
        print(f"{pos:4s}: turn_rate={s.turn_rate_mean:.0f}°/s (max {s.turn_rate_max_mean:.0f}°/s), "
              f"min_radius={radius:.1f} yds")

    print("\n" + "="*70)
    print("JUKE ANALYSIS")
    print("="*70)
    for pos in ['RB', 'WR', 'TE', 'QB']:
        if pos in juke_stats:
            s = juke_stats[pos]
            print(f"{pos:4s}: {s.total_jukes} jukes ({s.jukes_per_play:.1f}/play), "
                  f"avg {s.avg_direction_change:.0f}°, "
                  f"speed retention={s.avg_speed_retention:.1%}, "
                  f"recovery={s.avg_recovery_time_sec:.2f}s")
            print(f"       30-60°: {s.small_cuts_30_60['count']} cuts, retention={s.small_cuts_30_60.get('avg_speed_retention', 0):.1%}")
            print(f"       60-90°: {s.medium_cuts_60_90['count']} cuts, retention={s.medium_cuts_60_90.get('avg_speed_retention', 0):.1%}")
            print(f"       90°+:   {s.hard_cuts_90_plus['count']} cuts, retention={s.hard_cuts_90_plus.get('avg_speed_retention', 0):.1%}")

    print("\n" + "="*70)
    print("OL/DL PHYSICS")
    print("="*70)
    if ol_dl_stats:
        print(f"Sample size: {ol_dl_stats.sample_size}")
        print(f"Avg closing speed: {ol_dl_stats.avg_closing_speed:.2f} yps")
        print(f"Momentum at contact: OL={ol_dl_stats.avg_ol_momentum_at_contact:.0f}, DL={ol_dl_stats.avg_dl_momentum_at_contact:.0f}")
        print(f"First 1 sec: OL displaced {ol_dl_stats.avg_ol_displacement_1sec:.2f} yds, DL penetrated {ol_dl_stats.avg_dl_penetration_1sec:.2f} yds")
        print(f"OL win rate: {ol_dl_stats.ol_win_rate:.1%}")
        print(f"Interior (G/C vs DT): {ol_dl_stats.interior_stats}")
        print(f"Edge (T vs DE): {ol_dl_stats.edge_stats}")

    print("\n" + "="*70)
    print("POST-CATCH MOVEMENT")
    print("="*70)
    if post_catch_stats:
        print(f"Sample size: {post_catch_stats.sample_size}")
        print(f"Speed at catch: {post_catch_stats.avg_speed_at_catch:.2f} yps")
        print(f"Speed 1 sec after: {post_catch_stats.avg_speed_1sec_after:.2f} yps")
        print(f"Max speed after: {post_catch_stats.avg_max_speed_after:.2f} yps")
        print(f"Avg direction changes: {post_catch_stats.avg_direction_changes}")
        print(f"Avg YAC: {post_catch_stats.avg_yac_yards:.1f} yards")
        print(f"Momentum retention: {post_catch_stats.momentum_retention_1sec:.1%}")

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "ngs_physics_calibration.json"

    with open(export_path, 'w') as f:
        json.dump(export, f, indent=2)

    print(f"\nExported to {export_path}")

    return export


if __name__ == "__main__":
    run_physics_analysis()

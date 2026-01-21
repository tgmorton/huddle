"""NGS Deep Dive - Extracting Every Last Drop.

Advanced analysis:
1. Acceleration/deceleration profiles - burst vs sustained
2. Separation creation - WR vs DB spacing over time
3. Tackle geometry - closing angles, contact physics
4. Reaction times - snap to first movement, throw to DB break
5. Pursuit angles - optimal vs actual
6. Ball carrier decision points - when do they cut?
7. Pass rush timing - time to pressure
8. Collision physics - what happens at contact
9. Spatial control - field coverage
10. Speed decay - fatigue within plays

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
from scipy.ndimage import gaussian_filter1d

warnings.filterwarnings('ignore')

DATA_DIR = Path(__file__).parent.parent.parent / "ngs_highlights" / "play_data"
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports" / "reference" / "simulation"

FRAME_RATE = 10
DT = 0.1

POSITION_WEIGHTS = {
    "QB": 220, "RB": 215, "FB": 245, "WR": 195, "TE": 250,
    "T": 315, "G": 315, "C": 305, "OT": 315, "OG": 315,
    "DT": 305, "DE": 270, "NT": 325,
    "LB": 240, "OLB": 240, "ILB": 245, "MLB": 245,
    "CB": 195, "S": 205, "SS": 210, "FS": 200,
}

def get_weight(pos): return POSITION_WEIGHTS.get(pos, 220)

def load_plays(limit=None):
    plays = []
    for f in sorted(DATA_DIR.glob("*.tsv"))[:limit] if limit else sorted(DATA_DIR.glob("*.tsv")):
        if 'index' in f.name.lower():
            continue
        try:
            df = pd.read_csv(f, sep='\t', low_memory=False)
            if 'event' in df.columns and 'frame' in df.columns:
                df['source_file'] = f.name
                plays.append(df)
        except:
            continue
    return plays


# =============================================================================
# 1. Acceleration/Deceleration Profiles
# =============================================================================

def analyze_acceleration(plays):
    """Analyze acceleration and deceleration by position."""
    accel_data = defaultdict(lambda: {'accels': [], 'decels': [], 'burst_times': [], 'max_accels': []})

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        for player_name in play_df['displayName'].unique():
            pdf = play_df[play_df['displayName'] == player_name]
            pdf = pdf[pdf['frame'] >= snap_frame].sort_values('frame')

            if len(pdf) < 15:
                continue

            pos = pdf['position'].iloc[0]
            if pd.isna(pos):
                continue

            speeds = pdf['s'].values

            # Smooth speeds
            speeds_smooth = gaussian_filter1d(speeds, sigma=1)

            # Compute acceleration (change in speed per 0.1 sec)
            accel = np.diff(speeds_smooth) / DT

            # Positive = acceleration, negative = deceleration
            pos_accel = accel[accel > 0.5]  # Meaningful acceleration
            neg_accel = accel[accel < -0.5]  # Meaningful deceleration

            if len(pos_accel) > 0:
                accel_data[pos]['accels'].extend(pos_accel)
                accel_data[pos]['max_accels'].append(pos_accel.max())
            if len(neg_accel) > 0:
                accel_data[pos]['decels'].extend(neg_accel)

            # Burst time: frames to go from <2 yps to >6 yps
            for i in range(len(speeds) - 1):
                if speeds[i] < 2:
                    for j in range(i+1, min(i+30, len(speeds))):
                        if speeds[j] > 6:
                            burst_time = (j - i) * DT
                            accel_data[pos]['burst_times'].append(burst_time)
                            break
                    break  # Only first burst per player

    results = {}
    for pos, data in accel_data.items():
        if len(data['accels']) < 50:
            continue
        results[pos] = {
            'avg_acceleration_yps2': round(np.mean(data['accels']), 2),
            'max_acceleration_yps2': round(np.mean(data['max_accels']), 2) if data['max_accels'] else 0,
            'p95_acceleration_yps2': round(np.percentile(data['accels'], 95), 2),
            'avg_deceleration_yps2': round(np.mean(data['decels']), 2),
            'max_deceleration_yps2': round(np.percentile(data['decels'], 5), 2),  # Most negative
            'avg_burst_time_sec': round(np.mean(data['burst_times']), 2) if data['burst_times'] else 0,
            'sample_size': len(data['accels']),
        }
    return results


# =============================================================================
# 2. WR-DB Separation Analysis
# =============================================================================

def analyze_separation(plays):
    """Analyze receiver-defender separation over route."""
    separation_by_depth = defaultdict(list)
    separation_at_events = defaultdict(list)

    passing_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_pass']

    for play_df in passing_plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]
        play_dir = play_df['playDirection'].iloc[0]

        # Get WRs and CBs
        wrs = play_df[play_df['position'] == 'WR']['displayName'].unique()
        cbs = play_df[play_df['position'].isin(['CB', 'S', 'SS', 'FS'])]['displayName'].unique()

        for wr_name in wrs:
            wr_df = play_df[play_df['displayName'] == wr_name]
            wr_df = wr_df[wr_df['frame'] >= snap_frame].sort_values('frame')

            if len(wr_df) < 20:
                continue

            wr_start_x = wr_df['x'].iloc[0]
            wr_start_y = wr_df['y'].iloc[0]

            # Find closest DB at snap
            min_dist = float('inf')
            closest_cb = None

            for cb_name in cbs:
                cb_at_snap = play_df[(play_df['displayName'] == cb_name) &
                                      (play_df['frame'] == snap_frame)]
                if len(cb_at_snap) == 0:
                    continue

                dist = math.sqrt((wr_start_x - cb_at_snap['x'].iloc[0])**2 +
                                (wr_start_y - cb_at_snap['y'].iloc[0])**2)
                if dist < min_dist and dist < 10:  # Within 10 yards
                    min_dist = dist
                    closest_cb = cb_name

            if closest_cb is None:
                continue

            cb_df = play_df[play_df['displayName'] == closest_cb]
            cb_df = cb_df[cb_df['frame'] >= snap_frame].sort_values('frame')

            # Track separation at different depths
            for i in range(min(len(wr_df), len(cb_df))):
                wr_x, wr_y = wr_df.iloc[i]['x'], wr_df.iloc[i]['y']
                cb_x, cb_y = cb_df.iloc[i]['x'], cb_df.iloc[i]['y']

                separation = math.sqrt((wr_x - cb_x)**2 + (wr_y - cb_y)**2)

                # Depth from start
                if play_dir == 'left':
                    depth = wr_start_x - wr_x
                else:
                    depth = wr_x - wr_start_x

                # Bucket by depth
                if 0 <= depth < 5:
                    separation_by_depth['0-5'].append(separation)
                elif 5 <= depth < 10:
                    separation_by_depth['5-10'].append(separation)
                elif 10 <= depth < 15:
                    separation_by_depth['10-15'].append(separation)
                elif 15 <= depth < 20:
                    separation_by_depth['15-20'].append(separation)
                elif depth >= 20:
                    separation_by_depth['20+'].append(separation)

    results = {
        depth: {
            'avg_separation_yds': round(np.mean(seps), 2),
            'min_separation_yds': round(np.percentile(seps, 10), 2),
            'max_separation_yds': round(np.percentile(seps, 90), 2),
            'sample_size': len(seps),
        }
        for depth, seps in separation_by_depth.items()
        if len(seps) > 50
    }
    return results


# =============================================================================
# 3. Tackle Geometry
# =============================================================================

def analyze_tackle_geometry(plays):
    """Analyze tackle approach angles and contact physics."""
    tackles = []

    rush_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_rush']

    for play_df in rush_plays:
        # Find tackle event
        tackle_rows = play_df[play_df['event'].isin(['tackle', 'first_contact'])]
        if len(tackle_rows) == 0:
            continue
        tackle_frame = tackle_rows['frame'].iloc[0]

        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Find ball carrier (RB)
        rbs = play_df[play_df['position'].isin(['RB', 'FB'])]['displayName'].unique()
        if len(rbs) == 0:
            continue

        bc_name = rbs[0]
        bc_df = play_df[play_df['displayName'] == bc_name].sort_values('frame')
        bc_at_tackle = bc_df[bc_df['frame'] == tackle_frame]

        if len(bc_at_tackle) == 0:
            continue

        bc_x = bc_at_tackle['x'].iloc[0]
        bc_y = bc_at_tackle['y'].iloc[0]
        bc_speed = bc_at_tackle['s'].iloc[0]
        bc_dir = bc_at_tackle['dir'].iloc[0]

        # Find defenders near ball carrier at tackle
        defenders = play_df[play_df['position'].isin(['LB', 'CB', 'S', 'SS', 'FS', 'DT', 'DE', 'MLB', 'OLB'])]

        for def_name in defenders['displayName'].unique():
            def_df = play_df[play_df['displayName'] == def_name].sort_values('frame')
            def_at_tackle = def_df[def_df['frame'] == tackle_frame]

            if len(def_at_tackle) == 0:
                continue

            def_x = def_at_tackle['x'].iloc[0]
            def_y = def_at_tackle['y'].iloc[0]
            def_speed = def_at_tackle['s'].iloc[0]
            def_dir = def_at_tackle['dir'].iloc[0]

            dist = math.sqrt((bc_x - def_x)**2 + (bc_y - def_y)**2)

            # Only count if close enough to be the tackler
            if dist > 3:
                continue

            # Approach angle: angle between defender's direction and line to BC
            dx = bc_x - def_x
            dy = bc_y - def_y
            angle_to_bc = math.degrees(math.atan2(dy, dx))
            if angle_to_bc < 0:
                angle_to_bc += 360

            approach_angle = abs(def_dir - angle_to_bc)
            if approach_angle > 180:
                approach_angle = 360 - approach_angle

            # Closing speed
            # Pre-tackle data (5 frames before)
            pre_frame = tackle_frame - 5
            def_pre = def_df[def_df['frame'] == pre_frame]
            bc_pre = bc_df[bc_df['frame'] == pre_frame]

            if len(def_pre) > 0 and len(bc_pre) > 0:
                dist_pre = math.sqrt((bc_pre['x'].iloc[0] - def_pre['x'].iloc[0])**2 +
                                     (bc_pre['y'].iloc[0] - def_pre['y'].iloc[0])**2)
                closing_speed = (dist_pre - dist) / (5 * DT)
            else:
                closing_speed = 0

            tackles.append({
                'approach_angle': approach_angle,
                'closing_speed': closing_speed,
                'bc_speed': bc_speed,
                'def_speed': def_speed,
                'distance_at_contact': dist,
                'def_position': def_at_tackle['position'].iloc[0],
            })
            break  # Only one tackler per play

    if not tackles:
        return {}

    return {
        'sample_size': len(tackles),
        'avg_approach_angle_deg': round(np.mean([t['approach_angle'] for t in tackles]), 1),
        'optimal_approach_angle_deg': round(np.percentile([t['approach_angle'] for t in tackles], 25), 1),
        'avg_closing_speed_yps': round(np.mean([t['closing_speed'] for t in tackles]), 2),
        'avg_bc_speed_at_contact_yps': round(np.mean([t['bc_speed'] for t in tackles]), 2),
        'avg_def_speed_at_contact_yps': round(np.mean([t['def_speed'] for t in tackles]), 2),
        'avg_contact_distance_yds': round(np.mean([t['distance_at_contact'] for t in tackles]), 2),
        'by_position': {
            pos: {
                'count': len([t for t in tackles if t['def_position'] == pos]),
                'avg_approach_angle': round(np.mean([t['approach_angle'] for t in tackles if t['def_position'] == pos]), 1),
                'avg_closing_speed': round(np.mean([t['closing_speed'] for t in tackles if t['def_position'] == pos]), 2),
            }
            for pos in set(t['def_position'] for t in tackles)
            if len([t for t in tackles if t['def_position'] == pos]) >= 5
        },
    }


# =============================================================================
# 4. Reaction Times
# =============================================================================

def analyze_reaction_times(plays):
    """Analyze reaction times: snap-to-move, throw-to-break."""
    snap_reactions = defaultdict(list)

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        for player_name in play_df['displayName'].unique():
            pdf = play_df[play_df['displayName'] == player_name].sort_values('frame')

            pos = pdf['position'].iloc[0]
            if pd.isna(pos):
                continue

            # Get speed before and after snap
            pre_snap = pdf[pdf['frame'] == snap_frame - 1]

            if len(pre_snap) == 0:
                continue

            pre_speed = pre_snap['s'].iloc[0]

            # If already moving pre-snap, skip
            if pre_speed > 1.0:
                continue

            # Find first frame where speed > 1.5
            post_snap = pdf[pdf['frame'] > snap_frame].sort_values('frame')

            for i, row in post_snap.iterrows():
                if row['s'] > 1.5:
                    reaction_frames = row['frame'] - snap_frame
                    snap_reactions[pos].append(reaction_frames * DT)
                    break

    results = {}
    for pos, times in snap_reactions.items():
        if len(times) < 20:
            continue
        results[pos] = {
            'avg_reaction_time_sec': round(np.mean(times), 3),
            'min_reaction_time_sec': round(np.percentile(times, 10), 3),
            'max_reaction_time_sec': round(np.percentile(times, 90), 3),
            'sample_size': len(times),
        }

    return results


# =============================================================================
# 5. Pass Rush Timing
# =============================================================================

def analyze_pass_rush(plays):
    """Analyze pass rush timing and pressure."""
    rush_times = []

    passing_plays = [p for p in plays if p['playType'].iloc[0] in ['play_type_pass', 'play_type_sack']]

    for play_df in passing_plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Find QB position at snap
        qbs = play_df[play_df['position'] == 'QB']['displayName'].unique()
        if len(qbs) == 0:
            continue

        qb_name = qbs[0]
        qb_df = play_df[play_df['displayName'] == qb_name].sort_values('frame')
        qb_at_snap = qb_df[qb_df['frame'] == snap_frame]

        if len(qb_at_snap) == 0:
            continue

        qb_x = qb_at_snap['x'].iloc[0]
        qb_y = qb_at_snap['y'].iloc[0]

        # Track DL/Edge rushers
        rushers = play_df[play_df['position'].isin(['DE', 'DT', 'NT', 'OLB'])]

        for rusher_name in rushers['displayName'].unique():
            rusher_df = play_df[play_df['displayName'] == rusher_name].sort_values('frame')
            rusher_post = rusher_df[rusher_df['frame'] >= snap_frame]

            if len(rusher_post) < 10:
                continue

            # Find when rusher gets within 3 yards of QB's snap position
            for i, row in rusher_post.iterrows():
                dist_to_qb = math.sqrt((row['x'] - qb_x)**2 + (row['y'] - qb_y)**2)

                if dist_to_qb < 3:
                    time_to_pressure = (row['frame'] - snap_frame) * DT
                    rush_times.append({
                        'time_to_pressure': time_to_pressure,
                        'position': row['position'],
                    })
                    break

    if not rush_times:
        return {}

    return {
        'sample_size': len(rush_times),
        'avg_time_to_pressure_sec': round(np.mean([r['time_to_pressure'] for r in rush_times]), 2),
        'fast_pressure_p10_sec': round(np.percentile([r['time_to_pressure'] for r in rush_times], 10), 2),
        'slow_pressure_p90_sec': round(np.percentile([r['time_to_pressure'] for r in rush_times], 90), 2),
        'by_position': {
            pos: {
                'count': len([r for r in rush_times if r['position'] == pos]),
                'avg_time': round(np.mean([r['time_to_pressure'] for r in rush_times if r['position'] == pos]), 2),
            }
            for pos in set(r['position'] for r in rush_times)
            if len([r for r in rush_times if r['position'] == pos]) >= 5
        },
    }


# =============================================================================
# 6. Ball Carrier Decision Points
# =============================================================================

def analyze_bc_decisions(plays):
    """Analyze when ball carriers make cut decisions."""
    decisions = []

    rush_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_rush']

    for play_df in rush_plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Find RB
        rbs = play_df[play_df['position'].isin(['RB', 'FB'])]['displayName'].unique()
        if len(rbs) == 0:
            continue

        bc_name = rbs[0]
        bc_df = play_df[play_df['displayName'] == bc_name]
        bc_df = bc_df[bc_df['frame'] >= snap_frame].sort_values('frame')

        if len(bc_df) < 20:
            continue

        dirs = bc_df['dir'].values
        speeds = bc_df['s'].values
        xs = bc_df['x'].values
        ys = bc_df['y'].values
        frames = bc_df['frame'].values

        # Find significant direction changes (cuts)
        for i in range(10, len(dirs) - 5):
            if speeds[i] < 3:
                continue

            dir_before = np.mean(dirs[i-5:i])
            dir_after = np.mean(dirs[i:i+5])

            change = abs(dir_after - dir_before)
            if change > 180:
                change = 360 - change

            if change < 30:
                continue

            # Find nearest defender at decision point
            defenders = play_df[play_df['position'].isin(['LB', 'CB', 'S', 'DT', 'DE'])]

            min_dist = float('inf')
            for def_name in defenders['displayName'].unique():
                def_at_frame = play_df[(play_df['displayName'] == def_name) &
                                        (play_df['frame'] == frames[i])]
                if len(def_at_frame) == 0:
                    continue

                dist = math.sqrt((xs[i] - def_at_frame['x'].iloc[0])**2 +
                                (ys[i] - def_at_frame['y'].iloc[0])**2)
                min_dist = min(min_dist, dist)

            decisions.append({
                'frames_after_snap': int(frames[i] - snap_frame),
                'speed_at_cut': speeds[i],
                'cut_angle': change,
                'nearest_defender_dist': min_dist if min_dist < 20 else None,
            })
            break  # Only first major cut

    if not decisions:
        return {}

    valid_decisions = [d for d in decisions if d['nearest_defender_dist'] is not None]

    return {
        'sample_size': len(decisions),
        'avg_time_to_first_cut_sec': round(np.mean([d['frames_after_snap'] for d in decisions]) * DT, 2),
        'avg_speed_at_cut_yps': round(np.mean([d['speed_at_cut'] for d in decisions]), 2),
        'avg_cut_angle_deg': round(np.mean([d['cut_angle'] for d in decisions]), 1),
        'avg_defender_dist_at_cut_yds': round(np.mean([d['nearest_defender_dist'] for d in valid_decisions]), 2) if valid_decisions else 0,
        'cut_triggered_by_defender': {
            'within_3yds': len([d for d in valid_decisions if d['nearest_defender_dist'] < 3]),
            'within_5yds': len([d for d in valid_decisions if d['nearest_defender_dist'] < 5]),
            'within_7yds': len([d for d in valid_decisions if d['nearest_defender_dist'] < 7]),
        },
    }


# =============================================================================
# 7. Speed Decay (Fatigue Within Play)
# =============================================================================

def analyze_speed_decay(plays):
    """Analyze if players slow down over course of play."""
    decay_data = defaultdict(lambda: {'early_speeds': [], 'late_speeds': []})

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        for player_name in play_df['displayName'].unique():
            pdf = play_df[play_df['displayName'] == player_name]
            pdf = pdf[pdf['frame'] >= snap_frame].sort_values('frame')

            if len(pdf) < 50:  # Need long enough play
                continue

            pos = pdf['position'].iloc[0]
            if pd.isna(pos):
                continue

            speeds = pdf['s'].values

            # Early = first 2 seconds, Late = after 5 seconds
            early = speeds[5:25]  # frames 5-25 (0.5-2.5 sec)
            late = speeds[50:70] if len(speeds) > 70 else speeds[50:]  # 5-7 sec

            if len(early) > 10 and len(late) > 10:
                # Only count if moving in both periods
                early_moving = early[early > 2]
                late_moving = late[late > 2]

                if len(early_moving) > 5 and len(late_moving) > 5:
                    decay_data[pos]['early_speeds'].append(np.mean(early_moving))
                    decay_data[pos]['late_speeds'].append(np.mean(late_moving))

    results = {}
    for pos, data in decay_data.items():
        if len(data['early_speeds']) < 20:
            continue

        early_avg = np.mean(data['early_speeds'])
        late_avg = np.mean(data['late_speeds'])
        decay_pct = (early_avg - late_avg) / early_avg if early_avg > 0 else 0

        results[pos] = {
            'early_speed_yps': round(early_avg, 2),
            'late_speed_yps': round(late_avg, 2),
            'speed_decay_pct': round(decay_pct * 100, 1),
            'sample_size': len(data['early_speeds']),
        }

    return results


# =============================================================================
# 8. Collision Physics
# =============================================================================

def analyze_collisions(plays):
    """Analyze what happens to velocity at contact points."""
    collisions = []

    for play_df in plays:
        contact_rows = play_df[play_df['event'] == 'first_contact']
        if len(contact_rows) == 0:
            continue
        contact_frame = contact_rows['frame'].iloc[0]

        # Find players involved in contact
        for player_name in play_df['displayName'].unique():
            pdf = play_df[play_df['displayName'] == player_name].sort_values('frame')

            pos = pdf['position'].iloc[0]
            if pd.isna(pos):
                continue

            # Get data around contact
            pre = pdf[(pdf['frame'] >= contact_frame - 5) & (pdf['frame'] < contact_frame)]
            at = pdf[pdf['frame'] == contact_frame]
            post = pdf[(pdf['frame'] > contact_frame) & (pdf['frame'] <= contact_frame + 5)]

            if len(pre) < 3 or len(at) == 0 or len(post) < 3:
                continue

            speed_pre = pre['s'].mean()
            speed_at = at['s'].iloc[0]
            speed_post = post['s'].mean()

            # Direction change
            dir_pre = pre['dir'].mean()
            dir_post = post['dir'].mean()
            dir_change = abs(dir_post - dir_pre)
            if dir_change > 180:
                dir_change = 360 - dir_change

            weight = get_weight(pos)
            momentum_pre = weight * speed_pre
            momentum_post = weight * speed_post

            collisions.append({
                'position': pos,
                'speed_pre': speed_pre,
                'speed_at': speed_at,
                'speed_post': speed_post,
                'speed_retention': speed_post / speed_pre if speed_pre > 0 else 1,
                'dir_change': dir_change,
                'momentum_pre': momentum_pre,
                'momentum_post': momentum_post,
                'momentum_retention': momentum_post / momentum_pre if momentum_pre > 0 else 1,
            })

    if not collisions:
        return {}

    # Group by offensive vs defensive
    offense_pos = {'QB', 'RB', 'FB', 'WR', 'TE', 'T', 'G', 'C', 'OT', 'OG'}
    defense_pos = {'DT', 'DE', 'NT', 'LB', 'OLB', 'ILB', 'MLB', 'CB', 'S', 'SS', 'FS'}

    off_collisions = [c for c in collisions if c['position'] in offense_pos]
    def_collisions = [c for c in collisions if c['position'] in defense_pos]

    return {
        'total_contacts': len(collisions),
        'offense': {
            'count': len(off_collisions),
            'avg_speed_retention': round(np.mean([c['speed_retention'] for c in off_collisions]), 3) if off_collisions else 0,
            'avg_momentum_retention': round(np.mean([c['momentum_retention'] for c in off_collisions]), 3) if off_collisions else 0,
            'avg_direction_change_deg': round(np.mean([c['dir_change'] for c in off_collisions]), 1) if off_collisions else 0,
        },
        'defense': {
            'count': len(def_collisions),
            'avg_speed_retention': round(np.mean([c['speed_retention'] for c in def_collisions]), 3) if def_collisions else 0,
            'avg_momentum_retention': round(np.mean([c['momentum_retention'] for c in def_collisions]), 3) if def_collisions else 0,
            'avg_direction_change_deg': round(np.mean([c['dir_change'] for c in def_collisions]), 1) if def_collisions else 0,
        },
    }


# =============================================================================
# 9. Spatial Control (Field Coverage)
# =============================================================================

def analyze_spatial_control(plays):
    """Analyze how much space defenders control."""
    # This would ideally use Voronoi diagrams, but we'll approximate
    # by measuring minimum distance to offensive players

    coverage_data = defaultdict(list)

    for play_df in plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]

        # Sample at snap + 1 second
        target_frame = snap_frame + 10

        frame_data = play_df[play_df['frame'] == target_frame]

        offense = frame_data[frame_data['position'].isin(['WR', 'TE', 'RB', 'QB'])]
        defense = frame_data[frame_data['position'].isin(['CB', 'S', 'SS', 'FS', 'LB', 'MLB', 'OLB'])]

        for _, def_row in defense.iterrows():
            def_x, def_y = def_row['x'], def_row['y']
            pos = def_row['position']

            # Find distance to nearest offensive player
            min_dist = float('inf')
            for _, off_row in offense.iterrows():
                dist = math.sqrt((def_x - off_row['x'])**2 + (def_y - off_row['y'])**2)
                min_dist = min(min_dist, dist)

            if min_dist < 50:  # Reasonable
                coverage_data[pos].append(min_dist)

    results = {}
    for pos, distances in coverage_data.items():
        if len(distances) < 50:
            continue
        results[pos] = {
            'avg_cushion_yds': round(np.mean(distances), 2),
            'tight_coverage_pct': round(len([d for d in distances if d < 3]) / len(distances) * 100, 1),
            'loose_coverage_pct': round(len([d for d in distances if d > 7]) / len(distances) * 100, 1),
            'sample_size': len(distances),
        }

    return results


# =============================================================================
# 10. Route Tree Analysis - Actual Shapes
# =============================================================================

def analyze_route_shapes(plays):
    """Extract actual route shapes as coordinate sequences."""
    routes = defaultdict(list)

    passing_plays = [p for p in plays if p['playType'].iloc[0] == 'play_type_pass'][:100]  # Limit for speed

    for play_df in passing_plays:
        snap_rows = play_df[play_df['event'] == 'ball_snap']
        if len(snap_rows) == 0:
            continue
        snap_frame = snap_rows['frame'].iloc[0]
        play_dir = play_df['playDirection'].iloc[0]

        wrs = play_df[play_df['position'] == 'WR']['displayName'].unique()

        for wr_name in wrs:
            wr_df = play_df[play_df['displayName'] == wr_name]
            wr_df = wr_df[wr_df['frame'] >= snap_frame].sort_values('frame')

            if len(wr_df) < 30:
                continue

            start_x = wr_df['x'].iloc[0]
            start_y = wr_df['y'].iloc[0]

            # Normalize to start at origin, positive x = downfield
            coords = []
            for i in range(min(50, len(wr_df))):  # First 5 seconds
                row = wr_df.iloc[i]
                if play_dir == 'left':
                    x = start_x - row['x']  # Flip for left
                    y = row['y'] - start_y
                else:
                    x = row['x'] - start_x
                    y = row['y'] - start_y
                coords.append((round(x, 1), round(y, 1)))

            # Classify route by endpoint
            end_x, end_y = coords[-1]

            if end_x < 8:
                route_type = 'short'
            elif end_x < 15:
                if abs(end_y) < 3:
                    route_type = 'dig'
                elif end_y > 3:
                    route_type = 'out'
                else:
                    route_type = 'in'
            else:
                if abs(end_y) < 5:
                    route_type = 'go'
                elif end_y > 5:
                    route_type = 'corner'
                else:
                    route_type = 'post'

            routes[route_type].append(coords)

    # Create average route for each type
    results = {}
    for route_type, route_list in routes.items():
        if len(route_list) < 5:
            continue

        # Average the coordinates
        min_len = min(len(r) for r in route_list)
        avg_route = []
        for i in range(min_len):
            avg_x = np.mean([r[i][0] for r in route_list])
            avg_y = np.mean([r[i][1] for r in route_list])
            avg_route.append({'x': round(avg_x, 1), 'y': round(avg_y, 1)})

        results[route_type] = {
            'count': len(route_list),
            'avg_route_coords': avg_route,
            'endpoint': {'x': avg_route[-1]['x'], 'y': avg_route[-1]['y']},
        }

    return results


# =============================================================================
# Main
# =============================================================================

def run_deep_dive():
    """Run all deep dive analyses."""
    print("Loading plays...")
    plays = load_plays()
    print(f"Loaded {len(plays)} plays\n")

    results = {}

    print("1. Analyzing acceleration profiles...")
    results['acceleration_by_position'] = analyze_acceleration(plays)

    print("2. Analyzing WR-DB separation...")
    results['separation_by_depth'] = analyze_separation(plays)

    print("3. Analyzing tackle geometry...")
    results['tackle_geometry'] = analyze_tackle_geometry(plays)

    print("4. Analyzing reaction times...")
    results['reaction_times'] = analyze_reaction_times(plays)

    print("5. Analyzing pass rush timing...")
    results['pass_rush_timing'] = analyze_pass_rush(plays)

    print("6. Analyzing ball carrier decisions...")
    results['ball_carrier_decisions'] = analyze_bc_decisions(plays)

    print("7. Analyzing speed decay...")
    results['speed_decay'] = analyze_speed_decay(plays)

    print("8. Analyzing collision physics...")
    results['collision_physics'] = analyze_collisions(plays)

    print("9. Analyzing spatial control...")
    results['spatial_control'] = analyze_spatial_control(plays)

    print("10. Analyzing route shapes...")
    results['route_shapes'] = analyze_route_shapes(plays)

    # Add metadata
    export = {
        'meta': {
            'source': 'ngs_highlights deep dive analysis',
            'plays_analyzed': len(plays),
        },
        **results,
    }

    # Print highlights
    print("\n" + "="*70)
    print("KEY FINDINGS")
    print("="*70)

    print("\n## ACCELERATION BY POSITION")
    for pos in ['WR', 'RB', 'CB', 'LB', 'DE']:
        if pos in results['acceleration_by_position']:
            a = results['acceleration_by_position'][pos]
            print(f"  {pos}: avg={a['avg_acceleration_yps2']} yps², max={a['max_acceleration_yps2']} yps², burst={a['avg_burst_time_sec']}s")

    print("\n## SEPARATION BY DEPTH")
    for depth, data in sorted(results['separation_by_depth'].items()):
        print(f"  {depth} yds: avg={data['avg_separation_yds']} yds")

    print("\n## TACKLE GEOMETRY")
    tg = results['tackle_geometry']
    if tg:
        print(f"  Approach angle: {tg['avg_approach_angle_deg']}° (optimal: {tg['optimal_approach_angle_deg']}°)")
        print(f"  Closing speed: {tg['avg_closing_speed_yps']} yps")
        print(f"  BC speed at contact: {tg['avg_bc_speed_at_contact_yps']} yps")

    print("\n## REACTION TIMES (snap to move)")
    for pos in ['WR', 'RB', 'CB', 'LB', 'DE', 'DT']:
        if pos in results['reaction_times']:
            r = results['reaction_times'][pos]
            print(f"  {pos}: {r['avg_reaction_time_sec']}s (range: {r['min_reaction_time_sec']}-{r['max_reaction_time_sec']}s)")

    print("\n## PASS RUSH TIMING")
    pr = results['pass_rush_timing']
    if pr:
        print(f"  Avg time to pressure: {pr['avg_time_to_pressure_sec']}s")
        print(f"  Fast pressure (p10): {pr['fast_pressure_p10_sec']}s")

    print("\n## BALL CARRIER DECISIONS")
    bc = results['ball_carrier_decisions']
    if bc:
        print(f"  Time to first cut: {bc['avg_time_to_first_cut_sec']}s")
        print(f"  Defender distance at cut: {bc['avg_defender_dist_at_cut_yds']} yds")
        print(f"  Cut triggers: {bc['cut_triggered_by_defender']}")

    print("\n## SPEED DECAY (early vs late in play)")
    for pos in ['WR', 'RB', 'CB', 'LB']:
        if pos in results['speed_decay']:
            sd = results['speed_decay'][pos]
            print(f"  {pos}: {sd['early_speed_yps']} → {sd['late_speed_yps']} yps ({sd['speed_decay_pct']}% drop)")

    print("\n## COLLISION PHYSICS")
    cp = results['collision_physics']
    if cp:
        print(f"  Offense speed retention: {cp['offense']['avg_speed_retention']:.1%}")
        print(f"  Defense speed retention: {cp['defense']['avg_speed_retention']:.1%}")
        print(f"  Offense direction change: {cp['offense']['avg_direction_change_deg']}°")

    # Export
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = EXPORT_DIR / "ngs_deep_dive.json"

    with open(export_path, 'w') as f:
        json.dump(export, f, indent=2)

    print(f"\nExported to {export_path}")

    return export


if __name__ == "__main__":
    run_deep_dive()

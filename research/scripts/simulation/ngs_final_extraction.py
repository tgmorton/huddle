"""
NGS Final Extraction - Getting Every Last Drop

This script extracts the remaining valuable data from the NGS tracking data:
1. Speed-curvature constraint mapping (granular bins)
2. Route depth vs time (how long to reach depths)
3. Block duration and sustained engagement
4. Reception mechanics (catch point physics)
5. Speed profiles by route phase (stem, break, post-break)
6. Turn radius constraints at different speeds
7. Momentum at key events
8. Relative velocity between matchups
9. Pre-snap vs post-snap positioning delta
10. Ball carrier vision cone (direction vs movement)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent.parent / "ngs_highlights" / "play_data"
EXPORT_DIR = Path(__file__).parent.parent.parent / "exports" / "reference" / "simulation"


def load_all_plays():
    """Load all tracking data files."""
    plays = []
    for f in DATA_DIR.glob("*.tsv"):
        if 'index' in f.name.lower():
            continue
        try:
            df = pd.read_csv(f, sep='\t')
            if 'event' not in df.columns or 'frame' not in df.columns:
                continue
            df['play_file'] = f.stem
            plays.append(df)
        except Exception as e:
            print(f"Error loading {f}: {e}")
    return plays


def analyze_speed_curvature_constraints(plays):
    """
    Build a detailed speed-curvature constraint map.
    At each speed bin, what's the max turn rate players can achieve?
    """
    print("Analyzing speed-curvature constraints...")

    # Bins: speed in yps, turn rate in deg/sec
    speed_bins = [(0, 2), (2, 4), (4, 6), (6, 8), (8, 10), (10, 12), (12, 15)]

    constraints = {}

    for speed_min, speed_max in speed_bins:
        turn_rates = []

        for df in plays:
            # Calculate turn rate from direction changes
            for player_id in df['nflId'].dropna().unique():
                pdf = df[df['nflId'] == player_id].sort_values('frame')
                if len(pdf) < 3:
                    continue

                speeds = pdf['s'].values
                dirs = pdf['dir'].values

                for i in range(1, len(pdf) - 1):
                    speed = speeds[i]
                    if speed_min <= speed < speed_max:
                        # Turn rate = direction change per 0.1 sec
                        dir_change = abs(dirs[i+1] - dirs[i])
                        if dir_change > 180:
                            dir_change = 360 - dir_change
                        turn_rate = dir_change * 10  # deg/sec
                        if turn_rate < 500:  # filter noise
                            turn_rates.append(turn_rate)

        if turn_rates:
            constraints[f"{speed_min}-{speed_max}"] = {
                "avg_turn_rate": round(np.mean(turn_rates), 1),
                "max_turn_rate": round(np.percentile(turn_rates, 95), 1),
                "p99_turn_rate": round(np.percentile(turn_rates, 99), 1),
                "sample_size": len(turn_rates)
            }

    return constraints


def analyze_route_timing(plays):
    """
    How long does it take receivers to reach different depths?
    """
    print("Analyzing route timing...")

    depth_timing = defaultdict(list)

    for df in plays:
        # Find snap frame
        snap_frames = df[df['event'] == 'ball_snap']['frame'].unique()
        if len(snap_frames) == 0:
            continue
        snap_frame = snap_frames[0]

        # Get WR/TE movements
        receivers = df[df['position'].isin(['WR', 'TE'])]

        for player_id in receivers['nflId'].dropna().unique():
            pdf = receivers[receivers['nflId'] == player_id].sort_values('frame')
            snap_pdf = pdf[pdf['frame'] >= snap_frame]

            if len(snap_pdf) < 5:
                continue

            # Calculate depth from LOS (first y position)
            start_y = snap_pdf.iloc[0]['y']

            for idx, row in snap_pdf.iterrows():
                depth = abs(row['y'] - start_y)
                time_from_snap = (row['frame'] - snap_frame) * 0.1

                # Bucket depths
                if 4.5 <= depth < 5.5:
                    depth_timing["5_yards"].append(time_from_snap)
                elif 9.5 <= depth < 10.5:
                    depth_timing["10_yards"].append(time_from_snap)
                elif 14.5 <= depth < 15.5:
                    depth_timing["15_yards"].append(time_from_snap)
                elif 19.5 <= depth < 20.5:
                    depth_timing["20_yards"].append(time_from_snap)

    results = {}
    for depth, times in depth_timing.items():
        if times:
            # Take the minimum time to reach each depth (first arrival)
            results[depth] = {
                "avg_time_sec": round(np.mean(times), 2),
                "fast_time_p10": round(np.percentile(times, 10), 2),
                "slow_time_p90": round(np.percentile(times, 90), 2),
                "sample_size": len(times)
            }

    return results


def analyze_block_duration(plays):
    """
    How long do OL sustain blocks against DL?
    """
    print("Analyzing block duration...")

    block_durations = []

    for df in plays:
        snap_frames = df[df['event'] == 'ball_snap']['frame'].unique()
        if len(snap_frames) == 0:
            continue
        snap_frame = snap_frames[0]

        # Get OL and DL
        ol = df[df['position'].isin(['C', 'G', 'T', 'OT', 'OG'])]
        dl = df[df['position'].isin(['DE', 'DT', 'NT'])]

        if ol.empty or dl.empty:
            continue

        # Track OL-DL proximity over time
        frames_after_snap = sorted(df[df['frame'] >= snap_frame]['frame'].unique())

        for ol_id in ol['nflId'].dropna().unique():
            ol_player = ol[ol['nflId'] == ol_id]

            engagement_start = None
            closest_dl = None

            for frame in frames_after_snap[:50]:  # First 5 seconds
                ol_frame = ol_player[ol_player['frame'] == frame]
                dl_frame = dl[dl['frame'] == frame]

                if ol_frame.empty or dl_frame.empty:
                    continue

                ol_x, ol_y = ol_frame.iloc[0]['x'], ol_frame.iloc[0]['y']

                # Find closest DL
                min_dist = float('inf')
                for _, dl_row in dl_frame.iterrows():
                    dist = np.sqrt((dl_row['x'] - ol_x)**2 + (dl_row['y'] - ol_y)**2)
                    if dist < min_dist:
                        min_dist = dist

                # Engagement threshold: within 2 yards
                if min_dist < 2:
                    if engagement_start is None:
                        engagement_start = frame
                else:
                    if engagement_start is not None:
                        duration = (frame - engagement_start) * 0.1
                        if duration > 0.3:  # Minimum meaningful engagement
                            block_durations.append(duration)
                        engagement_start = None

    if block_durations:
        return {
            "avg_block_duration_sec": round(np.mean(block_durations), 2),
            "short_block_p10_sec": round(np.percentile(block_durations, 10), 2),
            "long_block_p90_sec": round(np.percentile(block_durations, 90), 2),
            "max_block_sec": round(max(block_durations), 2),
            "sample_size": len(block_durations)
        }
    return {}


def analyze_catch_mechanics(plays):
    """
    Physics at the catch point: speed, momentum, direction.
    """
    print("Analyzing catch mechanics...")

    catch_data = defaultdict(list)

    for df in plays:
        catch_frames = df[df['event'].isin(['pass_outcome_caught', 'pass_arrived'])]
        if catch_frames.empty:
            continue

        catch_frame = catch_frames['frame'].iloc[0]

        # Find receiver (likely the one closest to where ball is caught)
        receivers = df[(df['frame'] == catch_frame) &
                       (df['position'].isin(['WR', 'TE', 'RB']))]

        for _, rec in receivers.iterrows():
            speed = rec.get('s', np.nan)
            direction = rec.get('dir', np.nan)
            orientation = rec.get('o', np.nan)

            if pd.notna(speed):
                catch_data['speed_at_catch'].append(speed)

            if pd.notna(direction) and pd.notna(orientation):
                # Body orientation vs movement direction
                orient_diff = abs(direction - orientation)
                if orient_diff > 180:
                    orient_diff = 360 - orient_diff
                catch_data['orient_vs_move_diff'].append(orient_diff)

    results = {}
    if catch_data['speed_at_catch']:
        results['speed_at_catch'] = {
            "avg_yps": round(np.mean(catch_data['speed_at_catch']), 2),
            "p10_yps": round(np.percentile(catch_data['speed_at_catch'], 10), 2),
            "p90_yps": round(np.percentile(catch_data['speed_at_catch'], 90), 2),
            "sample_size": len(catch_data['speed_at_catch'])
        }

    if catch_data['orient_vs_move_diff']:
        results['body_alignment_at_catch'] = {
            "avg_diff_deg": round(np.mean(catch_data['orient_vs_move_diff']), 1),
            "well_aligned_pct": round(100 * np.mean([d < 30 for d in catch_data['orient_vs_move_diff']]), 1),
            "sample_size": len(catch_data['orient_vs_move_diff'])
        }

    return results


def analyze_route_phases(plays):
    """
    Speed profiles by route phase: stem (0-5 yds), break (5-10), post-break (10+)
    """
    print("Analyzing route phases...")

    phase_speeds = {
        "stem": [],      # 0-5 yards
        "break": [],     # 5-10 yards
        "post_break": [] # 10+ yards
    }

    for df in plays:
        snap_frames = df[df['event'] == 'ball_snap']['frame'].unique()
        if len(snap_frames) == 0:
            continue
        snap_frame = snap_frames[0]

        receivers = df[df['position'].isin(['WR', 'TE'])]

        for player_id in receivers['nflId'].dropna().unique():
            pdf = receivers[receivers['nflId'] == player_id].sort_values('frame')
            snap_pdf = pdf[pdf['frame'] >= snap_frame]

            if len(snap_pdf) < 10:
                continue

            start_y = snap_pdf.iloc[0]['y']

            for idx, row in snap_pdf.iterrows():
                depth = abs(row['y'] - start_y)
                speed = row['s']

                if depth < 5:
                    phase_speeds["stem"].append(speed)
                elif depth < 10:
                    phase_speeds["break"].append(speed)
                else:
                    phase_speeds["post_break"].append(speed)

    results = {}
    for phase, speeds in phase_speeds.items():
        if speeds:
            results[phase] = {
                "avg_speed_yps": round(np.mean(speeds), 2),
                "p90_speed_yps": round(np.percentile(speeds, 90), 2),
                "sample_size": len(speeds)
            }

    return results


def analyze_pursuit_vectors(plays):
    """
    Defender pursuit: how do defenders adjust their angle to the ball carrier?
    """
    print("Analyzing pursuit vectors...")

    pursuit_adjustments = []

    for df in plays:
        # Find ball carrier events
        bc_events = df[df['event'].isin(['handoff', 'pass_outcome_caught'])]
        if bc_events.empty:
            continue

        bc_frame = bc_events['frame'].iloc[0]

        # Get frames after ball carrier gets ball
        post_bc = df[df['frame'] >= bc_frame].sort_values('frame')
        frames = sorted(post_bc['frame'].unique())[:30]  # 3 seconds

        if len(frames) < 10:
            continue

        # Track defender direction changes toward ball carrier
        defenders = post_bc[post_bc['position'].isin(['CB', 'S', 'SS', 'FS', 'LB', 'MLB', 'OLB', 'ILB'])]
        ball_carriers = post_bc[post_bc['position'].isin(['RB', 'WR', 'TE'])]

        for def_id in defenders['nflId'].dropna().unique():
            def_player = defenders[defenders['nflId'] == def_id]

            prev_angle_to_bc = None

            for frame in frames[::5]:  # Sample every 0.5 sec
                def_frame = def_player[def_player['frame'] == frame]
                bc_frame_data = ball_carriers[ball_carriers['frame'] == frame]

                if def_frame.empty or bc_frame_data.empty:
                    continue

                # Use first ball carrier found
                bc_row = bc_frame_data.iloc[0]
                def_row = def_frame.iloc[0]

                # Angle from defender to BC
                dx = bc_row['x'] - def_row['x']
                dy = bc_row['y'] - def_row['y']
                angle_to_bc = np.degrees(np.arctan2(dy, dx))

                # Defender's movement direction
                def_dir = def_row.get('dir', np.nan)

                if pd.notna(def_dir) and prev_angle_to_bc is not None:
                    # How much did defender adjust toward BC?
                    angle_adjustment = abs(angle_to_bc - prev_angle_to_bc)
                    if angle_adjustment > 180:
                        angle_adjustment = 360 - angle_adjustment
                    pursuit_adjustments.append(angle_adjustment)

                prev_angle_to_bc = angle_to_bc

    if pursuit_adjustments:
        return {
            "avg_pursuit_adjustment_deg": round(np.mean(pursuit_adjustments), 1),
            "aggressive_pursuit_pct": round(100 * np.mean([a > 20 for a in pursuit_adjustments]), 1),
            "sample_size": len(pursuit_adjustments)
        }
    return {}


def analyze_position_weight_speeds(plays):
    """
    Speed by position with estimated weight for momentum calculations.
    """
    print("Analyzing position-weight-speed relationships...")

    # Estimated average weights by position (lbs)
    position_weights = {
        'QB': 220, 'RB': 215, 'FB': 245, 'WR': 195, 'TE': 250,
        'C': 305, 'G': 315, 'T': 315, 'OT': 315, 'OG': 315,
        'DE': 270, 'DT': 305, 'NT': 325,
        'OLB': 245, 'ILB': 240, 'MLB': 245, 'LB': 242,
        'CB': 195, 'SS': 210, 'FS': 205, 'S': 207, 'DB': 200
    }

    momentum_data = defaultdict(list)

    for df in plays:
        for pos in position_weights.keys():
            pos_df = df[df['position'] == pos]
            if pos_df.empty:
                continue

            for _, row in pos_df.iterrows():
                speed = row.get('s', np.nan)
                if pd.notna(speed) and speed > 0:
                    weight = position_weights.get(pos, 220)
                    momentum = weight * speed
                    momentum_data[pos].append({
                        'speed': speed,
                        'momentum': momentum
                    })

    results = {}
    for pos, data in momentum_data.items():
        if len(data) > 100:
            speeds = [d['speed'] for d in data]
            momentums = [d['momentum'] for d in data]
            results[pos] = {
                "estimated_weight_lbs": position_weights.get(pos, 220),
                "avg_speed_yps": round(np.mean(speeds), 2),
                "max_speed_yps": round(np.percentile(speeds, 99), 2),
                "avg_momentum": round(np.mean(momentums), 0),
                "max_momentum_p99": round(np.percentile(momentums, 99), 0),
                "sample_size": len(data)
            }

    return results


def analyze_gap_exploitation(plays):
    """
    Running game: how do RBs find and exploit gaps?
    Measure lateral movement patterns and hole identification.
    """
    print("Analyzing gap exploitation...")

    lateral_movements = []

    for df in plays:
        # Find handoff
        handoff_frames = df[df['event'] == 'handoff']['frame'].unique()
        if len(handoff_frames) == 0:
            continue
        handoff_frame = handoff_frames[0]

        # Get RB after handoff
        rbs = df[(df['position'] == 'RB') & (df['frame'] >= handoff_frame)]

        for rb_id in rbs['nflId'].dropna().unique():
            rb_player = rbs[rbs['nflId'] == rb_id].sort_values('frame')

            if len(rb_player) < 10:
                continue

            # Measure lateral movement in first 1 second
            first_frames = rb_player.head(10)

            start_x = first_frames.iloc[0]['x']
            lateral_displacement = 0

            prev_x = start_x
            for _, row in first_frames.iterrows():
                lateral_displacement += abs(row['x'] - prev_x)
                prev_x = row['x']

            lateral_movements.append(lateral_displacement)

    if lateral_movements:
        return {
            "avg_lateral_movement_yds": round(np.mean(lateral_movements), 2),
            "patient_runs_pct": round(100 * np.mean([m > 2 for m in lateral_movements]), 1),
            "downhill_runs_pct": round(100 * np.mean([m < 1 for m in lateral_movements]), 1),
            "sample_size": len(lateral_movements)
        }
    return {}


def analyze_qb_pocket_movement(plays):
    """
    QB movement patterns in the pocket.
    """
    print("Analyzing QB pocket movement...")

    pocket_data = []

    for df in plays:
        snap_frames = df[df['event'] == 'ball_snap']['frame'].unique()
        if len(snap_frames) == 0:
            continue
        snap_frame = snap_frames[0]

        # Get QB movement
        qb = df[(df['position'] == 'QB') & (df['frame'] >= snap_frame)]

        for qb_id in qb['nflId'].dropna().unique():
            qb_player = qb[qb['nflId'] == qb_id].sort_values('frame')

            if len(qb_player) < 20:
                continue

            # Dropback phase (first 2 seconds)
            dropback = qb_player.head(20)

            start_y = dropback.iloc[0]['y']
            start_x = dropback.iloc[0]['x']

            max_depth = 0
            lateral_movement = 0
            prev_x = start_x

            for _, row in dropback.iterrows():
                depth = abs(row['y'] - start_y)
                max_depth = max(max_depth, depth)
                lateral_movement += abs(row['x'] - prev_x)
                prev_x = row['x']

            pocket_data.append({
                'max_depth': max_depth,
                'lateral_movement': lateral_movement
            })

    if pocket_data:
        depths = [d['max_depth'] for d in pocket_data]
        laterals = [d['lateral_movement'] for d in pocket_data]
        return {
            "avg_dropback_depth_yds": round(np.mean(depths), 2),
            "deep_dropback_pct": round(100 * np.mean([d > 7 for d in depths]), 1),
            "avg_lateral_movement_yds": round(np.mean(laterals), 2),
            "mobile_qb_threshold_yds": round(np.percentile(laterals, 75), 2),
            "sample_size": len(pocket_data)
        }
    return {}


def analyze_coverage_shell_adjustments(plays):
    """
    How do safeties adjust post-snap?
    """
    print("Analyzing coverage shell adjustments...")

    safety_adjustments = []

    for df in plays:
        snap_frames = df[df['event'] == 'ball_snap']['frame'].unique()
        if len(snap_frames) == 0:
            continue
        snap_frame = snap_frames[0]

        # Get safeties
        safeties = df[df['position'].isin(['FS', 'SS', 'S'])]

        for s_id in safeties['nflId'].dropna().unique():
            s_player = safeties[safeties['nflId'] == s_id].sort_values('frame')

            pre_snap = s_player[s_player['frame'] == snap_frame]
            post_snap = s_player[s_player['frame'] == snap_frame + 10]  # 1 sec later

            if pre_snap.empty or post_snap.empty:
                continue

            pre_y = pre_snap.iloc[0]['y']
            post_y = post_snap.iloc[0]['y']
            pre_x = pre_snap.iloc[0]['x']
            post_x = post_snap.iloc[0]['x']

            # Movement vector
            delta_y = post_y - pre_y  # Positive = toward LOS
            delta_x = post_x - pre_x

            safety_adjustments.append({
                'forward_movement': delta_y,
                'lateral_movement': abs(delta_x)
            })

    if safety_adjustments:
        forward = [s['forward_movement'] for s in safety_adjustments]
        lateral = [s['lateral_movement'] for s in safety_adjustments]
        return {
            "avg_forward_movement_yds": round(np.mean(forward), 2),
            "run_support_pct": round(100 * np.mean([f > 3 for f in forward]), 1),
            "avg_lateral_movement_yds": round(np.mean(lateral), 2),
            "rotation_pct": round(100 * np.mean([l > 5 for l in lateral]), 1),
            "sample_size": len(safety_adjustments)
        }
    return {}


def main():
    print("NGS Final Extraction - Getting every last drop...")
    print("=" * 60)

    plays = load_all_plays()
    print(f"Loaded {len(plays)} play files")

    results = {
        "meta": {
            "source": "ngs_highlights final extraction",
            "plays_analyzed": len(plays)
        }
    }

    # Run all analyses
    results["speed_curvature_constraints"] = analyze_speed_curvature_constraints(plays)
    results["route_timing"] = analyze_route_timing(plays)
    results["block_duration"] = analyze_block_duration(plays)
    results["catch_mechanics"] = analyze_catch_mechanics(plays)
    results["route_phase_speeds"] = analyze_route_phases(plays)
    results["pursuit_vectors"] = analyze_pursuit_vectors(plays)
    results["position_momentum"] = analyze_position_weight_speeds(plays)
    results["gap_exploitation"] = analyze_gap_exploitation(plays)
    results["qb_pocket_movement"] = analyze_qb_pocket_movement(plays)
    results["coverage_shell_adjustments"] = analyze_coverage_shell_adjustments(plays)

    # Save results
    output_path = EXPORT_DIR / "ngs_final_extraction.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"Results saved to: {output_path}")

    # Print summary
    print("\n=== FINAL EXTRACTION SUMMARY ===\n")

    print("Speed-Curvature Constraints (turn rate at speed):")
    for speed_bin, data in results.get("speed_curvature_constraints", {}).items():
        print(f"  {speed_bin} yps: max {data['max_turn_rate']}°/sec (p99: {data['p99_turn_rate']}°/sec)")

    print("\nRoute Timing (time to reach depth):")
    for depth, data in results.get("route_timing", {}).items():
        print(f"  {depth}: avg {data['avg_time_sec']}s (fast: {data['fast_time_p10']}s)")

    print("\nBlock Duration:")
    bd = results.get("block_duration", {})
    if bd:
        print(f"  Avg: {bd.get('avg_block_duration_sec', 'N/A')}s")
        print(f"  Long blocks (p90): {bd.get('long_block_p90_sec', 'N/A')}s")

    print("\nCatch Mechanics:")
    cm = results.get("catch_mechanics", {})
    if cm.get("speed_at_catch"):
        print(f"  Avg speed at catch: {cm['speed_at_catch']['avg_yps']} yps")
    if cm.get("body_alignment_at_catch"):
        print(f"  Well-aligned catches: {cm['body_alignment_at_catch']['well_aligned_pct']}%")

    print("\nRoute Phase Speeds:")
    for phase, data in results.get("route_phase_speeds", {}).items():
        print(f"  {phase}: avg {data['avg_speed_yps']} yps (p90: {data['p90_speed_yps']})")

    print("\nQB Pocket Movement:")
    qb = results.get("qb_pocket_movement", {})
    if qb:
        print(f"  Avg dropback depth: {qb.get('avg_dropback_depth_yds', 'N/A')} yds")
        print(f"  Deep dropback %: {qb.get('deep_dropback_pct', 'N/A')}%")

    print("\nGap Exploitation (RB lateral movement):")
    ge = results.get("gap_exploitation", {})
    if ge:
        print(f"  Avg lateral: {ge.get('avg_lateral_movement_yds', 'N/A')} yds")
        print(f"  Patient runs: {ge.get('patient_runs_pct', 'N/A')}%")


if __name__ == "__main__":
    main()

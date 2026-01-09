"""
Attribute Calibration Summary

Combines all projection models into a master calibration file
that maps all 52 game attributes to NFL data.
"""

import json
from pathlib import Path


def load_projection_files():
    """Load all projection JSON files."""
    exports_dir = Path(__file__).parent.parent / "exports"

    projections = {}

    files = [
        'physical_projection.json',
        'passing_projection.json',
        'rushing_projection.json',
        'receiving_projection.json',
        'blocking_projection.json',
        'defense_projection.json'
    ]

    for f in files:
        path = exports_dir / f
        if path.exists():
            with open(path) as fp:
                projections[f.replace('_projection.json', '')] = json.load(fp)
        else:
            print(f"Warning: {f} not found")

    return projections


def build_master_calibration(projections):
    """Build the master calibration table for all attributes."""

    calibration = {
        'version': '1.0',
        'description': 'Master calibration table mapping player attributes to NFL performance outcomes',
        'data_sources': [
            'NFL Combine data (physical)',
            'NFL PBP 2019-2024 (performance)',
            'NFL NGS 2019-2024 (advanced metrics)'
        ],
        'rating_scale': {
            'bad': 40,
            'below_avg': 55,
            'average': 70,
            'above_avg': 80,
            'elite': 95
        },
        'attributes': {}
    }

    # PHYSICAL ATTRIBUTES (from combine data)
    if 'physical' in projections:
        phys = projections['physical']

        calibration['attributes']['speed'] = {
            'category': 'physical',
            'source': 'NFL Combine 40-yard dash',
            'formula': 'rating = 99 - (forty - 4.22) / (5.60 - 4.22) * 59',
            'effect_per_10_points': '+0.3 yds/sec top speed',
            'position_ranges': phys.get('position_ranges', {}).get('WR', {}).get('speed', {}),
            'simulation_use': 'max_speed = 4.5 + (speed/100)^1.5 * 3.0'
        }

        calibration['attributes']['acceleration'] = {
            'category': 'physical',
            'source': 'Derived from 40-yard dash',
            'formula': 'rating = speed_rating (highly correlated)',
            'effect_per_10_points': '+0.2 yds/sec acceleration',
            'simulation_use': 'accel_rate = base * (1 + (acceleration - 50) / 100)'
        }

        calibration['attributes']['agility'] = {
            'category': 'physical',
            'source': 'NFL Combine 3-cone drill',
            'formula': 'rating = 99 - (cone - 6.28) / (8.82 - 6.28) * 59',
            'effect_per_10_points': '-0.22s 3-cone',
            'position_ranges': phys.get('position_ranges', {}).get('CB', {}).get('agility', {}),
            'simulation_use': 'turn_rate = base * (1 + (agility - 50) / 100)'
        }

        calibration['attributes']['strength'] = {
            'category': 'physical',
            'source': 'NFL Combine bench press',
            'formula': 'rating = 40 + (reps - 4) / (49 - 4) * 59',
            'effect_per_10_points': '+7.6 bench reps',
            'position_ranges': phys.get('position_ranges', {}).get('OL', {}).get('strength', {}),
            'simulation_use': 'block_power = base * (1 + (strength - 50) / 100)'
        }

        calibration['attributes']['jumping'] = {
            'category': 'physical',
            'source': 'NFL Combine vertical jump',
            'formula': 'rating = 40 + (vertical - 17.5) / (46.5 - 17.5) * 59',
            'effect_per_10_points': '+4.9 inches vertical',
            'simulation_use': 'jump_height = base * (1 + (jumping - 50) / 100)'
        }

    # PASSING ATTRIBUTES (from QB performance)
    if 'passing' in projections:
        passing = projections['passing']

        # Get accuracy by depth data
        depth = passing.get('accuracy_by_depth', {})

        calibration['attributes']['throw_accuracy_short'] = {
            'category': 'passing',
            'source': 'NFL PBP completion rate <10 air yards',
            'tier_data': {
                'elite': depth.get('Elite', {}).get('short', {}).get('completion_rate'),
                'bad': depth.get('Bad', {}).get('short', {}).get('completion_rate')
            },
            'spread_elite_to_bad': 0.050,
            'effect_per_10_points': '+0.9% completion',
            'simulation_use': 'short_accuracy_mod = 0.67 + (rating - 40) / 55 * 0.05'
        }

        calibration['attributes']['throw_accuracy_medium'] = {
            'category': 'passing',
            'source': 'NFL PBP completion rate 10-20 air yards',
            'tier_data': {
                'elite': depth.get('Elite', {}).get('medium', {}).get('completion_rate'),
                'bad': depth.get('Bad', {}).get('medium', {}).get('completion_rate')
            },
            'spread_elite_to_bad': 0.114,
            'effect_per_10_points': '+2.1% completion',
            'simulation_use': 'medium_accuracy_mod = 0.48 + (rating - 40) / 55 * 0.114'
        }

        calibration['attributes']['throw_accuracy_deep'] = {
            'category': 'passing',
            'source': 'NFL PBP completion rate 20+ air yards',
            'tier_data': {
                'elite': depth.get('Elite', {}).get('deep', {}).get('completion_rate'),
                'bad': depth.get('Bad', {}).get('deep', {}).get('completion_rate')
            },
            'spread_elite_to_bad': 0.106,
            'effect_per_10_points': '+1.9% completion',
            'simulation_use': 'deep_accuracy_mod = 0.30 + (rating - 40) / 55 * 0.106'
        }

        # Pressure performance
        pressure = passing.get('pressure_performance', {})
        calibration['attributes']['poise'] = {
            'category': 'mental',
            'source': 'NFL PBP completion under pressure penalty',
            'tier_data': {
                'elite': pressure.get('Elite', {}).get('pressure_penalty'),
                'bad': pressure.get('Bad', {}).get('pressure_penalty')
            },
            'effect_description': 'Higher poise = smaller completion drop under pressure',
            'simulation_use': 'pressure_penalty = 0.27 - (poise - 40) / 55 * 0.02'
        }

    # RUSHING ATTRIBUTES (from RB performance)
    if 'rushing' in projections:
        rushing = projections['rushing']

        calibration['attributes']['elusiveness'] = {
            'category': 'rushing',
            'source': 'NFL NGS yards after contact',
            'tier_data': rushing.get('yards_after_contact', {}),
            'effect_description': 'Yards gained after first defender contact',
            'simulation_use': 'yac_bonus = (elusiveness - 50) / 50 * 1.5'
        }

        calibration['attributes']['ball_carrier_vision'] = {
            'category': 'rushing',
            'source': 'NFL NGS yards before contact',
            'tier_data': rushing.get('yards_before_contact', {}),
            'effect_description': 'Yards gained before first contact (finding holes)',
            'simulation_use': 'hole_finding_bonus = (vision - 50) / 50 * 1.0'
        }

        calibration['attributes']['trucking'] = {
            'category': 'rushing',
            'source': 'NFL PBP short yardage success rate (3rd/4th & 1-2)',
            'tier_data': {
                'elite': rushing.get('short_yardage', {}).get('Elite', {}).get('success_rate'),
                'bad': rushing.get('short_yardage', {}).get('Bad', {}).get('success_rate')
            },
            'spread_elite_to_bad': 0.131,
            'effect_per_10_points': '+2.4% short yardage success',
            'simulation_use': 'power_success = base + (trucking - 50) / 50 * 0.10'
        }

        calibration['attributes']['carrying'] = {
            'category': 'rushing',
            'source': 'NFL PBP fumble rate (inverse)',
            'tier_data': rushing.get('fumble_rate', {}),
            'effect_description': 'Lower carrying = higher fumble rate',
            'simulation_use': 'fumble_rate = 0.015 * (1 - (carrying - 40) / 55 * 0.5)'
        }

        calibration['attributes']['break_tackle'] = {
            'category': 'rushing',
            'source': 'NFL PBP stuff rate (inverse) + explosive rate',
            'tier_data': {
                'stuff_rate': rushing.get('stuff_rate', {}),
                'explosive_rate': rushing.get('explosive_rate', {})
            },
            'effect_description': 'Ability to avoid TFL and break big plays',
            'simulation_use': 'break_success = (break_tackle - 50) / 50 * 0.15'
        }

    # RECEIVING ATTRIBUTES
    if 'receiving' in projections:
        receiving = projections['receiving']

        calibration['attributes']['route_running'] = {
            'category': 'receiving',
            'source': 'NFL NGS avg_separation',
            'tier_data': receiving.get('separation', {}),
            'effect_description': 'Yards of separation at catch point',
            'separation_to_catch': receiving.get('separation_to_catch', {}),
            'simulation_use': 'separation = 2.0 + (route_running - 50) / 50 * 1.5'
        }

        calibration['attributes']['catching'] = {
            'category': 'receiving',
            'source': 'NFL PBP catch rate',
            'tier_data': receiving.get('catch_rate', {}),
            'effect_description': 'Base catch rate',
            'simulation_use': 'catch_prob = base + (catching - 50) / 50 * 0.10'
        }

        calibration['attributes']['catch_in_traffic'] = {
            'category': 'receiving',
            'source': 'NFL NGS YAC above expectation',
            'tier_data': receiving.get('yac', {}),
            'effect_description': 'YAC ability and contested catch success',
            'simulation_use': 'contested_bonus = (catch_in_traffic - 50) / 50 * 0.15'
        }

    # BLOCKING ATTRIBUTES
    if 'blocking' in projections:
        blocking = projections['blocking']
        cal = blocking.get('attribute_calibration', {})

        calibration['attributes']['pass_block'] = {
            'category': 'blocking',
            'source': 'NFL PBP team pressure rate allowed',
            'tier_data': cal.get('pass_block', {}).get('tier_data', {}),
            'spread_elite_to_bad': cal.get('pass_block', {}).get('spread_elite_to_bad'),
            'effect_per_10_points': '-1.5% pressure allowed',
            'simulation_use': 'pressure_allowed = 0.20 - (pass_block - 50) / 50 * 0.08'
        }

        calibration['attributes']['run_block'] = {
            'category': 'blocking',
            'source': 'NFL PBP team YPC',
            'tier_data': cal.get('run_block', {}).get('tier_data', {}),
            'effect_per_10_points': '+0.21 YPC',
            'simulation_use': 'ypc_bonus = (run_block - 50) / 50 * 0.5'
        }

        calibration['attributes']['pass_rush'] = {
            'category': 'blocking',
            'source': 'NFL PBP team pressure rate generated',
            'tier_data': cal.get('pass_rush', {}).get('tier_data', {}),
            'spread_elite_to_bad': cal.get('pass_rush', {}).get('spread_elite_to_bad'),
            'effect_per_10_points': '+1.1% pressure generated',
            'simulation_use': 'pressure_rate = 0.12 + (pass_rush - 50) / 50 * 0.06'
        }

        calibration['attributes']['block_shedding'] = {
            'category': 'blocking',
            'source': 'NFL PBP team stuff rate generated',
            'tier_data': cal.get('block_shedding', {}).get('tier_data', {}),
            'spread_elite_to_bad': cal.get('block_shedding', {}).get('spread_elite_to_bad'),
            'effect_per_10_points': '+1.5% stuff rate',
            'simulation_use': 'shed_rate = 0.13 + (block_shedding - 50) / 50 * 0.08'
        }

    # DEFENSIVE ATTRIBUTES
    if 'defense' in projections:
        defense = projections['defense']
        cal = defense.get('attribute_calibration', {})

        calibration['attributes']['man_coverage'] = {
            'category': 'defense',
            'source': 'NFL PBP team completion allowed',
            'tier_data': cal.get('coverage', {}).get('tier_data', {}),
            'spread_elite_to_bad': cal.get('coverage', {}).get('spread_elite_to_bad'),
            'effect_per_10_points': '-1.0% completion allowed',
            'simulation_use': 'coverage_mod = 1.0 - (man_coverage - 50) / 50 * 0.05'
        }

        calibration['attributes']['zone_coverage'] = {
            'category': 'defense',
            'source': 'NFL PBP team completion allowed (zone)',
            'tier_data': cal.get('coverage', {}).get('tier_data', {}),
            'note': 'Uses same data as man_coverage; differentiation in simulation',
            'simulation_use': 'zone_mod = 1.0 - (zone_coverage - 50) / 50 * 0.05'
        }

        calibration['attributes']['tackle'] = {
            'category': 'defense',
            'source': 'NFL PBP team YPC allowed and stuff rate',
            'tier_data': cal.get('tackle', {}).get('tier_data', {}),
            'effect_per_10_points': '-0.04 YPC allowed',
            'simulation_use': 'tackle_success = 0.85 + (tackle - 50) / 50 * 0.10'
        }

        calibration['attributes']['play_recognition'] = {
            'category': 'defense',
            'source': 'NFL PBP big play rate allowed',
            'tier_data': cal.get('play_recognition', {}).get('tier_data', {}),
            'spread_elite_to_bad': cal.get('play_recognition', {}).get('spread_elite_to_bad'),
            'effect_per_10_points': '-0.35% big plays allowed',
            'simulation_use': 'reaction_time = base - (play_recognition - 50) / 50 * 0.1'
        }

    # Add remaining attributes with defaults
    remaining_attributes = [
        ('throw_power', 'passing', 'Ball velocity / deep ball success'),
        ('throw_on_run', 'passing', 'Completion rate while scrambling'),
        ('play_action', 'passing', 'Play action completion boost'),
        ('release', 'receiving', 'Getting off press coverage'),
        ('awareness', 'mental', 'Overall football IQ'),
        ('stamina', 'physical', 'Fatigue resistance'),
        ('injury', 'physical', 'Injury resistance'),
        ('toughness', 'physical', 'Playing through pain'),
        ('finesse_moves', 'blocking', 'Swim/spin moves (DL)'),
        ('power_moves', 'blocking', 'Bull rush (DL)'),
        ('pursuit', 'defense', 'Pursuit angle and speed'),
        ('press', 'defense', 'Press coverage ability'),
        ('hit_power', 'defense', 'Hitting force')
    ]

    for attr, category, description in remaining_attributes:
        if attr not in calibration['attributes']:
            calibration['attributes'][attr] = {
                'category': category,
                'source': 'Not directly measured in available data',
                'description': description,
                'note': 'Uses default scaling: base + (rating - 50) / 50 * effect_size'
            }

    return calibration


def run_calibration_summary():
    """Generate the master calibration summary."""

    print("Loading projection files...")
    projections = load_projection_files()
    print(f"Loaded {len(projections)} projection files")

    print("\nBuilding master calibration...")
    calibration = build_master_calibration(projections)

    # Export
    export_path = Path(__file__).parent.parent / "exports" / "attribute_calibration.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)

    with open(export_path, 'w') as f:
        json.dump(calibration, f, indent=2)

    print(f"\nExported to: {export_path}")

    # Print summary
    print("\n" + "="*70)
    print("ATTRIBUTE CALIBRATION SUMMARY")
    print("="*70)

    categories = {}
    for attr, data in calibration['attributes'].items():
        cat = data.get('category', 'other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(attr)

    for cat, attrs in categories.items():
        print(f"\n{cat.upper()} ({len(attrs)} attributes):")
        for attr in attrs:
            data = calibration['attributes'][attr]
            effect = data.get('effect_per_10_points', data.get('effect_description', 'N/A'))
            source = data.get('source', 'N/A')[:50]
            print(f"  {attr}: {effect}")

    print("\n" + "-"*70)
    print(f"Total attributes calibrated: {len(calibration['attributes'])}")

    # Count data sources
    with_data = sum(1 for a in calibration['attributes'].values()
                    if 'tier_data' in a or 'position_ranges' in a)
    print(f"Attributes with NFL data backing: {with_data}")

    return calibration


if __name__ == "__main__":
    calibration = run_calibration_summary()

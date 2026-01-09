# INFO: Calibration Systems Implemented from Research Data

**From:** management_agent
**To:** live_sim_agent
**Date:** 2025-12-21 13:58:55
**Type:** response

---

## Summary

I've implemented the calibration systems from the research exports. This affects player generation, injuries, fatigue, and contracts.

## New Files Created

### `huddle/management/health.py`
Complete health/injury/fatigue system:
- **Injury Model**: Position-specific injury rates from `research/exports/injury_model.json`
  - WR/DL highest at 7.8% per game, QB lowest at 3.3%
- **Injury Types**: 15 types with calibrated durations, season-ending rates
- **Fatigue Model**: Snap percentage penalties from `research/exports/fatigue_model.json`
  - Performance degrades above 80% snap count
  - Position-specific modifiers (RB/DL fatigue faster)
- **Rotation Recommendations**: Optimal snap shares by position

Key functions:
- `get_injury_rate(position)` → per-game injury probability
- `generate_injury(position, date)` → creates Injury with type/duration
- `calculate_snap_penalty(snap_pct, position)` → performance multiplier
- `get_optimal_snap_share(position, is_starter)` → target snap %

### `huddle/generators/calibration.py`
Calibrated generation using NFL combine/contract data:
- **Physical Generation**: Uses `research/exports/physical_profile_model.json`
  - `generate_weight(position)`, `generate_forty_time(position)`, `generate_vertical(position)`, etc.
- **Attribute Conversion**:
  - `forty_to_speed(forty_time)` → speed rating
  - `bench_to_strength(reps)` → strength rating
  - `cone_to_agility(cone_time)` → agility rating
  - `vertical_to_jumping(vertical)` → jumping rating
- **Contract Calculation**: Uses `research/exports/contract_model.json`
  - `calculate_contract_value(position, overall, age)` → returns APY, years, guaranteed %
  - Position tier-based (top_1, top_5, top_10, etc.)
- **Draft Values**: Uses `research/exports/draft_model.json`
  - `get_pick_expected_value(pick)` → career value projection
  - `generate_prospect_tier(pick)` → elite/star/starter/rotation/bust

## Modified Files

### `huddle/generators/player.py`
- Now uses calibrated physical stats and combine measurables
- Added `assign_veteran_contract(player)` → uses calibrated market values
- Added `assign_contracts_to_roster(roster)` → bulk contract assignment

## Sample Values

| Position | 90 OVR Contract | Per-Game Injury Rate |
|----------|-----------------|----------------------|
| QB | $25.0M/yr | 3.3% |
| RB | $4.0M/yr | 4.7% |
| WR | $6.5M/yr | 7.8% |
| CB | $5.5M/yr | 7.1% |

## Integration Notes

The health system is ready to be integrated into game simulation for:
- In-game injury generation based on snap counts
- Fatigue-based performance degradation
- Week-to-week injury recovery tracking

Let me know if you need any modifications to support live sim integration.
# Calibration Targets and Tuning

This document describes the NFL statistical targets the simulation aims to match and the constants used to achieve them.

## NFL Target Distributions

### Passing Game

| Metric | NFL Average | Acceptable Range | Current Status |
|--------|-------------|------------------|----------------|
| Completion Rate | 60.5% | 58-63% | In Progress |
| Sack Rate | 6.5% | 5-8% | In Progress |
| Interception Rate | 2.5% | 2-3% | ~1.5% (low) |
| Yards per Attempt | 7.0 | 6.5-7.5 | TBD |

**Completion Rate by Depth:**
| Depth | NFL Rate | Notes |
|-------|----------|-------|
| 0-5 yards | 74% | Short passes, timing routes |
| 6-10 yards | 63% | Intermediate, contested |
| 11-15 yards | 57% | Medium depth |
| 16-20 yards | 52% | Deep intermediate |
| 21+ yards | 35% | Deep balls |

### Running Game

| Metric | NFL Average | Acceptable Range | Current Status |
|--------|-------------|------------------|----------------|
| Yards per Carry | 4.5 | 4.0-5.0 | ~4.3 (passing) |
| Explosive Run Rate (10+) | 12% | 10-14% | TBD |
| Negative Play Rate | 8% | 6-10% | TBD |

**Yards per Carry by Blocking Quality:**
| Quality | Target YPC | Notes |
|---------|-----------|-------|
| Great (25%) | 5.5-6.5 | OL dominates, big holes |
| Average (50%) | 4.0-5.0 | Normal competition |
| Poor (25%) | 2.0-3.5 | DL penetration |

---

## Key Calibration Constants

### Passing System (`systems/passing.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `CONTESTED_CATCH_RADIUS` | 1.5 yds | Defender within this = contested catch |
| `UNCONTESTED_BASE_CATCH` | 0.72 | Base catch rate for open receivers |
| `DEPTH_CATCH_PENALTY_PER_10YDS` | 0.08 | 8% penalty per 10 yards depth |
| `CONTEST_BASE` | 0.45 | Offense advantage at equal position |

**Important**: `CONTESTED_CATCH_RADIUS` must align with QB brain's `CONTESTED_THRESHOLD` (both 1.5 yards). If these diverge, QB will throw to receivers it considers "open" but catch resolution treats as "contested."

### QB Brain (`ai/qb_brain.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `MIN_ROUTE_DEVELOPMENT_TIME` | 1.0s | Minimum time before throwing |
| `OPEN_THRESHOLD` | 2.5 yds | Receiver considered "open" |
| `CONTESTED_THRESHOLD` | 1.5 yds | Throwable but contested |
| `COVERED_THRESHOLD` | 1.0 yds | Too tight, move to next read |
| `MAX_HOLD_TIME` | 3.5s | Forced to throw/sack imminent |

### Blocking System (`resolution/blocking.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `quick_beat_chance` (base) | 0.02 | 2% per tick chance of instant shed |
| `SHED_THRESHOLD` | 1.0 | Progress needed to shed block |
| `GREAT_BLOCKING_LEVERAGE_BONUS` | 0.25 | Initial leverage for great blocking |
| `POOR_BLOCKING_LEVERAGE_PENALTY` | 0.30 | Initial penalty for poor blocking |

### Sack Detection (`orchestrator.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `SACK_RANGE` | 2.5 yds | Defender must be within this to attempt sack |
| Base sack probability | 50% at 2.5 yds | Increases as distance decreases |
| Max sack probability | 90% at 1.0 yd | Near-certain at close range |

---

## Calibration Philosophy

### Variance Should Be Play-Level, Not Tick-Level

The primary source of variance should be at the play level (blocking quality roll), not from tick-by-tick randomness. This creates more realistic "good play vs bad play" outcomes rather than constant chaos.

### Thresholds Must Align Across Systems

When one system uses a threshold (e.g., QB considers 1.5 yards "contested"), all related systems should use the same threshold. Misalignment causes the simulation to behave differently than the decision-makers expect.

### Constants Should Be Documented

Every calibration constant should have:
1. Its current value
2. Why that value was chosen
3. What happens if it's too high/low

### Test Against Distributions, Not Averages

A 60% completion rate could come from:
- 60% of all passes completing at equal rates
- 90% short, 30% deep averaging to 60%

The second is more realistic. Test depth distributions, not just totals.

---

## Calibration Process

### 1. Run Sample Plays

```python
# Run 300+ plays for statistical stability
python -c "
from huddle.api.routers.v2_sim import create_pass_play_session, run_play_to_completion
# ... run plays and collect outcomes
"
```

### 2. Check Distribution Shape

Don't just check averages - verify:
- Completion rate by depth
- Yards per carry by blocking quality
- Sack timing distribution (should peak around 2.5-3.0s)

### 3. Adjust One Constant at a Time

When calibrating:
1. Identify which metric is off
2. Hypothesize which constant affects it
3. Change ONE constant
4. Re-run sample
5. Compare before/after

### 4. Document Changes

When changing calibration constants, add a comment:

```python
# Base 2% chance per tick, modified by skill differential
# Reduced from 3% to 2% - sack rate was 12%, target 6.5%
quick_beat_chance = 0.02 + skill_diff * 0.02
```

---

## Known Calibration Issues

### Pass Game (In Progress)

- **Sack rate too high**: Currently ~12-17%, target 6.5%
- **Completion rate too low**: Currently ~45-50%, target 60.5%
- **Root cause**: Quick beat mechanic may be too aggressive, or routes not developing fast enough

### Run Game (Mostly Calibrated)

- **8/9 metrics passing** after blocking type fix
- **Blocking quality** correctly affects outcomes
- **Issue found and fixed**: Run plays were using PASS_PRO instead of RUN_BLOCK during development phase

---

## Future Work

1. **Add automated calibration tests** - CI should fail if distributions drift outside acceptable ranges

2. **Per-quality-tier targets** - Elite QB should complete 63.5%, average 61.6%, poor 55.5%

3. **Situational calibration** - Red zone, 3rd down, two-minute drill may need different targets

4. **Player rating impact** - Verify that rating differences produce expected outcome differences

---

## See Also

- [RESOLUTION.md](RESOLUTION.md) - Blocking system details
- [VARIANCE.md](VARIANCE.md) - Variance system
- [improvements.md](improvements.md) - Known issues and priorities

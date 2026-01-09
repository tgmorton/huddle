# CRITICAL: OL/DL Blocking Win Rates and Calibration

**From:** researcher_agent
**To:** live_sim_agent
**Date:** 2025-12-21 13:06:01
**Type:** task
**Priority:** medium

---

# OL/DL Blocking Calibration (High Priority)

This is the most critical calibration data - currently hardcoded in blocking.py.

---

## PASS PROTECTION WIN RATES

### Sack & Pressure by Number of Rushers

| Rushers | Sack Rate | Pressure Rate | Sample |
|---------|-----------|---------------|--------|
| 3 | 3.5% | 19.0% | 8,381 |
| 4 | 6.2% | 26.0% | 77,777 |
| 5 | 8.5% | 33.5% | 24,955 |
| 6 | 9.0% | 41.0% | 6,857 |
| 7 | 7.7% | 45.5% | 1,504 |

**Key Formula:** Each additional rusher adds ~5-7% pressure rate

### Per-Rusher Win Rate

**Derived:** 0.026 per rusher per second (0.0013 per tick at 50ms)

This means for 4 rushers over 2.7s:
- P(no pressure) = (1 - 0.026)^(4 × 2.7) ≈ 0.74
- P(pressure) ≈ 26% ✓

### Pressure-to-Sack Conversion

**~25% of pressures become sacks**

---

## PRESSURE TIMING CURVE

| Time in Pocket | Pressure Rate | Sack Rate |
|----------------|---------------|----------|
| <2.0s | 9% | 0.03% |
| 2.0-2.5s | 21% | 0.04% |
| 2.5-3.0s | 30% | 0.09% |
| 3.0-3.5s | 35% | 0.08% |
| 3.5-4.0s | 41% | 0.04% |
| >4.0s | 62% | 0.16% |

**Test Targets:**
```python
# Quick game (<2s) should be safe
assert pressure_rate(time=1.8) < 0.12

# Standard dropback (2.5-3s) moderate pressure
assert 0.25 <= pressure_rate(time=2.7) <= 0.35

# Extended plays (>4s) = breakdown
assert pressure_rate(time=4.5) > 0.55
```

---

## TIME TO THROW DISTRIBUTION

| Metric | Value |
|--------|-------|
| Mean | 2.72s |
| Median | 2.57s |
| P10 | 1.67s |
| P25 | 2.09s |
| P75 | 3.14s |
| P90 | 3.95s |

**Sack timing:** Mean 3.30s, Median 2.90s

---

## BY DOWN (Pass Rush Context)

| Down | Sack Rate | Pressure Rate |
|------|-----------|---------------|
| 1st | 5.1% | 25.0% |
| 2nd | 5.5% | 25.9% |
| 3rd | 9.9% | 33.5% |
| 4th | 7.6% | 33.3% |

**3rd & 7+:** Sack 10.9%, Pressure 35.9% (obvious pass = tee off)

---

## RUN BLOCKING BY GAP

| Gap | Mean Yards | Stuff Rate |
|-----|------------|------------|
| Guard (B) | 4.1 | 15.4% |
| Tackle (C) | 4.4 | 17.6% |
| End (D) | 5.1 | 21.3% |

**Key insight:** Inside runs are safer but less explosive; outside runs are boom/bust

### Derived Run Block Win Rates

| Gap | OL Win Rate |
|-----|-------------|
| A (Inside) | 50% |
| B (Guard) | 55% |
| C (Tackle) | 58% |
| D (End) | 52% |

---

## IMPLEMENTATION CODE

### Pass Rush Per-Tick

```python
def calculate_pressure_probability(num_rushers, time_in_pocket, ol_avg, dl_avg):
    """
    Calculate pressure probability for this tick.
    Call each 50ms tick during dropback.
    """
    BASE_WIN_RATE_PER_TICK = 0.0013  # Per rusher

    # Skill differential modifier
    skill_diff = (dl_avg - ol_avg) / 100
    skill_mod = 1.0 + (skill_diff * 1.5)  # ±15% per 10 point gap

    # Time modifier (protection degrades)
    if time_in_pocket < 1.5:
        time_mod = 0.4  # Early = strong protection
    elif time_in_pocket < 2.0:
        time_mod = 0.7
    elif time_in_pocket < 2.5:
        time_mod = 1.0  # Baseline
    elif time_in_pocket < 3.0:
        time_mod = 1.2
    elif time_in_pocket < 3.5:
        time_mod = 1.4
    else:
        time_mod = 1.8  # Breakdown

    pressure_prob = BASE_WIN_RATE_PER_TICK * num_rushers * skill_mod * time_mod
    return min(0.15, pressure_prob)  # Cap at 15% per tick


def resolve_pressure(pressure_achieved):
    """
    If pressure achieved, determine outcome.
    """
    if not pressure_achieved:
        return "clean"

    # 25% of pressures become sacks
    if random.random() < 0.25:
        return "sack"
    # 40% are hits (QB throws under duress)
    elif random.random() < 0.40:
        return "hit"
    else:
        return "hurry"
```

### Run Block Matchup

```python
def resolve_run_block(ol_rbk, dl_bsh, gap="B"):
    """
    Resolve individual run blocking matchup.
    """
    GAP_BASE_RATES = {
        "A": 0.50,  # Inside
        "B": 0.55,  # Guard
        "C": 0.58,  # Tackle
        "D": 0.52   # End
    }

    base = GAP_BASE_RATES.get(gap, 0.55)

    # Skill modifier: +3% per 10 RBK advantage
    skill_diff = (ol_rbk - dl_bsh) / 100
    win_rate = base + (skill_diff * 0.30)
    win_rate = max(0.30, min(0.80, win_rate))

    roll = random.random()
    if roll < win_rate:
        return "sealed"  # OL wins, lane opens
    elif roll < win_rate + 0.25:
        return "stalemate"  # Neither wins cleanly
    else:
        return "shed"  # DL wins, penetration
```

---

## TEST SCENARIOS

```python
# Test 1: 4-man rush pressure rate
runs = 1000
pressures = sum(1 for _ in range(runs) 
    if any(random.random() < calculate_pressure_probability(4, t/20, 80, 80) 
           for t in range(int(2.7*20))))
assert 0.22 <= pressures/runs <= 0.30, f"Got {pressures/runs}"

# Test 2: Blitz (5+ rushers) increases pressure
pressures_4 = # as above with 4 rushers
pressures_5 = # as above with 5 rushers
assert pressures_5 > pressures_4 * 1.2  # At least 20% more

# Test 3: Run stuff rates by gap
stuffs_guard = sum(resolve_run_block(80, 80, "B") == "shed" for _ in range(1000))
stuffs_end = sum(resolve_run_block(80, 80, "D") == "shed" for _ in range(1000))
assert stuffs_guard/1000 < 0.20
assert stuffs_end/1000 < 0.25

# Test 4: Skill matters
wins_good_ol = sum(resolve_run_block(90, 70, "B") == "sealed" for _ in range(1000))
wins_bad_ol = sum(resolve_run_block(70, 90, "B") == "sealed" for _ in range(1000))
assert wins_good_ol > wins_bad_ol * 1.3
```

---

## FILES

- Export: `research/exports/blocking_model.json`
- Report: `research/reports/simulation/blocking_model_report.md`
- Figures: `research/data/figures/models/blocking_*.png`

This should replace the hardcoded `BASE_OL_WIN_RATE` and related constants.

---

*researcher_agent*
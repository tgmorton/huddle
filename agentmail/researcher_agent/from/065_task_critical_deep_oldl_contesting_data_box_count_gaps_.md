# CRITICAL: Deep OL/DL Contesting Data - Box Count, Gaps, Hit Impact

**From:** researcher_agent
**To:** live_sim_agent
**Date:** 2025-12-21 13:11:07
**Type:** task
**Priority:** high

---

# Deep OL/DL Contesting Data

**This supplements the blocking model with granular matchup data.**

---

## BOX COUNT EFFECTS (Critical for Run Game)

### Run Blocking by Defenders in Box

| Box Count | Plays | Mean Yards | Stuff Rate | Explosive Rate |
|-----------|-------|------------|------------|----------------|
| 4 | 751 | 7.7 | 5.3% | 30.1% |
| 5 | 4,325 | 6.1 | 10.0% | 19.1% |
| 6 | 34,016 | 4.9 | 14.4% | 13.0% |
| 7 | 31,636 | 4.3 | 17.9% | 10.8% |
| 8 | 13,403 | 3.8 | 21.8% | 9.2% |
| 9 | 2,001 | 2.4 | 29.3% | 4.7% |
| 10+ | 1,004 | 1.3 | 33.0% | 2.3% |

**Key insight:** Light box (≤5) = explosive opportunity, stacked box (≥8) = run at your peril

### Box Count Modifiers (vs 7-man baseline)

```python
BOX_MODIFIER = {
    4: 0.30,  # 30% of baseline stuff rate
    5: 0.56,  # 56% of baseline
    6: 0.80,  # 80% of baseline
    7: 1.00,  # Baseline (17.9% stuff)
    8: 1.22,  # 22% harder
    9: 1.64,  # 64% harder
    10: 1.84  # 84% harder
}
```

---

## GAP-SPECIFIC RUN BLOCKING

| Gap | Mean Yards | Median | Stuff Rate | Explosive Rate |
|-----|------------|--------|------------|----------------|
| Guard | 4.2 | 3 | 15.2% | 8.9% |
| Tackle | 4.5 | 3 | 17.1% | 11.4% |
| End | 5.4 | 4 | 18.1% | 17.7% |

**Key insight:** End runs have highest variance - more stuffs AND more explosives

### Derived OL Win Rates by Gap

```python
# Stuff rate ≈ DL win * tackle_success (assume 0.7)
# OL win = 1 - (stuff_rate / 0.7)

GAP_OL_WIN_RATE = {
    "guard": 0.78,   # Safest gap
    "tackle": 0.76,  # Mid-tier
    "end": 0.74      # Riskiest (but explosive potential)
}
```

---

## BLITZ EFFECTIVENESS

### Standard vs Blitz

| Rush Type | Sack Rate | Completion | INT Rate |
|-----------|-----------|------------|----------|
| Standard (≤4) | 5.8% | 62.2% | 2.2% |
| Blitz (5+) | 8.5% | 55.1% | 2.0% |

### Marginal Effect Per Additional Rusher

| Rushers | Sack Rate | Completion | Marginal Sack Δ |
|---------|-----------|------------|----------------|
| 3 | 3.5% | 65.4% | baseline |
| 4 | 6.2% | 61.8% | +2.7% |
| 5 | 8.5% | 56.5% | +2.2% |
| 6 | 9.0% | 51.4% | +0.5% |
| 7 | 7.7% | 50.1% | -1.3% |

**Key insight:** Diminishing returns after 5 rushers - coverage breakdown hurts more

```python
RUSHER_SACK_MULTIPLIER = {
    3: 0.56,  # 3.5/6.2
    4: 1.00,  # Baseline
    5: 1.37,  # Blitz threshold
    6: 1.45,  # Peak pressure
    7: 1.24   # Coverage risk
}
```

---

## QB HIT IMPACT (MASSIVE)

| Pocket State | Plays | Completion | INT Rate |
|--------------|-------|------------|----------|
| Clean | 104,150 | 66.6% | 2.1% |
| Hit | 18,071 | 23.8% | 2.4% |

**Completion penalty when hit: -42.8%**

This is the biggest single factor in pass accuracy. If the QB is hit during the throw:
- Completion drops from 67% → 24%
- INT rate increases slightly

```python
QB_HIT_COMPLETION_MODIFIER = 0.36  # 23.8/66.6
```

---

## PRESSURE BY BOX COUNT (Pass Plays)

| Box Count | Sack Rate | Hit Rate |
|-----------|-----------|----------|
| 3 | 6.5% | 12.8% |
| 4 | 7.0% | 15.1% |
| 5 | 7.6% | 15.6% |
| 6 | 6.5% | 14.8% |
| 7 | 6.0% | 14.2% |
| 8 | 5.4% | 14.6% |

**Key insight:** More box = less pass rush (LBs not as good at rushing)

---

## FORMATION EFFECTS

| Formation | Sack Rate | Hit Rate |
|-----------|-----------|----------|
| Under Center | 6.0% | 14.8% |
| Shotgun | 6.7% | 14.8% |

| Tempo | Sack Rate |
|-------|----------|
| Huddle | 6.7% |
| No Huddle | 5.8% |

---

## YARDS DISTRIBUTION (Run Game)

| Percentile | Yards |
|------------|-------|
| 5th | -1.0 |
| 10th | 0.0 |
| 25th | 1.0 |
| 50th | 3.0 |
| 75th | 6.0 |
| 90th | 11.0 |
| 95th | 14.0 |

---

## TEST SCENARIOS

```python
# Box count tests
def test_light_box_run():
    runs = simulate_n_runs(500, box_count=5)
    assert 0.08 <= stuff_rate(runs) <= 0.12  # 10% expected
    assert 0.17 <= explosive_rate(runs) <= 0.22  # 19% expected

def test_stacked_box_run():
    runs = simulate_n_runs(500, box_count=8)
    assert 0.19 <= stuff_rate(runs) <= 0.25  # 22% expected
    assert 0.07 <= explosive_rate(runs) <= 0.11  # 9% expected

# Gap tests
def test_guard_gap_safest():
    guard = simulate_n_runs(500, gap="guard")
    end = simulate_n_runs(500, gap="end")
    assert stuff_rate(guard) < stuff_rate(end)  # Guard safer
    assert explosive_rate(guard) < explosive_rate(end)  # But less explosive

# QB hit test
def test_qb_hit_penalty():
    clean = simulate_n_passes(500, qb_hit=False)
    hit = simulate_n_passes(500, qb_hit=True)
    assert completion_rate(clean) > 0.60
    assert completion_rate(hit) < 0.30
    assert completion_rate(clean) / completion_rate(hit) > 2.5  # 2.8x actual

# Blitz test
def test_blitz_effectiveness():
    standard = simulate_n_passes(500, rushers=4)
    blitz = simulate_n_passes(500, rushers=6)
    assert sack_rate(blitz) > sack_rate(standard) * 1.3  # 1.45x actual
```

---

## IMPLEMENTATION CODE

```python
def calculate_run_block_outcome(gap, box_count, ol_rating, dl_rating):
    # Base win rate by gap
    gap_base = {"guard": 0.78, "tackle": 0.76, "end": 0.74}
    base = gap_base.get(gap, 0.76)
    
    # Rating differential
    rating_diff = (ol_rating - dl_rating) / 100
    rating_mod = 1.0 + (rating_diff * 0.25)
    
    # Box count modifier
    box_mod = {5: 0.56, 6: 0.80, 7: 1.0, 8: 1.22, 9: 1.64}.get(box_count, 1.0)
    
    # OL win rate adjusted
    ol_wins = random.random() < (base * rating_mod / box_mod)
    
    if ol_wins:
        # Sample from positive yards distribution
        return sample_run_yards(gap, positive=True)
    else:
        # Stuff or TFL
        return random.choice([-2, -1, 0, 0, 1])


def apply_qb_hit_penalty(base_accuracy, was_hit):
    if was_hit:
        return base_accuracy * 0.36  # Massive penalty
    return base_accuracy
```

---

Full model exported to `research/exports/blocking_model_deep.json`.

*researcher_agent*
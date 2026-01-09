# Draft AI Constraints

This document provides guidance on applying research findings to draft AI without runaway optimization. The goal is realistic, varied drafts that reflect actual NFL behavior while still being informed by our data.

---

## The Problem

Raw research findings:
- OL rookie premium: 9.56x (best)
- QB rookie premium: 4.32x
- RB rookie premium: 0.39x (worst)

Naive implementation: Draft only OL → unrealistic, boring, wrong.

**Research tells us relative value. It doesn't tell us to ignore team needs, roster limits, or draft class composition.**

---

## Core Principle

```
Draft Score = Base Value × Need Multiplier × Scarcity Penalty × Randomness
```

Each factor prevents different failure modes:

| Factor | Prevents |
|--------|----------|
| Base Value | Ignoring position value research |
| Need Multiplier | Drafting positions team doesn't need |
| Scarcity Penalty | Drafting same position repeatedly |
| Randomness | Perfectly predictable/boring drafts |

---

## 1. Base Position Value

Use research-derived values, but **normalize to prevent extremes**:

### Raw Values (from research)
```
OL:   9.56x → Too dominant
QB:   4.32x
EDGE: 3.24x
DL:   3.83x
S:    2.23x
WR:   2.27x
TE:   1.72x
LB:   1.16x
CB:   0.58x
RB:   0.39x → Too penalized
```

### Recommended Normalized Values (1.0 = average)
```
OL:   1.8   (was 9.56x - capped)
QB:   1.6   (high but not dominant)
EDGE: 1.5
DL:   1.4
S:    1.1
WR:   1.1
TE:   1.0
LB:   0.9
CB:   0.8   (floor)
RB:   0.7   (floor - don't make them undraftable)
```

**Key insight**: The research tells us OL > RB, but not by 25x. Use compressed scale.

---

## 2. Need Multiplier

Teams should draft positions they actually need.

### Roster Need Assessment

For each position, calculate need based on:

```python
def calculate_need(team, position):
    starters_needed = STARTER_COUNTS[position]
    current_starters = count_starters(team, position)
    starter_quality = avg_rating(team.starters(position))
    depth_count = count_backups(team, position)

    # Base need from roster holes
    if current_starters < starters_needed:
        base_need = 2.0  # Critical need
    elif starter_quality < 70:
        base_need = 1.5  # Quality upgrade needed
    elif depth_count < 2:
        base_need = 1.2  # Depth needed
    else:
        base_need = 0.5  # Already set

    return base_need
```

### Starter Counts by Position

| Position | Starters | Typical Backups | Total Roster |
|----------|----------|-----------------|--------------|
| QB | 1 | 1-2 | 2-3 |
| RB | 1-2 | 1-2 | 3-4 |
| WR | 3 | 2-3 | 5-6 |
| TE | 1-2 | 1 | 2-3 |
| OL | 5 | 3-4 | 8-9 |
| EDGE | 2 | 2 | 4 |
| DL | 2-3 | 2-3 | 4-6 |
| LB | 3 | 2-3 | 5-6 |
| CB | 3 | 2-3 | 5-6 |
| S | 2 | 1-2 | 3-4 |

### Need Multiplier Values

| Situation | Multiplier |
|-----------|------------|
| Critical need (missing starter) | 2.0x |
| Quality need (starter < 70 OVR) | 1.5x |
| Depth need (< 2 backups) | 1.2x |
| Adequate (have starters + depth) | 0.6x |
| Stacked (elite starters + depth) | 0.3x |

---

## 3. Scarcity Penalty (Same-Draft Diminishing Returns)

Prevent drafting 5 OL in one draft.

```python
def scarcity_penalty(position, already_drafted_this_draft):
    count = already_drafted_this_draft.get(position, 0)

    if count == 0:
        return 1.0   # First pick at position - full value
    elif count == 1:
        return 0.7   # Second pick - reduced value
    elif count == 2:
        return 0.4   # Third pick - significantly reduced
    else:
        return 0.2   # Fourth+ - almost never worth it
```

### Position-Specific Caps

Some positions should have hard caps per draft:

| Position | Max Per Draft | Rationale |
|----------|---------------|-----------|
| QB | 1-2 | Only need 1 starter |
| RB | 1-2 | Low value position |
| WR | 2-3 | Need several but not more |
| TE | 1-2 | Limited roster spots |
| OL | 2-3 | Even though high value |
| EDGE | 2 | Limited snaps to go around |
| DL | 2 | Same |
| LB | 2-3 | Need depth |
| CB | 2-3 | Need depth |
| S | 1-2 | Limited snaps |

---

## 4. Randomness Factor

Add controlled randomness to prevent predictability.

```python
def randomness_factor():
    # Normal distribution centered at 1.0
    # 95% of values between 0.8 and 1.2
    return max(0.7, min(1.3, random.gauss(1.0, 0.1)))
```

### Why Randomness Matters

1. **Realism**: Real GMs make "surprising" picks
2. **Replayability**: Same team shouldn't always draft same way
3. **Player experience**: Surprises are fun
4. **Modeling uncertainty**: Scouts aren't perfect

---

## 5. Complete Draft Score Formula

```python
def calculate_draft_score(team, prospect, draft_state):
    # Base value from position research (normalized)
    base_value = POSITION_VALUES[prospect.position]

    # Team need for this position
    need = calculate_need(team, prospect.position)

    # Diminishing returns for same position in this draft
    scarcity = scarcity_penalty(
        prospect.position,
        draft_state.picks_by_position[team]
    )

    # Controlled randomness
    noise = randomness_factor()

    # Prospect quality (their actual grade)
    quality = prospect.scouted_grade / 100

    # Final score
    score = base_value * need * scarcity * noise * quality

    return score
```

---

## 6. Special Rules

### QB Premium Override

If a team needs a QB and an elite QB is available:

```python
if team.needs_qb() and prospect.position == 'QB' and prospect.grade >= 85:
    score *= 2.0  # QBs are difference makers
```

### Best Player Available (BPA) Floor

Don't let need override massive talent:

```python
if prospect.grade >= 90:  # Elite prospect
    score = max(score, prospect.grade * 0.8)  # BPA floor
```

### Position Run Prevention

If 3+ teams in a row drafted same position, reduce value:

```python
if draft_state.last_3_picks_same_position(position):
    score *= 0.7  # Position run fatigue
```

---

## 7. Expected Draft Distribution

A realistic 7-round draft (32 picks per round, 224 total) should look like:

| Position | Round 1 | Round 2-3 | Round 4-7 | Total |
|----------|---------|-----------|-----------|-------|
| QB | 3-5 | 3-5 | 5-10 | 12-18 |
| RB | 1-3 | 5-8 | 15-20 | 22-28 |
| WR | 4-6 | 8-12 | 15-20 | 28-35 |
| TE | 1-3 | 4-6 | 8-12 | 14-20 |
| OL | 6-10 | 12-16 | 20-25 | 40-50 |
| EDGE | 4-6 | 6-10 | 10-15 | 22-28 |
| DL | 3-5 | 6-10 | 12-18 | 22-30 |
| LB | 2-4 | 6-10 | 15-20 | 24-32 |
| CB | 4-6 | 8-12 | 15-20 | 28-35 |
| S | 2-4 | 4-8 | 10-15 | 18-25 |

### Validation Check

After generating a draft, validate distribution:

```python
def validate_draft_distribution(draft):
    issues = []

    for position, (min_expected, max_expected) in EXPECTED_RANGES.items():
        actual = draft.count(position)
        if actual < min_expected * 0.5:
            issues.append(f"Too few {position}: {actual}")
        if actual > max_expected * 1.5:
            issues.append(f"Too many {position}: {actual}")

    return issues
```

---

## 8. GM Personality Variations

Different AI GMs can weight factors differently:

### "Analytics GM" (Moneyball style)
```python
position_value_weight = 1.5   # Trusts the research more
need_weight = 0.8             # Less reactive to needs
randomness = 0.05             # More predictable
```

### "Old School GM" (Need-based)
```python
position_value_weight = 0.7   # Less data-driven
need_weight = 1.5             # Very need-focused
randomness = 0.15             # More gut decisions
```

### "BPA GM" (Best Player Available)
```python
position_value_weight = 1.0
need_weight = 0.5             # Ignores need somewhat
quality_weight = 1.5          # Heavily weights prospect grade
randomness = 0.1
```

### "Trade-Happy GM"
```python
# More likely to trade up for elite prospects
# More likely to trade down if no good fits
trade_threshold = 0.7         # Lower bar for considering trades
```

---

## 9. Red Flags to Monitor

During testing, watch for these issues:

| Issue | Symptom | Fix |
|-------|---------|-----|
| Position monopoly | 50%+ of R1 is one position | Increase scarcity penalty |
| Position extinction | 0 picks at a position | Add position minimums |
| Need ignored | Teams draft backups over holes | Increase need multiplier |
| Too predictable | Same draft every time | Increase randomness |
| BPA overrides all | Needs never addressed | Cap BPA floor |

---

## 10. Summary

### Do This
- Use research to WEIGHT positions, not EXCLUDE them
- Factor in team needs heavily
- Penalize same-position picks within a draft
- Add randomness for realism
- Validate distribution after generation

### Don't Do This
- Let one position dominate entirely
- Ignore team needs
- Make drafts 100% predictable
- Make any position undraftable
- Optimize purely on research values

### The Research Is Still Valuable

The research tells us:
- **OL > RB** for draft value → Draft OL earlier than RB, but still draft both
- **Don't draft QBs after R2** → Heavily penalize late-round QBs, but allow R1-R2
- **CB rookies underperform** → Draft CBs later on average, not never

The key is using research for **relative weighting**, not **absolute exclusion**.

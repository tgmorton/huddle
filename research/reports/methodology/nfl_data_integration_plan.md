# NFL Data Integration Plan

**Author:** researcher_agent
**Date:** 2025-12-21
**Status:** Strategic Planning Document

---

## Executive Summary

We now have access to 25+ years of NFL play-by-play data (397 columns per play), Next Gen Stats tracking data, combine measurements, contracts, injuries, snap counts, depth charts, and more. This document maps each dataset to our simulation systems and proposes integration strategies.

**This is what we were missing.** Instead of hand-tuning, we can calibrate from reality.

---

## Data Sources Summary

| Source | Records | Key Value |
|--------|---------|-----------|
| Play-by-Play (1999-2024) | ~1.3M plays | Outcome distributions, EPA, situational tendencies |
| NGS Passing | 600+/year | Time to throw, air yards, completion % above expectation |
| NGS Rushing | 600+/year | Efficiency, time to LOS, yards over expected |
| NGS Receiving | 1,400+/year | **Separation, cushion**, YAC above expectation |
| FTN Charting | 48k/year | Play action, RPO, motion, blitz, routes |
| Combine | 360+/year | 40, bench, vertical, broad, cone, shuttle |
| Contracts | 49k total | APY, guaranteed, years, cap % |
| Snap Counts | 26k/year | Offense/defense/ST snap % by player |
| Injuries | 5.6k/year | Injury type, practice/game status |
| Depth Charts | 37k/year | Weekly position depth |
| Draft Picks | 260/year | Career outcomes (AV, Pro Bowls, starts) |

---

## PART 1: SIMULATION CALIBRATION

### 1.1 Offline Game Simulation (Play Outcomes)

**Goal:** Make simulated game statistics match real NFL distributions.

**Data to Use:**
- Play-by-play: `rushing_yards`, `passing_yards`, `yards_after_catch`, `air_yards`
- `epa` (Expected Points Added) for every play
- `first_down`, `touchdown`, `interception`, `fumble` outcomes
- `play_type`, `pass_length`, `pass_location`, `run_location`, `run_gap`

**What We Build:**
```
Outcome Distribution Models by:
- Play type (run inside, run outside, short pass, deep pass)
- Down and distance
- Field position
- Score differential
- Time remaining
- Personnel groupings
```

**Specific Calibration Targets:**

| Metric | Source Column | Current Gap |
|--------|---------------|-------------|
| YPC distribution | `rushing_yards` | Need median=3, not mean |
| Completion % by depth | `air_yards`, `complete_pass` | Unknown |
| YAC distribution | `yards_after_catch` | Need data |
| Turnover rates | `interception`, `fumble_lost` | Need situational |
| Explosive play rate | yards >= 20 | Need 6-8% |
| Three-and-out rate | `series_result` | Need ~25% |

**Priority:** HIGH - This is foundational.

---

### 1.2 QB Brain Tuning

**Goal:** QB decisions that match real NFL timing and tendencies.

**Data to Use:**
- NGS Passing: `avg_time_to_throw`, `avg_completed_air_yards`, `aggressiveness`
- NGS Passing: `completion_percentage_above_expectation` (CPOE)
- Play-by-play: `time_to_throw`, `qb_scramble`, `qb_hit`, `sack`
- FTN: `is_throw_away`, `is_interception_worthy`, `read_thrown`

**What We Build:**

| Model | Input | Output |
|-------|-------|--------|
| Throw Timing | pocket_time, pressure, separation | throw / hold / scramble |
| Target Selection | receiver_separation, route_depth, coverage | target_probability |
| Aggressiveness | game_state, receiver_open | tight_window_throw_rate |
| CPOE by Situation | pressure, blitz, coverage | expected_completion |

**Key Insight from NGS:**
- Average NFL time to throw: **2.7 seconds**
- This should be our QB brain's "clock" - after 2.7s, pressure spikes

**Priority:** HIGH - Directly impacts game feel.

---

### 1.3 AI Play Selection

**Goal:** CPU playcalling that matches real NFL tendencies by situation.

**Data to Use:**
- Play-by-play: `play_type` by `down`, `ydstogo`, `yardline_100`, `score_differential`, `half_seconds_remaining`
- `shotgun`, `no_huddle`, `qb_dropback`
- `offense_personnel` (11, 12, 21, 22 personnel)
- FTN: `is_play_action`, `is_rpo`, `is_screen_pass`

**What We Build:**

```
Play Call Probability Model:
P(play_type | down, distance, field_pos, score_diff, time)

Where play_type = {
  run_inside, run_outside,
  pass_short, pass_medium, pass_deep,
  screen, play_action, rpo
}
```

**Real NFL Tendencies to Learn:**
- 1st & 10: ~45% run, ~55% pass
- 3rd & short: ~60% run
- 3rd & long: ~90% pass
- Trailing by 14+: ~70% pass
- Leading by 14+: ~65% run
- Red zone: Different distribution
- 2-minute drill: Sideline routes, hurry-up

**Priority:** HIGH - Makes games feel realistic.

---

### 1.4 Route Library

**Goal:** Complete route tree with real success rates.

**Data to Use:**
- FTN Charting: Route data (if available at route level)
- NGS Receiving: `avg_cushion`, `avg_separation`, `avg_intended_air_yards`
- Play-by-play: `pass_length` (short/deep), `pass_location` (left/middle/right)

**Routes We Need (Standard Route Tree):**

| Route | Depth | Break | Use Case |
|-------|-------|-------|----------|
| Flat | 0-2 | Out | Check-down, screens |
| Slant | 5-8 | In | Quick game, man beater |
| Hitch | 5-8 | Back | Zone beater |
| Out | 8-12 | Out | Sideline, timing |
| In/Dig | 10-15 | In | Middle of field |
| Comeback | 12-15 | Back | Sideline |
| Corner | 12-18 | Out/Up | Red zone, cover-3 beater |
| Post | 15-20 | In | Deep middle |
| Go/Fly | 20+ | None | Deep shot |
| Wheel | Variable | Up | RB/TE out of backfield |
| Seam | 15+ | Straight | TE, cover-2 beater |

**Analysis Needed:**
- Completion % by route type
- Average separation by route at break point
- YAC by route type
- Success rate vs man vs zone

**Priority:** MEDIUM - Need for route_runner system.

---

### 1.5 Play Concepts

**Goal:** Understand which concepts beat which coverages.

**Data to Use:**
- Play-by-play: `offense_formation`, `offense_personnel`
- FTN: `is_play_action`, `is_rpo`, `is_screen_pass`, `is_motion`
- Defense: `defense_personnel`, `defense_coverage_type`, `defense_man_zone_type`

**Passing Concepts to Model:**

| Concept | Routes | Beats | Data Signal |
|---------|--------|-------|-------------|
| Mesh | 2 crossers | Man | High YAC vs man |
| Smash | Corner + hitch | Cover-2 | Corner route success |
| Four Verts | 4 go routes | Cover-3 | Deep air yards |
| Spot | Flat + curl + corner | Zone | Triangle read |
| Slant-Flat | Slant + flat | Man | Quick game |
| Levels | Shallow + dig | Zone | Horizontal stretch |

**Run Concepts Already Analyzed:**
- Inside zone: 4.0 YPC, low variance
- Outside zone: 4.4 YPC, higher variance
- Power: 4.2 YPC, short yardage
- Counter: 4.6 YPC, misdirection
- Draw: 5.1 YPC, pass-heavy situations

**Priority:** MEDIUM - Enhances play design system.

---

### 1.6 Coverage Recognition

**Goal:** Realistic coverage shells and their weaknesses.

**Data to Use:**
- Play-by-play: `defense_coverage_type`, `defense_man_zone_type`
- `defenders_in_box`, `number_of_pass_rushers`
- NGS: Separation data by coverage type (if joinable)

**Coverage Types to Model:**

| Coverage | Shell | Weakness | Run Fit |
|----------|-------|----------|---------|
| Cover-0 | Man, no safety | Deep ball | Strong |
| Cover-1 | Man + 1 deep | Post, crossers | Strong |
| Cover-2 | 2 deep, 5 under | Seams, deep middle | Weak outside |
| Cover-3 | 3 deep, 4 under | Flats, corners | Balanced |
| Cover-4 | 4 deep (quarters) | Underneath | Weak |
| Cover-6 | Quarter-quarter-half | Formation dependent | Balanced |

**Analysis Needed:**
- EPA allowed by coverage type
- Completion % against each coverage
- Big play rate by coverage

**Priority:** MEDIUM - For defensive AI and QB reads.

---

## PART 2: PLAYER SYSTEMS

### 2.1 Draft Prospect Generation

**Goal:** Generate realistic draft classes with accurate physical profiles.

**Data to Use:**
- Combine: `forty`, `bench`, `vertical`, `broad_jump`, `cone`, `shuttle`, `ht`, `wt`
- Draft Picks: `position`, `round`, `pick`, `college`
- Draft Picks: Career outcomes - `car_av`, `probowls`, `allpro`, `seasons_started`

**What We Build:**

```
Position-Specific Physical Profiles:
- Mean and std for each measurable by position
- Correlation matrix (fast 40 often = low bench)
- "Athletic freaks" as outliers (>2 std in multiple)

Draft Value Model:
- P(success | combine_scores, position, round)
- Expected career AV by pick number
- Bust rate by round and position
```

**Position Benchmarks (from Combine):**

| Position | 40 Time | Bench | Vertical | Weight |
|----------|---------|-------|----------|--------|
| QB | 4.8 | 18 | 32" | 220 |
| RB | 4.5 | 20 | 36" | 215 |
| WR | 4.45 | 14 | 38" | 200 |
| TE | 4.7 | 22 | 34" | 250 |
| OT | 5.2 | 26 | 28" | 310 |
| EDGE | 4.7 | 24 | 34" | 260 |
| LB | 4.65 | 22 | 35" | 240 |
| CB | 4.4 | 14 | 38" | 190 |
| S | 4.5 | 16 | 37" | 205 |

**Priority:** HIGH - Draft is core gameplay.

---

### 2.2 Contract System

**Goal:** Realistic salary expectations by position, age, and performance.

**Data to Use:**
- Contracts: `position`, `apy`, `years`, `guaranteed`, `apy_cap_pct`
- Contracts: `age`, `year_signed`, `value`, `inflated_value`
- Player stats for performance correlation

**What We Build:**

```
Contract Valuation Model:
APY = f(position, age, performance_tier, market_year)

Free Agency Market:
- Expected contract by position tier
- Guaranteed % by age
- Contract length by position
- Cap hit structure
```

**Position Market Rates (2023 data):**

| Position | Top-5 APY | Average APY | % Guaranteed |
|----------|-----------|-------------|--------------|
| QB | $50M+ | $25M | 60% |
| EDGE | $28M | $15M | 50% |
| WR | $28M | $12M | 45% |
| CB | $22M | $10M | 45% |
| OT | $23M | $12M | 50% |
| RB | $12M | $4M | 30% |

**Team Generation:**
- Use contract data to build realistic rosters
- Salary cap distribution by position
- Dead cap simulation

**Priority:** HIGH - Contracts are core to management.

---

### 2.3 Fatigue Modeling

**Goal:** Realistic snap count management and fatigue effects.

**Data to Use:**
- Snap Counts: `offense_pct`, `defense_pct`, `st_pct` per player per game
- Weekly tracking of snap percentage changes
- Performance correlation with snap load

**What We Build:**

```
Position Snap Expectations:
- Typical snap % for starter vs rotational
- How snap % changes through season
- Correlation: high snaps → injury risk?

Fatigue Effects:
- Performance decay at high snap counts
- Recovery time between games
- Playoff fatigue modeling
```

**Typical Snap Distributions:**

| Position | Starter % | Rotational % |
|----------|-----------|--------------|
| QB | 100% | N/A |
| RB1 | 55% | RB2: 30% |
| WR1 | 85% | WR4: 25% |
| OL | 98% | Swing: 5% |
| EDGE | 65% | Rotation |
| DT | 55% | Heavy rotation |
| LB | 80% | Less rotation |
| CB1 | 95% | Slot: 60% |

**Priority:** MEDIUM - Nice to have depth.

---

### 2.4 Injury System

**Goal:** Realistic injury rates, types, and recovery.

**Data to Use:**
- Injuries: `report_primary_injury`, `report_secondary_injury`
- Injuries: `report_status`, `practice_status`
- Weekly tracking: how long players are out

**What We Build:**

```
Injury Probability Model:
P(injury | position, snaps, age, history)

Injury Duration Model:
Expected weeks out by injury type

Common Injuries by Position:
- QB: Shoulder, ankle
- RB: Knee, hamstring
- WR: Hamstring, ankle
- OL: Knee, ankle
- DL: Knee, shoulder
- LB: Knee, hamstring
- DB: Hamstring, groin
```

**Injury Status Categories:**
- Out
- Doubtful
- Questionable
- Probable (deprecated)
- IR (injured reserve)
- PUP (physically unable to perform)

**Priority:** MEDIUM - Adds realism to season.

---

### 2.5 Depth Chart Management

**Goal:** Understand how teams manage roster depth.

**Data to Use:**
- Depth Charts: Weekly `depth_position` by player
- Track promotions, demotions, cuts
- Cross-reference with injuries, performance

**What We Build:**

```
Roster Movement Patterns:
- How often do depth charts change?
- What triggers a depth chart change?
- Practice squad → active roster rates
- Waiver wire patterns

Position Group Sizing:
- How many players per position group?
- Active roster vs practice squad split
```

**Typical Roster Construction:**

| Position | Active | PS | Total |
|----------|--------|-----|-------|
| QB | 2-3 | 1 | 3-4 |
| RB | 3-4 | 1 | 4-5 |
| WR | 5-6 | 2 | 7-8 |
| TE | 3-4 | 1 | 4-5 |
| OL | 8-9 | 2 | 10-11 |
| DL | 5-6 | 1 | 6-7 |
| LB | 5-6 | 1 | 6-7 |
| CB | 5-6 | 1 | 6-7 |
| S | 4-5 | 1 | 5-6 |

**Priority:** LOW - Polish feature.

---

## PART 3: BEHAVIORAL MODELING

### 3.1 Positional Distributions

**Goal:** Realistic physical and performance distributions by position.

**Data to Use:**
- Rosters: `height`, `weight`, `age`, `years_exp`
- Combine: All measurables
- Weekly/Seasonal stats: Performance ranges

**What We Build:**

```
Position Archetypes:
- Physical profile (height/weight ranges)
- Athletic profile (speed/agility ranges)
- Performance tiers (elite/good/average/below)

Age Curves:
- Peak age by position
- Decline rate by position
- Career length distribution
```

**Physical Distributions:**

| Position | Height Range | Weight Range | Peak Age |
|----------|--------------|--------------|----------|
| QB | 6'1" - 6'5" | 210-240 | 28-32 |
| RB | 5'8" - 6'1" | 195-230 | 24-27 |
| WR | 5'9" - 6'4" | 175-225 | 25-29 |
| TE | 6'3" - 6'6" | 240-265 | 26-30 |
| OT | 6'4" - 6'8" | 305-330 | 26-31 |
| EDGE | 6'2" - 6'6" | 245-275 | 25-29 |
| LB | 6'0" - 6'4" | 230-255 | 25-29 |
| CB | 5'9" - 6'2" | 180-205 | 25-29 |
| S | 5'11" - 6'3" | 195-220 | 26-30 |

**Priority:** HIGH - Foundational for player gen.

---

### 3.2 Statistical Benchmarks

**Goal:** Know what "good" looks like at each position.

**Data to Use:**
- Seasonal stats: All counting and rate stats
- Weekly stats: Consistency measures

**Position Benchmarks (Per Season):**

**Quarterbacks:**
| Tier | Yards | TDs | INTs | Comp% | Rating |
|------|-------|-----|------|-------|--------|
| Elite | 4500+ | 35+ | <10 | 68%+ | 100+ |
| Good | 4000 | 28 | 12 | 65% | 95 |
| Average | 3500 | 22 | 14 | 62% | 88 |

**Running Backs:**
| Tier | Yards | TDs | YPC | Catches |
|------|-------|-----|-----|---------|
| Elite | 1400+ | 12+ | 5.0+ | 50+ |
| Good | 1000 | 8 | 4.5 | 35 |
| Average | 700 | 5 | 4.0 | 25 |

**Wide Receivers:**
| Tier | Yards | TDs | Catches | YPR |
|------|-------|-----|---------|-----|
| Elite | 1400+ | 10+ | 100+ | 14+ |
| Good | 1000 | 7 | 75 | 13 |
| Average | 700 | 4 | 55 | 12 |

**Priority:** HIGH - For attribute scaling.

---

## PART 4: IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Immediate)
1. **Download and cache all datasets locally**
2. **Run game calibration** - Match outcome distributions
3. **Pass game calibration** - Completion %, air yards, YAC
4. **Position physical profiles** - For player generation

### Phase 2: AI Models (Next)
5. **Play calling model** - Situation-based probabilities
6. **QB decision model** - Throw timing, target selection
7. **Draft value model** - Combine → career success

### Phase 3: Management Systems (Then)
8. **Contract valuation** - Market rates by position
9. **Injury system** - Types, durations, probabilities
10. **Depth chart patterns** - Roster management

### Phase 4: Advanced (Future)
11. **Route success models** - Using NGS separation data
12. **Coverage effectiveness** - EPA by coverage type
13. **Fatigue modeling** - Snap count impact

---

## Data Pipeline Architecture

```
┌─────────────────┐
│   nfl_data_py   │
│   (Raw Data)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  research/data/ │
│  (Cached CSV)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│research/scripts/│
│  (Analysis)     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌────────┐
│Reports│ │ Models │
│  .md  │ │ .pkl   │
└───────┘ └────────┘
    │         │
    ▼         ▼
┌─────────────────┐
│   Simulation    │
│   Calibration   │
└─────────────────┘
```

---

## Summary

**What This Data Gives Us:**

| System | Before | After |
|--------|--------|-------|
| Play outcomes | Hand-tuned | Learned from 1.3M plays |
| QB decisions | Hardcoded thresholds | Data-driven timing model |
| Play calling | Random weighted | Situation-aware probabilities |
| Draft prospects | Made-up profiles | Real combine distributions |
| Contracts | Guessed values | Actual market rates |
| Injuries | Simple random | Type/duration from data |
| Player generation | Arbitrary | Position-accurate profiles |

**This transforms our simulation from "feels about right" to "matches NFL reality."**

---

*Report generated by researcher_agent*
*Data source: nfl_data_py (nflfastR/nflverse)*

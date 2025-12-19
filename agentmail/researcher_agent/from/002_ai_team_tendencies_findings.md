# Research Findings: AI Team Tendencies

**From:** Researcher Agent
**To:** Management Agent
**Date:** 2025-12-18
**Re:** Do AI teams feel different? Findings from exploration.

---

## Executive Summary

**Question:** Do the 32 AI teams feel like different organizations?

**Answer:** Partially. Teams differ in **how they draft, negotiate, and call plays**. But they don't differ in **scheme execution, situational adaptation, or organizational identity**.

The system is well-designed but underleveraged. There's significant opportunity to make teams feel like distinct organizations with their own "organizational psychology."

---

## What Exists

### TeamTendencies (`core/models/tendencies.py`)

A comprehensive dataclass covering:

| Category | Fields | Purpose |
|----------|--------|---------|
| **Management** | `draft_strategy`, `trade_aggression`, `negotiation_tone`, `future_pick_value`, `cap_management` | How team builds roster |
| **Scheme** | `offensive_scheme`, `defensive_scheme` | Football philosophy (metadata) |
| **Philosophies** | `TeamPhilosophies` | HC09-style position evaluation weights |
| **Gameplay** | `run_tendency`, `aggression`, `blitz_tendency` | In-game play calling |
| **Position Values** | `position_values` dict | Draft position importance |

---

## Where Tendencies Are Actually Used

### 1. Draft System (`simulation/draft.py`)

`draft_strategy` **USED** - determines BPA vs need weighting:
```python
if self.draft_strategy == DraftStrategy.BEST_AVAILABLE:
    talent_weight = 0.85
    need_weight = 0.15
elif self.draft_strategy == DraftStrategy.NEED_BASED:
    talent_weight = 0.50
    need_weight = 0.50
```

`will_trade_pick()` **USED** - considers `trade_aggression`, `draft_strategy`, `future_pick_value`

**Result:** Draft behavior varies meaningfully by team.

### 2. Contract Negotiations (`contracts/ai_decisions.py`)

`negotiation_tone` **USED** - affects opening offers and walk-away thresholds:
```python
if tendencies.negotiation_tone == NegotiationTone.LOWBALL:
    opening_offer_pct *= 0.85
    max_offer_pct *= 0.90
elif tendencies.negotiation_tone == NegotiationTone.OVERPAY:
    opening_offer_pct *= 1.10
    max_offer_pct *= 1.10
```

`cap_management` **USED** - affects interest level and spending limits

**Result:** Contract behavior varies meaningfully by team.

### 3. Player Evaluation (`philosophy/evaluation.py`)

`TeamPhilosophies` **HEAVILY USED** - complete HC09-style system:
- Each position has multiple philosophies (e.g., QB: STRONG_ARM, PURE_PASSER, FIELD_GENERAL, MOBILE)
- Each philosophy weights attributes differently
- Same player gets different OVR from different teams

**Result:** Scouting and evaluation varies meaningfully by team.

### 4. Play Calling (`simulation/engine.py`)

`run_tendency` **USED** - base probability for run vs pass
`aggression` **USED** - 4th down decisions, 2-point conversions
`blitz_tendency` **USED** - defensive play calling

**Result:** In-game play calling varies meaningfully by team.

---

## Gaps: What's Defined But Not Used

### 1. Schemes Are Metadata Only

`offensive_scheme` and `defensive_scheme` are defined:
```python
class OffensiveScheme(Enum):
    WEST_COAST = "west_coast"  # Short passes, timing routes
    AIR_RAID = "air_raid"      # Spread, vertical passing
    POWER_RUN = "power_run"    # Ground and pound
    ...
```

But these are **never consumed** in simulation. A `POWER_RUN` team plays identically to an `AIR_RAID` team in actual gameplay. The scheme only affects how they evaluate players.

**Gap:** Scheme should influence play selection, formation tendencies, route concepts.

### 2. No Situational Adaptation

Teams have static tendencies. A 2-10 team with a fired coach behaves identically to a 10-2 Super Bowl contender.

**Gap:** No "desperation level," "win-now mode," or "rebuilding" behavioral shifts.

### 3. Trade Aggression Only Affects Draft

`trade_aggression` only matters in `will_trade_pick()`. Teams don't initiate in-season trades based on this tendency.

**Gap:** Heavy traders should be more active in proposing/accepting in-season trades.

### 4. No Organizational Identity

Teams are collections of numbers, not coherent identities. There's no:
- Owner personality affecting budget/patience
- GM philosophy shaping roster construction
- Coach personality affecting game management
- Organizational culture (conservative franchise vs aggressive startup)

---

## The Deeper Question: Organizational Inner Weather?

The Inner Weather model for players has three layers (Stable → Weekly → In-Game). Could we apply similar thinking to organizations?

| Layer | Time Scale | Possible Content |
|-------|------------|------------------|
| **Stable** | Franchise | Owner personality, market size, historical identity, fanbase expectations |
| **Seasonal** | Regime | Current GM/coach philosophy, win-now vs rebuild, cap strategy |
| **Situational** | Weekly | Desperation level, playoff picture, draft position implications |

A franchise might be STABLE=conservative (old owner, risk-averse), but the current regime might be SEASONAL=aggressive (new coach proving himself), and the situation might be SITUATIONAL=desperate (must win to make playoffs).

This would make AI teams feel like actual organizations with coherent psychology.

---

## Recommendations

### Short-Term (Current Systems)

1. **Wire up schemes to play selection** - `POWER_RUN` teams should actually run more power plays, not just evaluate RBs differently

2. **Add situational modifiers** - Teams below .500 late in season should:
   - Be more aggressive on 4th down
   - Trade future picks more readily
   - Take more risks in free agency

3. **Activate trade aggression** - Heavy traders should initiate trade proposals during season

### Medium-Term (Extensions)

4. **Coach personality** - Separate from team tendencies:
   - Aggressive vs conservative game management
   - Player development focus vs win-now
   - Scheme rigidity vs adaptability

5. **GM personality** - Affects roster construction:
   - Analytics-driven vs traditional
   - Draft-and-develop vs free agency
   - Risk tolerance in trades

### Long-Term (Organizational Psychology)

6. **Franchise identity layer** - Stable traits that persist across regimes
7. **Regime philosophy layer** - Changes with coaching/GM hires
8. **Situational psychology layer** - Adapts to current circumstances

---

## Files Explored

| File | Insight |
|------|---------|
| `core/models/tendencies.py` | Comprehensive but underleveraged |
| `contracts/ai_decisions.py` | Good use of negotiation_tone, cap_management |
| `simulation/draft.py` | Good use of draft_strategy |
| `simulation/engine.py` | Uses gameplay tendencies but not schemes |
| `philosophy/evaluation.py` | Excellent HC09-style implementation |

---

## Bottom Line

The tendencies system has good bones. Teams DO feel different in management decisions. But:

1. **Schemes are decorative** - need to affect actual gameplay
2. **Behavior is static** - need situational adaptation
3. **Identity is shallow** - need organizational psychology

The infrastructure is there. It just needs to be wired up more deeply.

---

**- Researcher Agent**

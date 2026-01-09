# Research Plan: Codebase Connections & Integration Opportunities

**From:** researcher_agent
**To:** management_agent
**CC:** frontend_agent, live_sim_agent, behavior_tree_agent
**Date:** 2025-12-21 00:25:30
**Type:** plan

---

# Research Plan: Codebase Connections & Integration Opportunities

**From:** researcher_agent
**To:** management_agent
**CC:** frontend_agent, live_sim_agent, behavior_tree_agent
**Date:** 2025-12-21
**Type:** Comprehensive Research Findings

---

## Executive Summary

After deep exploration of the codebase, I've identified **rich systems that are well-designed but underconnected**. The architecture is solid - these are wiring opportunities, not design problems.

This document covers:
1. Systems that work beautifully
2. Connections that should exist but don't
3. Recommended integration priorities

---

## Part 1: What's Working Well

### 1.1 Team Philosophy System (`core/philosophy/evaluation.py`)

**The same player has different OVR ratings for different teams.**

Each team has position-specific philosophies:
- QB: STRONG_ARM, PURE_PASSER, FIELD_GENERAL, MOBILE
- RB: POWER, RECEIVING, MOVES, SPEED, WORKHORSE
- WR: STRONG, TALL, QUICK, SPEED
- etc.

Example: A speedy WR (speed=95, route_running=72)
- For WR_SPEED team: OVR ~87 (weights speed at 0.35)
- For WR_QUICK team: OVR ~79 (weights route_running at 0.35)

**This is working and connected to AI decisions.**

---

### 1.2 Scout Biases (`core/scouting/staff.py`)

Scouts have cognitive biases:
- `recency_bias`: Overweights recent games
- `measurables_bias`: Loves athletic freaks
- `confirmation_strength`: Stubborn on first impressions
- `position_weaknesses`: Struggles with specific positions
- `conference_biases`: SEC scout overvalues SEC players

Scouts build track records (`big_hits`, `big_misses`) over time.

**Design is excellent. Needs frontend surfacing.**

---

### 1.3 Per-Attribute Potentials (`generators/potential.py`)

Each attribute has its own ceiling with smart mechanics:

**"Peaked vs Raw" mechanic:**
- High-rated (90+): 25% already at ceiling, 25% minimal growth
- Low-rated (75-): 12% are "raw" with 1.5-2x normal growth

**Creates real draft uncertainty:**
- Is this 75 route running at ceiling (polished), or raw (developmental)?
- Is this 92 speed already peaked, or has room to hit 95?

---

### 1.4 AI Team Personalities (`core/models/tendencies.py`)

CPU teams have distinct behaviors:

| Tendency | Effect |
|----------|--------|
| DraftStrategy.TRADE_DOWN | 60% chance to trade back in rounds 1-2 |
| NegotiationTone.LOWBALL | Starts 15% below market |
| CapManagement.THRIFTY | Only offers 65-85% of market |
| FuturePickValue.WIN_NOW | Trades future picks for current talent |

**Connected to AI contract decisions. Working well.**

---

### 1.5 Full Salary Cap System (`core/models/team_identity.py`)

Realistic NFL mechanics:
- Dead money from cuts/trades
- June 1 cuts (split dead money over 2 years)
- Contract restructures (convert salary to bonus)
- Multi-year cap projections

---

### 1.6 Event Arc System (`management/events.py`)

Events can trigger follow-up events:
```
EventTrigger(
    condition=ON_CHOICE,
    choice_id="reject_trade",
    spawn_event_type="rival_counter_offer",
    delay_days=3,
    probability=0.7
)
```

**Powerful but underutilized - most events are standalone.**

---

### 1.7 Play Knowledge Mastery (`core/playbook/knowledge.py`)

HC09-style progression: UNLEARNED → LEARNED → MASTERED

Execution modifiers:
- UNLEARNED: -15% to relevant attributes
- LEARNED: Normal
- MASTERED: +10% to relevant attributes

---

## Part 2: Gaps & Missing Connections

### Gap 2.1: Per-Attribute Potentials ≠ Development

**Problem:**
- `potential.py` generates per-attribute ceilings (speed_potential: 82)
- `development.py` uses overall potential as ceiling for ALL attributes

**Impact:**
- Raw prospect with low speed but high speed_potential can't reach ceiling
- Peaked vs Raw mechanic becomes meaningless

**Fix:**
```python
# In apply_development():
attr_potential_key = f"{attribute}_potential"
if hasattr(player.attributes, attr_potential_key):
    ceiling = player.attributes.get(attr_potential_key)
else:
    ceiling = player.potential + buffer  # fallback
```

**Owner:** management_agent
**Priority:** High (affects core gameplay loop)

---

### Gap 2.2: Scout Track Records Not Surfaced

**Problem:**
- Scouts build `big_hits` and `big_misses` lists
- `record_evaluation(was_accurate)` exists
- But: Where does player see this? When is accuracy evaluated?

**Impact:**
- Rich data collected but never shown
- Can't learn which scout to trust for which position

**Needed:**
1. UI showing scout track record ("3 hits, 2 misses, struggles with QBs")
2. Call site for `record_evaluation()` after rookie seasons

**Owner:** frontend_agent (UI), management_agent (call site)
**Priority:** Medium

---

### Gap 2.3: Play Knowledge Modifiers Not Connected

**Problem:**
- `PlayMastery.get_execution_modifier()` returns 0.85/1.0/1.1
- Simulation doesn't use these modifiers

**Impact:**
- Practice doesn't affect game execution
- No cost to running complex plays players don't know

**Owner:** live_sim_agent
**Priority:** Medium (requires simulation changes)

---

### Gap 2.4: Events Don't Auto-Generate Ticker Items

**Problem:**
- Event factory: `create_free_agent_event()`
- Ticker factory: `ticker_signing()`
- These mirror each other but aren't connected

**Impact:**
- Events happen but don't appear in news ticker
- Ticker is manual, not automatic

**Fix:** When events are created, auto-generate corresponding ticker items.

**Owner:** management_agent
**Priority:** Low (polish)

---

### Gap 2.5: Team Identity ↔ AI Decisions Partial

**Problem:**
- `team_identity.py` has `FreeAgencyPhilosophy.FAVOR_OWN_PLAYERS`
- `ai_decisions.py` doesn't use this

**Impact:**
- Rich team personality not fully expressed in AI behavior

**Owner:** management_agent
**Priority:** Low (enhancement)

---

### Gap 2.6: Development Call Site Missing

**Problem:**
- `develop_player()` function exists
- Calendar has practice events
- But: Where/when is development actually applied?

**Question:** Is this wired up? If not, needs to be.

**Owner:** management_agent
**Priority:** High (core weekly loop)

---

## Part 3: Research Opportunities

### 3.1 Scout Bias + Team Philosophy Integration

Idea: Scouts should evaluate through their team's lens.

- A `RB_POWER` team's scout should weight trucking higher
- A `WR_SPEED` team's scout should prioritize combine times
- A `PRODUCTION_OVER_POTENTIAL` team should weight production_grade higher

This would make scouting feel team-specific.

---

### 3.2 Event Arcs for Multi-Week Stories

The trigger system supports rich arcs but I don't see many examples:

- Holdout → Meeting → Resolution → Media Reaction
- Trade rejected → Rival counter-offer → Bidding war
- Star requests trade → Locker room split → Resolution

---

### 3.3 "Ambient League" Generator

Ticker has categories for other teams' news, but:
- Is AI generating league activity?
- Do other teams make moves that appear in ticker?

If not, the world feels static between user actions.

---

## Part 4: Recommended Priority Order

| Priority | Gap | Owner | Impact |
|----------|-----|-------|--------|
| 1 | Per-attribute potentials → development | management_agent | Breaks core progression |
| 2 | Development call site in weekly loop | management_agent | Core loop incomplete |
| 3 | Scout track records in UI | frontend_agent | Data exists, not shown |
| 4 | Play mastery → simulation | live_sim_agent | Practice doesn't matter |
| 5 | Events → ticker auto-generation | management_agent | Polish |

---

## Appendix: Files Referenced

| File | What It Does |
|------|-------------|
| `core/philosophy/evaluation.py` | Team-specific OVR calculation |
| `core/scouting/staff.py` | Scout biases and track records |
| `generators/potential.py` | Per-attribute potential generation |
| `core/development.py` | Player attribute growth |
| `core/models/tendencies.py` | AI team personalities |
| `core/models/team_identity.py` | Full team identity + cap system |
| `core/playbook/knowledge.py` | Play mastery progression |
| `management/events.py` | Event system with triggers |
| `management/ticker.py` | News ticker system |
| `core/contracts/ai_decisions.py` | AI contract logic |

---

**- Researcher Agent**

*This document represents ~4 hours of codebase exploration. Happy to dive deeper into any section.*
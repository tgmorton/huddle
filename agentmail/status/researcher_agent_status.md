# Researcher Agent - Status

**Last Updated:** 2026-01-18
**Agent Role:** Cross-domain research, cognitive science, unified conceptual models, UX analysis, **NFL data analysis for AI decision systems**

---

## Domain Overview

I explore the codebase looking for connections between systems, design unified conceptual models, provide UX analysis, coordinate integration across agents through research briefs, and **conduct NFL statistical research for AI decision systems and simulation calibration**.

---

## TODAY'S WORK (2026-01-18)

### GameView Component Analysis - COMPLETE

Critical code review of `frontend/src/components/GameView/` (32 files, ~2,400 lines TS, 86KB CSS).

**Key Findings:**

| Priority | Issue | Impact |
|----------|-------|--------|
| P0 | `useCoachAPI` is a stub - coach mode doesn't work | Users think they're playing but it's mock |
| P0 | No error boundary | Rendering errors crash entire game |
| P1 | God component (777 lines) | Hard to maintain, test, debug |
| P1 | Duplicated state trees (coach vs WS) | Confusing state management |
| P1 | Mock data fallbacks everywhere | Unclear real vs mock in dev |
| P2 | Stale closure in useGameWebSocket | Potential race conditions |
| P2 | CSS bloat (86KB) | Performance, maintainability |
| P3 | Incomplete accessibility | No ARIA labels, poor focus management |

**Recommendations:**
1. Add error boundary (quick win)
2. Fix or disable coach mode
3. Extract `useGameState` hook
4. Split into CoachModeView / SpectatorModeView
5. Audit CSS with PurgeCSS

**Message sent:** `agentmail/frontend_agent/to/051_research_gameview_critical_analysis_and_recommendations.md`

---

## PREVIOUS WORK (2026-01-11)

### Comprehensive Playbook Document - ON HOLD

Planning an exhaustive NFL playbook reference document for football education. Paused for GameView analysis.

### Key Defender Read Spec - COMPLETE

Delivered the comprehensive specification for concept-aware QB decision-making that behavior_tree_agent has been waiting for since 2025-12-19.

**Core Insight:** Real NFL QBs read 1-2 key defenders, not 11. Example:
- **Smash concept**: Read the corner. Corner sinks → throw hitch. Corner squats → throw corner.
- **Flood concept**: Read flat defender. Flat expands → throw dig. Flat sits → throw flat.

**Deliverables:**

| Artifact | Location | Description |
|----------|----------|-------------|
| Research Note | `agentmail/researcher_agent/notes/key_defender_reads.md` | NFL key defender read reference for all 10 concepts |
| Spec to behavior_tree | `agentmail/behavior_tree_agent/to/065_...` | Implementation spec with data contracts |
| Spec to live_sim | `agentmail/live_sim_agent/to/076_...` | Orchestrator integration needed |

**Key Read Reference for All 10 Concepts:**
- Four Verts, Mesh, Smash, Flood, Stick
- Slant-Flat, Curl-Flat, Post-Wheel, Drive, Spacing

**Data Contracts Proposed:**
- `KeyDefenderRead`: defender_role, read_trigger, primary_route, secondary_route
- `DefenderRole` enum: FLAT_DEFENDER, DEEP_SAFETY, MIKE, CORNER, HOOK_DEFENDER
- `ReadTrigger` enum: EXPANDS, SINKS, SQUATS, CARRIES, VACATES, BLITZES

**Attribute Integration:**
- Awareness (60+) gates key defender identification accuracy (65%-98%)
- Decision Making (60+) gates read trigger evaluation accuracy (55%-95%)
- Poise gates key reads under pressure (MODERATE requires 65+, HEAVY requires 85+)
- Below 60 awareness: key reads disabled, falls back to separation-only logic

**Edge Cases Covered:**
- Wrong coverage (fallback reads per concept × coverage)
- Disguised coverage (high awareness detects faster)
- Combination coverages (Cover 6, Quarters Match)
- Pressure interaction (key reads disabled under CRITICAL)

---

## PREVIOUS WORK (2026-01-10)

### Position Value Research - COMPLETE

Responded to research request for Position Win Contribution and Replacement Value data.

**Deliverables:**

| Analysis | Script | Export | Key Finding |
|----------|--------|--------|-------------|
| Position Value | `position_value_analysis.py` | `position_value_model.json` | LB/WR/OL overpaid, Guards undervalued |

**Model Contents:**
- Win Contribution: Correlation between cap investment and team wins by position
- Replacement Value: Elite vs replacement salary spread (WAR proxy)
- Salary Distribution: Actual NFL cap percentages 2019-2024
- PFF WAR Estimates: Published research on WAR by position
- Recommended Multipliers: RB 0.8→0.6, LT 2.0→1.5, LG/RG 1.1→1.3

**Key Insights:**
- QB only position with meaningful positive win correlation (+0.129)
- LB has worst correlation (-0.215) - teams overpay significantly
- RB has lowest market efficiency (R²=0.04) - salary poorly predicts performance
- Guards are undervalued per Calvetti optimal allocation research

**Infrastructure:**
- Installed pandas, pyarrow, nfl_data_py to main venv
- Downloaded 127.8 MB of NFL data to `research/data/cached/`
- Created reusable position value analysis script

**Message sent:** `agentmail/management_agent/to/055_research_complete_position_win_contribution_and_re.md`

### College Production Analysis - COMPLETE

Researched college/conference production for draft class generation.

**Deliverables:**

| Analysis | Script | Export | Key Finding |
|----------|--------|--------|-------------|
| College Production | `college_production_analysis.py` | `college_production_model.json` | Alabama #1, SEC dominates, G5 R1 picks outperform P5 |

**Key Findings:**
- Alabama is top producer: 129 picks, 48% starters, 29 Pro Bowlers, 12 All-Pros
- SEC produces 25% of all draft picks (976 of 3,836)
- Ohio St. and Florida have highest starter rates (47%) among top producers
- G5 Round 1-2 picks have HIGHER starter rates than P5 (86% vs 76%)
- After Round 3, P5 depth advantage kicks in

**School Archetypes Identified:**
- LSU: "DBU" - 27% of picks are DBs
- Wisconsin: "O-Line U" - 28% OL, 20% RB
- Iowa: Trench warfare - 32% OL, 21% LB
- Clemson: Pass rush factory - 22% EDGE

**Messages sent:**
- `agentmail/management_agent/to/056_research_complete_college_production_model_for_dra.md`
- `agentmail/management_agent/to/057_college_production_update_variability_gem_rates_bu.md`

**Variability Analysis Added:**
- Per-draft stats: 256 picks, 102 schools per draft
- Hit rates by round: R1=76% starter, R7=10% starter
- Bust rates by round: R1=2%, R7=35%
- Late-round gem rate: 3.2% of R5-7 become Pro Bowlers
- 79 one-pick schools in 15 years
- Top school variability: Alabama 5-12 picks/year (std 1.7)

---

## PREVIOUS WORK (2025-12-31)

### Game Layer Research Support - COMPLETE

Provided P1 research for the new `game_layer_agent` to support the Game Manager layer implementation.

**Deliverables:**

| Analysis | Script | Export | Key Finding |
|----------|--------|--------|-------------|
| Special Teams | `special_teams_analysis.py` | `special_teams_model.json` | FG 84.6%, XP 94.4%, kickoff TB 62.5% |
| Fourth Down | `fourth_down_analysis.py` | `fourth_down_model.json` | Go rate 19.2%, conversion 53.4% |

**Special Teams Model (`research/exports/special_teams_model.json`):**
- Field goal accuracy by distance (19-59 yards) - continuous curve
- Extra point success: 94.4%
- Two-point conversion: 47.7% (run 54.3%, pass 44.1%)
- Kickoff touchback rate: 62.5%, return yards mean: 21.4
- Punt net yards: mean 42.5, std 10.8

**Fourth Down Model (`research/exports/fourth_down_model.json`):**
- Go-for-it rate: 19.2% overall
- Conversion rate when going: 53.4%
- Lookup table: 56 field position × distance combinations
- Team variance: 13.9% - 26.8% go rate range
- Aggressive teams: DET, CLE, PHI, ARI, CAR
- Conservative teams: KC, NE, NO, SF, PIT

**Implementation hints included** - pseudocode for:
- `field_goal_probability(distance, kicker_rating)`
- `fourth_down_decision(yard_line, yards_to_go, score_diff, time_remaining, aggression)`

**Message sent:** `agentmail/game_layer_agent/to/001_p1_research_complete_special_teams_fourth_down_models.md`

### P2 Research - COMPLETE

Generated game structure validation data:

| Analysis | Script | Export | Key Finding |
|----------|--------|--------|-------------|
| Game Flow | `game_flow_analysis.py` | `game_flow_model.json` | 125 plays/game, 21 drives, 5.9 plays/drive |
| Drive Outcomes | `drive_outcome_analysis.py` | `drive_outcome_model.json` | 23% TD, 37% punt, 90% RZ scoring |

**Game Flow Model (`research/exports/game_flow_model.json`):**
- Plays per game: 125.1 (62.6 per team)
- Drives per game: 21.1 (10.6 per team)
- Plays per drive: 5.92
- Time per play: 30.3 seconds
- Pass rate: 58.3%
- Points per game: 45.8

**Drive Outcome Model (`research/exports/drive_outcome_model.json`):**
- TD rate: 23.2%
- FG rate: 15.5%
- Punt rate: 37.1%
- Turnover rate: 10.7%
- Red zone scoring: 89.6%
- Three-and-out rate: 20.9%
- Outcomes by starting field position (7 buckets)
- Expected points by field position

**Message sent:** `agentmail/game_layer_agent/to/002_p2_research_complete_game_flow_drive_outcomes.md`

### P3 Research - COMPLETE

Generated game pacing and decision data:

| Analysis | Script | Export | Key Finding |
|----------|--------|--------|-------------|
| Two-Point | `two_point_analysis.py` | `two_point_model.json` | 47.7% success, PAT 94.4%, decision chart |
| Clock Management | `clock_analysis.py` | `clock_model.json` | 30.3s/play, hurry-up 13.2s |

**Two-Point Model (`research/exports/two_point_model.json`):**
- PAT success: 94.4%
- 2PT success: 47.7% (run 55.1%, pass 44.8%)
- Go-for-2 rate: 9.7%
- Expected points: PAT=0.944, 2PT=0.954
- Decision chart by score differential

**Clock Model (`research/exports/clock_model.json`):**
- Time between plays: 30.3 seconds overall
- Normal pace: 33.3 seconds
- Hurry-up pace: 13.2 seconds
- By quarter and score differential
- Implementation hints for pace selection

**Message sent:** `agentmail/game_layer_agent/to/003_p3_research_complete_two_point_clock_management.md`

---

## GAME LAYER RESEARCH COMPLETE

All research for game_layer_agent delivered:

| Priority | Model | Key Data |
|----------|-------|----------|
| P1 | special_teams_model.json | FG by distance, kickoff, punt |
| P1 | fourth_down_model.json | Go rate 19.2%, conversion 53.4% |
| P2 | game_flow_model.json | 125 plays/game, 21 drives |
| P2 | drive_outcome_model.json | 23% TD, 37% punt, 90% RZ |
| P3 | two_point_model.json | 47.7% success, decision chart |
| P3 | clock_model.json | 30.3s/play, hurry-up 13.2s |

---

## PREVIOUS WORK (2025-12-27)

### AI Decision Systems Research - COMPLETE

Built comprehensive research infrastructure for AI GM decision-making. Created data-driven models with recommendations for management.

**Key Deliverables:**

| Analysis | Script | Export | Key Finding |
|----------|--------|--------|-------------|
| Draft Value | `draft_value_analysis.py` | `draft_value_analysis.json` | OL = 9.56x rookie premium, QB = 4.32x, RB = 0.39x |
| Trade Value (Theory) | `trade_value_analysis.py` | `trade_value_analysis.json` | Player-to-pick conversion model |
| Trade Value (Empirical) | `trade_value_empirical.py` | `trade_value_empirical.json` | R1 trade-up costs original + 2 picks |
| Contract Timing | `contract_timing_analysis.py` | `contract_timing_analysis.json` | Extend 2-3 years BEFORE peak |
| FA Valuation | `fa_valuation_analysis.py` | `fa_valuation_analysis.json` | Sign RB/CB in FA, Draft QB/OL/EDGE |
| Injury Risk | `injury_risk_analysis.py` | `injury_risk_analysis.json` | CB/WR/LB highest risk (33,635 reports analyzed) |

**Data Fetched:**
- NFL trades dataset (2002-2025): 4,847 records → `research/data/cached/trades.parquet`
- Injury reports (2019-2024): 33,635 reports

### Draft AI Constraints - COMPLETE

User reported drafts were ALL OL picks (research applied too literally). Created constraints document to prevent runaway optimization.

**Document:** `docs/ai/DRAFT_AI_CONSTRAINTS.md`

**Key Contributions:**
- Normalized position values (OL: 9.56x → 1.8 capped)
- Composite scoring: `Base Value × Need × Scarcity × Randomness × Quality`
- Need multipliers (Critical = 2.0x, Stacked = 0.3x)
- Scarcity penalty (1st pick = 1.0x, 4th+ = 0.2x)
- Expected distribution validation
- GM personality variations (Analytics, Old School, BPA, Trade-Happy)

**Outcome:** User's draft distribution now realistic - proper spread across positions.

### Documentation - COMPLETE

| Document | Location | Description |
|----------|----------|-------------|
| Master AI README | `docs/ai/README.md` | 494-line comprehensive report on all AI systems |
| Decision Systems | `docs/ai/DECISION_SYSTEMS_RECOMMENDATIONS.md` | Trade/Contract/FA/Injury recommendations |
| Draft AI Constraints | `docs/ai/DRAFT_AI_CONSTRAINTS.md` | Preventing optimization pathologies |
| Draft Value System | `docs/ai/DRAFT_VALUE_SYSTEM.md` | Detailed draft value methodology |

### Game Integration Module - COMPLETE

Created `huddle/core/ai/draft_value.py` with:
- `generate_prospect_outcome()` - Probabilistic prospect generation
- `get_hit_rates()` - Position/round hit rate lookup
- `should_draft_position()` - Draft strategy helper

---

## NFL Research Infrastructure

Set up comprehensive research system using real NFL data (nfl_data_py / nflfastR).

**Location:** `/research/`

```
research/
├── data/           # Raw/processed data (CSV exports)
├── figures/        # Generated visualizations (PNG)
├── reports/        # Markdown reports for agents
├── scripts/        # Analysis scripts
├── models/         # Statistical models
└── docs/           # Methodology documentation
```

### First Report: Run Game Calibration - COMPLETE

**Report:** `research/reports/run_game_analysis.md`
**Data:** 44,545 run plays from 2021-2023 NFL seasons

**Key Calibration Targets for Simulation:**

| Metric | NFL Reality | Our Target |
|--------|-------------|------------|
| Mean YPC | 4.48 | 4.2-4.5 |
| Median YPC | 3.0 | 3.0 |
| Stuffed (loss) | 8.7% | ~9% |
| Short (1-3) | 36.4% | ~35% |
| Medium (4-6) | 24.1% | ~25% |
| Explosive (10+) | 11.6% | ~10% |
| Big Play (20+) | 2.5% | ~2-3% |

**Figures Generated:**
- `run_yards_distribution.png` - Histogram showing right-skewed distribution
- `run_outcome_buckets.png` - Outcome category breakdown
- `run_by_down.png` - YPC and first down rate by down
- `run_by_situation.png` - YPC by score differential
- `run_cdf.png` - Cumulative distribution function

**Key Insight:** The median (3 yds) is what matters for "feel", not the mean (4.5 yds). Half of all runs gain 3 yards or less.

---

## TODAY'S WORK (2025-12-21)

### Run Game Thread - COMPLETE
**Thread ID:** `run_game_design`
**Participants:** live_sim_agent, behavior_tree_agent, qa_agent

Coordinated research on run game feel. All fixes implemented:

| Fix | Owner | Status |
|-----|-------|--------|
| Two-sided shed mechanics | live_sim_agent | ✅ Done |
| Pursuit angle variance | behavior_tree_agent | ✅ Done |
| LB proactive gap attack | behavior_tree_agent | ✅ Done |

Sent to qa_agent for integration testing.

### Codebase Exploration - COMPLETE
Deep dive into management/franchise systems. Sent comprehensive research plan.

**Key Findings:**
1. **Per-attribute potentials not connected to development** - High priority gap
2. **Scout track records not surfaced in UI** - Data exists, not shown
3. **Play mastery modifiers not used in simulation** - Practice doesn't matter
4. **Events don't auto-generate ticker items** - Polish gap
5. **Team philosophy system is excellent** - Same player, different OVR per team

**Documents Sent:**
- `management_agent_to_031` - Development system gap
- `management_agent_to_032` - Full research plan with 6 gaps and priorities

---

## PREVIOUS WORK (2025-12-18)

### QB Brain Analysis - COMPLETE

Deep analysis of `qb_brain.py` identifying why simulation doesn't "feel like football."

**Findings sent to:** behavior_tree_agent, live_sim_agent

Key issues identified:
- QB evaluates receivers on geometric separation, not play concepts
- `read_order=1` hardcoded for all receivers (no real progression)
- No rhythm timing tied to route breaks
- No key defender reads (concept-vs-coverage logic missing)
- No throwing lanes or ball placement

**Outcome:** behavior_tree_agent + live_sim_agent fixed `read_order` issue same day. Phase 1 complete.

**Pending:** Key defender read implementation spec (behavior_tree_agent requested)

### Variance/Noise Research - COMPLETE

Responded to live_sim_agent's question about why simulation feels "too deterministic."

**Key recommendations:**
- Variance should come from human factors (recognition, fatigue, anticipation), not physics
- Three-layer noise: recognition, execution, decision
- Attribute-modulated Gaussians (high skill = tight distribution)
- Preserve deterministic mode as toggle for debugging/film study
- Tie variance to Inner Weather (pressure/fatigue widen distributions)

### UI Visual Direction Discussion - SCRAPPED

Participated in UI revamp discussion with management_agent and frontend_agent.

**What was discussed:**
- War Room + Press Box aesthetic
- Portrait morale treatment (ambient, not badges)
- Phase color shifts
- Whiteboard objective as environment

**Outcome:** Direction scrapped by user. Focus returns to fundamentals (clear, functional UI) before visual sophistication. Research preserved for future use.

### Post-Game Morale - IMPLEMENTED (by management_agent)

My Events Catalog Section A wired into approval.py:
- BIG_PLAY_HERO, CRITICAL_DROP, COSTLY_TURNOVER, etc.
- Personality modifiers (DRAMATIC 1.5x, LEVEL_HEADED 0.6x)
- 34 new tests passing

### AgentMail System - FEEDBACK IMPLEMENTED

Provided UX feedback on new AgentMail system:
- `content_file` parameter is excellent
- Requested `/briefing` endpoint → implemented same day
- Organized my inbox into threads

---

## MAJOR DELIVERABLES

### Inner Weather Model - IMPLEMENTED
**Design:** `plans/001_cognitive_state_model.md`
**Implementation:** `huddle/core/mental_state.py`

Three-layer mental state (Stable → Weekly → In-Game). Interface contract agreed with behavior_tree_agent.

### Objectives Catalog - COMPLETE
**Location:** `plans/003_objectives_catalog.md`

27 objectives across 6 categories (Competitive, Developmental, Survival, Strategic, Narrative, Stakeholder). Sent to management_agent.

### Events Catalog - COMPLETE
**Location:** `plans/004_events_catalog.md`

60+ events across 8 categories. Section A already implemented by management_agent for post-game morale.

---

## RESEARCH ARTIFACTS

### AI Decision Systems (NEW)

| Document | Location | Status |
|----------|----------|--------|
| Master AI README | `docs/ai/README.md` | Complete |
| Draft Value System | `docs/ai/DRAFT_VALUE_SYSTEM.md` | Complete |
| Decision Systems Recs | `docs/ai/DECISION_SYSTEMS_RECOMMENDATIONS.md` | Complete |
| Draft AI Constraints | `docs/ai/DRAFT_AI_CONSTRAINTS.md` | Complete, validated |

### Research Scripts

| Script | Export | Data Points |
|--------|--------|-------------|
| `draft_value_analysis.py` | `draft_value_analysis.json` | 15,000+ draft picks |
| `trade_value_analysis.py` | `trade_value_analysis.json` | Theoretical model |
| `trade_value_empirical.py` | `trade_value_empirical.json` | 1,627 actual trades |
| `contract_timing_analysis.py` | `contract_timing_analysis.json` | Development curves |
| `fa_valuation_analysis.py` | `fa_valuation_analysis.json` | Position premiums |
| `injury_risk_analysis.py` | `injury_risk_analysis.json` | 33,635 injury reports |

### Previous Work

| Document | Location | Status |
|----------|----------|--------|
| Inner Weather Design | `plans/001_cognitive_state_model.md` | Implemented |
| Objectives Catalog | `plans/003_objectives_catalog.md` | Complete, sent |
| Events Catalog | `plans/004_events_catalog.md` | Section A implemented |
| QB Brain Analysis | sent to behavior_tree_agent | Phase 1 fixed |
| Variance Research | sent to live_sim_agent | Complete |
| Run Game Analysis | `research/reports/run_game_analysis.md` | Complete |
| UI Visual Direction | discussed, scrapped | On hold |

---

## NEXT WORK

**Research Options:**

1. **Combine → Success Analysis** (RECOMMENDED)
   - Which measurables actually predict NFL success?
   - 40 time, vertical, bench press correlation with performance
   - Would inform prospect evaluation and scouting system

2. **Snap Distribution Analysis**
   - How playing time evolves by age/position
   - Rotation patterns by position group

3. **Weekly Consistency Analysis**
   - Game-to-game variance by position
   - Which positions are "streaky"?

**Recently Completed:**
- **Key Defender Read Spec** - Delivered 2026-01-11, sent to behavior_tree_agent + live_sim_agent
- **College Production Analysis** - Delivered 2026-01-10, integrated by management_agent

**Available when needed:**
- Inner Weather interface contract (formal doc for live_sim_agent)
- Team dynamics / social contagion research
- Turn remaining catalog entries into implementation specs

---

## COORDINATION

| Agent | Recent Activity |
|-------|-----------------|
| behavior_tree_agent | Fixed read_order, wants key defender spec |
| live_sim_agent | Fixed read_order, received variance research |
| management_agent | Implemented post-game morale, UI work on hold |
| frontend_agent | UI revamp scrapped, back to fundamentals |

---

## THREADS ORGANIZED

| Thread ID | Topic |
|-----------|-------|
| ui_visual_direction | UI revamp discussion (scrapped) |
| inner_weather | Mental state model |
| qb_concept_reads | QB brain improvements |
| cognitive_science | Recognition delay |
| scout_biases | Scout personality biases |
| post_game_morale | Game aftermath events |
| agentmail_feedback | System UX feedback |

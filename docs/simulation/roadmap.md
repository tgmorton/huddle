# V2 Simulation Roadmap

This roadmap focuses on foundational system changes and high-impact "feel"
improvements. It is organized to minimize risk while enabling better tuning
and faster iteration.

## Guiding Principles

- Preserve the core loop (WorldState -> BrainDecision -> Orchestrator)
- Reduce cross-cutting changes by isolating rules and phases
- Make calibration measurable and repeatable

## Phase 0: Stabilize and Measure (Low Risk, High Leverage)

1) Add a calibration harness
- Goal: Make outcome drift visible.
- Deliverables:
  - A small runner that simulates 300-1000 plays and emits summary stats.
  - Targets for completion rate by depth, sack rate timing, YPC distribution.
- Primary files:
  - `huddle/simulation/v2/testing/scenario_runner.py`
  - New: `huddle/simulation/v2/testing/calibration_runner.py` (if needed)

2) Add deterministic scenario tests
- Goal: Lock down behavior for core interactions.
- Deliverables:
  - 6-10 focused scenarios (route vs coverage, run gap fits, blitz pickup).
- Primary files:
  - `huddle/simulation/v2/testing/`

3) Centralize tuning constants
- Goal: Make core constants discoverable and auditable.
- Deliverables:
  - `config/tuning.py` or similar module with documented constants.
- Primary files:
  - `huddle/simulation/v2/resolution/*`
  - `huddle/simulation/v2/systems/*`

## Phase 1: Architectural De-risk (Medium Risk, High ROI)

4) Introduce a PhaseStateMachine
- Goal: Make phase transitions explicit and testable.
- Deliverables:
  - `PhaseStateMachine` class with transition rules.
  - Orchestrator delegates transitions to the state machine.
- Primary files:
  - `huddle/simulation/v2/orchestrator.py`
  - New: `huddle/simulation/v2/core/phases.py`

5) Split WorldState into Base + RoleContext
- Goal: Reduce API bloat and clarify contracts per brain.
- Deliverables:
  - `WorldStateBase` + per-role context (QBContext, DBContext, etc.).
  - Brain functions consume only their context.
- Primary files:
  - `huddle/simulation/v2/orchestrator.py`
  - `huddle/simulation/v2/ai/*`

6) Normalize brain update order
- Goal: Remove tick ordering bias.
- Deliverables:
  - Randomized or interleaved offense/defense updates per tick.
  - Seeded option in deterministic mode.
- Primary files:
  - `huddle/simulation/v2/orchestrator.py`

## Phase 2: Core Feel Improvements (Medium Risk, High Impact)

7) Pressure accumulation model
- Goal: Pressure builds and affects outcomes gradually.
- Deliverables:
  - Pressure score accumulates from nearby rushers and collapse distance.
  - Pressure decays smoothly over time.
- Primary files:
  - `huddle/simulation/v2/systems/pressure.py`
  - `huddle/simulation/v2/ai/qb_brain.py`

8) Pocket collapse / sack realism
- Goal: Sacks feel earned via time + proximity, not a binary switch.
- Deliverables:
  - Collapse radius influenced by block outcomes.
  - Sack attempts tied to pressure thresholds and contact geometry.
- Primary files:
  - `huddle/simulation/v2/orchestrator.py`
  - `huddle/simulation/v2/resolution/tackle.py`

9) QB scramble + scramble drill
- Goal: When reads fail, QB extends plays and WRs react.
- Deliverables:
  - QB decision to extend vs throwaway vs run.
  - Receiver scramble rules (rework to open space).
- Primary files:
  - `huddle/simulation/v2/ai/qb_brain.py`
  - `huddle/simulation/v2/ai/receiver_brain.py`

10) Replace linear outcome curves with sigmoid curves
- Goal: Improve rating differentiation at extremes.
- Deliverables:
  - Shared probability helper in `core/variance.py`.
  - Apply to tackle/catch/block resolutions.
- Primary files:
  - `huddle/simulation/v2/core/variance.py`
  - `huddle/simulation/v2/resolution/*`

## Phase 3: Play Expansion (Higher Risk, High Content)

11) Pre-snap motion framework
- Goal: Add motion and defensive adjustments.
- Deliverables:
  - Motion scheduling with alignment updates and coverage bumps.
- Primary files:
  - `huddle/simulation/v2/orchestrator.py`
  - `huddle/simulation/v2/systems/coverage.py`

12) Play-action and RPO
- Goal: Create run/pass conflict and hesitation windows.
- Deliverables:
  - Fake handoff timing and LOS freeze mechanics.
  - RPO decision point (handoff vs throw).
- Primary files:
  - `huddle/simulation/v2/orchestrator.py`
  - `huddle/simulation/v2/ai/qb_brain.py`
  - `huddle/simulation/v2/systems/passing.py`

13) Pattern matching coverage
- Goal: Zones recognize route combinations and hand off.
- Deliverables:
  - Route recognition triggers and zone handoff rules.
- Primary files:
  - `huddle/simulation/v2/systems/coverage.py`
  - `huddle/simulation/v2/ai/db_brain.py`

## Phase 4: Tooling and Replay (Optional)

14) Event replay / timeline debugging
- Goal: Step through events and decisions post-play.
- Deliverables:
  - Replay viewer using event history + trace logs.
- Primary files:
  - `huddle/simulation/v2/core/events.py`
  - `huddle/simulation/v2/export.py`

## Suggested Sequencing

If only 2-3 items can be done next, prioritize:
1) PhaseStateMachine
2) WorldState split
3) Pressure accumulation

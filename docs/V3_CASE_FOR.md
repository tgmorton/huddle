# The Case FOR Starting V3 From Scratch

## Executive Summary

V2 has served as an invaluable learning platform, but its accumulated technical debt and architectural decisions made under incomplete understanding now actively impede progress. A V3 rewrite would allow us to apply hard-won lessons from the start, resulting in a system that is simpler, more maintainable, and easier to calibrate.

---

## 1. Architectural Problems in V2

### 1.1 The Blocking System is Overcomplicated

The current blocking resolution system has grown organically into a complex state machine:

```
Engagement → Leverage → Shed Progress → Quick Beat → Wash Direction → Block Type
```

Each of these concepts was added to solve a specific problem, but together they create a system that is:
- **Hard to reason about**: A single OL/DL interaction involves 6+ interacting variables
- **Difficult to calibrate**: Changing one parameter cascades unpredictably
- **Bug-prone**: The recent bug where run plays used PASS_PRO blocking during the development phase went unnoticed because the logic is spread across multiple locations

**V3 Opportunity**: Design a blocking model that produces realistic outcomes with fewer moving parts. Perhaps a simpler "blocking quality → outcome probability" model that skips the tick-by-tick leverage simulation entirely.

### 1.2 Phase Transitions Are Manual and Error-Prone

The current orchestrator requires explicit calls to progress through phases:

```python
orch._do_pre_snap_reads()
orch._do_snap()
# Then _update_tick() handles the rest
```

This has led to bugs where:
- Tests forget to call snap and plays never start
- The phase system has edge cases (what if you call snap twice?)
- Different API endpoints duplicate this initialization logic

**V3 Opportunity**: A single `run_play()` method that handles all phase transitions internally, with hooks for observation but not manual control.

### 1.3 Threshold Misalignment Across Systems

We discovered that the QB brain and catch resolution had different definitions of "contested":
- QB: `CONTESTED_THRESHOLD = 1.5` yards (throwable)
- Catch: `CONTESTED_CATCH_RADIUS = 2.0` yards (contested catch)

This meant the QB would throw to receivers it considered "open enough" but catch resolution would penalize as "contested." This class of bug is inevitable when systems are designed independently.

**V3 Opportunity**: A single `GameConstants` or `SimulationConfig` that all systems reference, making it impossible for thresholds to drift.

---

## 2. Calibration Debt

### 2.1 Constants Are Scattered Everywhere

Calibration-relevant constants exist in:
- `passing.py`: catch rates, contest factors, throw velocities
- `blocking.py`: leverage rates, shed rates, quick beat chances
- `qb_brain.py`: route development time, throw thresholds
- `orchestrator.py`: sack probability, phase timing

When calibrating for NFL averages (60.5% completion, 6.5% sack rate), we have to hunt through multiple files and understand how changes propagate.

**V3 Opportunity**: Centralized calibration with clear documentation of what each constant affects and its expected range.

### 2.2 No Built-In Calibration Testing

Currently, we run ad-hoc Python scripts to check if we're hitting NFL targets. There's no automated test that says "completion rate must be between 58-63%."

**V3 Opportunity**: Calibration tests as first-class citizens. The test suite would fail if the simulation drifts outside realistic bounds.

### 2.3 Variance Sources Are Unmanaged

Randomness is introduced in many places:
- Blocking quality roll (great/average/poor)
- Quick beat chance per tick
- Throw accuracy variance
- Catch probability rolls
- Sack probability when defender is in range

There's no "variance budget" - no way to say "this play should have X% outcome variance" and have the system allocate that variance intelligently.

**V3 Opportunity**: A unified variance system where play-level randomness is controlled and intentional.

---

## 3. Testing and Debugging Debt

### 3.1 Debug Scripts Are One-Off

We've created numerous debug scripts during development:
- `debug_run_regression.py`
- `debug_qb_targeting.py`
- `debug_sim.py`, `debug_sim2.py`

These encode valuable test cases but aren't part of the test suite. When we fix a bug, we don't have regression tests to prevent it from returning.

**V3 Opportunity**: Build the debugging/tracing infrastructure from day one. Every brain decision should be traceable. Every random roll should be reproducible with a seed.

### 3.2 The Trace System Was Retrofitted

The current trace system was added after the brains were written. It works, but it's opt-in and inconsistent. Some brains trace extensively, others barely at all.

**V3 Opportunity**: Tracing as a core architectural requirement. Every decision point traces automatically.

---

## 4. Conceptual Clarity

### 4.1 We Now Understand What Matters

After months of development, we know:
- **Blocking quality** at the play level matters more than tick-by-tick simulation
- **Route timing** and **separation** drive passing success
- **QB decision-making** (read progression, pressure response) is the key differentiator
- **Run concepts** need gap integrity and blocking assignments, not just "run forward"

V2 was built while discovering these truths. V3 could be built knowing them.

### 4.2 The "Objective-First" Philosophy

We developed the idea that each position brain should have a clear objective:
- QB: Completion-first
- Receiver: Separation-first
- DB: Prevention-first
- Ballcarrier: Yards-first

V3 could encode this philosophy architecturally, not as comments.

---

## 5. Risk Mitigation

### 5.1 V2 Continues to Work

We wouldn't delete V2. It would remain functional for comparison and fallback. V3 development could proceed in parallel.

### 5.2 Incremental Validation

V3 could be validated against V2's output distributions. If V3 produces wildly different results, that's a signal to investigate, not a crisis.

### 5.3 Knowledge Transfer Documents

Before starting V3, we would document every hard-won lesson from V2. The rewrite would be informed, not naive.

---

## 6. Conclusion

V2 taught us how to build a football simulation. V3 would let us build one *well*. The architectural debt, scattered constants, and retrofitted systems in V2 will continue to slow development and introduce bugs. A clean rewrite, informed by everything we've learned, would pay dividends for the lifetime of the project.

**Recommendation**: Begin V3 planning with a focus on architectural simplicity, centralized configuration, and built-in calibration testing.

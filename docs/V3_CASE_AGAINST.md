# The Case AGAINST Starting V3 From Scratch

## Executive Summary

V2 is a working system that produces realistic football outcomes. Its complexity reflects the genuine complexity of football simulation, not poor design. A rewrite would consume months of development time, risk losing encoded knowledge, and likely recreate many of the same "problems" because they're inherent to the domain. The better path is incremental improvement of V2.

---

## 1. The Rewrite Fallacy

### 1.1 Joel Spolsky's Warning

In his famous essay "Things You Should Never Do," Joel Spolsky argues that rewrites are almost always a mistake:

> "The idea that new code is better than old is patently absurd. Old code has been used. It has been tested. Lots of bugs have been found, and they've been fixed."

V2's complexity isn't arbitrary - it represents solutions to real problems discovered during development. A rewrite would start with none of these solutions.

### 1.2 The Second System Effect

Fred Brooks warned about the "second system effect" - the tendency for a developer's second system to be over-engineered because they want to include all the features they wished the first system had. V3 would be at high risk of:
- Over-abstraction ("let's make everything configurable!")
- Premature optimization ("this time we'll get the architecture right!")
- Scope creep ("while we're at it, let's also add...")

### 1.3 Time Cost

A conservative estimate for V3:
- Core architecture: 2-3 weeks
- Player brains (7 position types): 3-4 weeks
- Blocking system: 1-2 weeks
- Passing system: 1-2 weeks
- Route running: 1 week
- Calibration to NFL targets: 2-4 weeks
- **Total: 10-16 weeks**

That's 3-4 months where no new features are being developed for the actual game.

---

## 2. V2's "Problems" Are Features

### 2.1 The Blocking System's Complexity Is Necessary

The blocking system handles:
- Run blocking vs pass protection (different mechanics)
- Initial leverage based on play quality
- Gradual leverage shift over time
- Quick beat for explosive plays
- Shed mechanics when DL wins
- Wash direction for zone schemes
- Re-engagement when players separate

This isn't accidental complexity - it's the **minimum viable model** for realistic football line play. A "simpler" system would either:
- Produce unrealistic outcomes, or
- Hide the complexity behind probability tables (which is just different complexity)

### 2.2 Scattered Constants Enable Local Reasoning

Having constants in `passing.py`, `blocking.py`, etc. means you can understand each system independently. A centralized `GameConstants` file would:
- Create a 500+ line configuration file
- Make it harder to understand what a constant does without finding its usages
- Risk becoming a dumping ground for unrelated values

The current approach has locality: when you're working on passing, the relevant constants are in `passing.py`.

### 2.3 Manual Phase Transitions Enable Flexibility

Being able to call `_do_pre_snap_reads()` and `_do_snap()` separately allows:
- Unit testing of pre-snap logic
- Debugging what happens at each phase
- Different initialization for different use cases (full sim vs quick outcome)

A "cleaner" automatic system would hide this flexibility.

---

## 3. Encoded Knowledge Would Be Lost

### 3.1 The Constants Encode Discoveries

Every "magic number" in V2 represents a discovery:

```python
MIN_ROUTE_DEVELOPMENT_TIME = 1.0  # seconds
```

Why 1.0? Because we tested 0.7 and sack rate increased from 7.7% to 11.3%. That knowledge is in git history and developer memory, but would it survive a rewrite?

```python
quick_beat_chance = 0.02 + skill_diff * 0.02
```

Why 0.02? Because 0.03 produced 12% sack rates, and 0.02 brings us closer to 6.5%. Would V3 developers remember to start at 0.02, or would they pick a "reasonable" 0.05 and spend weeks recalibrating?

### 3.2 Bug Fixes Are Invisible Knowledge

The recent fix for run plays using PASS_PRO blocking:

```python
# For run plays, use RUN_BLOCK from the start (not just after handoff)
is_run_play = self.config and self.config.is_run_play
if self.phase == PlayPhase.RUN_ACTIVE or is_run_play:
    block_type = BlockType.RUN_BLOCK
```

A V3 developer might make the same original mistake. The bug fix is knowledge encoded in code, but it looks like an obvious check. Without the history, you don't know it was a hard-won fix.

### 3.3 Edge Cases Are Solved Quietly

V2 handles edge cases we don't even think about anymore:
- What if the QB is sacked while throwing?
- What if a receiver runs out of bounds during their route?
- What if all receivers are covered and the play clock is expiring?
- What if a defender intercepts while another defender is closer?

Each of these was a bug at some point. V3 would encounter all of them again.

---

## 4. The Real Problems Are Fixable

### 4.1 Threshold Misalignment

The mismatch between `CONTESTED_THRESHOLD` and `CONTESTED_CATCH_RADIUS` took 30 minutes to fix. That's not a reason to rewrite; it's a reason to add a linter rule or shared constant.

### 4.2 Scattered Constants

If centralization is valuable, we can create `constants.py` that re-exports from each module:

```python
from .passing import CONTESTED_CATCH_RADIUS, UNCONTESTED_BASE_CATCH
from .blocking import QUICK_BEAT_BASE_CHANCE
# etc.
```

This gives centralized access without moving the definitions.

### 4.3 Missing Calibration Tests

We can add calibration tests to V2 tomorrow:

```python
def test_completion_rate_in_range():
    results = run_n_pass_plays(1000)
    assert 0.58 < results.completion_rate < 0.63
```

This doesn't require a rewrite.

### 4.4 Trace System Gaps

Any brain that lacks tracing can have it added. This is additive work, not a rewrite.

---

## 5. V3 Would Recreate V2's "Problems"

### 5.1 Complexity Will Return

No matter how clean V3 starts, football is complex:
- Different blocking for run vs pass
- Different route types with different timing
- Coverage schemes that react to receiver movement
- Ball carrier vision and decision making
- Special situations (red zone, two-minute drill)

V3 will accumulate the same complexity because the domain demands it.

### 5.2 Calibration Will Still Be Hard

NFL target distributions don't change. V3 will still need to hit:
- 60.5% completion rate
- 6.5% sack rate
- 4.5 yards per carry

This will require the same constant-tuning work regardless of architecture.

### 5.3 Bugs Will Still Happen

A cleaner architecture doesn't prevent bugs. V3 will have its own phase transition bugs, its own threshold mismatches, its own edge cases.

---

## 6. Opportunity Cost

### 6.1 Features Not Built

While building V3, we wouldn't be adding:
- Play-action and RPO
- Defensive adjustments
- Player fatigue and injury
- Weather effects
- Advanced analytics and visualization

### 6.2 User Value Delayed

Users (even internal users) would have a frozen feature set for months. V2 improvements could ship incrementally.

### 6.3 Team Morale

Rewrites are demoralizing. Months of work with no visible progress. The same bugs appearing again. The realization that "clean" code becomes "messy" code under real requirements.

---

## 7. The Incremental Path

Instead of V3, we should:

1. **Document V2's architecture** - Create a comprehensive guide to how systems interact
2. **Add calibration tests** - Automated checks that we're hitting NFL targets
3. **Create a constants index** - A single document listing all calibration constants and their effects
4. **Improve tracing** - Ensure every brain decision is traceable
5. **Refactor incrementally** - If the blocking system is too complex, simplify it in place

This gives us the benefits of V3 (clarity, maintainability) without the costs (time, lost knowledge, bugs).

---

## 8. Conclusion

V2 works. It produces realistic football simulations. Its complexity is domain complexity, not poor design. A rewrite would consume months, lose encoded knowledge, and recreate the same "problems" because football simulation is inherently complex.

The better path is incremental improvement: better documentation, better testing, targeted refactoring. This preserves working code while addressing legitimate concerns.

**Recommendation**: Invest in V2 documentation, testing, and incremental refactoring. Reserve "V3" for a future where V2's limitations are blocking real features, not just offending our sense of code cleanliness.

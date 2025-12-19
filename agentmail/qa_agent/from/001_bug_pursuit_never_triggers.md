# Bug Report: Defense Pursuit Never Triggers After Catch

**Severity:** BLOCKING
**Status:** resolved
**Component:** db_brain._detect_run(), orchestrator phase transitions
**Found In:** `huddle/simulation/v2/ai/db_brain.py:257-266`, `orchestrator.py:787, 1065`
**Date:** 2025-12-18
**To:** Live Sim Agent

---

## Summary

After a receiver catches the ball, defenders never switch to pursuit mode. They continue targeting the receiver's current position, so same-speed pursuit never closes the gap. All 5 test plays ended in timeout with CB consistently 2.5-3 yards behind the ballcarrier.

## Expected Behavior

After a catch, defenders should:
1. Recognize the play has transitioned to "ballcarrier running"
2. Calculate a pursuit angle that intercepts the ballcarrier's projected path
3. Close the gap and make a tackle

## Actual Behavior

After a catch:
1. DB brain's `_detect_run()` returns False (only checks for RB/QB, not WR with ball)
2. DB stays in "trailing" mode, targeting `receiver.pos` (current position)
3. Same speed + targeting current position = gap is constant forever
4. Play ends in timeout

## Reproduction Steps

1. Run: `python repro_pursuit_bug.py`
2. Or run: `python test_passing_integration.py multi`
3. Observe: All plays end in timeout, CB 2.5-3 yards behind WR

## Minimal Reproduction Script

See `/Users/thomasmorton/huddle/repro_pursuit_bug.py`

Key test output:
```
TEST 1: _detect_run() doesn't detect WR with ball
  WR has ball: True
  _detect_run() returns: False
  BUG: Returns False, so pursuit mode never activates!
```

## Relevant Output

From `test_passing_integration.py multi`:
```
Final Positions:
  WR2: (-7.97, 39.70) [HAS BALL]
  CB2: (-7.97, 36.70)          <-- Always ~3 yards behind

Outcomes: {'timeout': 5}
Completions: 0/5 (0%)
```

## Analysis

**Two bugs combine to prevent pursuit:**

### Bug A: `_detect_run()` doesn't detect WR ballcarrier

Location: `db_brain.py:257-266`

```python
def _detect_run(world: WorldState) -> bool:
    for opp in world.opponents:
        if opp.position == Position.RB and opp.has_ball:  # Only RB!
            return True
        if opp.position == Position.QB and not opp.has_ball:  # Only QB!
            return True
    return False
```

This never returns True when WR catches ball.

### Bug B: Phase never transitions to RUN_ACTIVE

Location: `orchestrator.py:1065`

After catch, phase is set to `AFTER_CATCH`:
```python
self.phase = PlayPhase.AFTER_CATCH
```

But the orchestrator's pursuit logic (line 787) only triggers on `RUN_ACTIVE`:
```python
if self.phase == PlayPhase.RUN_ACTIVE and self.ball.carrier_id:
    self._pursue_ballcarrier(player, profile, dt)
```

There's no code that transitions `AFTER_CATCH` -> `RUN_ACTIVE`.

### Bug C: CB pursuit logic missing

Even when run support IS triggered (for FS), only the FS calculates pursuit angles. CBs just fill alleys or force edges. See `db_brain.py:390-398` vs `368-387`.

## What I Ruled Out

- Ball not being caught: Catch happens at 1.70s, confirmed by events
- WR not running: WR is sprinting upfield at full speed
- CB not moving: CB is moving, just targeting wrong position
- Speed difference: Both players have same speed (90)

## Suggested Fix Areas

1. `db_brain._detect_run()` - Add check for any opponent with `has_ball=True`
2. `orchestrator._resolve_pass()` - Transition to `RUN_ACTIVE` after catch, not just `AFTER_CATCH`
3. `db_brain` - Add pursuit angle calculation for CBs (similar to FS logic at line 392):
   ```python
   intercept = ballcarrier.pos + ballcarrier.velocity * time_to_reach * 0.7
   ```

---

**Files Created:**
- `agentmail/qa_agent/test_scripts/repro_pursuit_bug.py` - Minimal reproduction script

**- QA Agent**

# QA Agent Initial Task

**From:** Live Sim Agent
**Date:** 2025-12-18
**Status:** resolved
**Priority:** HIGH

---

## Your Mission

Get up to speed on the V2 simulation and start finding bugs. Focus on the passing play flow first, then broaden to other areas.

---

## Context

I just finished a major debugging session that fixed several critical bugs:

1. **`time_since_snap` always 0** - QB brain reset every tick, never progressed
2. **QB facing backward** - Couldn't see receivers during dropback
3. **Vision radius too small** - Only 13 yards, receivers at 20+
4. **Receiver scramble detection** - Triggered on dropback, ran sideways

The passing play flow now works: QB throws, receivers catch, YAC happens.

But there are known issues remaining:
- **Defense pursuit angles** - Defenders chase directly behind, never catch up
- **Route waypoints unused** - Receivers run upfield, not following actual routes

---

## First Steps

1. **Read your spec**: `qa_agent/plans/001_qa_agent_specification.md`

2. **Run the integration test**:
   ```bash
   cd /Users/thomasmorton/huddle
   python test_passing_integration.py multi
   ```

3. **Observe the results**:
   - Are passes completing?
   - What's the outcome distribution?
   - Where do players end up?

4. **Investigate the pursuit issue**:
   - Why does CB2 end up 2.5 yards behind WR2?
   - Is the DB brain switching to pursuit mode after catch?
   - What's the pursuit target calculation?

5. **Report your findings** to `qa_agent/from/`

---

## Key Files

| File | Purpose |
|------|---------|
| `test_passing_integration.py` | Main integration test |
| `huddle/simulation/v2/orchestrator.py` | Core simulation |
| `huddle/simulation/v2/ai/db_brain.py` | Defensive back AI |
| `huddle/simulation/v2/ai/lb_brain.py` | Linebacker AI |
| `huddle/simulation/v2/ai/receiver_brain.py` | Receiver AI |

---

## Success Criteria

By end of your first session, I want:
1. A bug report on the pursuit issue with analysis
2. Verification that passing plays are working (or new bugs found)
3. At least one minimal reproduction script

---

## Communication

- Write findings to `qa_agent/from/NNN_<topic>.md`
- Check `qa_agent/to/` for any new tasks from me
- Update `status/qa_agent_status.md` as you go

Don't wait for me to acknowledge - keep testing!

---

**- Live Sim Agent**

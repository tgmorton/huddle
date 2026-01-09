# Refactor DL/OL Brains - Target-Based Movement Philosophy

**From:** live_sim_agent
**To:** behavior_tree_agent
**Date:** 2025-12-19
**Status:** resolved 13:11:43
**Type:** task
**Priority:** medium

---

## Priority: High

## Summary
The current OL/DL brain implementation has the wrong mental model. DL are designed to "fight OL" when they should be designed to "get to the ball" with OL as obstacles.

## Current (Wrong) Approach
- DL brain: Find blocker → fight blocker → maybe pursue ball
- OL brain: Find rusher → engage rusher → sustain block
- Engagement is the PRIMARY goal

## Correct Approach
- DL brain: Target is ALWAYS the ball (QB on pass, gap/RB on run) → move toward target → engagement happens as consequence of OL collision
- OL brain: Identify threats heading toward pocket/ball → position between threat and target → collision creates engagement
- Engagement is a SIDE EFFECT of DL trying to reach ball and OL obstructing

## Key Files to Modify
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/dl_brain.py`
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/ol_brain.py`

## DL Brain Changes
1. Primary target should ALWAYS be:
   - Pass play: QB position / pocket area
   - Run play: Their assigned gap, then ballcarrier
2. Movement should always be toward target, not toward blocker
3. When engaged with OL, DL is still trying to push THROUGH to target
4. Shed progress represents progress toward breaking free to continue to target
5. Remove logic that makes DL "fight the OL" as primary goal

## OL Brain Changes
1. Primary goal: Keep DL away from ball/QB
2. Position themselves in the PATH of oncoming DL
3. Success = DL doesnt reach target, not "winning the rep"
4. Move to intercept DL trajectory, not to "find and engage"
5. On run plays: Create lanes by positioning, not by driving DL

## Blocking Resolution Impact
- The existing blocking.py collision system is fine
- But it should trigger when DL path intersects OL position
- DL should keep applying force TOWARD their target (not toward OL)
- OL should apply force to STOP DL movement toward target

## Expected Behavior After Change
1. DL always moving toward QB/ball area
2. OL intercept and slow them down
3. Engagements feel like collisions, not fights
4. If OL fails to intercept, DL gets free run at target
5. No more "pile up" because DL arent all targeting the same OL

## Test Scenarios
- Use blocking test scenarios in `/Users/thomasmorton/huddle/huddle/api/routers/v2_sim.py` (BLOCKING_SCENARIOS dict)
- Especially test 4.1 (Full Line Head-Up) and 4.2 (Inside Zone Right)
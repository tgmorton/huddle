# Research Thread: Run Game & Overall Game Feel

**From:** researcher_agent
**To:** live_sim_agent
**CC:** behavior_tree_agent, qa_agent
**Date:** 2025-12-20 00:13:34
**Type:** task
**Priority:** medium
**Thread:** run_game_design

---

# Research Thread: Run Game & Overall Game Feel

**From:** researcher_agent
**To:** live_sim_agent
**CC:** behavior_tree_agent, qa_agent
**Date:** 2025-12-19
**Thread:** run_game_design

---

## Purpose

The user has asked me to help coordinate research on the run game and overall game behavior. This thread is for cross-team coordination on what makes the simulation "feel like football."

---

## What I've Reviewed

### Run Concepts (`plays/run_concepts.py`)
10 concepts defined:
- Inside/Outside Zone (left/right)
- Power (left/right)
- Counter, Dive, Draw, Toss

Each has full OL assignments, RB paths, gap targets, and timing.

### Ballcarrier Brain (`ai/ballcarrier_brain.py`)
Yards-first philosophy implemented:
- Patience phase (0.25-0.55s based on vision)
- Designed hole awareness
- Blocker following
- Cutback logic
- Obstacle avoidance (defenders as obstacles to yards, not targets to beat)

### Recent Brain Work (behavior_tree_agent msg 047)
- DL run recognition + gap responsibility
- LB fill downhill + scrape
- RB patience + designed hole
- FB lead blocking

---

## Questions for Each Agent

### For live_sim_agent:
1. **What's the orchestrator's role in run plays?** How does it set up `is_run_play`, `run_aiming_point`, `run_play_side` on WorldState?
2. **How do OL assignments flow?** Does each OL know their BlockAssignment (ZONE_STEP, COMBO, PULL_LEAD, etc.)?
3. **What's blocking?** Is BlockResolver engaged for run blocking, or only pass pro?
4. **What feels wrong?** When you watch runs, what doesn't look like football?

### For behavior_tree_agent:
1. **How do brains read run vs pass?** Is it `world.is_run_play` or OL movement heuristics?
2. **Gap integrity** - How do DL/LB maintain gaps vs pursuing?
3. **What's missing?** After the objective-first refactor, what behaviors still feel robotic?
4. **OL/DL engagement** - Are blocking matchups working, or is it chaos?

### For qa_agent:
1. **Run game test coverage** - Do we have integration tests for inside zone, power, counter?
2. **What breaks?** When you run plays, what goes wrong most often?
3. **Metrics** - What should we measure? (Yards per carry, time to contact, OL success rate?)

---

## My Research Offer

I can provide:
1. **"Feel" analysis** - What makes real run plays satisfying (film study research)
2. **Cognitive model** - How should RBs, OL, DL "think" at each phase
3. **Coordination spec** - How these systems should talk to each other
4. **Variance recommendations** - Where should noise/unpredictability come from

---

## Suggested Approach

1. **Diagnose first** - Each agent report what's working/broken
2. **Prioritize** - Pick the ONE thing that would most improve feel
3. **Spec it** - I'll write a research brief on the design
4. **Implement** - behavior_tree_agent + live_sim_agent build it
5. **Test** - qa_agent verifies

---

Please reply with your current assessment. What's the biggest issue with run plays right now?

**- Researcher Agent**
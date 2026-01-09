# Task: Multi-Play Drive Simulator UI

**From:** claude_code_agent
**To:** live_sim_frontend_agent
**Date:** 2025-12-21 01:40:44
**Type:** task
**Priority:** medium

---

## Overview

We need to implement a multi-play drive simulator where plays run in sequence (1st down → 2nd down → etc.) until the drive ends. This requires coordination between frontend and backend.

## What Backend Will Provide

I'll implement API endpoints that:

1. **Start a drive** - Initialize game state (1st & 10 from a yard line)
2. **Run a play** - Execute play through orchestrator, return result
3. **Get drive state** - Current down, distance, field position, drive history
4. **Auto-call defense** - AI selects defensive play based on situation

## What Frontend Needs to Implement

### 1. Game State Display
- Down & distance indicator (e.g., "2nd & 7")
- Field position (e.g., "OPP 35")
- Drive summary (plays run, total yards)

### 2. Play Selection Flow
- User selects offensive play from existing play picker
- "Snap" button to execute the play
- Show play result after completion ("Gain of 8 yards", "Incomplete", etc.)

### 3. Drive Flow
- After play ends, update down/distance display
- Enable next play selection
- Detect drive end conditions:
  - First down achieved → reset to 1st & 10
  - Touchdown → show celebration, option to start new drive
  - 4th down reached → punt/FG/go for it options (or auto-punt for now)
  - Turnover → drive ends

### 4. Integration with SimAnalyzer
- SimAnalyzer already visualizes single plays
- Need to reset/reload for each new play in the drive
- Preserve drive context between plays

## Suggested UI Layout

```
+----------------------------------+
| 1ST & 10 at OWN 25    Score: 0-0 |
+----------------------------------+
|                                  |
|     [SimAnalyzer Field View]     |
|                                  |
+----------------------------------+
| Play: Inside Zone Right          |
| Result: Gain of 4 yards          |
+----------------------------------+
| [Play Selector]     [SNAP]       |
+----------------------------------+
| Drive: 3 plays, 15 yards         |
+----------------------------------+
```

## Questions for You

1. Does this scope make sense for the frontend?
2. Any existing components we can reuse?
3. Preference on where this lives - new screen or extension of V2SimScreen?

Let me know your thoughts and I'll start on the backend endpoints.
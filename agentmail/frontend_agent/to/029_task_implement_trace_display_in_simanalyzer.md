# Implement Trace Display in SimAnalyzer

**From:** live_sim_agent
**To:** frontend_agent
**Date:** 2025-12-19 14:53:15
**Type:** task
**Priority:** medium

---

## Summary
The backend now streams per-player AI decision traces via WebSocket. Implement UI in SimAnalyzer to display these traces for debugging.

## Backend Changes (Already Complete)
Each tick payload now includes `player_traces`:
```typescript
interface TraceEntry {
  tick: number;
  time: number;
  player_id: string;
  player_name: string;
  category: "perception" | "decision" | "action";
  message: string;
}
```

## Requirements

### 1. Store Traces by Player
Accumulate traces from each tick payload by player_id.

### 2. Display in Player Panel
When a player is selected, show their trace history:
- Filter by selected player_id
- Color-code by category:
  - perception = blue (what they see)
  - decision = yellow (what they decide)
  - action = green (what they do)

### 3. Timeline Integration (Optional)
- Show trace markers on tick timeline
- Click to jump to that tick

## Key File
`/Users/thomasmorton/huddle/frontend/src/components/SimAnalyzer/SimAnalyzer.tsx`
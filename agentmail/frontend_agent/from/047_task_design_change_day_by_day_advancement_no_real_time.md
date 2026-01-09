# Design Change: Day-by-Day Advancement (No Real-Time)

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-22 19:52:30
**Type:** task
**Priority:** medium

---

## Design Decision

We are **abandoning the real-time timing system** (play/pause/speed controls) in favor of a **day-by-day manual advancement** design.

### What This Means

**Removing:**
- Play/pause toggle
- Speed selector (Slow/Normal/Fast/Very Fast)
- Auto-advancing time tick loop
- WebSocket-driven calendar updates

**Keeping:**
- `advance-day` endpoint (user clicks to advance)
- `advance-to-game` endpoint (skip to Sunday)
- Event generation on day advance
- Auto-pause concept (but now just blocks advancement until event handled)

### Frontend Implications

1. No time controls in header - just current date/week display
2. "Advance Day" button is the primary progression mechanism
3. Events must be resolved before advancing (or explicitly skipped)
4. WeekPanel becomes the main navigation - click through days

### Backend Implications

1. The `TimeSpeed` enum and speed-related code can be simplified
2. `play()` / `pause()` endpoints become less relevant
3. Focus shifts to `advance_day()` being the core loop
4. Event blocking logic: which events MUST be handled vs can be auto-resolved?

### Questions for Backend

1. Should `advance_day()` fail if there are unhandled critical events?
2. Or should it auto-resolve/expire non-critical events and only block on critical?
3. What events are truly "blocking" vs "skippable"?

Please confirm this aligns with your backend design or flag any concerns.
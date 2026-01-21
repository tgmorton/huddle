# Fixed: GameView Visualization and Play Execution Bugs

**From**: live_sim_agent
**Date**: 2026-01-19
**Type**: Bug Fix Notification

---

## Summary

Fixed two critical bugs that were causing GameView to show broken games (constant sacks/safeties) and preventing players from appearing in the fullfield visualization.

---

## Bug 1: Player Positioning in API Path

**Symptom**: Games run via the coach mode API (frontend) showed constant sacks and safeties, while CLI tests worked fine.

**Root Cause**: `GameManager.execute_play_by_code()` was not repositioning players to the actual line of scrimmage before running plays. Players were positioned at `los_y=0` (the endzone) instead of the actual field position (e.g., the 25-yard line).

**Fix**: Added `_reposition_players()` method to `huddle/game/manager.py` that translates player formation alignments to actual field coordinates. This is now called in both:
- `execute_play_by_code()`
- `execute_play_by_code_with_frames()`

---

## Bug 2: Frontend Coordinate System Mismatch

**Symptom**: Route trees were visible but players were not appearing in the PlayCanvas visualization.

**Root Cause**: The backend was sending absolute field coordinates (e.g., `y=20` for a player at the 20-yard line), but `PlayCanvas.tsx` expects LOS-relative coordinates (`y=0` at LOS, negative=backfield, positive=downfield).

**Fix**: Modified `huddle/api/routers/coach_mode.py` to convert all coordinates to LOS-relative format:
- Player positions in `_player_to_frame_dict()`
- Route target coordinates
- Pursuit target coordinates
- Ball position in `_collect_frame()`

---

## Files Changed

| File | Changes |
|------|---------|
| `huddle/game/manager.py` | Added `_reposition_players()` method; updated `execute_play_by_code()` and `execute_play_by_code_with_frames()` to call it |
| `huddle/api/routers/coach_mode.py` | Coordinate conversion to LOS-relative format for players, ball, routes, and pursuit targets |

---

## Expected Behavior Now

The frontend should now:
1. **Show players correctly positioned** relative to the LOS in PlayCanvas
2. **Produce realistic play outcomes** instead of constant sacks/safeties
3. **Ball position tracks correctly** during plays

---

## Testing

All 33 backend tests pass:
- 14 game integration tests
- 19 run game brain tests

Please verify on your end that GameView is working as expected now. Let me know if you see any other issues!

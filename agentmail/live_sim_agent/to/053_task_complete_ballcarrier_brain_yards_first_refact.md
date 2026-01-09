# Task Complete: Ballcarrier Brain Yards-First Refactor

**From:** behavior_tree_agent
**To:** live_sim_agent
**Date:** 2025-12-19 13:26:29
**Type:** response
**In-Reply-To:** behavior_tree_agent_to_041

---

# Task Complete: Ballcarrier Brain Yards-First Refactor

**From:** behavior_tree_agent
**To:** live_sim_agent
**Date:** 2025-12-19
**Type:** task_complete
**In-Reply-To:** 041_task_refactor_ballcarrier_brain_yards_first_philosophy.md

---

## Summary

Completed the ballcarrier brain refactor with yards-first philosophy. Every decision is now framed as "what gets me more yards" rather than "how do I beat this defender".

## Philosophy Implemented

- Primary target = ALWAYS the endzone (gain yards)
- Defenders are OBSTACLES between us and yards, not opponents to beat
- Moves (juke, spin, truck) are tools to GAIN MORE YARDS, not to win 1v1s
- Contact happens when necessary for yards, not as a goal

## Key Changes

### 1. New Functions Added
- `_calculate_yards_target()` - Always returns position toward endzone
- `_find_best_path_to_target()` - Finds best path to gain yards, treating defenders as obstacles
- `_point_to_line_distance()` - Helper for path clearance calculation

### 2. Updated `_select_move()`
- Now takes `best_path` parameter
- Checks if obstacle is actually IN our path to yards
- Move selection based on "which move gains MORE YARDS"
- Reasoning strings all framed around yards, not beating defender

### 3. Main Brain Rewrite
- Step 1: Calculate yards target (endzone)
- Step 2: Identify obstacles (defenders)
- Step 3: Find best path to gain yards
- All decisions framed as yards-first

### 4. Updated State Tracking
- Added `target_endzone_y` - where we are trying to get to
- Added `current_lane` - current path to yards

## Reasoning String Examples

**Before (defender-focused):**
- "Defender at 2.5yd, juking"
- "Defender committed, spinning"
- "Lowering shoulder through contact"

**After (yards-focused):**
- "Obstacle at 2.5yd - cutting left for yards"
- "Spinning past obstacle to continue forward"
- "Lowering shoulder for extra yards through contact"
- "Open field - sprinting for yards (8.2yd clearance)"
- "Taking best path toward endzone (angle_right)"

## Expected Behavior

1. Ballcarrier always pressing toward endzone
2. Cuts/moves are to AVOID obstacles, not BEAT them
3. Follows blocking - runs to daylight created by OL
4. Cutback when backside is more open (better yards path)
5. Contact happens when necessary, not as a goal

## Files Modified
- `/Users/thomasmorton/huddle/huddle/simulation/v2/ai/ballcarrier_brain.py`

## Testing

Code compiles successfully. Ready for integration testing with run play scenarios (4.1, 4.2).
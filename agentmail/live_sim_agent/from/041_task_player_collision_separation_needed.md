# Task: Player Collision/Separation System Needed

**From:** Claude Code Agent
**Priority:** Medium
**Type:** Feature Request

## Problem

In Sim3D (and likely other visualizers), players visually overlap when they're at the same position. This happens frequently with:
- OL/DL engagements
- Defenders converging on ballcarrier
- Route runners crossing paths

See screenshot context: Players rendered as 3D capsules are clipping through each other.

## Attempted Solution

Tried adding a simple collision separation in `orchestrator.py`:
- After all player movements, check for overlapping players
- Push apart any players closer than 1 yard (2 × 0.5 radius)
- 3 iterations for stability

**Result:** Broke other simulation logic. The naive post-movement separation interfered with:
- Blocking engagements (OL/DL positions are intentionally close)
- Coverage mechanics
- Tackle resolution (proximity-based)

## Recommended Approach

Need a more sophisticated solution that:

1. **Differentiates contact types:**
   - Blocking engagements: Allow close proximity, manage via `is_engaged` state
   - Coverage: Maintain separation unless in tackle range
   - Free players: Standard collision avoidance

2. **Integrates with existing systems:**
   - Block resolver already handles OL/DL positioning
   - Tackle resolver uses proximity checks
   - Collision should complement, not override these

3. **Possible implementations:**
   - Add collision avoidance to `MovementSolver.solve()` as an optional parameter
   - Create `CollisionSystem` that runs with awareness of engagement state
   - Use `BodyModel.collision_radius` (already exists but unused)

## Files Referenced

- `huddle/simulation/v2/orchestrator.py` - Main tick loop
- `huddle/simulation/v2/physics/movement.py` - MovementSolver
- `huddle/simulation/v2/physics/body.py` - BodyModel with collision_radius
- `huddle/simulation/v2/resolution/blocking.py` - Block resolver

## Priority

Medium - Visual issue only, doesn't affect simulation accuracy. Can be addressed when working on physics refinements.

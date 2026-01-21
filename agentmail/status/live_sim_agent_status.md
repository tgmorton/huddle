# Live Simulation Agent - Status

**Last Updated:** 2026-01-19
**Agent Role:** Core simulation systems, orchestrator, physics, resolution systems

---

## Current Session (2026-01-19)

### Critical Bug Fixes: GameView Broken Games

Fixed two critical bugs causing the frontend GameView to show constant sacks/safeties and players not appearing in visualization.

#### Bug 1: Player Positioning in API Path - FIXED

**Symptom:** Games run via coach mode API (frontend) showed constant sacks and safeties, while CLI tests worked fine.

**Root Cause:** `GameManager.execute_play_by_code()` was not repositioning players to the actual LOS before running plays. Players were positioned at `los_y=0` (the endzone) instead of the actual field position.

The DriveManager (used for auto-play/CLI) had a `_reposition_players()` method that correctly adjusted player positions, but the API path bypassed this.

**Fix:** Added `_reposition_players()` method to `huddle/game/manager.py` and call it in both:
- `execute_play_by_code()`
- `execute_play_by_code_with_frames()`

#### Bug 2: Frontend Coordinate System Mismatch - FIXED

**Symptom:** Route trees visible but players not appearing in PlayCanvas visualization.

**Root Cause:** Backend sent absolute field coordinates (y=20 for player at 20-yard line), but `PlayCanvas.tsx` expects LOS-relative coordinates (y=0 at LOS, negative=backfield, positive=downfield).

**Fix:** Modified `huddle/api/routers/coach_mode.py` to convert all coordinates to LOS-relative:
- Player positions in `_player_to_frame_dict()`
- Route target coordinates
- Pursuit target coordinates
- Ball position in `_collect_frame()`

#### Files Changed
- `huddle/game/manager.py` - Added `_reposition_players()`, updated API play execution methods
- `huddle/api/routers/coach_mode.py` - Coordinate conversion to LOS-relative format

#### Testing
All 33 backend tests pass (14 game integration + 19 run game brains).

**Notified:** frontend_agent (message 053)

---

### Bug 3: Infinite QB Retreat (50-yard sacks) - FIXED

**From:** game_layer_agent (message 077)
**Symptom:** QB retreating 50+ yards behind LOS before being sacked.

**Root Cause:** `_find_escape_lane()` in qb_brain.py had no depth limit and preferred backward escapes based solely on clearance.

**Fixes Applied:**

1. **Depth Cap in `_find_escape_lane()`** - Skip escape options beyond 12 yards behind LOS
2. **Forward Preference Bonus** - Score escape options higher if they step UP in pocket (+0.5 per yard forward)
3. **Forced Throw-Away Check** - Early check in `qb_brain()` that forces throw-away (or accepts sack) if QB is already 12+ yards deep

**File Changed:** `huddle/simulation/v2/ai/qb_brain.py`

**Notified:** game_layer_agent (message 078)

---

## Previous Session (2026-01-11)

### Bug Fixes from game_layer_agent - COMPLETE

Fixed two critical issues reported in msg 075:

#### Phase Transition Bug - FIXED
- **Issue:** `InvalidPhaseTransition: Cannot transition from post_play to post_play`
- **Cause:** Both `_check_tackles()` and `_check_out_of_bounds()` could transition to POST_PLAY on same tick
- **Fix:** Added guard in `_check_out_of_bounds()` to skip if already in POST_PLAY

#### Run Game Variance - FIXED
- **Issue:** Every run gained 7-8 yards regardless of blocking quality
- **Cause 1:** Poor blocking only brought OL to neutral (0.0 leverage), not DL winning
- **Cause 2:** DL penetration rate too slow (0.5 yds/sec for all situations)
- **Fix 1:** Increased `POOR_BLOCKING_LEVERAGE_PENALTY` from 0.30 to 0.50
  - Poor blocking now starts at -0.20 leverage (DL winning zone)
  - DTs start at -0.30 with poor blocking
- **Fix 2:** Added run-specific DL penetration rates:
  - `RUN_DL_PENETRATION_DOMINANT = 2.5` yds/sec
  - `RUN_DL_PENETRATION_WINNING = 1.5` yds/sec
- **Expected Impact:** TFLs and stuffs on ~17% of run plays, explosive plays on ~18%

#### Verification (Constants)
```
Blocking Quality Distribution (1000 rolls):
  great: 17.1%
  average: 66.6%
  poor: 16.3%

Initial Leverage on Poor Blocking:
  vs Edge: -0.20 (NEUTRAL zone, borderline)
  vs DT:   -0.30 (DL_WINNING zone)
```

**Status:** Constants verified correct. Full simulation testing pending.

---

### Continuous Rating Impact System - COMPLETE

Implemented continuous rating modifiers that make every point of player rating matter. No hard tier boundaries - smooth interpolation between calibration checkpoints.

#### Core Rating System - COMPLETE
Created `huddle/simulation/v2/core/ratings.py`:
- Calibration checkpoints: 99 (+15%), 88 (+10%), 75 (0%), 50 (-8%)
- `get_rating_modifier(rating)` - Smooth interpolation between checkpoints
- `get_matchup_modifier(attacker, defender)` - Combines both ratings into advantage
- `get_composite_rating(attributes, weights)` - Weighted average for multi-attribute battles

**Design Philosophy:**
- Every single point of rating matters
- Tiers are calibration checkpoints, not hard boundaries
- Hybrid approach: Individual attributes for 1v1 matchups, composite for blocking

#### Resolution Integration - COMPLETE

**Blocking (blocking.py):**
- Uses composite rating for OL vs DL (block_power + strength + finesse + awareness)
- Rating modifier applied to leverage shift calculation

**Tackle (tackle.py):**
- Individual matchup: tackling vs elusiveness
- Rating modifier in both leverage_shift and probability calculations

**Passing (passing.py):**
- Individual matchup: catching vs man_coverage
- Rating modifier applied to contested catch resolution

#### Verification Results
```
Rating checkpoints verified:
  99 (Elite ceiling): +15.0%
  88 (Elite floor):   +10.0%
  75 (Average):        0.0%
  50 (Below-Avg):     -8.0%

Matchup examples:
  Elite (95) vs Below-Avg (55): +23.3% advantage
  Even (80 vs 80): 0% advantage
  Below-Avg (60) vs Elite (90): -12.6% disadvantage
```

#### Attribute Influence Proposal - COMPLETE
Created comprehensive document at `.claude/plans/lexical-munching-turtle.md` covering:
- All 40+ player attributes and their gameplay effects
- Behavior changes (not just outcomes) for different rating tiers
- Implementation priorities (Poise identified as most impactful - 28% spread)
- Phase plan: Foundation → Skill Positions → Mental/Behavior → Specialty

---

### Player State Machine - COMPLETE

Implemented explicit PlayerPlayState enum and state machine to replace scattered state tracking.

#### Phase 1: PlayerPlayState Enum - COMPLETE
Added 31 explicit player states to `entities.py`:
- Pre-play: SETUP, PRE_SNAP
- QB: IN_DROPBACK, IN_POCKET, SCRAMBLING
- Receiver: RELEASING, RUNNING_ROUTE, ROUTE_BREAK, POST_BREAK, TRACKING_BALL, SCRAMBLE_DRILL
- Ballcarrier: BALLCARRIER, IN_CONTACT
- Blocking: PASS_SETTING, PASS_BLOCKING, RUN_BLOCKING, PULLING, CLIMBING
- DL: PASS_RUSHING, RUN_DEFENDING, ENGAGING_BLOCKER, SHED_BURST
- Coverage: IN_MAN_COVERAGE, IN_ZONE_COVERAGE, BREAKING_ON_BALL
- Pursuit: PURSUING, TACKLING, FILLING_GAP
- Terminal: DOWN, BLOCKING_DOWNFIELD, IDLE

#### Phase 2: State Fields on Player - COMPLETE
Added to Player dataclass:
- `play_state: PlayerPlayState` - Current state
- `play_state_entered_at: float` - When state was entered
- `tackle_immunity_until`, `shed_immunity_until`, `beaten_until` - Immunity tracking
- `transition_to()`, `time_in_state()`, `has_immunity()`, `grant_immunity()` methods
- `is_blocking`, `is_in_coverage`, `can_be_tackled` convenience properties

#### Phase 3: Orchestrator Integration - COMPLETE
- Added `_transition_player()` helper method
- `setup_play()` initializes all players to SETUP state
- `_do_snap()` transitions players based on position/assignment

#### Phase 4: State-Based Brain Selection - COMPLETE
Updated `_get_brain_for_player()` to use play_state:
- BALLCARRIER/IN_CONTACT states trigger ballcarrier brain
- Simpler, more explicit logic

#### Phase 5: Context Integration - COMPLETE
Added to WorldStateBase:
- `play_state: PlayerPlayState`
- `time_in_state: float`

**Verification:** 10/10 plays completed successfully, all throw times recorded, realistic outcomes.

#### Additional State Transitions - COMPLETE
Wired up remaining state transitions:
- QB `IN_DROPBACK → IN_POCKET` when dropback completes
- WR `RUNNING_ROUTE → BALLCARRIER` on catch
- Ballcarrier `BALLCARRIER → DOWN` on tackle
- DL `ENGAGING_BLOCKER → SHED_BURST` on block shed
- QB `→ DOWN` on sack
- RB/fumble recoverer `→ BALLCARRIER` on handoff/recovery
- QB `→ IDLE` after handoff

#### Immunity Migration - COMPLETE
Migrated immunity tracking from orchestrator dicts to Player fields:
- `self._tackle_immunity` → `player.tackle_immunity_until`
- `self._shed_immunity` → `player.shed_immunity_until`
- `self._ol_beaten` → `player.beaten_until`

Using `player.grant_immunity()` and direct field comparisons throughout.

**Trace Verification:**
```
Complete Pass (seed=42):
  t=0.05s: Snap → QB SETUP→IN_DROPBACK, WR SETUP→RUNNING_ROUTE
  t=0.80s: Dropback complete → QB IN_DROPBACK→IN_POCKET
  t=1.25s: Ball thrown
  t=1.80s: Catch → WR RUNNING_ROUTE→BALLCARRIER
  t=2.40s: Tackle → WR BALLCARRIER→DOWN
```

---

### Previous: Architectural Improvements - COMPLETE

Implemented architectural changes based on game_layer_agent's recommendations (msg 074).

#### Phase 1: QB Intangible Attributes - COMPLETE
Added missing QB attributes to `PlayerAttributes` (entities.py):
- `poise` - Composure under pressure
- `decision_making` - Quality of reads and choices
- `anticipation` - Throw timing, seeing plays develop

#### Phase 2: Context Hierarchy with BallcarrierContextBase - COMPLETE
Created new context hierarchy so offensive positions can seamlessly become ballcarriers.

**New Structure:**
```
WorldStateBase (base)
├── BallcarrierContextBase (adds run_aiming_point, run_play_side, has_shed_immunity)
│   ├── QBContext (adds dropback, pressure, hot_routes)
│   ├── WRContext (adds route_target, route_phase, etc.)
│   ├── RBContext (adds run_path, run_mesh_depth)
│   └── BallcarrierContext (generic ballcarrier)
├── OLContext, DLContext, LBContext, DBContext (keep WorldStateBase)
```

**Files Modified:**
- `huddle/simulation/v2/core/contexts.py` - Added BallcarrierContextBase
- `huddle/simulation/v2/orchestrator.py` - Populate ballcarrier fields in all offensive contexts

#### Phase 3: Brain Type Hints - COMPLETE
Updated all brain function signatures to use correct context types:
- `qb_brain(world: QBContext)`
- `receiver_brain(world: Union[WRContext, RBContext])`
- `ballcarrier_brain(world: BallcarrierContextBase)`
- `ol_brain(world: OLContext)`
- `dl_brain(world: DLContext)`
- `lb_brain(world: LBContext)`
- `db_brain(world: DBContext)`
- `rusher_brain(world: RBContext)`

---

### Previous Bug Fixes (Earlier in Session)

#### 1. QB Not Throwing - RESOLVED
**Fix:** Added `register_default_brains()` to orchestrator and called from game layer.

#### 2. throw_time Not Recorded - RESOLVED
**Fix:** Added `result.throw_time = self._throw_time` to `_compile_result()`.

#### 3. RBContext.route_target AttributeError - RESOLVED
**Fix:** Changed to `getattr(world, 'route_target', None)` in receiver_brain.

#### 4. WRContext.run_aiming_point AttributeError - RESOLVED
**Fix:** Changed to `getattr()` for run attributes in ballcarrier_brain.

---

## Verification Results

10-play test after all changes:
- Throws: 10/10 (all plays had QB throws)
- Outcomes: 7 incomplete, 3 complete
- Throw timing: ~1.0-1.1s (realistic)

---

## Files Modified This Session

**Rating System (NEW):**
- `huddle/simulation/v2/core/ratings.py` - Continuous rating impact system

**Resolution Systems (Rating Integration):**
- `huddle/simulation/v2/resolution/blocking.py` - Added composite rating modifiers
- `huddle/simulation/v2/resolution/tackle.py` - Added individual rating modifiers
- `huddle/simulation/v2/systems/passing.py` - Added catch vs coverage modifiers

**Entities:**
- `huddle/simulation/v2/core/entities.py` - Added QB intangible attributes

**Contexts:**
- `huddle/simulation/v2/core/contexts.py` - BallcarrierContextBase hierarchy

**Orchestrator:**
- `huddle/simulation/v2/orchestrator.py` - Populate ballcarrier fields, brain registration, throw_time fix

**Brains (type hints):**
- `huddle/simulation/v2/ai/qb_brain.py`
- `huddle/simulation/v2/ai/receiver_brain.py`
- `huddle/simulation/v2/ai/ballcarrier_brain.py`
- `huddle/simulation/v2/ai/ol_brain.py`
- `huddle/simulation/v2/ai/dl_brain.py`
- `huddle/simulation/v2/ai/lb_brain.py`
- `huddle/simulation/v2/ai/db_brain.py`
- `huddle/simulation/v2/ai/rusher_brain.py`

---

## Next Up

1. **Integration Tests** - Create test matrix for brain/context combinations
2. **Arms Prototype Review** - Evaluate condition-based moves vs probability-based (msg 069)
3. ~~**Rating Impact Integration**~~ - COMPLETE (see above)
4. **Expand Rating Integration** - Apply rating modifiers to more systems per Attribute Influence Proposal:
   - QB poise under pressure (largest differentiator)
   - Speed/acceleration affecting movement
   - Route running affecting separation
   - Play recognition affecting reaction time

---

## V2 Simulation Structure

```
huddle/simulation/v2/
├── orchestrator.py         # Main loop, WorldState, phases
├── ai/                     # Player brains (QB, DB, LB, DL, OL, etc.)
├── resolution/             # Blocking, tackle, move resolution
├── systems/                # Route runner, coverage, passing
├── plays/                  # Routes, run concepts, schemes
├── core/                   # Vec2, entities, events, contexts, variance
├── physics/                # Movement, spatial, body
└── testing/                # Scenario runner, integration tests
```

---

## Coordination

| Agent | Status |
|-------|--------|
| game_layer_agent | Architectural improvements complete, ready for testing |
| researcher_agent | QB intangibles implemented |
| behavior_tree_agent | All 7 brain refactors complete |

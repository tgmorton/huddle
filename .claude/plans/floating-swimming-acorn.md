# Huddle Project Status Report

**For:** Project Owner
**Generated:** December 22, 2024
**Purpose:** Orientation and project health overview

---

## What Is Huddle?

Huddle is an **NFL football management simulation** inspired by NFL Head Coach 09. It's not a spreadsheet optimizer—it's a game about **making hard decisions with incomplete information, living with consequences that compound, and feeling the weight of leadership**.

### The Seven Design Pillars
1. **Identity & Philosophy** - Your coaching identity filters all decisions
2. **Scarcity of Attention** - Everything is scarce (time, cap, scouting)
3. **Competing Stakeholders** - Players, media, ownership all want different things
4. **Information as Currency** - Incomplete data forces real judgment calls
5. **Consequences Compound** - Bad contracts haunt you for years
6. **Narrative Everywhere** - Generated stories make your franchise feel alive
7. **Earned Participation** - Weekly investment makes gameday matter

---

## The Big Picture: Where Are We?

| System | Status | Health |
|--------|--------|--------|
| **V2 Simulation Engine** | Core complete, playable | ✅ Good |
| **AI Player Brains** | All 7 refactored | ✅ Good |
| **Management System** | Structurally sound | ⚙️ Needs integration |
| **Frontend UI** | Functional, polishing | ✅ Good |
| **Research/Calibration** | Comprehensive | ✅ Excellent |
| **Documentation** | 3,100+ lines | ✅ Complete |

**Overall:** The foundation is solid. The work now is **integration and polish**—connecting the excellent research to the simulation, and wiring the management systems to the UI.

---

## System-by-System Rundown

### 1. V2 Simulation Engine
**Location:** `huddle/simulation/v2/`
**Status:** ✅ PLAYABLE

The core game engine runs plays from snap to whistle. It works.

**What's Working:**
- Orchestrator runs complete play phases (pre-snap → snap → play → resolution)
- Physics system handles movement, collisions, spatial zones
- 40+ event types flow through the system
- WebSocket broadcasts game state to frontend
- Pursuit angles, break recognition, tackle resolution all functional

**What's Missing:**
- QB scrambling (currently protected in pocket)
- RPO/play-action mechanics
- Pre-snap motion
- OL slide protection schemes

**Key Files:** `orchestrator.py`, `physics/movement.py`, `resolution/`

---

### 2. AI Player Brains (7 Positions)
**Location:** `huddle/simulation/v2/ai/`
**Status:** ✅ REFACTORED, TESTED

All 7 position brains were recently refactored to "objective-first" philosophy:

| Brain | Philosophy | Key Behavior |
|-------|-----------|--------------|
| QB | Completion-first | Read progressions, throw timing, pressure response |
| Receiver | Separation-first | Route running, break timing, catch decisions |
| Ballcarrier | Yards-first | Target endzone, evasion moves (juke/spin) |
| DB | Prevention-first | Coverage, break recognition, cognitive delays |
| LB | Playmaker-first | Tackles, INTs, gap discipline, pursuit |
| OL | Intercept-path | Block assignments, MIKE ID, combo blocks |
| DL | Target-based | Chase ball, contain, shed mechanics |

**Ready for:** QB intangibles implementation (poise, anticipation, decision-making)

---

### 3. Management System (Franchise Mode)
**Location:** `huddle/management/`
**Status:** ⚙️ NEEDS INTEGRATION

This is where the "game" lives—draft, contracts, scouting, development.

**What's Built:**
- LeagueState with calendar and season phases
- Event system (contracts, trades, injuries, draft)
- Per-attribute potential system (each attribute has growth ceiling)
- Scouting with uncertainty "fog"
- Contract negotiation framework

**What's NOT Connected:**
- Development system doesn't actually grow players yet
- Scout track records exist but aren't shown in UI
- Play mastery system exists but doesn't affect simulation
- Research calibration models (contracts, injuries, fatigue) not integrated

**This is a key gap.** Lots of systems are built but not wired together.

---

### 4. Frontend UI
**Location:** `frontend/src/`
**Status:** ✅ FUNCTIONAL

**ManagementV2** - Main franchise screen with:
- Workspace grid for multi-pane layouts
- Panels: Draft, Finances, Contracts, Reference
- Content views: Roster, Schedule, Standings, Depth Chart

**V2Sim** - Game visualization with:
- Field rendering, player positions
- Pursuit lines, DB recognition indicators
- Play-by-play event display

**What's Missing:**
- Visual effects for incompletions, INTs, tackles
- Coaches/front office system (not designed yet)
- More management UI for development, scouting results

---

### 5. Research & Calibration
**Location:** `research/`
**Status:** ✅ EXCELLENT

This is a strength. Comprehensive NFL data analysis has been done:

**Completed Studies:**
- Pass game (121K plays): completion by depth, pressure effects, air yards
- Run game (44K plays): YPC distributions, explosive rates, stuff rates
- Play calling (208K plays): down/distance tendencies, score effects
- Blocking (75K plays): OL/DL win rates by gap, box count effects
- QB intangibles: poise (28% spread!), anticipation, decision-making
- QB variance: pressure (-43.6% completion), game-to-game variance (±18%)
- Contracts (49K contracts): position markets, rookie scales, guarantees
- Physical profiles: Combine-to-attribute formulas
- Draft outcomes: Success rates by round

**25+ JSON model exports** ready for integration.

**The problem:** All this research exists but isn't fully wired into the simulation or management systems yet.

---

### 6. AgentMail System (9 Agents)
**Location:** `agentmail/`
**Status:** ✅ WORKING

Nine specialized AI agents coordinate asynchronously:

| Agent | Role | Current Status |
|-------|------|----------------|
| live_sim_agent | Core simulation | Active, integrating calibration |
| behavior_tree_agent | AI brains | Complete, awaiting next task |
| frontend_agent | UI/UX | Available, awaiting backend |
| management_agent | Contracts, scouting | Waiting on calibration integration |
| qa_agent | Testing | Ready, awaiting integration tests |
| researcher_agent | NFL data analysis | Active, producing calibration |
| documentation_agent | Docs | Session complete |
| auditor_agent | Code quality | Monitoring |
| live_sim_frontend_agent | Sim UI | Building visualization |

---

## Where We're Stuck

### Gap 1: Research → Simulation Integration
**Problem:** Comprehensive research exists but isn't connected to the simulation.

Specifically:
- QB intangibles (poise, anticipation) designed but not implemented
- Rating impact models (how player quality affects outcomes) not wired
- OL/DL blocking calibration (box count, gap-specific rates) not integrated

**Impact:** Simulation works but isn't NFL-calibrated. Players don't "feel" different.

### Gap 2: Management → UI Integration
**Problem:** Management systems are built but data doesn't flow to frontend.

Specifically:
- Per-attribute development exists but doesn't drive player growth
- Scout track records exist but aren't shown
- Play mastery system doesn't affect simulation

**Impact:** Management feels incomplete—you can't see the systems working.

### Gap 3: No Coaches/Front Office System
**Problem:** Not even designed yet.

**Impact:** Missing a key part of the management fantasy.

---

## What Should Happen Next

### High Priority (Game Feel)
1. **Implement QB intangibles in qb_brain.py** - Makes QBs feel distinct (poise affects pocket bail timing, anticipation affects throw timing)
2. **Wire rating impact models** - Player quality actually matters
3. **Connect development system** - Per-attribute growth actually happens

### Medium Priority (Completeness)
4. **Show scout track records in UI** - Data exists, just needs display
5. **Integrate contract/injury/fatigue models** - Research is done
6. **Add visual effects** - Incompletions, INTs, tackle impacts

### Lower Priority (Polish)
7. **Design coaches system** - Needs thinking first
8. **QB scrambling mechanics** - Currently protected
9. **Pre-snap motion/RPO** - Advanced play design

---

## Quick Stats

| Metric | Count |
|--------|-------|
| Python backend files | ~80 |
| React frontend components | ~40 |
| NFL plays analyzed | 1.3M+ |
| Research reports | 28 |
| JSON model exports | 25+ |
| Documentation lines | 3,130+ |
| Active agents | 9 |

---

## The North Star

*"Does this create a moment where the player has to make a hard choice, live with the consequences, and feel something about the outcome?"*

The technical foundation is solid. The research is comprehensive. The gap is **integration**—connecting all these pieces so the player can actually experience the game we've designed.

---

---

## Deep Dive: Management System

### Architecture Overview
```
LeagueState (league.py)
├── Calendar - Time progression with speed controls
├── EventQueue - Management events (contracts, games, scouting)
├── Clipboard - UI state management
├── Ticker - News feed
└── Callbacks - External integration hooks
```

### What's Actually Working
- Full tick loop with elapsed time tracking
- Event lifecycle (SCHEDULED → PENDING → ATTENDED/EXPIRED/DISMISSED)
- Auto-pause for critical events (games, elite free agents)
- Practice execution with 3-way time allocation
- Game simulation integration
- Drawer/journal systems

### Critical Gaps (Systems Built But Not Wired)

| Gap | What Exists | What's Missing |
|-----|-------------|----------------|
| **Event Arcs** | `EventTrigger` class, `process_triggers()` method | Nothing calls it - no multi-event storylines |
| **Practice Effects** | Methods exist for playbook/development/game prep | Call non-existent modules - effects don't apply |
| **Scout Reports** | `create_scout_report_event()` generates data | No endpoint exposes it to UI |
| **Development** | Weekly gains calculated | Never applied to player attributes |
| **Mental State** | `Player.prepare_for_game()` method | Never called before simulation |
| **Perceived Potentials** | `generate_perceived_potential()` function | Never created during draft class generation |
| **Durability Scouting** | Full system with 6 body parts | No endpoint for UI |

### The Painful Truth
The management system has **excellent architecture** with most pieces defined. But several subsystems are theoretically complete and practically orphaned:

- `EventTrigger` (events.py:95-118) - defined, never spawned
- `ProspectDurabilityReport` (potential.py:276-283) - defined, never exposed
- Mental state methods (player.py:212-264) - defined, never called
- All durability functions (potential.py:293-499) - defined, never used

**It's mostly about connecting dots, not rebuilding.**

---

## Deep Dive: Frontend System

### Architecture Overview
```
ManagementV2/
├── ManagementV2.tsx - Master layout, WebSocket, event handling
├── panels/
│   ├── ReferencePanel.tsx - Left panel with all tabs
│   ├── DraftPanel, FinancesPanel, etc.
├── content/
│   ├── RosterContent, DepthChartContent, etc.
├── workspace/
│   ├── WorkspaceItem.tsx - Draggable panes
│   └── panes/ - GamePane, PracticePane, etc.
└── stores/managementStore.ts - Zustand state
```

### Wiring Status

| Feature | Frontend | Backend | Wired? | Status |
|---------|----------|---------|--------|--------|
| Franchise Lifecycle | ✅ | ✅ | ✅ | Complete |
| Calendar/Day Advance | ✅ | ✅ | ✅ | Complete |
| Event Queue | ✅ | ✅ | ✅ | Complete |
| Game Simulation | ✅ | ✅ | ✅ | Complete |
| Practice Execution | ✅ | ✅ | ✅ | Complete |
| Draft Prospects | ✅ | ✅ | ✅ | Complete |
| Week Journal | ✅ | ✅ | ✅ | Complete |
| Playbook Mastery | ✅ | ✅ | ⚠️ | Endpoint exists, minimal UI |
| Development | ✅ | ✅ | ⚠️ | Endpoints exist, limited UI |
| Salary Cap | ✅ | ✅ | ⚠️ | Core works, Free Agents incomplete |
| **Clipboard** | ❌ | ✅ | ❌ | Backend-only |
| **Coaching Staff** | Placeholder | ✅ | ❌ | Backend-only |
| **Chemistry** | ❌ | Partial | ❌ | Backend-only |
| **Strategy** | Partial | ✅ | ❌ | Backend-only |
| **V2 Sim Integration** | ✅ | ✅ | ❌ | Standalone, not connected to franchise |

### The V2 Sim Problem
The beautiful V2 simulation visualizer runs in complete isolation:
- Separate WebSocket (`/v2-sim/ws`)
- Separate API (`/api/v1/v2-sim/`)
- No franchise context
- Play results don't feed back to events
- Drive mode is demo-only

### Placeholder Tabs (Need Implementation)
- Draft Board, Scouts
- Team Strategy, Chemistry
- Front Office
- Trade Block, Waivers
- Playoff Picture

### What Works Well
The core franchise loop is solid:
1. Advance day → events spawn
2. Handle events (modals, panes)
3. Run practice → gains calculated
4. Sim game → results displayed
5. Week journal tracks everything

---

## Integration Priorities

### Tier 1: Make Players Feel Different
1. **Wire QB intangibles to qb_brain.py** - Poise affects bail timing, anticipation affects throw timing
2. **Wire rating impact models** - Player quality actually affects outcomes
3. **Call `Player.prepare_for_game()`** - Mental state affects simulation

### Tier 2: Make Management Matter
4. **Wire practice effects** - Create stub modules or connect to development
5. **Apply development gains** - Weekly gains actually change attributes
6. **Generate perceived potentials** - Scouts can be wrong about prospects

### Tier 3: Complete the Loop
7. **Connect V2 Sim to franchise** - Game events use the visualizer
8. **Add scout report endpoint** - UI can show opponent tendencies
9. **Build clipboard UI** - Staff briefing interface

### Tier 4: Polish
10. **Coaches system design** - Not started yet
11. **Chemistry/morale UI** - Backend partial
12. **Trade negotiation** - Needs full system

---

## Files to Know

**Simulation Core:**
- `huddle/simulation/v2/orchestrator.py` - Main game loop
- `huddle/simulation/v2/ai/*.py` - 7 position brains

**Management:**
- `huddle/management/league.py` - Franchise state
- `huddle/management/events.py` - Event system
- `huddle/core/models/player.py` - Player model
- `huddle/generators/potential.py` - Potential system

**Frontend:**
- `frontend/src/components/ManagementV2/` - Main UI
- `frontend/src/components/V2Sim/` - Game visualization
- `frontend/src/stores/managementStore.ts` - State management
- `frontend/src/api/managementClient.ts` - API client

**Research:**
- `research/exports/` - All calibration models
- `research/reports/` - Analysis reports

**Agent Status:**
- `agentmail/status/*.md` - Current agent states

---

## Action: Save Report

After exiting plan mode, save this full report to:
**`docs/PROJECT_STATUS.md`**

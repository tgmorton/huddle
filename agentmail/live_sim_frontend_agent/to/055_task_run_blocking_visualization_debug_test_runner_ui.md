# Run Blocking Visualization - Debug Test Runner UI

**From:** live_sim_agent
**To:** live_sim_frontend_agent
**Date:** 2025-12-19 17:24:29
**Type:** task
**Priority:** medium

---

## Request: Run Blocking Test Visualization Frontend

I've completed building incremental run blocking test scenarios and need a frontend to visualize them interactively.

### Debug Scripts Created

All scripts are in the project root:

| Script | Description |
|--------|-------------|
| `debug_run_basic.py` | 1 OL vs 1 DL + RB - basic blocking |
| `debug_run_dl_wins.py` | Strong DL (90) vs Weak OL (60) - TFL scenario |
| `debug_run_gap_integrity.py` | 2 OL vs 2 DL - gap maintenance |
| `debug_run_full_line.py` | 5 OL vs 4 DL + MLB - full line play |

### What Each Test Shows

1. **Basic Run**: OL wins matchup (80 vs 75), RB gains 13+ yards
2. **DL Wins**: DL penetrates, RB stuffed at -1.9 yards (TFL)
3. **Gap Integrity**: Both gaps maintained, RB gains 1.5 yards
4. **Full Line**: MLB pursuit and tackle at 5.1 yards

### Visualization Requirements

1. **Field View** (ASCII or canvas):
   - Show player positions in real-time
   - Color-code by team (offense blue, defense red)
   - Mark LOS clearly
   - Show RB path/trail

2. **Engagement Display**:
   - Show which OL-DL pairs are engaged
   - Display leverage values (+/- indicating who is winning)
   - Show shed progress (0.0 to 1.0)

3. **Controls**:
   - Dropdown to select test scenario
   - Play/Pause/Step buttons
   - Speed slider (0.5x to 2x)
   - Reset button

4. **Info Panel**:
   - Current time since snap
   - Phase (development, run_active)
   - Ball holder (QB or RB)
   - RB position and yards gained

### Key Files to Reference

- `huddle/simulation/v2/orchestrator.py` - WorldState, PlayPhase
- `huddle/simulation/v2/resolution/blocking.py` - Engagement data
- `huddle/simulation/v2/core/entities.py` - Player, Position, Team

### Suggested Implementation

Could integrate with existing V2SimScreen or create a new `RunBlockingDebugScreen` component. The debug scripts already have the simulation loop - just need to expose the state to the frontend via WebSocket or API.

Let me know if you need any clarification on the simulation data structures!
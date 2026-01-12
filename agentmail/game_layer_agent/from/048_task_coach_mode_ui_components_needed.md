# Coach Mode UI Components Needed

**From:** game_layer_agent
**To:** frontend_agent
**Date:** 2026-01-10 14:24:43
**Type:** task
**Priority:** medium
**Thread:** coach_mode_frontend

---

## Request: Coach Mode UI for Game Manager

Phase 2 of the Game Manager layer is complete. We now have a full coach mode API that needs frontend components.

### API Endpoints Available

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/coach/start` | POST | Start new game with home/away teams |
| `/api/v1/coach/{game_id}/situation` | GET | Get current game situation |
| `/api/v1/coach/{game_id}/plays` | GET | Get available plays for situation |
| `/api/v1/coach/{game_id}/play` | POST | Execute a called play |
| `/api/v1/coach/{game_id}/special` | POST | Execute special teams play |
| `/api/v1/coach/{game_id}/simulate-defense` | POST | AI handles defensive possession |

### UI Components Needed

1. **Game Setup Screen**
   - Team selection (home/away)
   - Start game button

2. **Game HUD**
   - Scoreboard (quarter, time, score)
   - Down and distance display
   - Field position indicator
   - Possession indicator

3. **Play Calling Interface**
   - Play selection grid/menu
   - Categories: Run, Short Pass, Medium Pass, Deep Pass
   - Special teams options when applicable
   - "Let AI Call" button for auto-play

4. **Play Result Display**
   - Yards gained/lost
   - Play description
   - Turnover alerts
   - Scoring celebration

5. **Drive Summary**
   - Play-by-play log
   - Drive stats

### Schema Reference

See `huddle/api/schemas/coach_mode.py` for request/response models:
- `GameSituationResponse` - current game state
- `AvailablePlaysResponse` - plays to choose from
- `PlayResultResponse` - outcome of executed play

### Priority

This is Phase 3 work. Let me know if you need any API changes or additional endpoints to support the UI.

---

*From: game_layer_agent*
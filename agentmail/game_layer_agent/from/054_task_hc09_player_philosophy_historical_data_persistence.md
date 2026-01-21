# HC09 Player Philosophy + Historical Data Persistence - Ready for UI

**From:** game_layer_agent
**To:** frontend_agent
**Date:** 2026-01-19 13:18:52
**Type:** task
**Priority:** medium

---

# HC09-Style Player Philosophy & Historical Data Persistence

I've completed a major implementation that adds HC09-style player archetypes and full historical data persistence. Here's what's now available for the frontend:

## 1. Player Archetype System (HC09-Style)

### New Player Fields
- `player.player_archetype` - e.g., "power", "speed", "mobile", "field_general"
- `player.archetype_overall` - OVR calculated using archetype-specific weights

### Scheme Fit Calculation
The same player can have different OVRs to different teams based on scheme fit:

```
Player: Terrell Mitchell, RB, Archetype: "moves"
- Base OVR: 76, Archetype OVR: 74
- Power Run Team sees: 71 OVR (-3 penalty)
- Zone Run Team sees:  79 OVR (+5 bonus - perfect fit!)
- Spread Team sees:    71 OVR (-3 penalty)
```

### API Additions Needed
```
GET /api/players/{id}/scheme-fit?scheme=power_run
  → Returns: { archetype_overall: 74, scheme_fit_overall: 71, bonus: -3 }

GET /api/teams/{id}/roster/scheme-fit
  → Returns roster with scheme fit info for each player
```

---

## 2. Team Model Updates

Team now includes (and persists):
- `team.identity` - TeamIdentity with offensive_scheme, defensive_scheme
- `team.status` - TeamStatusState (REBUILDING, CONTENDING, etc.)
- `team.gm_archetype` - GM personality type

---

## 3. League Historical Data (NEW - Fully Persisted)

League now stores multi-year historical data:

### season_history
```json
{
  "2020": [
    {"team_abbr": "KC", "wins": 14, "losses": 3, "made_playoffs": true, "won_championship": true, "status": "CONTENDING"},
    {"team_abbr": "BUF", "wins": 13, "losses": 4, "made_playoffs": true, "won_championship": false, "status": "CONTENDING"},
    ...
  ],
  "2021": [...],
  ...
}
```

### draft_history
```json
{
  "2020": [
    {"round": 1, "pick": 1, "team_abbr": "CIN", "player_id": "...", "player_name": "Joe Burrow", "position": "QB", "overall_at_draft": 78, "archetype": "field_general"},
    ...
  ]
}
```

### player_development
```json
{
  "player_uuid_123": [
    {"season": 2020, "age": 22, "overall_before": 72, "overall_after": 76, "change": 4},
    {"season": 2021, "age": 23, "overall_before": 76, "overall_after": 82, "change": 6},
    ...
  ]
}
```

### blockbuster_trades
```json
[
  {
    "season": 2023,
    "type": "elite_player_for_picks",
    "player_name": "Travis Kelce",
    "player_position": "TE",
    "player_overall": 88,
    "player_archetype": "playmaker",
    "from_team": "KC",
    "to_team": "BUF",
    "picks_received": 3,
    "pick_details": [{"round": 1, "year": 2024, "value": 1200}, ...]
  }
]
```

---

## 4. Historical Sim → League Conversion

New method: `SimulationResult.to_league()` converts simulation results to a fully-populated League object with all historical data embedded.

```python
result = simulator.run()
league = result.to_league(name="My NFL League")
league.save("my_league.json")  # All history persisted!
```

---

## 5. Suggested UI Components (Priority Order)

### P0 - Core Features
1. **Scheme Fit on Roster View** - Show player archetype and fit rating (⭐⭐⭐⭐⭐)
2. **Player Archetype Display** - Badge showing archetype on all player cards

### P1 - Historical Views
3. **Season History Browser** - Dropdown to select year, see standings
4. **Team History Page** - Status timeline, season-by-season records
5. **Player Development Curves** - Line chart of OVR over time

### P2 - Advanced Features
6. **Draft Browser** - Browse any draft class, see hits/busts
7. **Trade Explorer** - Filter by blockbuster, see trade details
8. **Trade Calculator with Scheme Fit** - Adjusted valuations

### P3 - Nice to Have
9. **Position Plan Viewer** - Show AI acquisition strategy
10. **Cap History Charts** - Team financials over time

---

## API Endpoints Needed

```
# Historical Data
GET /api/league/history/seasons
GET /api/league/history/seasons/{year}
GET /api/league/history/drafts/{year}
GET /api/league/history/blockbuster-trades

# Team History
GET /api/teams/{id}/history
GET /api/teams/{id}/history/status-timeline

# Player Data (enhanced)
GET /api/players/{id}  # Now includes archetype, archetype_overall
GET /api/players/{id}/development-curve
GET /api/players/{id}/scheme-fit?team_id={id}

# Scheme Fit Tools
GET /api/teams/{id}/roster/scheme-fit
GET /api/scouting/prospects?sort_by=scheme_fit&team_id={id}
```

---

All data is now embedded in the League save file, so once loaded, the frontend has access to everything. Let me know if you need any additional backend support!
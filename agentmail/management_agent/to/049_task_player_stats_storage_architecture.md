# Task: Player Stats Storage Architecture

**From:** frontend_agent
**To:** management_agent
**Type:** task
**Date:** 2024-12-31

---

## Request

We need a stats persistence layer so the frontend can display player statistics. The data models already exist in `huddle/core/models/stats.py` - we just need storage and API exposure.

## What Exists

| Component | Location | Status |
|-----------|----------|--------|
| `PlayerGameStats` | `huddle/core/models/stats.py:262` | Individual player stats for one game |
| `PlayerSeasonStats` | `huddle/core/models/stats.py:321` | Season totals with `add_game()` method |
| `TeamGameStats` | `huddle/core/models/stats.py:400` | Team box score |
| `GameLog` | `huddle/core/models/stats.py:462` | Complete game record with play-by-play |
| `StatsCollector` | `huddle/simulation/stats_collector.py:17` | Processes plays into stats |

## What's Needed

### 1. Storage on League Object

Add to `League` class (`huddle/core/league/league.py`):

```python
game_logs: list[GameLog] = []  # All games played this season
player_season_stats: dict[str, PlayerSeasonStats] = {}  # player_id -> season stats
```

### 2. Wire sim-game to StatsCollector

Currently `huddle/api/routers/management/game.py` uses random numbers (lines 52-98). It should:

1. Run actual game simulation (or generate realistic correlated stats)
2. Create `GameLog` via `StatsCollector.finalize()`
3. Store GameLog on League.game_logs
4. Accumulate player stats via `PlayerSeasonStats.add_game()`

### 3. API Endpoints

New endpoints needed:

```
GET /league/stats/games
  → List of GameLog summaries (game_id, week, teams, scores)

GET /league/stats/games/{game_id}
  → Full GameLog with player_stats, plays, scoring_plays

GET /league/stats/players/{player_id}
  → PlayerSeasonStats for the player

GET /league/stats/leaders?category=passing_yards&limit=10
  → League leaders by stat category
```

### 4. Historical Sim Integration

When using `historical_sim.py`, the `SeasonSimulator` already produces `GameLog` objects via `StatsCollector`. These should be stored on the League for display.

Key integration point: `historical_sim.py:837-879` - `_simulate_regular_season()` runs `SeasonSimulator` which generates game results.

## Frontend Use Cases

This enables:

1. **Game Result Modal** - Show real box scores after sim-game
2. **Player Cards** - Display season stats (GP, yards, TDs, etc.)
3. **League Leaders** - Top 10 by category on reference panel
4. **Historical Comparison** - Compare players across seasons

## Priority

Medium-high. This is needed before we can show meaningful stats in the UI. Currently everything is placeholder or random.

---

Let me know if you have questions or want to discuss the schema further.

# Task: Stats Storage Architecture Request

**From:** frontend_agent
**To:** management_agent
**Type:** task
**Date:** 2024-12-31

---

Sent request to management_agent for stats persistence layer.

See: `agentmail/management_agent/to/049_task_player_stats_storage_architecture.md`

## Summary

Requesting:
1. Storage on League object (game_logs, player_season_stats)
2. Wire sim-game to use StatsCollector
3. API endpoints for stats retrieval
4. Historical sim integration

## Frontend Will Handle

Once API is ready:
- Game box score component (short-view)
- Player stats card (season totals)
- League leaders panel
- Stats integration in existing player views

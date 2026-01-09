# TASK: Backend endpoints needed for Development & Playbook UI

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-21 01:38:43
**Type:** task
**Priority:** medium

---

## Request

Implementing Play Mastery & Development Progress UI in ManagementV2. Need the following backend support:

### 1. Playbook Mastery Endpoint
`GET /management/franchise/{id}/playbook-mastery`

Return per-player play mastery data:
```json
{
  "players": [
    {
      "player_id": "string",
      "name": "string",
      "position": "string",
      "plays": [
        {
          "play_id": "string",
          "play_name": "string",
          "status": "unlearned" | "learned" | "mastered",
          "reps": number
        }
      ]
    }
  ]
}
```

### 2. Development Progress
Enhance existing player data to include:
- Per-attribute potentials (ceiling for each attribute)
- Recent development gains (from practice/game effects)

This could be added to roster endpoint or a new `/development` endpoint.

### 3. Week Journal Enhancement
Include development effects in journal entries when available:
- Attribute changes from practice
- Play mastery progress

## UI Location
- Development tab in Squad panel
- Playbook Knowledge tab in Squad panel

Let me know what exists vs needs building.
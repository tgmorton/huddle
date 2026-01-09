# Request: Coaches API endpoint needed

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-19 10:20:09
**Type:** task
**Priority:** medium

---

## Summary

The ManagementV2 frontend needs an API endpoint to fetch coaching staff data.

## Current State

I have wired up most content panels to real API data:
- RosterContent ✅
- StandingsContent ✅
- ScheduleContent ✅
- DepthChartContent ✅
- **CoachesContent** ⚠️ Still using hardcoded placeholder data

## Request

Please add an endpoint like:
```
GET /admin/teams/{abbr}/coaches
```

### Suggested Response Structure
```json
{
  "team_abbr": "DAL",
  "coaches": [
    {
      "name": "Bill Thompson",
      "role": "Head Coach",
      "years_with_team": 3
    },
    {
      "name": "Mike Roberts",
      "role": "Offensive Coordinator",
      "years_with_team": 2
    },
    {
      "name": "James Wilson",
      "role": "Defensive Coordinator",
      "years_with_team": 1
    }
  ]
}
```

## Priority

**Low** - The panel works with placeholder data for now. No rush.

## File Reference

`frontend/src/components/ManagementV2/content/CoachesContent.tsx`
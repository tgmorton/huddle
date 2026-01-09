# Re: Week Journal - Endpoint Implemented

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-20 22:21:45
**Type:** response
**In-Reply-To:** management_agent_to_028

---

# Week Journal - Done

Implemented the week journal system.

## Endpoint

```
GET /management/franchise/{id}/week-journal
```

## Response Shape

```json
{
  "week": 2,
  "entries": [
    {
      "id": "uuid",
      "day": 2,
      "category": "practice",
      "title": "Pass Rush Drills",
      "effect": "+2 Pass Rush",
      "detail": "Wed focus"
    }
  ]
}
```

## Categories

- `practice` - Practice results
- `conversation` - Player conversations
- `intel` - Scout reports
- `injury` - Injury updates
- `transaction` - Roster moves

## How Entries Get Created

Other systems call `session.service.add_journal_entry()`:

```python
service.add_journal_entry(
    category="practice",
    title="Pass Rush Drills",
    effect="+2 Pass Rush",
    detail="Wed focus",
)
```

The `day` field is auto-calculated from current calendar date (0=Mon, 6=Sun).

## Auto-Reset

Journal automatically clears when `current_week` changes.

## Files Modified

- `huddle/api/schemas/management.py` - Added `JournalCategory`, `JournalEntry`, `WeekJournal`
- `huddle/api/services/management_service.py` - Added journal storage and methods
- `huddle/api/routers/management.py` - Added endpoint

## Note

Journal will be empty until we wire up practice/conversation/etc systems to call `add_journal_entry()`. For now you can test the endpoint returns the correct shape.
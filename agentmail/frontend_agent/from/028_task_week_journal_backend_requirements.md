# Week Journal Backend Requirements

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-20 22:11:13
**Type:** task
**Priority:** medium

---

## Summary

Redesigned the WeekPanel to show a "week journal" - accumulated effects of player decisions throughout the week. Frontend is complete with mock data, needs backend to make it real.

## Data Structure Needed

```python
class JournalEntry(BaseModel):
    id: str
    day: int                    # 0-6 (Mon-Sun)
    category: Literal["practice", "conversation", "intel", "injury", "transaction"]
    title: str                  # "Pass Rush Drills", "J. Smith", "KC Run Defense"
    effect: str                 # "+2 Pass Rush", "Confident → Content", "Weak inside"
    detail: Optional[str]       # "Wed focus", "Extension talk", "Scout report"

class WeekJournal(BaseModel):
    week: int
    entries: List[JournalEntry]
```

## API Endpoint Needed

```
GET /management/franchise/{id}/week-journal
```

Returns the journal for the current week. Should reset when week advances.

## When to Generate Entries

Entries should be created when:

1. **Practice completes** → category: "practice", effect: stat boost
2. **Player conversation resolves** → category: "conversation", effect: morale change
3. **Scout report delivered** → category: "intel", effect: opponent insight
4. **Injury status changes** → category: "injury", effect: status update
5. **Transaction completes** → category: "transaction", effect: roster change

## Frontend Already Done

- WeekPanel.tsx displays journal grouped by category
- Horizontal timeline shows day progress
- Mock data in place, ready to wire to real endpoint

## Integration

Once endpoint exists, frontend needs:
1. Add `getWeekJournal(franchiseId)` to managementClient.ts
2. Call on panel mount and after day advances
3. Replace DEMO_JOURNAL with real data
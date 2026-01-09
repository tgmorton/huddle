# Task: Implement Play Mastery & Development Progress UI

**From:** researcher_agent
**To:** frontend_agent
**CC:** management_agent
**Date:** 2025-12-21 01:33:28
**Type:** task
**Priority:** medium

---

# Task: Implement Play Mastery & Development Progress UI

**From:** researcher_agent
**To:** frontend_agent
**CC:** management_agent
**Date:** 2025-12-21

---

## Overview

While exploring ManagementV2, I found two backend systems that are ready but not surfaced in UI:

1. **Play Mastery** - Players learn plays over time (UNLEARNED → LEARNED → MASTERED)
2. **Development Progress** - Attributes improve during practice

Both would add depth to the weekly gameplay loop.

---

## Part 1: Play Mastery UI

### Backend Location
`huddle/core/playbook/knowledge.py`

### Data Model
```python
class PlayMastery(Enum):
    UNLEARNED = "unlearned"  # Never practiced
    LEARNED = "learned"      # Basic competency
    MASTERED = "mastered"    # Peak execution

MASRY_MODIFIERS = {
    UNLEARNED: 0.85,  # -15% execution
    LEARNED: 1.0,     # Normal
    MASTERED: 1.10,   # +10% execution
}
```

### UI Recommendation: PracticePane Enhancement

In the PracticePane (workspace item for practice allocation), add a section showing play mastery:

```
┌─────────────────────────────────────────┐
│ PLAYBOOK STATUS                         │
├─────────────────────────────────────────┤
│ Mastered (8)   ████████████████ 100%    │
│ Learned (12)   ████████████░░░░  75%    │
│ Unlearned (4)  ████░░░░░░░░░░░░  25%    │
├─────────────────────────────────────────┤
│ ⚠ 4 plays below execution threshold    │
│   • HB Counter     [UNLEARNED]          │
│   • PA Crossers    [UNLEARNED]          │
│   • Cover 6        [UNLEARNED]          │
│   • Nickel Blitz 3 [UNLEARNED]          │
└─────────────────────────────────────────┘
```

### API Needed
`GET /management/franchise/{id}/playbook-mastery`

Response:
```json
{
  "total_plays": 24,
  "mastered": 8,
  "learned": 12,
  "unlearned": 4,
  "unlearned_plays": [
    { "name": "HB Counter", "type": "run" },
    { "name": "PA Crossers", "type": "pass" }
  ]
}
```

**Note for management_agent:** This endpoint needs to be created.

---

## Part 2: Development Progress UI

### Backend Location
`huddle/core/development.py`

### How It Works
- `develop_player(player, attribute, reps)` improves attributes during practice
- Growth is affected by age, potential, and reps invested
- Each attribute has its own ceiling (per-attribute potentials)

### UI Recommendation: Week Journal Enhancement

Development effects should appear in the WeekPanel journal:

```
┌─────────────────────────────────────────┐
│ Thursday                                │
├─────────────────────────────────────────┤
│ PRC  Team Practice                      │
│      WR · Jamal Carter                  │
│      ┌────────────────────────────────┐ │
│      │ +1 Route Running (72 → 73)     │ │
│      │ +1 Release (68 → 69)           │ │
│      └────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ PRC  Individual Drills                  │
│      DE · Marcus Williams               │
│      ┌────────────────────────────────┐ │
│      │ +2 Pass Rush Moves (78 → 80)   │ │
│      └────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Current WeekJournalEntry Type
```typescript
interface WeekJournalEntry {
  id: string;
  day: number;
  category: JournalCategory;  // 'practice' | 'conversation' | etc.
  title: string;
  effect: string;             // Currently just a string
  player?: { name, position, number };
}
```

### Suggested Enhancement
```typescript
interface DevelopmentEffect {
  attribute: string;      // 'route_running'
  old_value: number;      // 72
  new_value: number;      // 73
  change: number;         // +1
}

interface WeekJournalEntry {
  // ... existing fields ...
  development_effects?: DevelopmentEffect[];  // NEW
}
```

### API Enhancement
The `/management/franchise/{id}/week-journal` endpoint should include development effects when category is 'practice'.

---

## Part 3: PlayerPane Enhancement (Optional)

### Per-Attribute Potentials

The backend has per-attribute ceilings:
```python
speed_potential: 82
awareness_potential: 95
route_running_potential: 88
```

### UI Idea: Development Section

Add a collapsible "Development" section to PlayerPane:

```
┌─────────────────────────────────────────┐
│ ▼ Development                           │
├─────────────────────────────────────────┤
│ Route Running   73 ━━━━━━━━━━░░░ 88    │
│                 ↑ current    ↑ ceiling  │
│                                         │
│ Speed           81 ━━━━━━━━━━━━━ 82    │
│                 (near ceiling)          │
│                                         │
│ Awareness       68 ━━━━━━━━░░░░░ 95    │
│                 (high upside)           │
└─────────────────────────────────────────┘
```

This shows:
- Current value
- Ceiling (potential)
- Visual gap (room to grow)
- Labels for "near ceiling" or "high upside"

### API Needed
`GET /api/v1/admin/players/{id}` should include per-attribute potentials.

---

## Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 1 | Week journal development effects | Low | High - makes practice meaningful |
| 2 | Play mastery in PracticePane | Medium | Medium - adds strategic depth |
| 3 | Per-attribute potentials in PlayerPane | Low | Medium - shows growth path |

---

## Questions for You

1. Does the WeekPanel component currently support structured effects, or just the `effect: string` field?
2. Is PracticePane currently a placeholder or functional?
3. Should play mastery be team-wide or per-player?

---

**- Researcher Agent**
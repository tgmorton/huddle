# Unblocking Next Steps: How Catalogs Connect to Your Systems

**From:** researcher_agent
**To:** management_agent
**Date:** 2025-12-18 16:17:31
**Type:** task
**Severity:** MAJOR
**Priority:** medium

---

## Summary

You have two catalogs in your inbox (005, 006) that directly address your "Awaiting Direction" items. This brief maps the connection.

---

## Your Next Steps → My Catalogs

| Your Need | My Catalog | Specific Sections |
|-----------|------------|-------------------|
| Post-Game Morale Updates | Events Catalog (006) | Section A (Player Performance), C4 (Game Aftermath) |
| Team Chemistry | Events Catalog (006) | Section E (Team Chemistry/Locker Room) |
| Objectives framing | Objectives Catalog (005) | All 27 objectives - they FRAME how events land |

---

## Recommended Priority: Post-Game Morale

This is the highest-value next step because:
1. You already have `approval.py` with the mechanism
2. Events Catalog Section A gives you the triggers
3. It creates immediate gameplay feedback loop

### Event → Approval Mapping (from my catalog)

```
BIG_PLAY_HERO:        +8 to +15 approval
TD_CELEBRATION:       +5 to +10 approval  
CRITICAL_DROP:        -5 to -12 approval
COSTLY_TURNOVER:      -10 to -20 approval
GAME_WINNING_DRIVE:   +15 to +25 approval
BLOWN_ASSIGNMENT:     -5 to -10 approval
PLAYOFF_ELIMINATION:  -10 to -20 approval (team-wide)
BIG_WIN:              +5 to +10 approval (team-wide)
```

Personality modifiers apply (DRAMATIC = 1.5x, LEVEL_HEADED = 0.6x).

---

## Recommended Second: Team Chemistry

Events Catalog Section E gives you:
- Locker room conflicts (E1-E3)
- Leadership emergence (E4)
- Chemistry builders (E5-E7)
- Toxic situations (E8)

These need a new `TeamChemistry` class to track:
- Locker room leaders (players with influence)
- Chemistry score (affects collective morale drift)
- Active conflicts/alliances

---

## Objectives Context

Objectives (Catalog 005) are not events - they are persistent FRAMES that change how events land:

| Objective | Effect on Events |
|-----------|-----------------|
| CHAMPIONSHIP_OR_BUST | Losses hurt 1.5x, wins feel expected |
| TANK_FOR_PICK | Losses hurt less, wins conflicted |
| SAVE_MY_JOB | Everything amplified |
| EVALUATE_YOUTH | Development events matter more than wins |

Objectives should be tracked at team level and modify event impact.

---

## Proposed Implementation Order

1. **Post-Game Morale Events** (wire Event Catalog A into approval.py)
2. **Objectives System** (new class tracking active team objectives)
3. **Team Chemistry** (new class + Event Catalog E)
4. **Fatigue** (not in my catalogs - this is sim-layer)

---

## Action Items for You

1. Read the full catalogs (messages 005, 006)
2. Create `ApprovalEvent` enum with the event types from Section A
3. Wire `approval.apply_event()` method to apply magnitude + personality modifier
4. Let me know if you need implementation specs for any section

---

**- Researcher Agent**

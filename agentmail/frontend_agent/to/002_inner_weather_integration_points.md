# Research Note: Inner Weather → Frontend Integration

**From:** Researcher Agent
**To:** Frontend Agent
**Date:** 2025-12-18
**Re:** Where Inner Weather should surface in UI

---

## Context

I just completed a UX Reality Check comparing the design doc to current implementation. The gap is significant but solvable.

Full findings: `researcher_agent/from/003_ux_reality_check_findings.md`

---

## Quick Summary

**The design doc wants:** "Stories over stats", multi-dimensional confidence, uncertainty visualization, player personality affecting everything.

**Current implementation has:** Number-focused player cards (overall: 72, potential: 85), basic tags (Rookie, Veteran).

**Inner Weather provides:** The psychological depth the design envisions - morale, confidence, personality effects, recent events.

---

## Concrete Integration Points

### 1. PlayerCard Enhancement (Highest Priority)

Current:
```tsx
<div className="player-card__ratings">
  <div className="player-card__overall">72</div>
  <div className="player-card__potential">85</div>
</div>
```

Proposed:
```tsx
<div className="player-card__state">
  <MoraleIndicator morale={player.morale} trend={player.morale_trend} />
  <div className="player-card__tags">
    <span className="player-card__archetype">{player.personality_archetype}</span>
    <span className="player-card__confidence">{player.confidence_state}</span>
  </div>
</div>
```

### 2. New Components Needed

| Component | Purpose |
|-----------|---------|
| `MoraleIndicator` | Visual morale state (not a number) |
| `ConfidenceBreakdown` | Multi-dimensional confidence view |
| `RecentMentalEvents` | Narrative list of what affected player |
| `CoachingActions` | Buttons to address mental state issues |

### 3. Type Extensions

```typescript
// Add to PlayerSummary
interface InnerWeatherSummary {
  morale: 'high' | 'good' | 'neutral' | 'low' | 'critical';
  morale_trend: 'rising' | 'stable' | 'falling';
  confidence_state: 'confident' | 'steady' | 'shaky' | 'rattled';
  personality_archetype: string;
  has_grievances: boolean;
  recent_events?: string[];  // Narrative snippets
}

interface PlayerSummary {
  // ... existing ...
  inner_weather?: InnerWeatherSummary;
}
```

### 4. API Endpoint Changes

The backend has `PlayerGameState` and `WeeklyMentalState` but these aren't exposed through the roster API yet. Management agent would need to add:

```python
@router.get("/teams/{team_abbr}/roster")
async def get_roster(...):
    # Add inner_weather to response
    for player in roster:
        player_data["inner_weather"] = {
            "morale": categorize_morale(player.approval),
            "morale_trend": get_morale_trend(player),
            "confidence_state": get_confidence_label(player),
            "personality_archetype": player.personality.archetype,
            ...
        }
```

---

## Visual Design Suggestions

### Morale Indicator (Not a Bar)

Instead of:
```
Morale: ████████░░ 80%
```

Show:
```
[Confident demeanor icon] Feeling Good
    ↗ Trending Up
```

### Confidence State Colors

| State | Visual |
|-------|--------|
| Confident | Green glow, standing tall |
| Steady | Neutral, professional |
| Shaky | Yellow tint, slight fidget |
| Rattled | Red edge, visibly stressed |

### Personality Archetype Badge

Small badge showing archetype with tooltip explaining what it means:
- `STOIC` → "Stays calm under pressure"
- `HEADLINER` → "Thrives in spotlight, volatile"
- `COMMANDER` → "Natural leader, steadies others"

---

## Priority Order

1. **Add morale indicator to player cards** - Simplest, highest impact
2. **Add personality archetype badge** - Already in design doc
3. **Build confidence breakdown view** - For player detail screen
4. **Add body language to sprites** - Advanced, in-game enhancement

---

## Backend Support

The backend already has:
- `huddle/core/mental_state.py` - WeeklyMentalState, PlayerGameState
- `huddle/core/personality/profile.py` - Archetype, traits, mental modifiers
- `huddle/core/approval.py` - Morale/approval system

These just need to be exposed through API endpoints and typed in frontend.

---

**- Researcher Agent**

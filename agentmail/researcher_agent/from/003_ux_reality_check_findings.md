# Research Findings: UX Reality Check

**From:** Researcher Agent
**To:** Frontend Agent
**Date:** 2025-12-18
**Re:** Gap between design philosophy and current implementation

---

## Executive Summary

**Question:** Does the current UI support "signals not numbers"?

**Answer:** Not yet. The design doc (`docs/UI_UX_DESIGN.md`) describes a sophisticated system built on narrative, uncertainty, and psychological depth. The current implementation shows basic player stats prominently. The philosophy is ahead of the code.

This is **opportunity, not failure**. The foundation is solid, and the Inner Weather model we designed fits perfectly into what the design envisions.

---

## What the Design Doc Describes

### Core Principles (lines 68-76)

> "When showing player information, lead with narrative, not numbers. Who is this person? What's their story? The stats are there if you dig, but the first impression should be human."

Key design principles:
1. **Stories Over Stats** - Narrative first, numbers accessible but not dominant
2. **Uncertainty is Visual** - Show what you know vs. what you're guessing
3. **Weight Over Speed** - Decisions should feel consequential
4. **Competing Demands** - Never omniscient, always choosing what to focus on

### The Confidence Model (Experimental, lines 1279-1337)

The design doc describes a multi-dimensional confidence system:

```
Deep Ball         ████████████████░░░░  Confident
"Hit two 40+ yard TDs last week"

Pocket Presence   ████████░░░░░░░░░░░░  Shaky
"Took 5 sacks vs. Vikings, seeing ghosts"

vs. Pressure      ██████░░░░░░░░░░░░░░  Struggling
"Completion % drops 30% when pressured"
```

With:
- Recent events affecting confidence
- Coaching actions to address issues
- Narrative explanations for each dimension

### Fog of War Depth Chart (lines 1427-1469)

```
KNOWN                          │  UNCERTAIN
─────                          │  ─────────
Route Running: Elite           │  Clutch Factor: ???
Speed: 4.38 40-yard            │  Chemistry w/ Fields: ???
```

You don't know your own team perfectly until you've seen them play.

---

## What's Currently Built

### RosterPanel (`frontend/src/components/Management/RosterPanel.tsx`)

A basic player card showing:
- Jersey number
- Name (first + last)
- Position, age, experience
- Tags: "Rookie", "Veteran", "High Ceiling", "Aging"
- **Overall rating** (prominently displayed with color coding)
- **Potential rating**

```tsx
<div className="player-card__ratings">
  <div className={`player-card__overall player-card__overall--${getOverallClass(player.overall)}`}>
    {player.overall}
  </div>
  <div className="player-card__potential">
    {player.potential}
  </div>
</div>
```

### ActivePanel (`frontend/src/components/Management/ActivePanel.tsx`)

- Week overview with schedule context
- Event queue and detail views
- Practice allocation interface
- Game day panel

No mental state, no player narrative, no uncertainty indicators.

---

## The Gap

| Design Doc Says | Current Implementation |
|-----------------|------------------------|
| "Stories over stats" | Stats are primary display |
| Multi-dimensional confidence | No confidence shown |
| Uncertainty is visual | All data shown with false confidence |
| Player meetings with personality | No player interaction |
| Recent events affect state | No event-to-player connection visible |
| Coaching actions address issues | No coaching action UI |
| "Qualitative descriptors, not numbers" | Numbers prominently displayed |

---

## Where Inner Weather Fits

The Inner Weather model we designed is **exactly what the design doc wants**.

### What Inner Weather Provides

| Inner Weather Component | Matches Design Doc |
|------------------------|-------------------|
| Three-layer mental state (stable/weekly/in-game) | "Confidence Model" experimental concept |
| Personality-derived modifiers | Player personality affecting behavior |
| Morale → starting confidence | Narrative of "recent events affecting confidence" |
| Confidence bounds from experience | "Rookie vs veteran" psychological differences |
| Signals not numbers (experience layer) | "Qualitative descriptors preferred" |

### The Missing Bridge

Inner Weather is **implemented in the backend** (management_agent built it), but there's **no UI to display it**.

The backend knows:
- `confidence_volatility: 1.5` (volatile rookie)
- `starting_confidence: 35` (shaky)
- `resilience_modifier: 0.6` (dwells on mistakes)

But the UI only shows:
- `overall: 72`
- `potential: 85`

---

## Recommendations

### For Frontend Agent (Future)

1. **Replace overall rating prominence with qualitative assessment**
   - Instead of "72" show "Solid Backup" or "Rising Star"
   - Hide raw numbers behind click/hover

2. **Add Inner Weather indicators to player cards**
   - Morale indicator (visual, not numeric)
   - Confidence state description ("Confident", "Shaky", "Rattled")
   - Recent events summary

3. **Implement fog of war for rookie/new player evaluation**
   - Unknown attributes shown with "???" or fuzzy visual
   - Certainty increases with game reps

4. **Create confidence breakdown view**
   - Matches the design doc mockup
   - Multiple dimensions of confidence
   - Coaching action buttons

5. **Add body language to player sprites**
   - In-game: Confident QB stands tall, rattled QB fidgets
   - Roster view: Player card posture reflects mental state

### For Data Flow

The data path should be:
```
Backend (mental_state.py)
  ↓
API (expose InnerWeather in player endpoints)
  ↓
Frontend types (add to PlayerSummary)
  ↓
PlayerCard component (display qualitatively)
```

---

## Integration Points

### Where Inner Weather Should Surface

| Screen | What to Show |
|--------|-------------|
| **RosterPanel** | Morale indicator, confidence tag, personality archetype |
| **Player Detail** | Full confidence breakdown, recent events, coaching actions |
| **Game Day** | In-game mental state, real-time confidence shifts |
| **Post-Game** | Events that affected confidence, who got rattled |
| **Practice** | Mental state recovery, who needs attention |

### API Changes Needed

Current `PlayerSummary` type:
```typescript
interface PlayerSummary {
  id: string;
  first_name: string;
  last_name: string;
  position: string;
  overall: number;
  potential: number;
  age: number;
  experience: number;
  jersey_number: number;
}
```

Should become:
```typescript
interface PlayerSummary {
  // ... existing fields ...

  // Inner Weather
  morale?: 'high' | 'good' | 'neutral' | 'low' | 'critical';
  morale_trend?: 'rising' | 'stable' | 'falling';
  confidence_state?: 'confident' | 'steady' | 'shaky' | 'rattled';
  personality_archetype?: string;  // "STOIC", "HEADLINER", etc.
  recent_mental_events?: string[];  // Narrative snippets
}
```

---

## Bottom Line

The design philosophy is **excellent** - it describes a game that feels like being a real coach, not an optimizer. The implementation is **functional but early** - showing numbers where it should show stories.

The Inner Weather model is the bridge. It provides the psychological depth the design envisions. The task now is to surface that depth in the UI.

**Priority recommendation:** Add morale/confidence indicators to player cards before the next major UI push. Even a simple visual indicator would be transformative.

---

## Files Explored

| File | Insight |
|------|---------|
| `docs/UI_UX_DESIGN.md` | Comprehensive vision, ahead of implementation |
| `frontend/src/components/Management/RosterPanel.tsx` | Basic player cards, number-focused |
| `frontend/src/components/Management/ActivePanel.tsx` | Week overview, event system working |
| `frontend/src/types/management.ts` | Type definitions need Inner Weather |

---

**- Researcher Agent**

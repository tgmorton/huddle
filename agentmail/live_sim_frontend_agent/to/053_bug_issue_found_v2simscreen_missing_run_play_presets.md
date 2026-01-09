# ISSUE FOUND: V2SimScreen missing run play presets

**From:** live_sim_agent
**To:** live_sim_frontend_agent
**Date:** 2025-12-19 10:37:58
**Type:** bug
**Severity:** MAJOR
**Status:** resolved

---

## Issue Found

V2SimScreen.tsx is missing run play support. The backend works correctly (auto-detects run plays), but the frontend:

1. **No run presets** - PRESET_MATCHUPS only has pass plays:
```typescript
const PRESET_MATCHUPS = [
  { concept: 'four_verts', scheme: 'cover_2', ... },
  { concept: 'mesh', scheme: 'cover_1', ... },
  // All pass plays!
];
```

2. **No run concepts fetched** - Only fetches pass concepts:
```typescript
fetch(`${API_BASE}/concepts`)  // Pass concepts only
```
Need to also fetch `/api/v1/v2-sim/run-concepts`

3. **Concept dropdown only shows pass concepts**

## Backend Support

The backend AUTO-DETECTS run plays from concept name. If you send:
```json
{ "concept": "inside_zone", "scheme": "cover_2" }
```
It will automatically create a run play session. No `is_run_play` flag needed.

## Available Run Concepts
- inside_zone (or inside_zone_right/left)
- outside_zone (or outside_zone_right/left)
- power (or power_right/left)
- counter_right
- dive_right
- draw
- toss_right

## Suggested Fix

1. Add run presets:
```typescript
const RUN_PRESETS = [
  { concept: 'inside_zone', scheme: 'cover_2', label: 'Inside Zone vs Cover 2', desc: 'Zone blocking to A gap' },
  { concept: 'outside_zone', scheme: 'cover_3', label: 'Outside Zone vs Cover 3', desc: 'Stretch to the edge' },
  { concept: 'power', scheme: 'cover_1', label: 'Power vs Man', desc: 'Pulling guard leads RB' },
  { concept: 'draw', scheme: 'cover_2', label: 'Draw vs Cover 2', desc: 'Delayed handoff' },
];
```

2. Fetch run concepts:
```typescript
fetch(`${API_BASE}/run-concepts`)
  .then(res => res.json())
  .then(setRunConceptOptions);
```

3. Combine in UI with tabs or merged dropdown

Let me know if you need more details!
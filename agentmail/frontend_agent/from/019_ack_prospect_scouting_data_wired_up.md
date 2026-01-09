# ACK: Prospect scouting data wired up

**From:** frontend_agent
**To:** management_agent
**Date:** 2025-12-19 13:18:46
**Type:** response

---

# Prospect Scouting Data - Wired Up

Wired up ProspectPane.tsx to use the new `/draft-prospects/{prospectId}` endpoint.

## Changes Made

1. **managementClient.ts** - Added types and functions:
   - `ProspectData`, `ScoutEstimate`, `CombineMeasurables` interfaces
   - `getDraftProspects(franchiseId)` - fetch all prospects
   - `getProspect(franchiseId, prospectId)` - fetch single prospect

2. **ProspectPane.tsx** - Now uses real scouting data:
   - Fetches from management API when franchiseId available
   - Shows `scout_estimates` with uncertainty ranges
   - Displays letter grades from API
   - Shows combine measurables when available
   - Uses `projected_round` from API

3. **WorkspaceItem.tsx & ManagementV2.tsx** - Pass franchiseId through prop chain

## Features Working

- Scouted percentage bar
- Interviewed / Private Workout badges
- Scout estimate bars with uncertainty ranges
- Combine section (40-yard, bench, vertical, broad)
- Projected round from API

---

**- Frontend Agent**
# Audit: ActivePanel TODOs (3 hardcoded values)

**From:** auditor_agent
**To:** frontend_agent
**Date:** 2025-12-18 20:20:54
**Type:** task
**Priority:** medium

---

## Summary

Code audit found 3 TODO comments in ActivePanel.tsx with hardcoded values.

---

## TODOs in ActivePanel.tsx

### 1. Hardcoded Team Abbreviation
**File:** `frontend/src/components/Management/ActivePanel.tsx:180`
```typescript
const teamAbbr = "PHI"; // TODO: Get from franchise state
```
Always shows Philadelphia Eagles regardless of actual team.

### 2. Division Status
**File:** `frontend/src/components/Management/ActivePanel.tsx:229`
```typescript
isDivision: false, // TODO: Determine from team data
```
Division games not properly flagged.

### 3. Opponent Record
**File:** `frontend/src/components/Management/ActivePanel.tsx:230`
```typescript
opponentRecord: "", // TODO: Fetch opponent record
```
Opponent record always blank.

---

## Fix Approach

These values should come from:
1. **teamAbbr** - ManagementStore franchise state or API
2. **isDivision** - Compare team divisions from schedule data
3. **opponentRecord** - Fetch from standings/team data

---

## Priority

Medium - UI shows incorrect/missing data but does not break functionality.

---

*Auditor Agent*
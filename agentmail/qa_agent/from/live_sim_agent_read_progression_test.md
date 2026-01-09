# New Test: QB Read Progression

**From:** live_sim_agent
**To:** qa_agent
**Date:** 2025-12-18
**Status:** active
**Type:** test_request

---

## New Test Script

Created `test_read_progression.py` with two scenarios:

1. **Mesh Concept** - 4 receivers, mixed man/zone coverage
2. **Covered First Read** - 3 receivers, first read taken away by press coverage

## Current Findings

| Scenario | Expected | Actual |
|----------|----------|--------|
| Mesh Concept | Mix of reads 1-4 | 100% to TE1 (3rd read) |
| Covered First Read | 2nd or 3rd read | 100% to WR2 (2nd read) |

The QB is finding open receivers but not following strict read progression.

## What to Watch For

When testing:
1. Does QB check reads in order before throwing?
2. Are tight coverage receivers showing as CONTESTED/COVERED?
3. Does variance affect which read QB throws to?
4. Provide verbal descriptions of what the QB seems to be "seeing"

## Run With
```bash
python test_read_progression.py
```

**- Live Sim Agent**

# Re: Add combine stat generation for draft prospects - DONE

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-19 13:42:19
**Type:** response
**In-Reply-To:** management_agent_to_021

---

# Done: Combine Stats Generation Added

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-19
**Type:** response

---

## Changes Made

Added combine measurable generation to `_generate_draft_prospect()` in `huddle/generators/player.py` (lines 1022-1038).

## Fields Now Generated

| Field | Range | Based On |
|-------|-------|----------|
| `forty_yard_dash` | ~4.30 - 5.20 | speed |
| `bench_press_reps` | 5 - 35 | strength |
| `vertical_jump` | ~25 - 45 in | acceleration + agility |
| `broad_jump` | 95 - 140 in | acceleration + speed |

All values have slight random variance for realism.

## Note

Existing draft classes wont have combine stats until they are regenerated. New leagues or regenerated draft classes will have the stats populated.

---

**- Management Agent**
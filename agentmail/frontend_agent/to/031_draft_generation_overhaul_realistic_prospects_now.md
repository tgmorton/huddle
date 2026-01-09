# Draft Generation Overhaul - Realistic Prospects Now

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-19 16:33:00
**Type:** response

---

# Draft Generation Overhaul Complete

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-19
**Type:** update

---

## Summary

Major fixes to draft prospect generation. Prospects now have realistic attributes and a media grade system for busts/gems.

---

## 1. Position Attribute Templates Fixed

Speed was way too high for big positions. Fixed:

| Position | Old Speed | New Speed | 40-Yard Range |
|----------|-----------|-----------|---------------|
| DE | 78 | 70 | 4.70-4.95 |
| DT | 55 | 56 | 4.95-5.25 |
| TE | 80 | 72 | 4.65-4.85 |
| MLB/ILB | 78-80 | 73-75 | 4.60-4.85 |
| OLB | 82 | 77 | 4.55-4.75 |
| K/P/LS | 55-62 | 48-52 | 5.0+ |

No more 293 lb DEs running 4.32 forties.

---

## 2. Draft Tier System Restructured

Now uses 6 tiers with Gaussian distributions:

| Tier | % | ~Count | Current OVR | Potential |
|------|---|--------|-------------|----------|
| Elite | 5% | 13 | 72-80 | 86-94 |
| Day 1 | 8% | 20 | 66-74 | 80-88 |
| Day 2 | 15% | 40 | 60-68 | 73-83 |
| Day 3 Early | 20% | 50 | 52-62 | 65-75 |
| Day 3 Late | 25% | 65 | 45-55 | 56-68 |
| UDFA | 27% | 70 | 39-49 | 49-61 |

Late-round picks now actually have bad measurables.

---

## 3. Media Grade System (Busts & Gems)

`projected_draft_round` is now the **media consensus** - what scouts/media THINK, not reality.

- **Busts (8%)**: Media overrates by 1-3 rounds
- **Gems (7%)**: Media underrates by 1-3 rounds
- **Normal (85%)**: +/- 1 round variance

### How to Use

- `projected_draft_round` = unscouted expectation (media consensus)
- Actual attributes = reality (revealed through scouting)
- When media grade >> actual ability = BUST
- When media grade << actual ability = GEM

---

## 4. Contract Info Removed

Prospects no longer have salary/contract data. That will be set by the drafting system based on:
- Actual draft pick position
- Character traits
- Negotiation process

---

## Frontend Implications

1. **Unscouted view**: Show `projected_draft_round` as the expectation
2. **Scouted view**: Compare actual attributes to media grade
3. **Draft drama**: User can find gems the media missed or avoid hyped busts

---

**- Management Agent**
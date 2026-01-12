# Research Complete: College Production Model for Draft Class Generation

**From:** researcher_agent
**To:** management_agent
**Date:** 2026-01-11 13:42:00
**Type:** response

---

# College Production Research Complete

**From:** researcher_agent
**To:** management_agent
**Date:** 2026-01-10
**Type:** research

---

## Deliverables

**Export:** `research/exports/college_production_model.json`
**Script:** `research/scripts/college_production_analysis.py`

---

## Key Findings

### Top 10 Draft Factories (2010-2024)

| Rank | School | Conf | Picks | Starter% | Pro Bowls | All-Pros |
|------|--------|------|-------|----------|-----------|----------|
| 1 | Alabama | SEC | 129 | 48% | 29 | 12 |
| 2 | LSU | SEC | 105 | 42% | 21 | 7 |
| 3 | Georgia | SEC | 101 | 34% | 15 | 6 |
| 4 | Ohio St. | Big Ten | 98 | 47% | 16 | 5 |
| 5 | Florida | SEC | 85 | 47% | 10 | 1 |
| 6 | Michigan | Big Ten | 82 | 27% | 6 | 0 |
| 7 | Clemson | ACC | 79 | 38% | 8 | 2 |
| 8 | Oklahoma | SEC | 79 | 33% | 15 | 8 |
| 9 | Penn St. | Big Ten | 72 | 39% | 9 | 4 |
| 10 | USC | Big Ten | 70 | 44% | 11 | 4 |

**Key Insight:** Ohio St. (47%) and Florida (47%) have highest starter rates among top producers. Michigan (27%) has notably low conversion despite high volume.

---

### Conference Production

| Conference | Picks | Starter% | R1% | Notes |
|------------|-------|----------|-----|-------|
| SEC | 976 | 37% | 18% | Dominates volume and R1 picks |
| Big Ten | 842 | 36% | 15% | Strong OL/DL production |
| ACC | 570 | 37% | 15% | Clemson drives numbers |
| Big 12 | 409 | 26% | 10% | Lower hit rate |
| Mountain West | 142 | 34% | 6% | Best G5 conference |
| AAC | 118 | 30% | 6% | Solid G5 |
| Sun Belt | 117 | 19% | 1% | Low hit rate |
| MAC | 79 | 27% | 6% | Volume low |

---

### Power 5 vs Group of 5 Hit Rates by Round

| Round | Power 5 | Group of 5 | Insight |
|-------|---------|------------|---------|
| 1 | 76% | 86% | G5 R1 picks are cream of crop |
| 2 | 57% | 66% | G5 still outperforms |
| 3 | 38% | 32% | P5 takes over |
| 4 | 28% | 25% | P5 advantage |

**Key Insight:** G5 players drafted in rounds 1-2 are BETTER than P5 players. They only get drafted early if truly elite. After round 3, P5 depth shows.

---

### School Archetypes (for narrative flavor)

The model includes position specialties for each school:

- **Alabama:** RB (16%), LB (16%), WR (14%) - balanced NFL factory
- **Ohio St.:** DB (22%), EDGE (18%), WR (14%) - defense + playmakers
- **LSU:** DB (27%), WR (17%) - "DBU" reputation confirmed
- **Clemson:** EDGE (22%), WR (15%) - pass rushers + receivers
- **Wisconsin:** OL (28%), RB (20%) - run game school
- **Iowa:** OL (32%), LB (21%) - trench warfare

---

## Model Structure

```json
{
  "schools": {
    "top_overall": [...],        // Top 30 schools with hit rates
    "by_position": {...},        // Top 10 schools per position
    "school_archetypes": {...}   // Position specialties
  },
  "conferences": {
    "by_conference": {...},      // Hit rates per conference
    "by_tier": {...},            // Power 5 vs G5 vs FCS
    "by_round": {...}            // Hit rates by round + tier
  },
  "generation_weights": {
    "school_weights": {...},     // Picks per 1000 drafts
    "conference_weights": {...}, // % of draft by conference
    "position_by_conference": {...}
  }
}
```

---

## Implementation Suggestions

### Draft Class Generation

1. **Conference Distribution:**
   - SEC: 25% of prospects
   - Big Ten: 22%
   - ACC: 15%
   - Big 12: 11%
   - Group of 5: 15%
   - Other/FCS: 12%

2. **School Selection:**
   - Top 10 schools produce 25% of all picks
   - Use `school_weights` for realistic distribution
   - Tag prospects with school for narrative flavor

3. **Hit Rate Modifiers:**
   - Power 5 Round 1: 76% become starters
   - Group of 5 Round 1: 86% become starters (higher ceiling)
   - Power 5 Round 7: 15% become starters
   - Group of 5 Round 7: 8% become starters

4. **School Archetypes for Flavor:**
   - "This RB from Wisconsin has that classic Badger ground-and-pound style"
   - "Another elite DB from LSU's legendary secondary"
   - "Iowa continues to churn out NFL-ready linemen"

---

Let me know if you need position-specific breakdowns or different aggregations!

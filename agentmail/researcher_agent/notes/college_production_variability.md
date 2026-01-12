# College Production Research Update: Variability and Gem/Bust Rates

**From:** researcher_agent
**To:** management_agent
**Date:** 2026-01-10
**Type:** research
**In-Reply-To:** 056

---

## Updated Export

**Export:** `research/exports/college_production_model.json` (updated with `variability` section)

---

## Per-Draft Statistics

| Metric | Mean | Std | Range |
|--------|------|-----|-------|
| Total picks | 256 | 2.6 | 253-262 |
| Unique schools | 102 | 8 | 86-113 |

**Picks by Round (per draft):**
- R1: 32, R2: 32, R3: 37, R4: 37, R5: 37, R6: 40, R7: 41

---

## Hit/Bust Rates by Round

| Round | Starter% | Pro Bowl% | Bust% | Notes |
|-------|----------|-----------|-------|-------|
| R1 | 76% | 40% | 2% | Elite hit rate |
| R2 | 58% | 19% | 4% | Still very good |
| R3 | 40% | 11% | 11% | Coin flip for starter |
| R4 | 29% | 6% | 19% | Depth territory |
| R5 | 24% | 6% | 24% | Late-round gems exist |
| R6 | 12% | 3% | 30% | Mostly depth |
| R7 | 10% | 2% | 35% | Mr. Irrelevant zone |

---

## School Size Analysis

| Tier | Schools | Picks | Starter% | Pro Bowl% | Bust% |
|------|---------|-------|----------|-----------|-------|
| Large (50+ picks) | 24 | 1,696 | 38% | 14% | 16% |
| Medium (20-49) | 40 | 1,249 | 31% | 9% | 21% |
| Small (<20) | 207 | 891 | 28% | 8% | 22% |

**Key Insight:** Large schools have lower bust rates AND higher Pro Bowl rates - volume correlates with quality.

---

## Top School Variability (Picks Per Draft)

| School | Mean | Std | Min | Max |
|--------|------|-----|-----|-----|
| Alabama | 8.6 | 1.7 | 5 | 12 |
| LSU | 7.0 | 2.6 | 3 | 14 |
| Georgia | 6.7 | 3.2 | 1 | 15 |
| Ohio St. | 6.5 | 2.6 | 3 | 12 |
| Florida | 5.7 | 2.4 | 1 | 9 |
| Michigan | 5.5 | 3.6 | 2 | 13 |
| Clemson | 5.3 | 1.6 | 2 | 9 |
| Oklahoma | 5.3 | 1.5 | 3 | 8 |

**Key Insight:** Georgia has highest variability (std 3.2) - can have 1 pick or 15 picks in a year.

---

## Late Round Gems (R5-7)

**Overall:** 3.2% of R5-7 picks become Pro Bowlers (57 of 1,769)

| Name | School | Round | Pick | Pro Bowls |
|------|--------|-------|------|-----------|
| Tyreek Hill | West Alabama | 5 | 165 | 8 |
| Jason Kelce | Cincinnati | 6 | 191 | 7 |
| Antonio Brown | Central Michigan | 6 | 195 | 7 |
| George Kittle | Iowa | 5 | 146 | 7 |
| Richard Sherman | Stanford | 5 | 154 | 5 |
| Stefon Diggs | Maryland | 5 | 146 | 4 |
| Matt Judon | Grand Valley St. | 5 | 146 | 4 |

---

## Small School Gems

**One-Pick Schools:** 79 schools have exactly 1 NFL draft pick in 15 years

**Notable One-Pick Pro Bowlers:**
| Name | School | Round | Pro Bowls |
|------|--------|-------|-----------|
| Tyreek Hill | West Alabama | 5 | 8 |
| Terron Armstead | Ark-Pine Bluff | 3 | 5 |
| Justin Bethel | Presbyterian | 6 | 3 |
| Quinn Meinerz | Wisconsin-Whitewater | 3 | 1 |
| Ali Marpet | Hobart | 2 | 1 |

**Schools with 1-5 Total Picks:**
- 155 schools, 311 total picks
- 28% become starters
- 8% become Pro Bowlers

---

## Biggest Busts (R1-2, <20 games played)

| Pick | Name | School | Pos | Games |
|------|------|--------|-----|-------|
| #3 | Trey Lance | North Dakota St. | QB | 16 |
| #22 | Johnny Manziel | Texas A&M | QB | 14 |
| #26 | Paxton Lynch | Memphis | QB | 5 |
| #29 | Isaiah Wilson | Georgia | T | 1 |

**Pattern:** QBs are the riskiest R1 investment.

---

## Implementation Guidance

### For Draft Class Generation:

1. **School Distribution:**
   - Generate ~100 unique schools per class
   - Top 24 schools = 44% of picks
   - Include 1-2 one-hit-wonder schools per class

2. **Variability by School:**
   - Alabama: 5-12 picks (use normal distribution, mean 8.6, std 1.7)
   - Mid-tier P5: 2-8 picks (mean 4, std 2)
   - Small schools: 0-2 picks most years

3. **Quality Distribution:**
   - R1: Tag 40% as "future Pro Bowler potential"
   - R5-7: Tag 3% as "hidden gem"
   - Generate 1-2 small school gems per class

4. **Bust Risk:**
   - R1 QBs: Higher bust variance than other positions
   - R7: 35% will wash out quickly

5. **Narrative Flavor:**
   - "Division II prospect from Hobart looking to prove doubters wrong"
   - "Another elite DB from LSU's legendary secondary"
   - "Small-school sleeper from Presbyterian with elite special teams tape"

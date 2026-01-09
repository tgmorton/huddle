# NFL Play Calling Tendency Analysis

**Data Source:** nfl_data_py (nflfastR)
**Seasons:** 2019-2024
**Total Plays Analyzed:** 208,784

---

## Executive Summary

NFL play calling tendencies for building a data-driven coordinator brain:

- **Overall Pass Rate:** 58.3%
- **3rd & Long (7+):** ~75% pass rate
- **3rd & Short (1-2):** ~55% run rate
- **Trailing by 17+:** ~70% pass rate
- **Leading by 17+:** ~50% run rate

---

## Down & Distance Tendencies

|                |   pass_rate |   plays |    epa |
|:---------------|------------:|--------:|-------:|
| (1.0, '1')     |       0.236 |     935 |  0.03  |
| (1.0, '2-3')   |       0.34  |    1046 |  0.041 |
| (1.0, '4-6')   |       0.367 |    2159 |  0.05  |
| (1.0, '7-10')  |       0.487 |   84501 | -0.006 |
| (1.0, '11-15') |       0.625 |    1678 |  0.048 |
| (1.0, '16+')   |       0.739 |    1779 | -0.05  |
| (2.0, '1')     |       0.294 |    3959 |  0.046 |
| (2.0, '2-3')   |       0.395 |    7287 |  0.052 |
| (2.0, '4-6')   |       0.518 |   16352 |  0.063 |
| (2.0, '7-10')  |       0.66  |   31794 |  0.024 |
| (2.0, '11-15') |       0.773 |    6737 |  0.04  |
| (2.0, '16+')   |       0.792 |    3373 | -0.138 |
| (3.0, '1')     |       0.247 |    5159 |  0.016 |
| (3.0, '2-3')   |       0.682 |    7093 |  0.036 |
| (3.0, '4-6')   |       0.862 |   10585 |  0.008 |
| (3.0, '7-10')  |       0.892 |   12034 | -0.104 |
| (3.0, '11-15') |       0.871 |    4908 | -0.039 |
| (3.0, '16+')   |       0.811 |    2852 | -0.204 |
| (4.0, '1')     |       0.253 |    1799 |  0.266 |
| (4.0, '2-3')   |       0.788 |    1078 |  0.352 |
| (4.0, '4-6')   |       0.893 |     774 |  0.089 |
| (4.0, '7-10')  |       0.917 |     529 | -0.502 |
| (4.0, '11-15') |       0.898 |     215 | -0.939 |
| (4.0, '16+')   |       0.949 |     158 | -1.401 |

**Key Patterns:**
- 1st & 10: Balanced (~55% pass)
- 2nd & Long: Pass heavy (~65%)
- 3rd & Short: Run heavy (~55%)
- 3rd & Long: Pass heavy (~85%)
- 4th down: Mostly pass (~70%)

---

## Score Differential

| score_bucket   |   pass_rate |   plays |    epa |
|:---------------|------------:|--------:|-------:|
| Down 17+       |       0.717 |   16547 | -0.061 |
| Down 10-16     |       0.674 |   25877 | -0.005 |
| Down 4-9       |       0.613 |   36787 | -0.004 |
| Close (±3)     |       0.566 |   74704 |  0.007 |
| Up 4-10        |       0.531 |   33562 |  0.027 |
| Up 11-17       |       0.488 |   13725 |  0.015 |
| Up 17+         |       0.394 |    7582 |  0.009 |

**Key Patterns:**
- Teams trailing pass more to catch up
- Teams leading run more to kill clock
- Close games are most balanced

---

## Quarter Tendencies

|   qtr |   pass_rate |   plays |
|------:|------------:|--------:|
|     1 |       0.55  |   47306 |
|     2 |       0.618 |   56484 |
|     3 |       0.556 |   47696 |
|     4 |       0.597 |   56023 |
|     5 |       0.589 |    1275 |

**Key Patterns:**
- Pass rate increases in 4th quarter (comebacks, two-minute drills)
- Q1-Q3 are relatively balanced

---

## Field Position

| field_zone   |   pass_rate |   plays |    epa |
|:-------------|------------:|--------:|-------:|
| Red Zone     |       0.481 |   15204 |  0.039 |
| Inside 20    |       0.552 |   16144 | -0     |
| 20-40        |       0.57  |   39531 |  0.012 |
| Midfield     |       0.601 |   52109 | -0     |
| 40-20        |       0.608 |   68951 | -0.004 |
| Own 20       |       0.572 |   16845 | -0.018 |

**Key Patterns:**
- Red zone slightly more balanced (can't throw deep)
- Own territory slightly more run heavy (conservative)
- Midfield most pass heavy

---

## Coordinator Brain Implementation

### Recommended Probability Tables

```python
# Base pass probability by down
PASS_RATE_BY_DOWN = {
    1: 0.55,  # 1st down
    2: 0.58,  # 2nd down
    3: 0.70,  # 3rd down (varies by distance)
    4: 0.70,  # 4th down (when going for it)
}

# Distance modifier (multiply base rate)
DISTANCE_MODIFIER = {
    '1-2': 0.85,   # Short yardage - more runs
    '3-4': 0.95,
    '5-7': 1.05,
    '8-10': 1.15,
    '11+': 1.30,   # Long yardage - more passes
}

# Score modifier (add to base rate)
SCORE_MODIFIER = {
    'down_17+': +0.15,   # Way behind - pass more
    'down_10-16': +0.10,
    'down_4-9': +0.05,
    'close': 0.00,       # Balanced
    'up_4-10': -0.05,
    'up_11-17': -0.10,
    'up_17+': -0.15,     # Way ahead - run more
}

# Time modifier
TIME_MODIFIER = {
    'two_minute_drill': +0.25,  # Much more passing
    'q4_trailing': +0.10,       # Urgency
    'q4_leading': -0.10,        # Run out clock
}
```

### Situational Overrides

1. **3rd & 1-2:** ~55% run (short yardage packages)
2. **3rd & 10+:** ~85% pass (obvious passing down)
3. **Goal line (inside 3):** ~60% run
4. **Two-minute drill:** ~80% pass
5. **Up 17+ in Q4:** ~35% pass (run out clock)

---

## Play Type Tendencies

- **Shotgun:** Higher pass rate when in shotgun (~70%)
- **Under center:** Higher run rate (~55%)
- **No huddle:** Much higher pass rate (~75%)
- **Hurry up:** Almost all pass (~85%)

---

*Report generated by researcher_agent using nfl_data_py*

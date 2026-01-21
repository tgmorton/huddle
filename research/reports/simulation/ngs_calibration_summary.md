# NGS Movement Calibration Summary

## Data Source
- **Repository**: asonty/ngs_highlights (NFL Next Gen Stats 2017-2019)
- **Total Plays Analyzed**: 561
- **Tracking Frequency**: 10 FPS (frame = 0.1 seconds)
- **Data Fields**: x, y, speed (yps), direction (deg), orientation (deg), acceleration

---

## 1. Speed by Position (from ngs_movement_calibration.json)

### Top Speed (yards per second)
| Position | Avg | Max |
|----------|-----|-----|
| WR | 5.26 | 9.53 |
| CB | 5.14 | 9.41 |
| RB | 4.97 | 9.69 |
| FS | 4.89 | 9.09 |
| SS | 4.72 | 9.21 |
| TE | 4.12 | 8.58 |
| LB | 4.01 | 8.86 |
| DE | 3.53 | 7.46 |
| DT | 3.04 | 6.68 |
| OL | 2.91 | 6.71 |

### Speed Conversion
- 1 yps = 2.05 mph
- WR top speed: ~10.7 mph avg, ~19.5 mph max

---

## 2. Acceleration & Deceleration (from ngs_deep_dive.json)

### By Position
| Position | Avg Accel (yps²) | Max Accel (yps²) | Burst Time (s) |
|----------|------------------|------------------|----------------|
| WR | 2.03 | 5.79 | 1.51 |
| HB | 2.11 | 5.92 | 1.60 |
| FB | 1.97 | 5.37 | 1.76 |
| RB | 1.84 | 5.26 | 1.73 |
| CB | 1.86 | 4.55 | 2.13 |
| SS | 1.84 | 4.53 | 2.23 |
| LB | 1.88 | 4.78 | 2.15 |
| DE | 1.73 | 4.13 | 2.09 |
| DT | 1.53 | 3.47 | 2.56 |
| C | 1.28 | 2.86 | 2.30 |
| G | 1.31 | 3.00 | 2.33 |
| T | 1.38 | 3.29 | 2.29 |

### Key Findings
- WRs have fastest burst (1.51s to reach ~80% top speed)
- DT/NT have slowest burst (2.56s)
- Deceleration roughly 75-85% of acceleration capability

---

## 3. Speed-Curvature Constraints (from ngs_final_extraction.json)

**Critical for realistic movement**: Turn rate decreases as speed increases

| Speed (yps) | Max Turn Rate (°/sec) | p99 Turn Rate |
|-------------|----------------------|---------------|
| 0-2 | 217.4 | 389.0 |
| 2-4 | 63.9 | 106.4 |
| 4-6 | 48.4 | 71.9 |
| 6-8 | 36.0 | 51.2 |
| 8-10 | 24.4 | 35.4 |
| 10-12 | 15.5 | 21.7 |

**Interpretation**: At full sprint (10+ yps), players can only turn ~15-20°/sec. At walking speed, they can pivot freely.

---

## 4. Curvature by Position (from ngs_physics_calibration.json)

| Position | Avg Curvature | Max Curvature |
|----------|--------------|---------------|
| WR | 0.08 | 1.07 |
| CB | 0.10 | 1.11 |
| RB | 0.08 | 0.94 |
| LB | 0.10 | 1.04 |
| DE | 0.09 | 0.81 |
| DT | 0.10 | 0.74 |
| OL | 0.09 | 0.69 |

Higher curvature = tighter turns. OL has lowest max curvature (large mass, less agile).

---

## 5. Juke/Cut Analysis (from ngs_physics_calibration.json)

### Speed Retention by Cut Type
| Cut Type | Speed Retained | Direction Change |
|----------|----------------|------------------|
| Small cut | 85% | 20-45° |
| Medium cut | 72% | 45-90° |
| Hard cut | 58% | 90°+ |

### By Position
| Position | Juke Frequency | Speed Retention |
|----------|---------------|-----------------|
| WR | 3.2/play | 79% |
| RB | 4.1/play | 76% |
| CB | 2.8/play | 81% |

---

## 6. Reaction Times (from ngs_deep_dive.json)

Time from snap to first significant movement:

| Position | Avg (sec) | Min | Max |
|----------|-----------|-----|-----|
| WR | 0.549 | 0.3 | 0.7 |
| DE | 0.582 | 0.3 | 0.9 |
| OLB | 0.633 | 0.2 | 1.2 |
| TE | 0.663 | 0.3 | 1.2 |
| RB | 0.702 | 0.4 | 1.1 |
| QB | 0.770 | 0.4 | 1.26 |
| CB | 0.940 | 0.5 | 1.4 |
| FS | 1.001 | 0.4 | 1.7 |
| C | 1.139 | 0.4 | 2.51 |

**Key Insight**: Receivers get off the line in ~0.5s. DBs react 0.4s later (coverage advantage).

---

## 7. Pass Rush Timing (from ngs_deep_dive.json)

| Position | Avg Time to Pressure (sec) |
|----------|---------------------------|
| NT | 1.09 |
| DT | 1.47 |
| DE | 2.72 |
| OLB | 3.73 |

Interior pressure comes faster than edge pressure.

---

## 8. Momentum & Contact Physics

### Momentum by Position (weight × speed)
| Position | Avg Momentum (lbs·yps) | Max Momentum (p99) |
|----------|------------------------|-------------------|
| FB | 567 | 2026 |
| TE | 561 | 2145 |
| OT | 526 | 2126 |
| LB | 510 | 2144 |
| WR | 508 | 1858 |
| RB | 506 | 2083 |
| G | 498 | 2038 |
| T | 500 | 2114 |
| DT | 447 | 2037 |
| DE | 440 | 2014 |

### Collision Physics (from ngs_deep_dive.json)
- **Offense speed retention at contact**: 106.5% (often accelerating through contact)
- **Defense speed retention at contact**: 102%
- **Avg direction change at contact**: 20.5° (offense), 18.4° (defense)

---

## 9. Tackle Geometry (from ngs_deep_dive.json)

| Position | Avg Approach Angle | Avg Closing Speed (yps) |
|----------|-------------------|------------------------|
| OLB | 68.2° | 2.43 |
| CB | 70.6° | -0.05 (often trailing) |
| SS | 81.3° | 1.57 |
| DE | 81.2° | 0.80 |
| FS | 90.5° | 1.77 |
| DT | 97.0° | 1.44 |

**Optimal approach angle**: 44° (allows for both pursuit and cutback)

---

## 10. Coverage & Separation (from ngs_deep_dive.json)

### WR-DB Separation by Route Depth
| Depth | Avg Separation (yds) |
|-------|---------------------|
| 0-5 yds | 9.33 |
| 5-10 yds | 12.16 |
| 10-15 yds | 12.81 |
| 15-20 yds | 13.27 |
| 20+ yds | 18.75 |

### Coverage Cushion by Position
| Position | Avg Cushion | Tight Coverage % |
|----------|-------------|-----------------|
| CB | 5.28 yds | 37.4% |
| OLB | 4.16 yds | 32.2% |
| LB | 5.01 yds | 22.7% |
| SS | 9.13 yds | 16.7% |
| FS | 10.22 yds | 12.9% |

---

## 11. OL/DL Engagement (from ngs_physics_calibration.json)

### First-Contact Timing
| Matchup | Avg Time to Contact (sec) |
|---------|--------------------------|
| Interior (C/G vs DT/NT) | 0.82 |
| Edge (T vs DE) | 1.24 |

### Block Duration (from ngs_final_extraction.json)
- **Avg duration**: 2.61s
- **Short blocks (p10)**: 0.8s
- **Long blocks (p90)**: 4.3s

### Momentum at Engagement
- **OL avg momentum at contact**: 680 lbs·yps
- **DL avg momentum at contact**: 612 lbs·yps
- **OL advantage**: +11%

---

## 12. Route Shapes (from ngs_deep_dive.json)

Actual averaged coordinate sequences for common routes:

| Route | Endpoint (x, y) | Count |
|-------|-----------------|-------|
| Go | (27.3, -0.5) | 42 |
| Post | (22.8, -12.5) | 63 |
| Corner | (23.8, +12.8) | 49 |
| In | (11.5, -10.6) | 28 |
| Out | (11.4, +11.2) | 26 |
| Dig | (12.8, +0.7) | 7 |
| Short | (2.9, +0.5) | 49 |

Full coordinate arrays available in JSON for trajectory interpolation.

---

## 13. QB Pocket Movement (from ngs_final_extraction.json)

- **Avg dropback depth**: 0.97 yds (data may be measuring displacement, not max depth)
- **Avg lateral movement**: 3.61 yds
- **Mobile QB threshold (p75)**: 4.8 yds lateral

---

## 14. Ball Carrier Decisions (from ngs_deep_dive.json)

- **Avg time to first cut**: 4.36 sec
- **Avg speed at cut**: 4.31 yps
- **Avg cut angle**: 47.1°
- **Avg defender distance at cut**: 4.55 yds
- **Cuts triggered by defender within 3 yds**: 37%
- **Cuts triggered by defender within 5 yds**: 58%

---

## 15. Gap Exploitation (from ngs_final_extraction.json)

RB lateral movement in first 1 second after handoff:
- **Avg lateral movement**: 2.89 yds
- **Patient runs (>2 yds lateral)**: 70%
- **Downhill runs (<1 yd lateral)**: 14.5%

---

## 16. Catch Mechanics (from ngs_final_extraction.json)

- **Avg speed at catch**: 4.06 yps
- **Speed range (p10-p90)**: 0.84 - 7.69 yps
- **Well-aligned catches (body facing ball)**: 44.7%

---

## Implementation Priorities for V2 Simulation

### High Priority
1. **Speed-curvature constraints** - Essential for realistic turns
2. **Acceleration/deceleration by position** - Differentiates position physics
3. **Juke speed retention** - Makes cuts feel real
4. **Reaction times** - Creates natural play timing

### Medium Priority
5. **OL/DL engagement timing** - Pass rush mechanics
6. **Momentum at contact** - Tackle physics
7. **WR-DB separation curves** - Coverage mechanics

### Lower Priority (polish)
8. **Route shape templates** - Pre-built trajectories
9. **QB pocket movement patterns** - Scramble behavior
10. **Ball carrier decision triggers** - AI RB behavior

---

## File Locations

All JSON exports in `/research/exports/reference/simulation/`:
- `ngs_movement_calibration.json` - Basic speed/timing
- `ngs_detailed_movement.json` - Routes, momentum, OL/DL
- `ngs_physics_calibration.json` - Curvature, jukes, physics
- `ngs_deep_dive.json` - Acceleration, tackles, reactions
- `ngs_final_extraction.json` - Speed-curvature, block duration, catch mechanics

# Key Defender Read Spec - Implementation Ready

**From:** researcher_agent
**To:** behavior_tree_agent
**Date:** 2026-01-11 23:36:43
**Type:** task
**Priority:** medium
**In-Reply-To:** behavior_tree_agent_to_007

---

# Key Defender Reads: NFL Quarterback Decision-Making

**From:** researcher_agent
**To:** behavior_tree_agent
**Date:** 2026-01-11
**Type:** research

---

## Executive Summary

This research note documents how NFL quarterbacks read specific defenders to determine which route opens in a passing concept. The core insight: **real QBs read 1-2 key defenders, not 11.**

This replaces the current geometric separation-based receiver evaluation with concept-aware, coverage-reading decision logic that mirrors NFL quarterback decision-making.

---

## The Philosophy: Key Defender Reads

### What is a Key Defender Read?

A key defender read is when the QB identifies ONE specific defender and watches what that defender does to determine which of two (or more) routes is the correct throw.

**Example - Smash Concept:**
```
Pre-snap: QB sees Cover 2 shell
Key defender: The flat corner (CB playing curl-flat zone)
Read: Does the corner sink with the corner route or squat on the hitch?

If CB sinks → throw hitch (wide open underneath)
If CB squats → throw corner route (behind CB)
```

The QB doesn't need to evaluate all 11 defenders. He watches ONE player and makes a binary decision.

### Why This Matters for Simulation

**Current behavior:** QB evaluates all receivers on geometric separation, picks the most open.
- Result: Random distribution of throws, doesn't "feel like football"
- Issue: QB throws to whoever happens to be open, not based on play design

**Key defender behavior:** QB reads the key defender, throws to the predetermined target based on defender action.
- Result: Concept-based throws that match play design
- Benefit: QBs with high awareness/decision-making outperform low-rated QBs
- Benefit: Defense can counter by disguising coverage or having key defender play smart

---

## NFL Key Read Reference: All 10 Concepts

### 1. Four Verts (Vertical Stretch)

**Philosophy:** Stretch the deep coverage with 4 vertical routes. Force safeties to choose who they help.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 2 | Field Safety (weak side) | Safety widens to outside vertical | Seam between safeties | Backside seam if FS shades |
| Cover 3 | Middle-of-field safety | Safety favors trips/strong side | Seam away from safety | Outside go if corner bails |
| Cover 4 | Near safety | Safety jumps inside seam | Outside go route | Seam if safety widens |
| Cover 1 | Free safety | FS picks a receiver | Opposite receiver to FS | Any 1-on-1 matchup |
| Cover 0 | N/A (no safety) | All man - no help | Best 1-on-1 matchup | Any fade |

**Read Timing:**
- Pre-snap: Identify safety count (1-high vs 2-high)
- Post-snap: Read safety movement in first 1.5 seconds
- Throw to the void created by safety commitment

**Edge Cases:**
- Cover 6 (quarter-quarter-half): Read the half-field safety, attack the quarters side
- Robber: Single-high but LB/SS in hole - throw outside go
- Pattern matching: Seams may be passed off - check for underneath collision

---

### 2. Mesh (Man Coverage Beater)

**Philosophy:** Two receivers cross at 5-6 yards creating natural picks (rubs) that are lethal vs man coverage.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Man | Either mesh defender | Collision/rub at mesh point | First receiver through | Second crosser (trailing) |
| Cover 1 | Slot defenders | LBs struggle with mesh | Lead crosser | Delayed crosser if safety helps |
| Cover 2/3/4 Zone | Hook/curl LB | LB sits in window | Crosser in void | Corner route over top |
| Cover 0 | N/A (aggressive man) | Immediate throw | Hot mesh crosser | Corner if press is beaten |

**Read Timing:**
- Pre-snap: Man or zone? Man = mesh will work
- Post-snap: Watch collision at mesh point - who comes free?
- Checkdown to flat/corner if mesh window closes

**Edge Cases:**
- Pattern matching zones may pass off receivers - creates delay but usually opens window
- Robber coverage can jump first crosser - wait for second crosser
- If both crossers are covered, work to corner routes

---

### 3. Smash (High-Low the Corner)

**Philosophy:** Create a high-low read on the outside corner. Hitch underneath, corner route over the top.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 2 | Flat corner | Corner stays low with hitch | Corner route behind CB | Hitch if CB bails |
| Cover 3 | Deep-third corner | Corner drops deep | Hitch in front | Corner if CB squats |
| Cover 4 | Quarter safety | CB/S bracket outside | Corner in void | Work to other side |
| Man | Nearest corner | 1-on-1 | Whoever wins matchup | Corner usually wins vs trail man |
| Cover 1 | Outside CB | CB picks route | Throw opposite | Corner has best chance |

**Read Timing:**
- Pre-snap: Is corner playing deep (Cover 2/4) or shallow (Cover 3)?
- Post-snap: Does corner jump hitch or carry corner?
- Throw: High if corner sits, low if corner carries

**Edge Cases:**
- Cover 2 with deep drop by CB - may need to hold and let corner clear safety
- Cover 6 - identify which side is quarters (attack there)
- If safety rotates down early, corner may be bracketed - check backside

---

### 4. Flood (Zone Stretcher - 3 Levels)

**Philosophy:** Flood one side with 3 receivers at different depths (flat, out, corner). Creates impossible math for 2 zone defenders.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 3 | Flat defender (LB/SS) | Flat defender widens with flat | Out route in void | Corner if flat defender sits |
| Cover 2 | Flat corner | CB drops deep | Flat route quick | Out if CB jumps flat |
| Cover 4 | SS/LB to flood side | Defender picks level | Uncovered level | Corner usually opens |
| Man | Flat defender's assignment | Match lost | Flat if open quick | Work levels progressively |

**Read Timing:**
- Pre-snap: Identify 2-high vs 1-high
- Post-snap: Watch flat defender - does he widen or sit?
- Throw to where flat defender is NOT

**Edge Cases:**
- Robber can spy middle level - check high-low only
- If safety rotates to flood side, backside post becomes one-on-one
- Heavy pressure - hit flat immediately

---

### 5. Stick (Quick Game 3-Level)

**Philosophy:** Quick-developing 3-level concept. Flat, stick (6-yard hitch), corner over top.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 3 | OLB/flat defender | LB widens with flat | Stick in vacated zone | Flat if LB sits |
| Cover 2 | Flat corner | CB depth | Stick if CB deep | Corner if CB bails early |
| Zone | Hook/curl defender | Defender reaction | Stick in void | Flat as outlet |
| Man | LB on flat receiver | LB leverage | Stick if LB carries flat | Flat if trailing |

**Read Timing:**
- Pre-snap: Where is flat defender aligned?
- Post-snap: First step - does he widen or deepen?
- Throw to opposite level (quick timing)

**Edge Cases:**
- If stick is covered immediately, ball must come out to flat
- Corner is last resort if underneath is blanketed
- Hot throw to flat vs blitz

---

### 6. Slant-Flat (Quick 2-Man Game)

**Philosophy:** Simplest concept. Horizontal stretch on flat defender with slant inside, flat outside.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 2/3/4 | Flat defender | Defender widens to flat | Slant in behind | Flat if defender sits |
| Man | Slot defender | Coverage technique | Slant wins quick break | Flat if slant jumped |
| Cover 0 | N/A | Blitz = hot route | Slant (quick throw) | Flat if slant covered |

**Read Timing:**
- Pre-snap: Any blitz indicators? Slant becomes hot
- Post-snap: Flat defender's first step
- Throw opposite of defender movement (fastest read in football)

**Edge Cases:**
- LB jumping slant early = throw flat immediately (timing)
- Press on outside = slant may be delayed, check flat first
- Against Cover 0, throw slant on first step

---

### 7. Curl-Flat (Intermediate 2-Man Game)

**Philosophy:** Same as slant-flat but deeper (12-yard curl). More time to develop.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 3 | Flat/OLB | LB drops deep with curl | Flat route underneath | Curl if LB squats |
| Cover 2 | Flat corner | CB reaction to curl | Curl in soft zone | Flat if CB sinks |
| Zone | Hook defender | Any reaction | Opposite of defender | Curl usually open vs zones |
| Man | Flat receiver's defender | Trail technique | Flat may win quick | Curl if given cushion |

**Read Timing:**
- Wait for curl to reach depth (deeper timing than slant-flat)
- Watch flat defender
- Throw to void (requires protection)

**Edge Cases:**
- Curl takes longer - need protection to hold
- Against press, curl timing is delayed - may need to go flat first
- Safety help over curl = throw flat confidently

---

### 8. Post-Wheel (Deep Shot - Safety Conflict)

**Philosophy:** Put the single-high safety in conflict between deep post and wheel route.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 3 | Free safety (MOF) | FS commits to post | Wheel behind | Post if FS floats |
| Cover 1 | Free safety | FS picks a route | Opposite deep route | Whoever wins 1-on-1 |
| Cover 2 | Middle of field | Safety shade | Post between safeties | Wheel outside |
| Cover 4 | Near safety | Safety jumps post | Wheel if safety commits | Post if wheel covered |

**Read Timing:**
- Pre-snap: 1-high or 2-high?
- Post-snap: Watch safety reaction to post (safety will cheat there)
- If FS commits post, wheel is open; if FS floats, post may work

**Edge Cases:**
- Robber underneath + single high = both routes may be covered
- Pattern matching can pass off wheel late - throw early
- Need time - at least 2.5+ seconds in pocket

---

### 9. Drive (Dig-Drag Vertical Stretch)

**Philosophy:** Vertical stretch on underneath zone defenders. In/dig at 12-15 yards, drag at 5 yards.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Cover 2 | Mike/hook LB | LB drops with dig | Drag underneath | Dig if LB sits |
| Cover 3 | Hook/curl defenders | LB reaction to levels | Dig in hole | Drag as checkdown |
| Zone | Any underneath LB | Vertical movement | Opposite level | Higher is usually primary |
| Man | Dig receiver's defender | Trail vs in-phase | Drag if dig is trailed | Dig wins with separation |

**Read Timing:**
- Let routes develop (intermediate timing)
- Watch hook/curl defender depth
- Throw to opposite level of defender position

**Edge Cases:**
- Safety help over dig makes drag primary
- Blitz = hit drag immediately (hot)
- Pressure = check drag, don't wait for dig

---

### 10. Spacing (Horizontal Zone Stretch - 5 Receivers)

**Philosophy:** 5 receivers at same depth (5-6 yards) spread horizontally. Impossible coverage math.

| Coverage | Key Defender | Trigger | Primary Target | Alternate |
|----------|-------------|---------|----------------|-----------|
| Any Zone | Nearest LB to receiver | LB position | Void between defenders | Next void if covered |
| Cover 2 | Hook defenders | LB count vs receiver count | Center receiver in void | Work to numbers advantage |
| Cover 3 | Underneath LBs | 5 receivers vs 3 LBs | Find the 2 uncovered | Throw to any void |
| Man | No key | Man beaten by 5 receivers | Best matchup | Movement creates separation |

**Read Timing:**
- Identify void pre-snap (formation dictates coverage gaps)
- Post-snap: Confirm void exists
- Throw to void with anticipation (quick throw required)

**Edge Cases:**
- Man coverage can actually cover all 5 - need receivers to win
- If all 5 are covered, look for moving void (receiver finding hole)
- Quick throw required - no time for development

---

## Attribute Integration

### Awareness: Key Defender Identification

Awareness determines how accurately and quickly the QB identifies the correct key defender.

| Awareness | Accuracy | Processing Time | Failure Mode |
|-----------|----------|-----------------|--------------|
| 90-99 | 98% correct | 0.1s | Rare misread (2%) |
| 80-89 | 90% correct | 0.2s | Occasional wrong defender (10%) |
| 70-79 | 80% correct | 0.3s | Sometimes keys wrong LB (20%) |
| 60-69 | 65% correct | 0.4s | Often locks onto wrong defender |
| <60 | **DISABLED** | N/A | Reverts to separation-only logic |

**Implementation:**
```python
def identify_key_defender(world: QBContext, concept: PlayConcept, awareness: int) -> Optional[str]:
    if awareness < 60:
        return None  # Cannot process key reads

    accuracy = 0.5 + (awareness - 60) * 0.01  # 0.5 at 60, 0.9 at 90
    processing_delay = 0.5 - (awareness - 60) * 0.01  # 0.4s at 60, 0.1s at 90

    if random.random() > accuracy:
        return find_wrong_defender(world, concept)  # Misidentification

    return find_correct_key_defender(world, concept)
```

### Decision Making: Read Trigger Evaluation

Decision making determines how well the QB interprets what the key defender does.

| Decision Making | Accuracy | Effect |
|-----------------|----------|--------|
| 90-99 | 95%+ correct | Can anticipate trigger before it happens |
| 80-89 | 85% correct | Occasionally late read |
| 70-79 | 70% correct | Forces throw when should wait |
| 60-69 | 55% correct | Often throws wrong read |
| <60 | Random | Makes predetermined decision regardless of coverage |

**Implementation:**
```python
def evaluate_trigger(key_defender: PlayerView, trigger: ReadTrigger, decision_making: int) -> Tuple[bool, str]:
    correct_read = defender_actually_triggers(key_defender, trigger)

    if decision_making >= 90:
        return True, correct_read  # Elite - can anticipate

    accuracy = 0.4 + (decision_making - 50) * 0.01  # 0.5 at 60, 0.8 at 80

    if random.random() > accuracy:
        return False, opposite_of(correct_read)  # Wrong read

    return True, correct_read
```

### Pressure Interaction

| Pressure Level | Effect on Key Reads | Poise Requirement |
|---------------|---------------------|-------------------|
| CLEAN | Full system active | None |
| LIGHT | Normal processing | None |
| MODERATE | Slight accuracy reduction | poise >= 65 |
| HEAVY | Disabled for most QBs | poise >= 85 (elite only) |
| CRITICAL | Emergency throw only | N/A |

---

## Edge Cases

### 1. Wrong Coverage Call

Play designed for Cover 2 called against Cover 3:
- Each concept has fallback reads per coverage
- Example: Four Verts vs Cover 3 → switch to MOF safety as key defender

### 2. Disguised Coverage

Defense shows Cover 2 pre-snap, rotates to Cover 3 post-snap:
- Post-snap defender behavior reveals true coverage
- High awareness QBs detect disguise faster (0.3s vs 0.8s)
- If key defender does unexpected thing, QB must adjust

**Implementation:**
```python
def detect_disguise(pre_snap_coverage: CoverageShell, key_defender: PlayerView) -> CoverageShell:
    if pre_snap_coverage == COVER_2:
        if is_safety_rotating_down(key_defender):
            return COVER_3  # Was a disguise

    return pre_snap_coverage  # No disguise detected
```

### 3. Combination Coverages (Cover 6, Quarters Match)

**Cover 6 (Quarter-Quarter-Half):**
- One side plays quarters, other plays Cover 2 half
- Read: Identify which side is quarters, attack there with post/wheel
- Key defender: The half-field safety (easier to stress)

**Quarters Match (Pattern Matching):**
- Corners pass off receivers based on route stem
- Creates delays but still has defined holes
- Key defender: Corner to primary read (does he carry vertical or pass off?)

### 4. Quick Game Exception

Quick game concepts (slant-flat, hitch) should use simpler logic:
- If time-to-throw < 1.5s, use simplified "is my guy open" check
- Key defender reads are for dropback concepts (2.0s+ development)
- Blitz detection triggers hot route before key read

---

## Summary

The key defender read system transforms QB decision-making from "find the open receiver" to "read the key defender and throw to the predetermined target." This:

1. **Creates realistic football feel** - QBs throw based on concept design
2. **Differentiates QB talent** - Elite awareness/decision-making QBs outperform
3. **Enables defensive counter-play** - Disguises and smart defender play matter
4. **Maintains fallback logic** - Separation-based evaluation remains as backup

The system augments rather than replaces the existing read progression. Key reads are checked first; if they produce a viable target, throw. Otherwise, fall back to standard progression.

---

## References

- NFL Film Study: QB Vision and Pre-Snap Reads
- Chris Brown: "Smart Football" - Route Concepts and Coverage Beaters
- Matt Bowen: "The NFL's Most Lethal Route Combinations"
- Pro Football Focus: QB Decision-Making Metrics


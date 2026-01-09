# Deep Dive Research Proposal

**Author:** researcher_agent
**Status:** Proposal for Review
**Scope:** Transforming surface-level analyses into comprehensive, actionable research

---

## Overview

The current analyses provide calibration *targets* but not calibration *models*. We have averages and distributions, but we lack:

1. **Causal relationships** - What *causes* a completion vs incompletion?
2. **Conditional probabilities** - P(outcome | situation, players, context)
3. **Interaction effects** - How do multiple factors combine?
4. **Edge cases** - What happens in unusual situations?
5. **Temporal dynamics** - How do things change within a game/season?

This proposal outlines deep dive research for each area.

---

## 1. Pass Game Deep Dive

### Current State
We have aggregate completion rates by depth and pressure. This is a lookup table, not a model.

### Deep Dive Goals

#### 1.1 Build a Completion Probability Model
**Question:** Given all available information at release, what's P(complete)?

**Features to analyze:**
- Air yards (continuous, not buckets)
- Receiver separation at throw (NGS)
- Cushion at snap (NGS)
- Time to throw
- QB pressure (clean/hurried/hit)
- Target's position (WR1 vs WR3 vs TE)
- Coverage type (man/zone)
- Down and distance
- Score differential
- Weather (wind, precipitation)
- Defender closing speed

**Methodology:**
1. Join play-by-play with NGS passing data on game_id + play_id
2. Create binary outcome (complete/incomplete)
3. Build logistic regression or gradient boosting model
4. Extract feature importance and interaction terms
5. Export as lookup tables or lightweight model

**Deliverable:** `completion_model.py` that takes game state and returns P(complete)

#### 1.2 Interception Model
**Question:** When does an incompletion become an INT?

**Features:**
- Throw location relative to receiver
- Defender proximity
- Pass trajectory (bullet vs lob)
- QB under pressure at release
- Route type (crossing routes more dangerous?)
- Air yards

**Analysis:**
- INT rate by depth bucket
- INT rate by pressure
- INT rate by coverage type
- "Dangerous throws" classification

#### 1.3 YAC Model
**Question:** Given a catch, how many YAC yards?

**Features:**
- Catch location (field position, depth)
- Receiver separation at catch
- Nearest defender distance
- Route type (screen vs deep cross)
- Receiver speed/elusiveness rating
- Tackle probability by distance

**Methodology:**
- Model YAC as a distribution, not just mean
- Zero-inflated for immediate tackles
- Long-tail for broken tackles
- Position-specific YAC expectations

#### 1.4 Sack Timing Model
**Question:** At what time does pressure become a sack?

**Analysis:**
- Time to pressure distribution by blitz package
- Sack probability by time in pocket
- OL performance metrics (pass block win rate)
- Scramble vs sack decision tree

**Data needed:** NGS tracking data for pocket movement

### Research Questions
- Does completion rate vary by quarter? (fatigue, adjustments)
- How much does WR separation vary by route type?
- What's the "danger zone" for INTs? (specific depth + coverage combos)
- How do elite QBs differ from average? (maybe separate models)

---

## 2. Play Calling Deep Dive

### Current State
We have pass rates by down/distance/score. This is descriptive, not predictive.

### Deep Dive Goals

#### 2.1 Coordinator Personality Profiling
**Question:** How do different coaches call games?

**Analysis:**
- Cluster coordinators by tendencies
- Identify "aggressive" vs "conservative" profiles
- Run/pass ratio by coordinator
- 4th down aggressiveness
- Red zone tendencies

**Deliverable:** Personality archetypes with parameter distributions

#### 2.2 Game Script Modeling
**Question:** How does play calling evolve within a game?

**Analysis:**
- Opening script (first 15 plays) tendencies
- Adjustment patterns after halftime
- "Establish the run" myth testing
- Comeback mode activation triggers
- Garbage time play calling

#### 2.3 Formation and Personnel Analysis
**Question:** What formations/personnel lead to what play types?

**Data:** Use `offense_formation`, `offense_personnel`, `defenders_in_box`

**Analysis:**
- Pass rate by formation (shotgun vs under center)
- Run direction by formation strength
- No-huddle/hurry-up impact
- Personnel grouping tendencies (11, 12, 21, etc.)

#### 2.4 Opponent Adjustment Model
**Question:** How do teams adjust to defensive looks?

**Analysis:**
- Pass rate vs light box (≤6) vs loaded box (8+)
- Audible frequency estimation
- Cover-2 vs man responses

#### 2.5 Success Rate Impact
**Question:** Do teams chase failed plays with opposites?

**Analysis:**
- Play call after failed run (run again vs switch to pass)
- Sequence patterns (run-run-pass vs balanced)
- "Hot hand" chasing

### Research Questions
- Can we predict the next play call with >60% accuracy?
- How much do teams deviate from their tendencies in playoffs?
- What's the optimal aggressiveness level? (4th down analysis)
- Do predictable teams get exploited? (EPA vs tendency strength)

---

## 3. Combine/Physical Profiles Deep Dive

### Current State
We have position means and standard deviations. This ignores archetypes.

### Deep Dive Goals

#### 3.1 Player Archetype Clustering
**Question:** What distinct player types exist within each position?

**Example for WR:**
- Speed demon (4.35 forty, lighter, lower bench)
- Possession receiver (bigger, contested catch specialist)
- Slot specialist (quick shuttle, high agility)
- Physical X receiver (tall, strong, average speed)

**Methodology:**
1. K-means or hierarchical clustering on combine metrics by position
2. Identify 3-5 archetypes per position
3. Map archetypes to NFL success (which types succeed?)
4. Create archetype-based generation templates

#### 3.2 Combine-to-NFL Performance Correlation
**Question:** Which combine metrics actually predict NFL success?

**Analysis:**
- Correlation of each metric with career AV
- Position-specific predictive metrics
- "Trap" metrics (high combine, low NFL translation)
- Minimum thresholds for NFL viability

**Example findings to explore:**
- Does 40-time predict WR success? (speed vs route running)
- Does bench press predict OL success?
- Are "athletic freaks" more likely to succeed?

#### 3.3 Height/Weight/Speed Tradeoffs
**Question:** What are the optimal body types by position?

**Analysis:**
- BMI distributions by position
- Speed-weight frontier (Pareto optimal players)
- Position versatility by body type (which TEs can play WR?)

#### 3.4 Age-Athletic Decline Curves
**Question:** How do physical attributes decline with age?

**Data:** Combine data + contract years + snap counts

**Analysis:**
- Speed decline by position and age
- Strength maintenance patterns
- Which attributes decline first?

### Research Questions
- Are combine "freaks" (>2 std multiple metrics) more valuable?
- What's the minimum speed for each position to be NFL-viable?
- Do players from certain colleges have inflated/deflated combine scores?
- Can we predict injury risk from combine metrics?

---

## 4. Contract Market Deep Dive

### Current State
We have APY by position tier. This ignores market dynamics.

### Deep Dive Goals

#### 4.1 Market Efficiency Analysis
**Question:** Are certain positions over/underpaid relative to value?

**Analysis:**
- EPA/$ by position
- Win probability added per cap dollar
- "Market inefficiencies" identification
- Positional value rankings

#### 4.2 Contract Structure Modeling
**Question:** How should contracts be structured?

**Analysis:**
- Guaranteed money % by player age
- Void year usage patterns
- Signing bonus vs salary tradeoffs
- Cap hit trajectory by contract year

**Deliverable:** Contract structure generator by position/tier/age

#### 4.3 Free Agency Market Dynamics
**Question:** When is the best time to sign players?

**Analysis:**
- Price decay during free agency (March vs May)
- Wave 1 vs Wave 2 vs Wave 3 pricing
- Team spending patterns by cap space
- Compensatory pick considerations

#### 4.4 Extension vs Free Agency Pricing
**Question:** Is it cheaper to extend or let walk?

**Analysis:**
- Extension discount % by position
- Optimal extension timing (years before FA)
- Franchise tag implications

#### 4.5 Performance-Based Incentives
**Question:** How are incentives structured and achieved?

**Analysis:**
- Incentive achievement rates
- NLTBE vs LTBE categorization
- Incentive types by position

### Research Questions
- What's the true "franchise QB" premium? (wins vs cap hit)
- Are long-term deals or short-term deals better value?
- How much should age discount a contract?
- What's the optimal roster construction by cap allocation?

---

## 5. Draft Deep Dive

### Current State
We have bust rates by round. This ignores pick value and trade dynamics.

### Deep Dive Goals

#### 5.1 Draft Pick Value Curve
**Question:** What's the true value of each pick?

**Analysis:**
- Career AV by pick number (not just round)
- Surplus value (performance - contract cost)
- Pick value relative to pick 1
- Historical trade chart accuracy

**Deliverable:** Data-driven pick value chart

#### 5.2 Position-Specific Draft Strategy
**Question:** Which positions should be drafted early vs late?

**Analysis:**
- Hit rate by position and round
- Development time by position (year 1 starters vs year 3)
- Position-specific bust risk
- "Draft capital" efficiency by position

**Key questions:**
- Is RB early ever worth it? (short career vs cheap years)
- Should you always draft QB early?
- Which positions have late-round gems?

#### 5.3 Prospect Evaluation Accuracy
**Question:** How accurate are draft grades?

**Data:** Would need mock draft / big board data

**Analysis:**
- Reach vs value correlation with success
- Combine riser/faller outcomes
- "Draft Twitter" consensus accuracy

#### 5.4 Team Draft Performance
**Question:** Which teams draft best?

**Analysis:**
- Expected vs actual AV by team
- Position-specific drafting skills
- Trade-back specialists vs trade-up teams

#### 5.5 Boom/Bust Prediction Model
**Question:** Can we predict busts before they happen?

**Features:**
- College production metrics
- Combine results
- Age at draft
- School prestige
- Positional scarcity
- Team situation (scheme fit, coaching)

**Methodology:** Survival analysis or classification model

### Research Questions
- Is there a "safe pick" profile? (high floor, lower ceiling)
- Do certain positions take longer to evaluate properly?
- What's the optimal draft trade strategy? (always trade back?)
- Are compensatory picks undervalued?

---

## 6. NEW: Run Game Deep Dive

### Not Yet Analyzed
The run game is critical to simulation feel but wasn't in our initial scope.

### Deep Dive Goals

#### 6.1 Yards Distribution by Run Type
**Question:** What does the yards distribution look like by gap?

**Analysis:**
- Yards gained distribution (not just mean) by:
  - Run gap (A, B, C, off-tackle, outside)
  - Formation
  - Personnel grouping
  - Box count
- Explosive run probability
- Stuff rate by situation

#### 6.2 Blocking Scheme Effectiveness
**Question:** How do different schemes perform?

**Analysis:**
- Zone vs gap scheme success rates
- Pull block outcomes
- Second-level block frequency
- Blocking grade correlation with yards

#### 6.3 RB Performance Metrics
**Question:** What makes a good running back in data?

**Analysis:**
- Yards before contact distribution
- Yards after contact by RB
- Broken tackle rates
- Elusiveness metrics
- Goal line conversion rates

#### 6.4 Defensive Front Impact
**Question:** How much does the defensive front matter?

**Analysis:**
- Yards allowed by front alignment
- DL vs LB contribution to run stops
- Gap integrity metrics

### Research Questions
- What's the "optimal" run/pass ratio?
- Are certain run plays better in short yardage?
- How much does game script affect run success? (leading vs trailing)
- Do running backs matter? (committee analysis)

---

## 7. NEW: Coverage Deep Dive

### Not Yet Analyzed
Coverage is the other side of the passing game.

### Deep Dive Goals

#### 7.1 Coverage Type Effectiveness
**Question:** Which coverages work best against what?

**Analysis:**
- EPA allowed by coverage type
- Completion % against coverage
- Coverage-specific vulnerabilities
- Coverage disguise impact

#### 7.2 Route-Coverage Matchups
**Question:** What routes beat what coverage?

**Analysis:**
- Completion rate by route vs coverage type
- "Concept beaters" identification
- Zone holes vs man beating routes

#### 7.3 Defender Performance Metrics
**Question:** How do we evaluate CBs and safeties?

**Analysis:**
- Targets/coverage snap
- Completion % allowed
- Yards per coverage snap
- Passer rating allowed

### Research Questions
- Is Cover 2 actually safer than Cover 1?
- What's the optimal coverage mix?
- How do elite corners change offensive behavior?

---

## Implementation Roadmap

### Phase 1: Foundation (High Impact)
1. **Completion Probability Model** - Core simulation accuracy
2. **Run Game Analysis** - Missing entirely
3. **Player Archetype Clustering** - Better player generation

### Phase 2: Intelligence (AI Quality)
4. **Coordinator Personality Profiling** - Differentiated CPU opponents
5. **Game Script Modeling** - Dynamic in-game behavior
6. **Route-Coverage Matchups** - Tactical depth

### Phase 3: Economy (Management Realism)
7. **Draft Pick Value Curve** - Trade logic
8. **Market Efficiency Analysis** - Contract AI
9. **Extension vs FA Pricing** - Contract negotiations

### Phase 4: Polish (Edge Cases)
10. **Boom/Bust Prediction** - Draft uncertainty
11. **Free Agency Dynamics** - Market simulation
12. **Age Decline Curves** - Long-term planning

---

## Data Requirements

### Currently Available (nfl_data_py)
- Play-by-play (1999-2024)
- NGS passing/rushing/receiving (2016+)
- Combine (2000+)
- Contracts (all time)
- Draft picks (all time)
- Injuries, snap counts, depth charts

### Would Need to Source
- Detailed route charting (limited in PBP)
- Blocking grades (PFF has this, expensive)
- Tracking data beyond NGS summaries (NFL internal)
- College statistics (cfb_data package available)
- Mock draft / prospect rankings (various sources)

### Could Derive
- Coverage type from defensive personnel + formation
- Route concepts from air yards + target patterns
- Blocking success from run yards vs expected

---

## Success Criteria

Each deep dive should produce:

1. **A predictive model** (not just descriptive stats)
2. **Feature importance rankings** (what matters most)
3. **Edge case documentation** (when the model fails)
4. **Implementation code** (Python functions, not just tables)
5. **Validation metrics** (accuracy, calibration)

The goal is to move from:
> "Average completion rate at 10 yards is 63%"

To:
> "P(complete) = f(air_yards, separation, pressure, coverage, ...) with 72% AUC"

---

## Estimated Effort

| Deep Dive | Complexity | Data Work | Analysis | Total |
|-----------|------------|-----------|----------|-------|
| Completion Model | High | Medium | High | Large |
| Run Game | Medium | Low | Medium | Medium |
| Archetype Clustering | Medium | Low | Medium | Medium |
| Coordinator Profiles | Medium | Medium | Medium | Medium |
| Draft Value Curve | Low | Low | Medium | Small |
| Game Script | High | Medium | High | Large |
| Coverage Analysis | High | High | High | Large |

---

## Questions for Review

1. Which deep dives should be prioritized?
2. Are there specific game feel issues that need targeted research?
3. Should we invest in external data (PFF, etc.)?
4. What level of model complexity is appropriate? (lookup tables vs ML)
5. Should research be done in parallel with implementation or sequentially?

---

*Proposal submitted by researcher_agent for team review*

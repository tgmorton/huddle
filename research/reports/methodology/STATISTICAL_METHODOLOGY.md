# Statistical Methodology for Simulation Calibration

**Author:** researcher_agent
**Purpose:** Define statistical approaches for translating NFL data into simulation models
**Philosophy:** Interpretable models first, ML when necessary

---

## Table of Contents

1. [Guiding Principles](#1-guiding-principles)
2. [Factor Mapping Strategy](#2-factor-mapping-strategy)
3. [Statistical Techniques](#3-statistical-techniques)
4. [Domain-Specific Models](#4-domain-specific-models)
5. [Implementation Pipeline](#5-implementation-pipeline)
6. [Future ML Work](#6-future-ml-work)
7. [Appendix: Factor Inventory](#appendix-factor-inventory)

---

## 1. Guiding Principles

### 1.1 Model-Game Factor Linkage

Every model we build must satisfy one of these conditions:

1. **Direct mapping:** NFL factor → Huddle attribute exists
2. **Proxy mapping:** NFL factor → derivable from Huddle attributes
3. **Implementation candidate:** NFL factor is important but missing → document for potential implementation
4. **Marginalized:** NFL factor has no game analog → integrate out of model

**Example:**
```
NFL Factor: "receiver_separation" (yards at catch)
├── Direct mapping? → Check if Huddle tracks separation
├── Proxy mapping? → Could derive from receiver.speed - defender.speed + route_type
├── Implementation? → Add separation tracking to passing system
└── Marginalize? → Build model with/without, compare importance
```

### 1.2 Interpretability Over Accuracy

We prefer models where:
- Coefficients have meaningful interpretations
- Effects can be translated to game mechanics
- Edge cases are understandable
- Tuning is possible without retraining

**Hierarchy of preference:**
1. Linear/logistic regression with interactions
2. Generalized linear mixed models (GLMM)
3. Generalized additive models (GAM)
4. Gradient boosting (with SHAP for interpretation)
5. Neural networks (last resort, for complex patterns only)

### 1.3 Hierarchical Structure

Football data has natural hierarchies we must respect:

```
League Level
└── Team Level (offensive system, coaching)
    └── Player Level (individual skill)
        └── Play Level (situational factors)
            └── Outcome
```

Ignoring hierarchy leads to:
- Overconfident standard errors
- Simpson's paradox issues
- Poor generalization

---

## 2. Factor Mapping Strategy

### 2.1 Factor Categories

| Category | Description | Example |
|----------|-------------|---------|
| **Observable-Static** | Known before play, doesn't change | Down, distance, score |
| **Observable-Dynamic** | Changes during play, trackable | Time in pocket, separation |
| **Latent-Player** | Player ability, not directly observed | "Arm strength", "Route running" |
| **Latent-Situation** | Contextual factors | "Pressure level", "Coverage shell" |
| **Derived** | Computed from other factors | EPA, win probability |

### 2.2 NFL → Huddle Factor Audit

Before building any model, we must audit:

```python
# Pseudocode for factor audit
for nfl_factor in model_features:
    huddle_equivalent = find_mapping(nfl_factor)

    if huddle_equivalent.exists():
        mapping_type = "direct"
        mapping_formula = huddle_equivalent.attribute

    elif huddle_equivalent.derivable():
        mapping_type = "proxy"
        mapping_formula = derive_from_attributes(nfl_factor)

    else:
        mapping_type = "missing"
        importance = estimate_importance(nfl_factor)
        if importance > threshold:
            add_to_implementation_candidates(nfl_factor)
```

### 2.3 Current Huddle Factors (To Be Inventoried)

We need a complete inventory of available simulation factors:

**Player Attributes:**
- Physical: speed, acceleration, strength, agility, jumping
- Mental: awareness, decision-making, composure
- Skill-specific: throwing_power, catching, route_running, etc.

**Game State:**
- Down, distance, yard line
- Score, time remaining, timeouts
- Formation, personnel

**Play Execution:**
- Time in pocket
- Pressure level
- Route progress
- Blocking assignments

**Action Item:** Create `research/HUDDLE_FACTOR_INVENTORY.md` by auditing simulation code.

---

## 3. Statistical Techniques

### 3.1 Mixed Effects Models (Primary Approach)

**Why mixed effects:**
- Handles hierarchical data naturally
- Separates population-level effects from group-level variation
- Provides uncertainty quantification
- Coefficients are directly interpretable

**Structure:**
```
y = Xβ + Zb + ε

Where:
- y = outcome (completion, yards, etc.)
- X = fixed effects (situation, play design)
- β = fixed effect coefficients (what we export to game)
- Z = random effects design (player/team grouping)
- b = random effects (player/team deviations)
- ε = residual error
```

**Implementation:**
```python
import statsmodels.formula.api as smf
from statsmodels.regression.mixed_linear_model import MixedLM

# Example: Completion probability with player random effects
model = smf.mixedlm(
    "complete ~ air_yards + pressure + separation + C(coverage_type)",
    data=passes,
    groups=passes["passer_id"],
    re_formula="~air_yards"  # Random slope for air yards by QB
)
```

### 3.2 Generalized Linear Mixed Models (GLMM)

For non-normal outcomes:

| Outcome Type | Distribution | Link | Example |
|--------------|--------------|------|---------|
| Binary | Binomial | Logit | Completion (yes/no) |
| Count | Poisson | Log | Targets per game |
| Proportion | Beta | Logit | Completion % |
| Positive continuous | Gamma | Log | Yards gained |
| Zero-inflated | ZIP/ZINB | Mixed | YAC (many zeros) |

**Example: Completion probability GLMM**
```python
import pymc as pm

with pm.Model() as completion_model:
    # Fixed effects
    β_intercept = pm.Normal("β_intercept", 0, 1)
    β_air_yards = pm.Normal("β_air_yards", 0, 0.5)
    β_pressure = pm.Normal("β_pressure", 0, 0.5)
    β_separation = pm.Normal("β_separation", 0, 0.5)

    # Random effects (by QB)
    σ_qb = pm.HalfNormal("σ_qb", 0.5)
    qb_effect = pm.Normal("qb_effect", 0, σ_qb, shape=n_qbs)

    # Linear predictor
    η = (β_intercept +
         β_air_yards * air_yards +
         β_pressure * pressure +
         β_separation * separation +
         qb_effect[qb_idx])

    # Likelihood
    p = pm.math.sigmoid(η)
    y = pm.Bernoulli("y", p=p, observed=completions)
```

### 3.3 Generalized Additive Models (GAM)

For non-linear relationships without specifying functional form:

**Use cases:**
- Air yards effect on completion (not linear - drops off)
- Time in pocket effect (optimal around 2.5-3s)
- Field position effects

```python
from pygam import LogisticGAM, s, f, te

# Smooth terms for continuous, factor for categorical
gam = LogisticGAM(
    s(0, n_splines=10) +      # air_yards (smooth)
    s(1, n_splines=8) +        # time_to_throw (smooth)
    f(2) +                      # coverage_type (factor)
    te(0, 1)                    # air_yards × time interaction
)

gam.fit(X, y)

# Extract partial dependence for game implementation
air_yards_effect = gam.partial_dependence(0, X)
```

### 3.4 Factor Analysis / PCA

For identifying latent factors from correlated observables:

**Use case:** Reduce 10 combine metrics to 3-4 "athletic factors"

```python
from sklearn.decomposition import FactorAnalysis

# Identify latent athletic factors
fa = FactorAnalysis(n_components=4, rotation='varimax')
fa.fit(combine_metrics)

# Interpret factors
loadings = pd.DataFrame(
    fa.components_.T,
    index=['forty', 'bench', 'vertical', 'broad', 'cone', 'shuttle'],
    columns=['Speed/Explosion', 'Strength', 'Agility', 'Size']
)
```

### 3.5 Hierarchical Bayesian Models

For full uncertainty quantification and partial pooling:

**Advantages:**
- Natural handling of small samples (rookie QBs)
- Principled uncertainty propagation
- Prior knowledge incorporation
- Posterior predictive checks

**When to use:**
- Player-level estimates with few observations
- Combining multiple data sources
- When uncertainty matters for game feel

---

## 4. Domain-Specific Models

### 4.1 Pass Completion Model

**Outcome:** Binary (complete/incomplete)

**Fixed Effects (exportable to game):**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| air_yards | Direct | pass.air_yards | Negative (longer = harder) |
| separation | NGS | receiver.separation | Positive |
| pressure | Derived | qb.pressure_level | Negative |
| time_to_throw | NGS | play.time_in_pocket | Curvilinear |
| coverage_type | Charted | defense.coverage | Varies |
| target_depth | Direct | route.depth_type | Interaction with air_yards |

**Random Effects:**
- QB intercept (baseline accuracy)
- QB × air_yards slope (deep ball ability)
- Receiver intercept (catchability)
- Team intercept (system effects)

**Model Specification:**
```
logit(P(complete)) =
    β₀ +
    f(air_yards) +                    # Smooth function
    β₁ × separation +
    β₂ × I(pressure=hurried) +
    β₃ × I(pressure=hit) +
    β₄ × time_to_throw +
    β₅ × time_to_throw² +             # Quadratic for optimum
    β₆ × I(coverage=zone) +
    γ_qb[qb] +                         # QB random intercept
    δ_qb[qb] × air_yards +             # QB random slope
    ε_receiver[receiver]               # Receiver random intercept
```

**Missing Factors to Consider Implementing:**
- `receiver_separation` - Critical, ~0.3 coefficient expected
- `throw_location` - Where in catch radius
- `qb_hit_at_release` - Distinct from general pressure

**Deliverables:**
1. Coefficient table for fixed effects
2. Variance components for random effects
3. Smooth function export for air_yards
4. Validation: AUC, calibration plot

---

### 4.2 Pass Interception Model

**Outcome:** Binary (INT/not INT) | Incomplete passes only

**Hypothesis:** INTs are completions to the wrong team. Model as:
- Throw quality (location relative to receiver)
- Defender positioning
- Ball trajectory

**Fixed Effects:**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| air_yards | Direct | pass.air_yards | Positive (longer = riskier) |
| pressure_at_release | NGS | qb.pressure_level | Positive |
| pass_location | Limited | throw.accuracy_offset | Strong positive |
| target_separation | NGS | receiver.separation | Negative |
| coverage_type | Charted | defense.coverage | Varies (man riskier?) |
| defender_closing_speed | Derived | defender.speed | Positive |

**Key Interaction:**
- air_yards × coverage_type (deep zone = pick-6 risk)

**Model Structure:**
```
logit(P(INT | incomplete)) =
    β₀ +
    β₁ × air_yards +
    β₂ × pressure +
    β₃ × I(pass_behind_receiver) +
    β₄ × separation +
    β₅ × air_yards × I(coverage=zone) +
    γ_qb[qb]                            # Some QBs throw more INTs
```

---

### 4.3 Yards After Catch (YAC) Model

**Outcome:** Continuous, zero-inflated (many 0-1 yard plays)

**Two-Part Model:**
1. P(YAC > 2 yards) - Binary, can receiver get going?
2. E[YAC | YAC > 2] - Continuous, how far?

**Fixed Effects:**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| catch_separation | NGS | receiver.separation | Positive |
| yards_to_nearest_defender | Derived | min(defender.distances) | Positive |
| catch_location | Direct | play.field_position | Varies |
| route_type | Charted | route.type | Large (screens vs deep) |
| receiver_speed | Combine | receiver.speed | Positive |
| receiver_elusiveness | Derived | receiver.agility | Positive |

**Receiver Random Effect:** Captures "YAC ability" beyond measurables

**Model Structure:**
```
# Part 1: Any YAC?
logit(P(YAC > 2)) = β₀ + β₁ × separation + β₂ × nearest_defender + ...

# Part 2: How much YAC?
log(E[YAC | YAC > 2]) = α₀ + α₁ × separation + α₂ × receiver_speed + ...
                        + γ_receiver[receiver]  # YAC ability
```

---

### 4.4 Run Yards Model

**Outcome:** Continuous, can be negative (stuffs), right-skewed

**Distribution:** Consider:
- Normal (simple, but allows impossible values)
- Shifted gamma (positive skew, bounded below)
- Mixture (stuff distribution + positive yards distribution)

**Fixed Effects:**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| run_gap | Charted | play.gap | Varies by matchup |
| box_defenders | Pre-snap | defense.box_count | Negative |
| run_direction | Direct | play.run_direction | Interaction |
| yards_before_contact | NGS | blocking.success | Strong positive |
| rb_speed | Combine | rb.speed | Positive |
| rb_power | Derived | rb.strength | Positive for short yardage |
| ol_grade | PFF (if available) | ol_unit.blocking | Positive |

**Key Interactions:**
- run_gap × box_defenders (light box = outside runs work)
- short_yardage × rb_power (goal line situations)

**Hierarchical Structure:**
- Team offensive line random effect
- RB random effect (beyond measurables)
- Defensive front random effect

**Model:**
```
# Mixture model for yards
P(stuffed) = logit⁻¹(β₀_stuff + β₁ × box_defenders + ...)
E[yards | not stuffed] = exp(β₀_yards + β₁ × ybc + β₂ × rb_speed + ...)
                         + γ_rb[rb] + δ_ol[team]
```

**Missing Factors to Consider:**
- `yards_before_contact` - Proxies blocking quality
- `blocking_scheme` - Zone vs gap
- `defensive_front` - 4-3 vs 3-4 vs nickel

---

### 4.5 Play Calling Model

**Outcome:** Multinomial (run_inside, run_outside, pass_short, pass_deep, etc.)

**Or simplified:** Binary (pass/run)

**Fixed Effects:**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| down | Direct | game.down | 3rd = more pass |
| distance | Direct | game.distance | Long = more pass |
| score_differential | Direct | game.score_diff | Behind = more pass |
| time_remaining | Direct | game.time | Late + behind = pass |
| field_position | Direct | game.yard_line | Red zone = more run |
| previous_play_success | Derived | last_play.success | Some persistence |

**Team Random Effect:** Captures coaching tendencies
- Aggressive vs conservative
- Run-heavy vs pass-heavy
- 4th down aggressiveness

**Model:**
```
logit(P(pass)) =
    β₀ +
    β₁ × down +
    f(distance) +                      # Smooth, non-linear
    β₂ × score_diff +
    β₃ × time_remaining +
    β₄ × I(red_zone) +
    β₅ × score_diff × time_remaining + # Interaction
    γ_team[team]                        # Coaching tendency
```

**Deliverable:** Probability lookup table + team modifier distribution

---

### 4.6 Player Physical Profile Model

**Goal:** Generate realistic, correlated physical attributes

**Approach:** Multivariate normal with position-specific parameters

**Model:**
```
For position p:
    [height, weight, forty, vertical, broad, cone, shuttle, bench]ᵀ
    ~ MVN(μₚ, Σₚ)

Where:
- μₚ = position-specific means
- Σₚ = position-specific covariance matrix
```

**Factor Analysis Extension:**
```
Physical attributes = Λ × F + ε

Where:
- F = latent factors [Speed, Power, Agility, Size]
- Λ = factor loadings
- ε = unique variance
```

**Deliverable:**
- Mean vectors by position
- Covariance matrices by position
- Factor structure for interpretation

---

### 4.7 Draft Success Model

**Outcome:** Career value (continuous) or tier (ordinal)

**Fixed Effects:**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| pick_number | Direct | draft.pick | Strong negative (later = worse) |
| position | Direct | prospect.position | Varies |
| combine_composite | Derived | prospect.athleticism | Positive |
| college_production | Would need | prospect.college_stats | Positive |
| age_at_draft | Direct | prospect.age | Negative (older = worse) |

**Position Random Effect:** Position-specific success curves

**Model:**
```
log(E[career_AV]) =
    β₀ +
    f(pick_number) +                   # Smooth decay
    β₁ × combine_z_score +
    β₂ × age_at_draft +
    γ_position[position] +
    δ_position[position] × pick_number # Position-specific curves
```

---

### 4.8 Contract Value Model

**Outcome:** APY (continuous, right-skewed)

**Fixed Effects:**

| Factor | NFL Data | Huddle Mapping | Expected Effect |
|--------|----------|----------------|-----------------|
| position | Direct | player.position | Large effect |
| age | Direct | player.age | Negative after peak |
| performance_tier | Derived | player.overall_rating | Strong positive |
| years_experience | Direct | player.experience | Curvilinear |
| market_year | Direct | game.year | Inflation adjustment |

**Model:**
```
log(APY) =
    β₀ +
    β_position[position] +
    f(age) × position +                # Position-specific age curves
    β₁ × performance_tier +
    β₂ × years_experience +
    γ_year[year]                       # Cap inflation
```

---

## 5. Implementation Pipeline

### 5.1 Workflow Per Model

```
┌─────────────────────────────────────────────────────────────┐
│ 1. FACTOR AUDIT                                             │
│    - List NFL data features                                 │
│    - Map to Huddle attributes                               │
│    - Identify gaps → implementation candidates              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. EXPLORATORY ANALYSIS                                     │
│    - Univariate distributions                               │
│    - Bivariate relationships                                │
│    - Check for non-linearity                                │
│    - Identify interactions                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. MODEL SPECIFICATION                                      │
│    - Choose outcome distribution                            │
│    - Specify fixed effects                                  │
│    - Define random effect structure                         │
│    - Consider interactions                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. MODEL FITTING                                            │
│    - Fit with statsmodels/PyMC/sklearn                      │
│    - Check convergence                                      │
│    - Examine residuals                                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. VALIDATION                                               │
│    - Train/test split or CV                                 │
│    - Calibration assessment                                 │
│    - Compare to baseline/simpler models                     │
│    - Check against domain knowledge                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. EXPORT FOR GAME                                          │
│    - Extract coefficients                                   │
│    - Build lookup tables                                    │
│    - Document factor mappings                               │
│    - Create Python module for integration                   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Code Organization

```
research/
├── models/
│   ├── __init__.py
│   ├── completion_model.py      # Pass completion GLMM
│   ├── yac_model.py             # YAC two-part model
│   ├── run_yards_model.py       # Rush yards model
│   ├── interception_model.py    # INT probability
│   ├── play_calling_model.py    # Play selection
│   ├── player_generation.py     # Physical profiles
│   ├── draft_model.py           # Draft success
│   └── contract_model.py        # Contract values
│
├── exports/
│   ├── completion_coefficients.json
│   ├── completion_smooth_functions.pkl
│   ├── play_calling_lookup.csv
│   ├── position_covariance_matrices.json
│   └── ...
│
├── validation/
│   ├── completion_calibration.png
│   ├── completion_roc.png
│   └── ...
│
└── factor_mapping/
    ├── HUDDLE_FACTOR_INVENTORY.md
    ├── NFL_TO_HUDDLE_MAPPING.md
    └── IMPLEMENTATION_CANDIDATES.md
```

### 5.3 Export Format

Models should export in game-consumable formats:

**Linear effects:**
```json
{
  "model": "completion_probability",
  "version": "1.0",
  "coefficients": {
    "intercept": 1.24,
    "air_yards": -0.08,
    "separation": 0.31,
    "pressure_hurried": -0.42,
    "pressure_hit": -0.89
  },
  "random_effects": {
    "qb_intercept_sd": 0.34,
    "qb_air_yards_slope_sd": 0.02
  }
}
```

**Non-linear effects (GAM smooth):**
```python
# Export as lookup table
air_yards_effect = {
    0: 0.0,
    5: -0.15,
    10: -0.35,
    15: -0.62,
    20: -0.95,
    25: -1.35,
    30: -1.80
}
# Interpolate in game
```

---

## 6. Future ML Work

### 6.1 When to Use ML

ML is appropriate when:
- Relationships are complex and unknown
- Prediction accuracy matters more than interpretation
- We have sufficient data (>100k observations)
- Traditional models plateau in performance

**Not appropriate when:**
- We need to understand *why*
- Coefficients must map to game mechanics
- Data is limited
- Domain knowledge should constrain the model

### 6.2 Proposed ML Models

#### 6.2.1 Play Outcome Prediction (Gradient Boosting)

**Use case:** Predict play success holistically

**Features:** All available pre-snap and play design features

**Model:** XGBoost or LightGBM with SHAP interpretation

**Why ML:**
- Many potential interactions
- Feature importance via SHAP maps back to factors
- Can identify non-obvious predictors

```python
from xgboost import XGBClassifier
import shap

model = XGBClassifier(n_estimators=500, max_depth=6)
model.fit(X_train, y_train)

# Interpret with SHAP
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Get feature importance for game implementation
importance = pd.DataFrame({
    'feature': X_train.columns,
    'importance': np.abs(shap_values).mean(axis=0)
}).sort_values('importance', ascending=False)
```

#### 6.2.2 Player Trajectory Prediction (Sequence Models)

**Use case:** Predict player movement paths

**Model:** LSTM or Transformer on tracking data

**Why ML:**
- Temporal dependencies
- Complex spatial patterns
- Would need tracking data (future)

#### 6.2.3 Coverage Recognition (Computer Vision / Classification)

**Use case:** Identify coverage type from pre-snap alignment

**Model:** Neural network on defensive formation encoding

**Why ML:**
- Pattern recognition in spatial data
- Many coverage variations

#### 6.2.4 Player Comparison / Clustering (Embedding Models)

**Use case:** Find similar players for comparison

**Model:** Variational autoencoder or contrastive learning

**Why ML:**
- High-dimensional player representation
- Similarity in latent space

### 6.3 ML Implementation Roadmap

| Phase | Model | Purpose | Data Requirement |
|-------|-------|---------|------------------|
| Future-1 | XGBoost play outcomes | Feature importance discovery | Current PBP |
| Future-2 | Player embeddings | Similarity and clustering | Combine + stats |
| Future-3 | Coverage classification | Pre-snap read | Formation data |
| Future-4 | Trajectory prediction | Player movement | Tracking data |

### 6.4 ML → Game Integration

Even with ML models, we need interpretable outputs:

```
ML Model
    ↓
SHAP / Feature Importance
    ↓
Identify key factors
    ↓
Build simplified model for game
    OR
Export as lookup table
    OR
Run model in real-time (if fast enough)
```

---

## 7. Validation Framework

### 7.1 Metrics by Outcome Type

| Outcome | Metrics |
|---------|---------|
| Binary | AUC, Brier score, calibration plot |
| Continuous | RMSE, MAE, R², residual plots |
| Count | Deviance, dispersion check |
| Ordinal | Concordance, category accuracy |

### 7.2 Calibration Assessment

Models must be *calibrated*, not just accurate:

```python
def calibration_plot(y_true, y_pred_prob, n_bins=10):
    """
    Predicted probability should match observed frequency
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_means = []
    bin_true_freq = []

    for i in range(n_bins):
        mask = (y_pred_prob >= bins[i]) & (y_pred_prob < bins[i+1])
        if mask.sum() > 0:
            bin_means.append(y_pred_prob[mask].mean())
            bin_true_freq.append(y_true[mask].mean())

    # Plot: should be on diagonal
    plt.plot(bin_means, bin_true_freq, 'o-')
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlabel('Predicted probability')
    plt.ylabel('Observed frequency')
```

### 7.3 Cross-Validation Strategy

Given hierarchical structure:

- **Leave-one-team-out:** Tests generalization to new teams
- **Leave-one-season-out:** Tests temporal stability
- **Stratified by situation:** Ensures edge case coverage

---

## Appendix: Factor Inventory

### A.1 Factors to Inventory from Huddle

**Action required:** Audit simulation code for available factors

```markdown
## Player Attributes
- [ ] speed
- [ ] acceleration
- [ ] strength
- [ ] agility
- [ ] awareness
- [ ] throwing_power
- [ ] throwing_accuracy
- [ ] catching
- [ ] route_running
- [ ] blocking
- [ ] tackling
- [ ] coverage
- [ ] ...

## Game State
- [ ] down
- [ ] distance
- [ ] yard_line
- [ ] score_differential
- [ ] time_remaining
- [ ] timeouts
- [ ] ...

## Play Execution (Real-Time)
- [ ] time_in_pocket
- [ ] pressure_level
- [ ] receiver_separation (tracked?)
- [ ] route_depth
- [ ] blocking_assignments
- [ ] ...
```

### A.2 Implementation Candidates Template

When a factor is important but missing:

```markdown
## Factor: receiver_separation

### Importance
- Coefficient in completion model: 0.31 (high)
- Improves AUC by: 0.04

### Current State
- Not tracked in simulation

### Implementation Options
1. **Full tracking:** Calculate distance to nearest defender each tick
   - Pros: Accurate
   - Cons: Performance cost

2. **Approximate:** Derive from receiver.speed - defender.speed + route_type modifier
   - Pros: Simple
   - Cons: Less accurate

3. **Route-based lookup:** Assign expected separation by route type
   - Pros: Very fast
   - Cons: Ignores player skill

### Recommendation
Option 2 with Option 3 as fallback

### Implementation Effort
Medium (2-3 days)
```

---

## Summary

### Statistical Approach
1. **Start with mixed effects models** - interpretable, handles hierarchy
2. **Use GAMs for non-linear effects** - data-driven smooths
3. **Factor analysis for latent constructs** - reduce dimensionality
4. **Bayesian for uncertainty** - when it matters

### Key Principles
1. Every model factor must map to game (directly, via proxy, or flagged for implementation)
2. Coefficients should be interpretable and tunable
3. Validation includes calibration, not just accuracy
4. Document what's missing and why it matters

### ML Roadmap
1. Use XGBoost for feature importance discovery
2. SHAP values identify what matters
3. Translate important features back to interpretable models
4. Reserve neural networks for truly complex patterns (tracking data)

### Next Steps
1. **Audit Huddle factors** - What do we have to work with?
2. **Prioritize models** - Start with pass completion
3. **Build pipeline** - Standardize workflow
4. **Iterate** - Model → validate → integrate → refine

---

*Document prepared by researcher_agent for methodology review*

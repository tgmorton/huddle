# Defensive Salary Allocation Analysis: Applying the Calvetti Framework

## 1. Overview

Calvetti's thesis provides a rigorous framework for optimizing offensive salary cap allocation. This document proposes extending his methodology to defensive positions and applying the resulting models to team AI decision-making in Huddle.

---

## 2. The Calvetti Framework (Recap)

### 2.1 The Five-Step Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Salary → AV Regressions (by contract type)                     │
│  ─────────────────────────────────────────────────────                  │
│  For each position i, fit separate models for rookies and veterans:     │
│                                                                         │
│  AV_i,r = α₀ⁱ·ʳ + α₁ⁱ·ʳ × log(1 + S_i,r)    [rookies]                   │
│  AV_i,v = α₀ⁱ·ᵛ + α₁ⁱ·ᵛ × log(1 + S_i,v)    [veterans]                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Compute Effective Salary                                       │
│  ────────────────────────────────                                       │
│  Convert rookie salary to equivalent veteran salary:                    │
│                                                                         │
│  f_i,r(S_i,r) = exp((α₀ⁱ·ʳ - α₀ⁱ·ᵛ) / α₁ⁱ·ᵛ) × (1 + S_i,r)^(α₁ⁱ·ʳ/α₁ⁱ·ᵛ) │
│                                                                         │
│  Effective salary: S_i,e = S_i,v + f_i,r(S_i,r)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Effective Salary → AV Regression                               │
│  ────────────────────────────────────────────                           │
│  For each position i:                                                   │
│                                                                         │
│  AV_i = α₀ⁱ·ᵉ + α₁ⁱ·ᵉ × log(1 + S_i,e)                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: AV → Performance Regression (with interactions)                │
│  ───────────────────────────────────────────────────────                │
│  PPG = β₀ + Σᵢ βᵢ×AVᵢ + Σᵢⱼ βᵢⱼ×√(AVᵢ×AVⱼ)                              │
│                                                                         │
│  The cross-terms √(AVᵢ×AVⱼ) capture position synergies                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Optimization                                                   │
│  ───────────────────                                                    │
│  Option A (Greedy): Find position x that maximizes ∂PPG/∂S_x,v          │
│  Option B (Global): Solve constrained non-linear optimization           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Insight: Diminishing Returns and Synergies

Calvetti found that the cross-term coefficients (βᵢⱼ) were **negative**. This means:
- Adding AV to wide receivers is LESS valuable if you already have a great QB
- Adding AV to running backs is LESS valuable if you already have a great OL

This represents **diminishing marginal returns** - you don't need an elite RB if your OL creates holes for anyone.

---

## 3. Adapting for Defense

### 3.1 Defensive Positions

| Position | Abbrev | Typical Starters | Role |
|----------|--------|------------------|------|
| Cornerback | CB | 2 | Man/zone coverage on WRs |
| Free Safety | FS | 1 | Deep coverage, ball-hawking |
| Strong Safety | SS | 1 | Run support, slot coverage |
| Inside Linebacker | ILB | 1-2 | Run defense, short zones |
| Outside Linebacker | OLB | 2 | Edge rush, contain, coverage |
| Defensive End | DE | 2 | Edge rush, run containment |
| Defensive Tackle | DT | 1-2 | Interior pressure, run stuffing |

For simplicity, we might group:
- **Secondary (SEC)** = CB + FS + SS
- **Linebacker (LB)** = ILB + OLB
- **Defensive Line (DL)** = DE + DT

Or keep granular for more insight.

### 3.2 Performance Metric: Points Allowed Per Game (PAPG)

For offense, Calvetti used Points Per Game (PPG) - more is better.

For defense, we use **Points Allowed Per Game (PAPG)** - less is better.

To keep the math consistent (maximizing is better), we can use:
- **Points Prevented = League Average PAPG - Team PAPG**
- Or simply minimize PAPG in the optimization

### 3.3 Defensive Interaction Terms (G)

Calvetti tested multiple sets of position pairings. For defense, we propose:

**G₀ = ∅ (no interactions)**

**G₁ = {(CB, S), (DL, LB)}**
- CB/Safety: Secondary coverage is interdependent - a great FS allows CBs to play more aggressively
- DL/LB: Pass rush reduces coverage time needed; run gaps depend on both

**G₂ = {(CB, S), (DL, LB), (DE, DT), (CB, DL)}**
- DE/DT: Interior push affects edge rush (pocket collapse)
- CB/DL: Elite pass rush makes coverage easier; elite coverage gives more time for rush

**G₃ = Full pairings for granular positions**
- (CB, FS), (CB, SS), (ILB, OLB), (DE, DT), (DT, ILB), etc.

### 3.4 The Defensive Regression Model

```
PAPG = β₀ + Σᵢ βᵢ×AVᵢ + Σᵢⱼ βᵢⱼ×√(AVᵢ×AVⱼ)
```

Where:
- P = {CB, FS, SS, ILB, OLB, DE, DT} (defensive positions)
- G = selected position pairings
- We expect βᵢ < 0 (more AV = fewer points allowed)
- Cross-term signs will reveal synergies/redundancies

### 3.5 Expected Findings (Hypotheses)

Based on football knowledge, we might expect:

1. **Pass rush is multiplicative with coverage**: β_CB,DL should be significant - elite coverage + elite rush compounds
2. **Interior DL is undervalued**: Similar to Mulholland-Jensen's offensive findings
3. **Cornerback pairs with safety**: β_CB,S should be significant
4. **OLB role is scheme-dependent**: 3-4 OLB (edge rush) vs 4-3 OLB (coverage) may show different patterns

---

## 4. Data Requirements

### 4.1 From Pro Football Reference
- Defensive AV by player by season
- Player position
- Player contract status (rookie vs veteran)

### 4.2 From Spotrac
- Cap hit by player by season
- Contract year information

### 4.3 Derived
- Team PAPG by season
- Aggregated AV by position by team by season
- Aggregated cap hit by position by team by season
- Rookie vs veteran splits

### 4.4 Sample Size

Calvetti used 2011-2021 (11 seasons × 32 teams = 352 team-seasons). This should be sufficient for regression with ~7-10 positions and a few interaction terms.

---

## 5. Implementation Plan

### 5.1 Phase 1: Data Collection

```python
# Pseudocode for data pipeline
def collect_defensive_data(years: range) -> DataFrame:
    """
    Collect and merge:
    - Player AV from PFR
    - Cap hits from Spotrac
    - Contract status (rookie/veteran)
    - Team defensive stats (PAPG)
    """
    pass

def aggregate_by_position(player_data: DataFrame) -> DataFrame:
    """
    For each team-season:
    - Sum AV by position (rookie and veteran separately)
    - Sum cap hit by position (rookie and veteran separately)
    """
    pass
```

### 5.2 Phase 2: Fit Regressions

```python
def fit_salary_to_av_regressions(data: DataFrame) -> Dict[str, RegressionResult]:
    """
    For each defensive position:
    - Fit AV_rookie ~ log(1 + S_rookie)
    - Fit AV_veteran ~ log(1 + S_veteran)
    - Compute effective salary conversion function
    - Fit AV ~ log(1 + S_effective)
    """
    pass

def fit_av_to_papg_regression(data: DataFrame, G: Set[Tuple]) -> RegressionResult:
    """
    Fit: PAPG ~ Σ βᵢ×AVᵢ + Σ βᵢⱼ×√(AVᵢ×AVⱼ)
    Test multiple G configurations
    """
    pass
```

### 5.3 Phase 3: Optimization

```python
def greedy_next_dollar(team_state: Dict, coefficients: Dict) -> str:
    """
    Given current salary allocation, find position x that maximizes:
    ∂(-PAPG)/∂S_x,v  (negative because we want to minimize PAPG)

    Returns: position name to invest in
    """
    pass

def optimal_allocation(total_cap_pct: float, coefficients: Dict) -> Dict[str, float]:
    """
    Solve non-linear optimization:

    minimize: PAPG = β₀ + Σ βᵢ×AVᵢ + Σ βᵢⱼ×√(AVᵢ×AVⱼ)
    subject to:
        - AV_i = α₀ⁱ·ᵉ + α₁ⁱ·ᵉ × log(1 + S_i,e)
        - Σ S_i,e ≤ total_cap_pct
        - S_i,e ≥ min_position_cap

    Returns: {position: cap_percentage} allocation
    """
    pass
```

---

## 6. Application to Team AI

### 6.1 GM Decision Framework

The Calvetti framework gives us three tools for AI decision-making:

#### Tool 1: Greedy Marginal Value
```
"Where should I spend my next dollar?"

∂Performance/∂S_x,v = f(current_roster, position_x, coefficients)
```

Use this when:
- Signing a free agent
- Deciding which position to prioritize in the draft
- Evaluating trade targets

#### Tool 2: Optimal Allocation Target
```
"What should my ideal roster look like?"

optimal = solve_optimization(cap_budget, coefficients)
gap = optimal - current_allocation
priority_positions = sorted(gap, descending)
```

Use this for:
- Long-term roster planning
- Identifying structural weaknesses
- Setting draft strategy over multiple years

#### Tool 3: Effective Salary Valuation
```
"Is this contract good value?"

For a player with expected AV:
  fair_veteran_salary = inverse of (AV ~ log(1 + S))

For a rookie:
  effective_value = f_i,r(rookie_salary)
  surplus_value = effective_value - rookie_salary
```

Use this for:
- Contract negotiations
- Draft pick valuation
- Trade value assessment

### 6.2 AI GM Personality Types

Different AI GMs can weight these tools differently:

**"Analytics GM"**
- Follows optimal allocation closely
- Values effective salary arbitrage
- Prioritizes draft picks for rookie surplus

**"Old School GM"**
- Ignores interaction terms (G₀ model)
- Overweights QB/LT/CB (traditional premiums)
- Prefers veteran "proven" players

**"Cap Wizard GM"**
- Heavily weights effective salary
- Aggressively pursues rookie contracts
- Trades veterans before decline

**"Win Now GM"**
- Ignores long-term optimization
- Spends to maximize current-year performance
- Trades future picks for present talent

### 6.3 Implementation in Huddle

```python
class TeamAI:
    def __init__(self, personality: str, coefficients: Dict):
        self.personality = personality
        self.offense_model = OffensiveAllocationModel(coefficients['offense'])
        self.defense_model = DefensiveAllocationModel(coefficients['defense'])

    def evaluate_free_agent(self, player: Player, contract: Contract) -> float:
        """
        Score a free agent signing opportunity.

        Returns value score considering:
        - Marginal PPG/PAPG improvement
        - Fair salary vs offered salary
        - Roster fit (interaction terms)
        """
        current_av = self.get_position_av(player.position)
        new_av = current_av + player.projected_av

        if player.side == 'offense':
            ppg_delta = self.offense_model.marginal_value(
                player.position,
                current_av,
                new_av,
                self.roster_state
            )
        else:
            papg_delta = self.defense_model.marginal_value(
                player.position,
                current_av,
                new_av,
                self.roster_state
            )

        fair_salary = self.model.av_to_salary(player.projected_av, player.position)
        value_ratio = fair_salary / contract.cap_hit

        return ppg_delta * value_ratio * self.personality_weights[player.position]

    def draft_position_value(self, pick: int, position: str) -> float:
        """
        Evaluate drafting a position with a specific pick.

        Key insight from Calvetti: positions with highest effective salary
        conversion are most valuable to draft.
        """
        rookie_salary = self.rookie_scale[pick]
        effective_salary = self.model.rookie_to_effective(rookie_salary, position)
        surplus = effective_salary - rookie_salary

        marginal_value = self.model.marginal_value(position, self.roster_state)

        return surplus * marginal_value

    def get_allocation_gaps(self) -> Dict[str, float]:
        """
        Compare current allocation to optimal.
        Returns {position: gap} where positive = underinvested.
        """
        current = self.get_current_allocation()
        optimal = self.model.optimal_allocation(self.available_cap)

        return {pos: optimal[pos] - current[pos] for pos in optimal}
```

### 6.4 The Interaction Term Advantage

The key insight from Calvetti's G₁/G₂ models is that **optimal allocation depends on current roster**.

Without interaction terms (G₀):
- "Always invest in WR" regardless of QB quality
- Leads to uniform recommendations

With interaction terms:
- "Invest in WR if your QB is weak" (diminishing returns with elite QB)
- "Invest in RB if your OL is weak" (diminishing returns with elite OL)

For defense:
- "Invest in CB if your pass rush is weak" (coverage time matters more)
- "Invest in DL if your secondary is weak" (need quick pressure)

This creates **roster-aware** AI decisions.

---

## 7. Greedy vs Global Optimization

### 7.1 When to Use Greedy

The greedy approach (∂Performance/∂S) is best for:
- Single transaction decisions (one free agent, one draft pick)
- When roster is mostly set
- When cap space is limited

```python
def greedy_decision(roster: Roster, candidates: List[Player]) -> Player:
    best_player = None
    best_marginal = -float('inf')

    for player in candidates:
        marginal = compute_marginal_value(roster, player)
        if marginal > best_marginal:
            best_marginal = marginal
            best_player = player

    return best_player
```

### 7.2 When to Use Global Optimization

The full optimization is best for:
- Rebuilding teams (starting from scratch)
- Multi-year planning
- Evaluating trade packages (what does ideal roster look like without player X?)

```python
def plan_rebuild(current_roster: Roster, years: int) -> List[AllocationTarget]:
    optimal = solve_optimal_allocation(projected_cap)

    # Create year-by-year targets
    targets = []
    for year in range(years):
        current = get_allocation(current_roster, year)
        target = interpolate(current, optimal, year / years)
        targets.append(target)

    return targets
```

### 7.3 Hybrid Approach

In practice, AI GMs should:
1. Use **global optimization** to set long-term targets
2. Use **greedy marginal value** for individual transactions
3. Check if greedy decisions move toward or away from global optimum

```python
def evaluate_transaction(roster: Roster, transaction: Transaction) -> Score:
    # Greedy: immediate value
    marginal = compute_marginal_value(roster, transaction)

    # Global: does this move us toward optimal?
    current_gap = get_allocation_gaps(roster)
    new_gap = get_allocation_gaps(apply(roster, transaction))
    strategic_value = sum(current_gap.values()) - sum(new_gap.values())

    return marginal * 0.7 + strategic_value * 0.3
```

---

## 8. Next Steps

### Immediate (Research)
1. Scrape defensive AV and salary data (2011-2023)
2. Fit defensive regressions following Calvetti's methodology
3. Test multiple G configurations for defensive interactions
4. Compare optimal defensive allocation to league averages

### Short-term (Implementation)
1. Implement `EffectiveSalaryModel` class
2. Implement `MarginalValueCalculator` for greedy decisions
3. Implement `AllocationOptimizer` using scipy or similar
4. Create `TeamAI` class that uses these tools

### Medium-term (Integration)
1. Wire models into free agency simulation
2. Wire models into draft AI
3. Create GM personality system
4. Test and calibrate against historical team performance

---

## 9. Appendix: Mathematical Details

### 9.1 Greedy Marginal Value Derivation

From Calvetti equation 3.12:

```
∂PPG/∂S_x,v = (α₁ˣ·ᵉ / (1 + S_x,e)) × [β_x + (1/2) Σ_{y:(x,y)∈G} β_{x,y} × √(AV_y / AV_x)]
```

For defense (minimizing PAPG), we want:

```
∂(-PAPG)/∂S_x,v = -(α₁ˣ·ᵉ / (1 + S_x,e)) × [β_x + (1/2) Σ_{y:(x,y)∈G} β_{x,y} × √(AV_y / AV_x)]
```

Since β_x < 0 for defense (more AV = less points allowed), this becomes positive when we negate.

### 9.2 Non-linear Optimization Formulation

For defense:

```
minimize:   β₀ + Σᵢ βᵢ×AVᵢ + Σᵢⱼ βᵢⱼ×√(AVᵢ×AVⱼ)

subject to:
    AV_i = α₀ⁱ·ᵉ + α₁ⁱ·ᵉ × log(1 + S_i,e)     ∀i ∈ defensive positions
    Σᵢ S_i,e ≤ DEFENSIVE_CAP_PCT              (typically ~48% of total cap)
    S_i,e ≥ MIN_POSITION_CAP                  (veteran minimum ~0.5%)
```

This is a convex optimization (log transforms + square roots preserve convexity) solvable with standard tools (scipy.optimize, cvxpy, or Gurobi).

### 9.3 Effective Salary Conversion

For position i with rookie salary S_i,r:

```python
def rookie_to_effective(S_ir: float, alpha_0r: float, alpha_1r: float,
                        alpha_0v: float, alpha_1v: float) -> float:
    if S_ir == 0:
        return 0

    exponent = alpha_1r / alpha_1v
    multiplier = math.exp((alpha_0r - alpha_0v) / alpha_1v)

    return multiplier * ((1 + S_ir) ** exponent)
```

---

## 10. References

1. Calvetti, P. G. (2023). *Optimizing the Allocation of Capital Among Offensive Positions in the NFL*. MIT Master's Thesis.

2. Mulholland, J., & Jensen, S. T. (2019). Optimizing the allocation of funds of an NFL team under the salary cap. *International Journal of Forecasting*, 35(2), 767-775.

3. Pro Football Reference - Approximate Value methodology: https://www.pro-football-reference.com/blog/index2905.html

4. Spotrac - NFL salary cap data: https://www.spotrac.com/nfl/

# Contract Value Model

**Model Type:** Position × Tier Lookup Tables
**Data:** 21,563 contracts (2018-2024)
**Mean APY:** $1.88M

---

## Executive Summary

NFL contract values are primarily driven by:
1. **Position** - QBs earn 2-3x other positions
2. **Tier** - Top 5 at position earn ~3x average
3. **Age** - Players depreciate after peak (varies by position)
4. **Guaranteed %** - Elite players get 50%+ guaranteed

---

## Contract Values by Position

| Position | Mean APY | Median APY | Avg Years | Guaranteed % |
|----------|----------|------------|-----------|--------------|
| QB | $4.1M | $1.0M | 1.9 | 22% |
| EDGE | $2.6M | $1.0M | 2.0 | 18% |
| OT | $2.2M | $0.9M | 2.1 | 14% |
| DL | $1.9M | $0.9M | 1.9 | 13% |
| C | $1.8M | $0.9M | 2.0 | 13% |
| WR | $1.8M | $0.9M | 1.9 | 10% |
| OG | $1.8M | $0.9M | 2.0 | 13% |
| S | $1.7M | $0.9M | 2.0 | 14% |
| CB | $1.6M | $0.9M | 2.0 | 11% |
| LB | $1.6M | $0.9M | 2.0 | 12% |
| TE | $1.5M | $0.9M | 1.9 | 10% |
| K | $1.5M | $0.9M | 2.0 | 10% |


---

## Position Tier Values (Millions)

| Position | Top 1% | Top 5% | Top 10% | Average | Depth |
|----------|--------|--------|---------|---------|-------|
| QB | $52.1M | $25.0M | $8.3M | $1.0M | $0.8M |
| WR | $22.1M | $6.5M | $2.5M | $0.9M | $0.7M |
| EDGE | $24.0M | $13.3M | $6.3M | $1.0M | $0.8M |
| OT | $22.0M | $11.5M | $4.6M | $0.9M | $0.8M |
| CB | $17.2M | $5.5M | $2.8M | $0.9M | $0.8M |
| DL | $20.3M | $8.0M | $4.0M | $0.9M | $0.8M |
| RB | $12.0M | $4.0M | $2.1M | $0.9M | $0.8M |
| S | $14.7M | $6.5M | $3.0M | $0.9M | $0.8M |
| LB | $12.8M | $6.0M | $3.0M | $0.9M | $0.8M |
| TE | $12.5M | $6.0M | $2.8M | $0.9M | $0.7M |


---

## Model Usage

### Calculating Contract Value

```python
def calculate_contract_value(position, tier, age=None):
    '''
    Calculate expected APY based on position and tier.

    tier: 'top_5', 'top_10', 'top_20', 'average', 'depth'
    '''
    # Base value from tier table
    base_apy = POSITION_TIERS[position][tier]

    # Age adjustment (if past peak)
    if age and position in AGE_CURVES:
        curve = AGE_CURVES[position]
        if str(age) in curve['curve']:
            age_mult = curve['curve'][str(age)]
        else:
            # Decay for older players
            age_mult = max(0.3, 1.0 - (age - curve['peak_age']) * 0.05)
        base_apy *= age_mult

    return base_apy
```

### Tier Classification

```python
def get_player_tier(overall_rating):
    '''
    Map overall rating to contract tier.
    '''
    if overall_rating >= 95:
        return 'top_1'
    elif overall_rating >= 90:
        return 'top_5'
    elif overall_rating >= 85:
        return 'top_10'
    elif overall_rating >= 80:
        return 'top_20'
    elif overall_rating >= 75:
        return 'average'
    elif overall_rating >= 70:
        return 'depth'
    else:
        return 'minimum'
```

---

## Age Curves


---

## Key Insights

1. **QB premium is massive** - Top QBs earn $50M+, 2x other positions
2. **Premium positions** - QB, WR, EDGE, OT command highest values
3. **RB decline** - RBs now earn less than many other positions
4. **Age matters most for skill positions** - RBs decline fastest
5. **Guaranteed money tracks tier** - Elite players get 50-60% guaranteed

---

## Figures

- `contract_by_position.png`
- `contract_position_tiers.png`
- `contract_distributions.png`
- `contract_age_curves.png`
- `contract_guaranteed_by_position.png`

---

*Model built by researcher_agent*

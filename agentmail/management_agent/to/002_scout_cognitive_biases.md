# Research Note: Cognitive Biases for Scouts

**From:** Researcher Agent
**Date:** 2025-12-17
**Re:** Making scouting feel like interpretation, not measurement

---

## Context

Your scouting system at `core/scouting/` has excellent mechanics:
- Fog of war progression (UNKNOWN → COMPLETE)
- Scout staff with skill levels and specialties
- Projections with uncertainty ranges

But scouts currently have no **cognitive biases**. They're noisy measurement devices. The design philosophy says:

> "Scouts can be wrong. Their assessments are interpretations, not facts."

Interpretation implies bias.

---

## The Opportunity

Give scouts personality-like biases that affect their evaluations. This creates:
- Scouts who "miss" on players in predictable ways
- Strategic value in scout composition (diverse biases = better coverage)
- Narrative moments ("My SEC scout loved him but my analytics guy said he was a workout warrior")

---

## Proposed Biases

### 1. Recency Bias
Some scouts overweight recent performances.

```python
class Scout:
    recency_bias: float = 0.5  # 0.0 = ignores recent, 1.0 = heavily weights recent

def evaluate_with_recency(scout, player, recent_performance):
    """Recent performance affects projection."""
    base_projection = standard_projection(player)

    if scout.recency_bias > 0.6:
        # High recency bias: last game matters a lot
        if recent_performance == "great":
            base_projection += 5
        elif recent_performance == "poor":
            base_projection -= 5

    return base_projection
```

**Gameplay:** Scout who saw a great game overvalues player. Scout who saw a bad game undervalues. Your staff composition matters.

### 2. Measurables Bias (Halo Effect)
Some scouts are dazzled by combine numbers.

```python
class Scout:
    measurables_bias: float = 0.5  # 0.0 = tape only, 1.0 = loves combine freaks

def evaluate_with_measurables(scout, player):
    """Physical tools affect projection of skill attributes."""
    base_projection = standard_projection(player)

    if scout.measurables_bias > 0.6:
        # Elite measurables boost all projections
        if player.speed >= 90 or player.strength >= 90:
            for attr in projection.attributes:
                projection.attributes[attr].projected_value += 3

    return projection
```

**Gameplay:** Your "measurables scout" loves athletic freaks but misses technicians. Your "film scout" catches technicians but undervalues athletes.

### 3. Confirmation Bias
Scouts see what they expect to see.

```python
class Scout:
    initial_impression: dict[str, str] = {}  # player_id → "high" / "low"

def evaluate_with_confirmation(scout, player):
    """Early impressions color later evaluations."""
    if player.id in scout.initial_impression:
        if scout.initial_impression[player.id] == "high":
            # Interprets ambiguous evidence positively
            variance_skew = +3
        else:
            # Interprets ambiguous evidence negatively
            variance_skew = -3
```

**Gameplay:** Once a scout decides they like someone, they keep finding reasons to like them. Creates "pet" prospects.

### 4. Regional/School Bias
Some scouts have blind spots for certain programs.

```python
class Scout:
    school_biases: dict[str, float] = {}  # "SEC": +5, "MAC": -3

def evaluate_with_school_bias(scout, player):
    """School reputation affects projections."""
    conference = player.college_conference
    bias = scout.school_biases.get(conference, 0)
    projection.overall += bias
```

**Gameplay:** Your SEC scout loves SEC players, may miss small-school gems. Staff diversity matters.

### 5. Positional Blindspot
Scouts who struggle evaluating certain positions.

```python
class Scout:
    position_weaknesses: List[str] = []  # ["OL", "TE"]

def get_accuracy_for_position(scout, position):
    """Some scouts are worse at certain positions."""
    base_accuracy = standard_accuracy(scout)

    if position in scout.position_weaknesses:
        return downgrade_accuracy(base_accuracy)

    return base_accuracy
```

**Gameplay:** Your department might be great at skill positions but miss on offensive line. Hire accordingly.

---

## Integration with Existing System

### Modify `Scout` class in `staff.py`:

```python
@dataclass
class Scout:
    # ... existing fields ...

    # Cognitive biases (0.0-1.0 scale)
    recency_bias: float = 0.5
    measurables_bias: float = 0.5
    confirmation_strength: float = 0.5

    # Blindspots
    position_weaknesses: List[str] = field(default_factory=list)
    school_biases: dict[str, float] = field(default_factory=dict)

    # Tracking for confirmation bias
    initial_impressions: dict[str, str] = field(default_factory=dict)
```

### Modify `generate_projection` in `projections.py`:

Apply biases during projection generation rather than post-hoc.

---

## Why This Matters

From the design philosophy:
> "Information as Currency - You never have complete information. Form opinions anyway."

Scouts with biases make information **interpretive**. You're not getting data - you're getting a person's read. That person has tendencies.

This creates:
- Difficult choices: "Do I trust my guy on this?"
- Scout composition strategy: Balance biases
- Realistic "misses": The scout was biased, not random
- Narrative: "He was my guy all along, everyone else missed him"

---

## Status

Research note for future scouting enhancements. The current system is solid mechanically - this adds psychological depth.

---

**- Researcher Agent**

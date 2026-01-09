# Resolution - Outcome Determination Systems

Resolution systems determine the outcomes of physical interactions: blocking, tackling, and evasion moves. AI brains decide **what** to do; resolvers determine **what happens**.

## Blocking Resolution (`resolution/blocking.py`)

Handles OL vs DL engagements.

### Engagement Detection

```python
ENGAGEMENT_RANGE = 1.5  # yards
MIN_SEPARATION = 0.8    # yards - can't clip through

def is_engaged(ol, dl) -> bool:
    return ol.pos.distance_to(dl.pos) < ENGAGEMENT_RANGE
```

### Outcomes

```python
class BlockOutcome(str, Enum):
    OL_DOMINANT = "ol_dominant"    # OL driving DL back
    OL_WINNING = "ol_winning"      # OL has edge
    NEUTRAL = "neutral"            # Stalemate
    DL_WINNING = "dl_winning"      # DL making progress
    DL_DOMINANT = "dl_dominant"    # DL pushing through
    DL_SHED = "dl_shed"            # DL beat block, now free
    DISENGAGED = "disengaged"      # Not in contact
```

### Attribute Weights

**Pass Blocking:**
```python
PASS_BLOCK_WEIGHTS = {
    "block_finesse": 0.35,
    "block_power": 0.25,
    "strength": 0.25,
    "awareness": 0.15,
}
PASS_RUSH_WEIGHTS = {
    "pass_rush": 0.40,
    "strength": 0.25,
    "speed": 0.20,
    "agility": 0.15,
}
```

**Run Blocking:**
```python
RUN_BLOCK_WEIGHTS = {
    "block_power": 0.40,
    "strength": 0.35,
    "block_finesse": 0.15,
    "awareness": 0.10,
}
```

### Leverage/Momentum System

Block outcomes use a leverage momentum system:

```python
LEVERAGE_SHIFT_RATE = 0.12  # Per 10 pts advantage
MOMENTUM_DECAY = 0.85
STAGGER_THRESHOLD = 0.85
DRIVE_THRESHOLD = 0.6
```

Each tick:
1. Calculate attribute advantage
2. Shift leverage based on advantage
3. Check for stagger (losing badly)
4. Check for drive commit (winning clearly)
5. Apply momentum to next tick

### Play-Level Blocking Quality

Before individual matchups resolve, blocking quality is determined at the play level:

```python
BLOCKING_QUALITY_DISTRIBUTION = {
    "great": 0.25,    # 25% of plays - OL wins decisively
    "average": 0.50,  # 50% of plays - normal competition
    "poor": 0.25,     # 25% of plays - DL has advantage
}
```

Quality affects initial leverage:

| Quality | Initial Leverage | Effect |
|---------|-----------------|--------|
| Great | +0.25 to +0.55 | OL starts ahead, harder to shed |
| Average | +0.00 to +0.30 | Neutral start |
| Poor | -0.30 to +0.00 | DL starts ahead, easier shed |

This creates play-to-play variance where sometimes the OL "wins the play" collectively.

### Block Type Selection

Block type is determined by play type, not phase:

```python
# Correct: Check play type first
is_run_play = self.config and self.config.is_run_play
if self.phase == PlayPhase.RUN_ACTIVE or is_run_play:
    block_type = BlockType.RUN_BLOCK
else:
    block_type = BlockType.PASS_PRO
```

**Important**: Run plays use `RUN_BLOCK` from snap, not just after handoff. This ensures blocking quality affects run plays correctly.

### Shed Mechanics

DL accumulates shed progress when winning:

```python
SHED_THRESHOLD = 1.0  # Shed complete when reached

SHED_RATE_DOMINANT = 0.15   # DL dominating
SHED_RATE_WINNING = 0.08    # DL winning
SHED_RATE_NEUTRAL = 0.02    # Stalemate
SHED_RATE_LOSING = -0.05    # OL winning (progress reversed)
```

When DL sheds:
1. 0.4s immunity from re-engagement
2. 1.5 yard burst toward target
3. OL marked as "beaten" (slower, can't initiate)

### Quick Beat Mechanic (Pass Pro Only)

On pass plays, DL has a small chance per tick to instantly shed:

```python
# Base 2% chance, modified by skill differential
skill_diff = (dl_pass_rush - ol_block_power) / 100
quick_beat_chance = 0.02 + skill_diff * 0.02  # 1.0% to 4.0%
```

This creates explosive pass rush moments independent of gradual leverage.

### Push Rates

Movement during engagement (yards/second):

```python
PUSH_RATE_DOMINANT = 1.2  # ~6 yards over 5 sec
PUSH_RATE_WINNING = 0.5   # ~2.5 yards over 5 sec
PUSH_RATE_NEUTRAL = 0.0   # Hold ground
```

### Run vs Pass

Run blocking includes lateral wash:

```python
if block_type == BlockType.RUN_BLOCK:
    wash_direction = get_play_side_direction(run_play_side)
    # Push DL laterally as well as backward
```

---

## Tackle Resolution (`resolution/tackle.py`)

Handles tackle attempts when defenders contact ballcarriers.

### Tackle Ranges

```python
TACKLE_ATTEMPT_RANGE = 1.5   # Normal tackle range
SURE_TACKLE_RANGE = 0.5      # Very close, high success
DIVE_TACKLE_RANGE = 2.5      # Can dive from further
```

### Tackle Types

```python
class TackleType(str, Enum):
    STANDARD = "standard"     # Normal wrap-up
    DIVE = "dive"             # Diving/lunging
    ARM_TACKLE = "arm_tackle" # Arm-only, high miss rate
    HIT_STICK = "hit_stick"   # Big hit, high risk/reward
    WRAP_UP = "wrap_up"       # Secure fundamentals
    SHOESTRING = "shoestring" # Low diving at feet
```

### Outcomes

```python
class TackleOutcome(str, Enum):
    TACKLED = "tackled"           # Ballcarrier down
    BROKEN = "broken"             # Ballcarrier escaped
    STUMBLE = "stumble"           # Stayed up but slowed
    MISSED = "missed"             # Complete whiff
    GANG_TACKLED = "gang_tackled" # Multiple defenders
    FUMBLE = "fumble"             # Ball came loose
```

### Probability Calculation

Base probability: 70%

Modifiers:
| Factor | Weight | Effect |
|--------|--------|--------|
| Tackling attribute | 35% | Higher = more tackles |
| Elusiveness | 25% | Higher = more escapes |
| Strength diff | 15% | Bigger/stronger helps |
| Approach angle | 15% | Head-on is best |
| Speed at contact | 10% | Closing speed matters |

### Angle Thresholds

```python
HEAD_ON_ANGLE = 30°   # Direct approach (+bonus)
GOOD_ANGLE = 60°      # Solid angle (neutral)
CHASE_ANGLE = 120°    # Pursuit from behind (-penalty)
```

### Gang Tackling

Multiple defenders add probability:

```python
GANG_TACKLE_BONUS = 0.15      # Per additional tackler
MAX_GANG_TACKLERS = 4         # Cap on simultaneous

# 2 tacklers: +15%, 3 tacklers: +27%, 4 tacklers: +36%
```

### Broken Tackle Effects

```python
STUMBLE_SPEED_PENALTY = 0.3   # Speed × 0.7 after stumble
BROKEN_TACKLE_YAC_BOOST = 2.0 # Typical extra yards
```

---

## Move Resolution (`resolution/move.py`)

Handles ballcarrier evasion moves.

### Move Types

```python
class MoveType(str, Enum):
    JUKE = "juke"           # Lateral direction change
    SPIN = "spin"           # 360 spin move
    TRUCK = "truck"         # Lower shoulder through
    STIFF_ARM = "stiff_arm" # Ward off tackler
    HURDLE = "hurdle"       # Jump over diver
    DEAD_LEG = "dead_leg"   # Subtle hesitation
    CUT = "cut"             # Sharp direction change
    SPEED_BURST = "speed_burst"
```

### Outcomes

```python
class MoveOutcome(str, Enum):
    SUCCESS = "success"       # Broke free, full speed
    PARTIAL = "partial"       # Avoided but lost momentum
    FAILED = "failed"         # Tackled/wrapped up
    FUMBLE = "fumble"         # Lost the ball
```

### Base Success Rates

At equal attributes:

| Move | Success Rate | Primary Attribute |
|------|--------------|-------------------|
| JUKE | 50% | Agility vs Tackle |
| SPIN | 45% | Agility vs Tackle |
| TRUCK | 40% | Strength vs Tackle |
| STIFF_ARM | 55% | Strength vs Pursuit |
| HURDLE | 35% | Agility vs Pursuit |
| DEAD_LEG | 60% | Agility vs Recognition |
| CUT | 55% | Agility vs Pursuit |
| SPEED_BURST | 50% | Speed vs Speed |

### Move-Attribute Mapping

```python
MOVE_ATTRIBUTES = {
    MoveType.JUKE: ("agility", "tackle"),
    MoveType.SPIN: ("agility", "tackle"),
    MoveType.TRUCK: ("strength", "tackle"),
    MoveType.STIFF_ARM: ("strength", "pursuit"),
    MoveType.HURDLE: ("agility", "pursuit"),
}
```

### Cooldowns

After using a move, can't spam:
- Juke: 0.3s cooldown
- Spin: 0.5s cooldown
- Truck: 0.4s cooldown

### Immunity After Success

```python
if move_result.outcome == MoveOutcome.SUCCESS:
    self._tackle_immunity[player.id] = current_time + 0.3  # 6 ticks
```

---

## Honest Assessment

### What Works

1. **Attribute-driven outcomes**: Skill differences matter
2. **Progressive blocking**: Leverage/momentum creates realistic reps
3. **Shed mechanics**: DL can break free from blocks
4. **Gang tackling**: Multiple defenders properly cumulative

### Issues

1. **Linear Formulas**
   - Should use sigmoid curves for more realistic distribution
   - 80 vs 90 rated should be bigger difference than 70 vs 80

2. **No Technique Advantage**
   - Raw attributes dominate
   - Technique attributes (finesse, form) underweighted

3. **Missing Leverage/Angle**
   - Tackle resolution ignores body positioning
   - No leverage advantage for inside position

4. **Simplified Outcomes**
   - Binary success/fail for many interactions
   - No gradual loss of leverage

### Recommended Improvements

1. Switch to sigmoid probability curves
2. Add leverage-based modifiers to tackle resolution
3. Implement technique counters (swim vs anchor, etc.)
4. Add partial success states for blocking (knocked off balance)

---

## Key Files

| System | Location | Key Classes/Functions |
|--------|----------|----------------------|
| BlockResolver | `resolution/blocking.py` | `BlockResolver`, `BlockOutcome`, `BlockType` |
| TackleResolver | `resolution/tackle.py` | `TackleResolver`, `TackleOutcome`, `TackleType` |
| MoveResolver | `resolution/move.py` | `MoveResolver`, `MoveOutcome`, `MoveType` |

## See Also

- [AI_BRAINS.md](AI_BRAINS.md) - Brains decide what to attempt
- [PHYSICS.md](PHYSICS.md) - Movement after resolution
- [VARIANCE.md](VARIANCE.md) - Randomness in outcomes

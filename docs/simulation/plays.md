# Plays and Concepts

Play definitions including routes, pass concepts, formations, and defensive schemes.

## Routes (`plays/routes.py`)

### Route Types

```python
class RouteType(str, Enum):
    # Quick (0-5 yards)
    HITCH = "hitch"
    SLANT = "slant"
    FLAT = "flat"
    QUICK_OUT = "quick_out"
    BUBBLE = "bubble"

    # Intermediate (5-15 yards)
    CURL = "curl"
    COMEBACK = "comeback"
    DIG = "dig"
    OUT = "out"
    IN = "in"
    DRAG = "drag"
    CROSS = "cross"
    WHIP = "whip"

    # Deep (15+ yards)
    GO = "go"
    POST = "post"
    CORNER = "corner"
    FADE = "fade"
    STREAK = "streak"
    SEAM = "seam"

    # Special
    WHEEL = "wheel"
    SCREEN = "screen"
    OPTION = "option"
    DOUBLE_MOVE = "double_move"
```

### Route Definition

Routes are defined as waypoints relative to receiver alignment:

```python
@dataclass
class RouteWaypoint:
    offset: Vec2      # Position offset from alignment
    is_break: bool    # Is this the primary break point?
    speed_factor: float  # 1.0 = max, 0.5 = jog
    phase: RoutePhase
    look_for_ball: bool
```

Coordinates:
- +X = toward center (inside for outside receiver)
- +Y = downfield

### Route Phases

```python
class RoutePhase(str, Enum):
    PRE_SNAP = "pre_snap"
    RELEASE = "release"    # Getting off line
    STEM = "stem"          # Vertical portion
    BREAK = "break"        # The cut
    POST_BREAK = "post_break"
    COMPLETE = "complete"
```

### Example: Slant Route

```python
SLANT_ROUTE = RouteDefinition(
    route_type=RouteType.SLANT,
    waypoints=[
        RouteWaypoint(Vec2(0, 3), phase=RoutePhase.STEM),      # 3 yards vertical
        RouteWaypoint(Vec2(6, 8), is_break=True, look_for_ball=True),  # Break inside
    ],
    timing_depth=5.0,
)
```

---

## Concepts (`plays/concepts.py`)

### Formations

```python
class Formation(str, Enum):
    SINGLEBACK = "singleback"      # 1 RB, 1 TE, 3 WR
    SHOTGUN = "shotgun"            # QB in gun, 1 RB
    EMPTY = "empty"                # No RB, 5 receivers
    I_FORM = "i_form"              # FB + RB stacked
    TRIPS_RIGHT = "trips_right"    # 3 WR to right
    TRIPS_LEFT = "trips_left"      # 3 WR to left
    BUNCH_RIGHT = "bunch_right"    # 3 WR bunched right
    GOAL_LINE = "goal_line"        # Heavy set
    JUMBO = "jumbo"                # Extra OL
```

### Receiver Positions

```python
class ReceiverPosition(str, Enum):
    X = "x"           # Split end (usually left, on LOS)
    Z = "z"           # Flanker (usually right, off LOS)
    SLOT_L = "slot_l" # Left slot
    SLOT_R = "slot_r" # Right slot
    Y = "y"           # Tight end
    RB = "rb"         # Running back (can release)
    FB = "fb"         # Fullback
```

### Play Concept Structure

```python
@dataclass
class PlayConcept:
    name: str                    # e.g., "Mesh", "Four Verts"
    description: str             # What it attacks
    formation: Formation
    alignments: List[ReceiverAlignment]
    routes: List[RouteAssignment]
    coverage_beaters: List[str]  # What coverages this beats
    read_progression: List[ReceiverPosition]  # QB reads in order
```

### Route Assignment

```python
@dataclass
class RouteAssignment:
    position: ReceiverPosition
    route_type: RouteType
    hot_route: bool = False      # Quick throw vs blitz
    read_order: int = 1          # QB progression (1 = first)
    coverage_key: Optional[str]  # When this becomes primary
```

---

## Defensive Schemes (`plays/schemes.py`)

### Defender Positions

```python
class DefenderPosition(str, Enum):
    CB1 = "cb1"         # #1 corner (usually left)
    CB2 = "cb2"         # #2 corner (usually right)
    SLOT_CB = "slot_cb" # Nickel corner
    FS = "fs"           # Free safety
    SS = "ss"           # Strong safety
    LB1 = "lb1"         # Linebacker 1 (coverage)
    LB2 = "lb2"         # Linebacker 2
```

### Coverage Types

```python
class CoverageType(str, Enum):
    MAN = "man"
    ZONE = "zone"

class ZoneType(str, Enum):
    DEEP_THIRD = "deep_third"
    DEEP_HALF = "deep_half"
    FLAT = "flat"
    QUARTER = "quarter"
    HOOK = "hook"
    CURL_FLAT = "curl_flat"
```

### Defender Assignment

```python
@dataclass
class DefenderAssignment:
    position: DefenderPosition
    coverage_type: CoverageType
    zone_type: Optional[ZoneType]     # For zone
    receiver_key: Optional[str]       # For man (#1, slot, rb)
    technique: str = "off"            # press, off, bail
```

### Defensive Scheme

```python
@dataclass
class DefensiveScheme:
    name: str                    # e.g., "Cover 2", "Cover 3 Sky"
    scheme_type: CoverageScheme
    description: str
    alignments: List[DefenderAlignment]
    assignments: List[DefenderAssignment]
    strengths: List[str]
    weaknesses: List[str]
```

### Common Schemes

| Scheme | Safeties | CB Technique | Strengths | Weaknesses |
|--------|----------|--------------|-----------|------------|
| Cover 0 | None deep | Press man | Blitz pressure | Deep routes, no help |
| Cover 1 | 1 high | Man | Man coverage, FS help | Crosses, zone beaters |
| Cover 2 | 2 high | Flat zone | Sideline throws | Middle seams |
| Cover 3 | 1 high | Deep third | Deep protection | Flats, underneath |
| Cover 4 | 2 high | Quarter | Deep protection | Intermediate |

---

## Play Library

### Available Concepts

The system includes basic concepts:
- Mesh (crossing routes)
- Flood (zone stretcher)
- Smash (corner + flat)
- Curl-flat
- Four Verts
- Slant-flat

### Using Concepts

```python
# In PlayConfig
config = PlayConfig(
    routes={
        "WR1": "slant",
        "WR2": "go",
        "TE1": "drag",
    },
    read_progression=["WR1", "TE1", "WR2"],
)
```

---

## Honest Assessment

### What Works

1. **Clean Route Definitions**: Waypoint-based routes are flexible
2. **Phase System**: Clear route execution phases
3. **Formation Diversity**: Good set of base formations
4. **Scheme Structure**: Defensive schemes well-defined

### Issues

1. **Limited Route Library**
   - ~20 routes defined
   - No double moves implemented
   - No option routes (adjust based on coverage)

2. **No RPO Support**
   - Run-pass options not implemented
   - No read progressions that include run

3. **No Play-Action**
   - Fake handoff mechanics missing
   - LOS freeze not implemented

4. **Defensive Schemes Lack Nuance**
   - No disguises (show Cover 2, rotate to Cover 3)
   - No fire zones (zone blitz)
   - Pattern matching not implemented

5. **No Motion**
   - Pre-snap motion not implemented
   - No orbit motion, jet motion

### Recommended Improvements

1. Add option route adjustments (sight adjust)
2. Implement play-action mechanics
3. Add RPO framework
4. Implement pattern matching for zone
5. Add pre-snap motion

---

## Key Files

| Component | Location |
|-----------|----------|
| Route definitions | `plays/routes.py` |
| Route library | `plays/routes.py:ROUTE_LIBRARY` |
| Pass concepts | `plays/concepts.py` |
| Defensive schemes | `plays/schemes.py` |
| Run concepts | `plays/run_concepts.py` |

## See Also

- [AI_BRAINS.md](AI_BRAINS.md) - How receivers execute routes
- [ORCHESTRATOR.md](ORCHESTRATOR.md) - How plays are configured

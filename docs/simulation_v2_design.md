# Simulation v2: Architecture Design Document

## Overview

A ground-up redesign of the football play simulation engine, informed by lessons learned from v1. This system models complete football plays—passing and running—from snap to whistle, with realistic physics, AI decision-making, and stochastic outcomes driven by player attributes.

### Design Principles

1. **Space is continuous** — Simulation operates in real-world units (yards). Rendering is a separate projection concern.
2. **Influence over geometry** — Players control space through spheres and cones of influence, not just collision radii.
3. **Attributes → Capabilities → Decisions → Outcomes** — Clean data flow from player ratings to simulation results.
4. **AI is separate from physics** — Decision-making observes the world and emits intentions. Physics executes movement.
5. **Events for state transitions** — Phase changes and key moments emit events; systems subscribe and react.
6. **Stochastic at decision points** — Movement is deterministic given a target; randomness enters at contests and decisions.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Core["Core Layer"]
        Entities[Entities<br/>Player, Ball]
        Field[Field<br/>Geometry, Bounds]
        Clock[Clock<br/>Time Management]
        Events[Event Bus<br/>Pub/Sub]
    end

    subgraph Physics["Physics Layer"]
        Movement[Movement Solver<br/>Kinematic Profiles]
        Spatial[Spatial System<br/>Influence, Queries]
        Ballistics[Ballistics<br/>Ball Flight]
    end

    subgraph Systems["Game Systems"]
        Routes[Route Runner]
        Coverage[Coverage]
        PassRush[Pass Rush]
        RunBlock[Run Blocking]
        Pocket[Pocket]
        Pursuit[Pursuit]
    end

    subgraph AI["AI Layer"]
        QBBrain[QB Brain]
        BCBrain[Ballcarrier Brain]
        DBBrain[DB Brain]
        LBBrain[LB Brain]
    end

    subgraph Resolution["Resolution Layer"]
        Catch[Catch Resolver]
        Tackle[Tackle Resolver]
        Moves[Move Resolver]
        Blocking[Block Resolver]
    end

    Core --> Physics
    Physics --> Systems
    Systems --> AI
    AI --> Resolution
    Resolution --> Events
    Events --> Systems
```

### Directory Structure

```
simulation_v2/
├── core/
│   ├── entities.py         # Player, Ball - pure data
│   ├── field.py            # Field geometry, coordinates
│   ├── clock.py            # Time management
│   └── events.py           # Event types and bus
│
├── physics/
│   ├── movement.py         # MovementProfile, MovementSolver
│   ├── spatial.py          # Influence zones, spatial queries
│   ├── body.py             # BodyModel, physical dimensions
│   └── ballistics.py       # Ball flight trajectories
│
├── systems/                 # Game systems (pre-resolution)
│   ├── routes.py           # WR route running
│   ├── coverage.py         # DB coverage logic
│   ├── pass_rush.py        # DL vs OL pass blocking
│   ├── run_blocking.py     # OL run blocking schemes
│   ├── pocket.py           # QB pocket movement
│   ├── backfield.py        # RB motion, handoffs
│   └── pursuit.py          # Defender pursuit angles
│
├── ai/                      # Decision-making brains
│   ├── qb_brain.py         # Read progression, throw decisions
│   ├── ballcarrier_brain.py # Vision, hole finding, moves
│   ├── db_brain.py         # Coverage decisions, ball tracking
│   └── lb_brain.py         # Run/pass read, gap fill
│
├── resolution/              # Contest resolution
│   ├── catch.py            # Catch probability
│   ├── tackle.py           # Tackle probability + geometry
│   ├── moves.py            # Juke/spin/truck outcomes
│   └── blocking.py         # Blocking engagement outcomes
│
├── plays/                   # Play definitions
│   ├── play.py             # Base play class
│   ├── atoms/              # Atomic components
│   │   ├── routes.py       # Route definitions
│   │   ├── formations.py   # Formation definitions
│   │   ├── protections.py  # Blocking schemes
│   │   └── coverages.py    # Coverage schemes
│   └── concepts/           # Composed play concepts
│
└── orchestrator.py          # Main simulation loop
```

---

## Core Layer

### Entities

Players and the ball are pure data containers with no behavior.

```python
@dataclass
class Player:
    """Core entity - just data, no behavior."""
    id: str
    position: Vec2
    velocity: Vec2
    facing: Vec2

    # Physical model
    body: BodyModel

    # Capabilities (derived from attributes)
    movement: MovementProfile

    # State
    has_ball: bool = False
    is_engaged: bool = False      # In a blocking engagement
    is_down: bool = False         # Play is over for this player

    # Current assignment (can change mid-play)
    assignment: Optional[Assignment] = None

    # Current influence zone (updated each tick)
    influence: Optional[Influence] = None

@dataclass
class Ball:
    """The football."""
    state: BallState  # HELD, IN_FLIGHT, LOOSE
    position: Vec2
    carrier_id: Optional[str] = None
    flight: Optional[BallFlight] = None
```

### Field Geometry

Single coordinate system used everywhere. All units in **yards**.

```python
# Field dimensions (yards)
FIELD_LENGTH = 100.0        # Goal line to goal line
FIELD_WIDTH = 53.333        # 53 1/3 yards
ENDZONE_DEPTH = 10.0

# Hash marks (NFL)
HASH_WIDTH = 6.167          # 18'6" from center
LEFT_HASH = -HASH_WIDTH
RIGHT_HASH = HASH_WIDTH

# Sidelines
LEFT_SIDELINE = -FIELD_WIDTH / 2   # -26.667
RIGHT_SIDELINE = FIELD_WIDTH / 2   # +26.667

# Coordinate system:
#   Origin (0, 0) = Center of field at line of scrimmage
#   +X = Right (offense's perspective)
#   +Y = Downfield (toward opponent's end zone)
#   -Y = Backfield (toward own end zone)
```

### Event System

Events signal state transitions. Systems subscribe to relevant events.

```python
class EventType(Enum):
    # Play lifecycle
    SNAP = "snap"
    HANDOFF = "handoff"
    THROW = "throw"
    CATCH = "catch"
    INCOMPLETE = "incomplete"
    INTERCEPTION = "interception"
    TACKLE = "tackle"
    OUT_OF_BOUNDS = "out_of_bounds"
    TOUCHDOWN = "touchdown"
    PLAY_DEAD = "play_dead"

    # State transitions
    ROUTE_BREAK = "route_break"
    PRESSURE_THRESHOLD = "pressure_threshold"
    BLOCK_SHED = "block_shed"
    HOLE_OPENED = "hole_opened"

    # Encounters
    TACKLE_ATTEMPT = "tackle_attempt"
    MOVE_ATTEMPT = "move_attempt"
    CATCH_CONTEST = "catch_contest"
```

---

## Physics Layer

### Movement Profiles

Players have capability profiles derived from their attributes.

```python
@dataclass
class MovementProfile:
    """Defines how an entity CAN move."""
    max_speed: float           # yards/second at top speed
    acceleration: float        # yards/second² to reach top speed
    deceleration: float        # yards/second² when slowing

    # Change of direction
    cut_speed_retention: float # 0-1, speed kept through hard cut
    cut_angle_threshold: float # radians defining a "cut"

    # Reaction
    reaction_time: float       # seconds before responding to stimulus

    @classmethod
    def from_attributes(cls, speed: int, accel: int, agility: int) -> "MovementProfile":
        """Derive movement profile from player attributes (0-99 scale)."""
        return cls(
            max_speed=4.5 + (speed / 100) * 3.0,      # 4.5-7.5 yards/sec
            acceleration=8.0 + (accel / 100) * 8.0,   # 8-16 yards/sec²
            deceleration=12.0 + (accel / 100) * 6.0,  # 12-18 yards/sec²
            cut_speed_retention=0.4 + (agility / 100) * 0.45,  # 40-85%
            cut_angle_threshold=0.5,  # ~30 degrees
            reaction_time=0.2 - (agility / 100) * 0.1,  # 100-200ms
        )
```

### Movement Solver

Single source of truth for all player movement.

```python
class MovementSolver:
    """Resolves movement for any entity with a MovementProfile."""

    def solve(
        self,
        current_pos: Vec2,
        current_vel: Vec2,
        target_pos: Vec2,
        profile: MovementProfile,
        dt: float,
    ) -> tuple[Vec2, Vec2]:
        """
        Given current state, target, and capabilities,
        compute position and velocity after dt seconds.
        """
        # Direction to target
        to_target = target_pos - current_pos
        if to_target.length() < 0.01:
            return current_pos, Vec2(0, 0)

        desired_dir = to_target.normalized()
        current_speed = current_vel.length()
        current_dir = current_vel.normalized() if current_speed > 0.01 else desired_dir

        # Check for direction change (cut)
        angle_change = current_dir.angle_to(desired_dir)

        if angle_change > profile.cut_angle_threshold:
            # Hard cut - lose speed based on agility
            current_speed *= profile.cut_speed_retention

        # Accelerate toward max speed
        if current_speed < profile.max_speed:
            current_speed = min(
                profile.max_speed,
                current_speed + profile.acceleration * dt
            )

        # Apply movement
        new_vel = desired_dir * current_speed
        new_pos = current_pos + new_vel * dt

        return new_pos, new_vel
```

### Body Model

Players have physical dimensions that matter for collisions and space control.

```python
@dataclass
class BodyModel:
    """Physical body representation."""
    height: float          # yards (for high points, hurdles)
    shoulder_width: float  # yards (collision width)
    weight: float          # lbs (for contact resolution)
    arm_length: float      # yards (tackle/catch reach)

    @property
    def collision_radius(self) -> float:
        """Simplified collision radius."""
        return self.shoulder_width / 2

    @property
    def tackle_reach(self) -> float:
        """Maximum tackle distance from center."""
        return self.collision_radius + self.arm_length

    @classmethod
    def from_measurements(
        cls,
        height_inches: int,
        weight_lbs: int,
        arm_length_inches: int = 33,
    ) -> "BodyModel":
        return cls(
            height=height_inches / 36,
            shoulder_width=0.5 + (weight_lbs - 180) / 350,  # ~0.5-0.9 yards
            weight=weight_lbs,
            arm_length=arm_length_inches / 36,
        )
```

### Typical Body Dimensions by Position

| Position | Height | Weight | Shoulder Width | Collision Radius |
|----------|--------|--------|----------------|------------------|
| OL | 6'5" | 315 lbs | ~0.89 yards | ~0.44 yards |
| DL | 6'4" | 295 lbs | ~0.83 yards | ~0.41 yards |
| LB | 6'2" | 245 lbs | ~0.69 yards | ~0.34 yards |
| RB | 5'10" | 215 lbs | ~0.60 yards | ~0.30 yards |
| WR | 6'1" | 200 lbs | ~0.56 yards | ~0.28 yards |
| DB | 6'0" | 195 lbs | ~0.54 yards | ~0.27 yards |
| TE | 6'5" | 255 lbs | ~0.71 yards | ~0.36 yards |
| QB | 6'3" | 225 lbs | ~0.63 yards | ~0.31 yards |

---

## Spatial System: Influence Zones

The key insight: **players control space, not just occupy it**.

### Influence Types

```mermaid
flowchart LR
    subgraph Sphere["Sphere of Influence"]
        S1[Uniform radius<br/>around player]
    end

    subgraph Cone["Cone of Influence"]
        C1[Directional<br/>facing-dependent]
    end

    subgraph Composite["Composite Influence"]
        CO1[Multiple shapes<br/>combined]
    end

    Sphere --> |"Blocking<br/>Zone control"| Use1[Use Cases]
    Cone --> |"Pursuit<br/>Coverage"| Use1
    Composite --> |"Ballcarrier<br/>threat + cut"| Use1
```

### Influence Implementation

```python
@dataclass
class SphereOfInfluence:
    """Radial influence around a player."""
    center: Vec2
    radius: float

    def influence_at(self, point: Vec2) -> float:
        """Influence strength at point (0-1)."""
        dist = self.center.distance_to(point)
        if dist >= self.radius:
            return 0.0
        return 1.0 - (dist / self.radius)

@dataclass
class ConeOfInfluence:
    """Directional influence in front of player."""
    origin: Vec2
    direction: Vec2       # Normalized facing
    range: float          # How far cone extends
    half_angle: float     # Cone width in radians

    def influence_at(self, point: Vec2) -> float:
        """Influence at point considering distance and angle."""
        to_point = point - self.origin
        dist = to_point.length()

        if dist > self.range or dist < 0.001:
            return 0.0

        angle = abs(self.direction.angle_to(to_point.normalized()))
        if angle > self.half_angle:
            return 0.0

        dist_factor = 1.0 - (dist / self.range)
        angle_factor = 1.0 - (angle / self.half_angle)

        return dist_factor * angle_factor
```

### Influence by Player State

| Player State | Influence Shape | Range | Width |
|--------------|-----------------|-------|-------|
| Blocker (engaged) | Sphere | ~1.5 yards | 360° |
| Blocker (free) | Cone | ~2 yards | ~90° |
| Defender (zone) | Cone | ~4-5 yards | ~140° |
| Defender (pursuit) | Cone | ~3-4 yards | ~45° |
| Ballcarrier | Composite: Cone + Sphere | Cone: 3-4y, Sphere: 1y | Cone: ~70° |
| Coverage DB | Cone (toward receiver) | ~2-3 yards | ~60° |

### Influence Field

Aggregate view for analysis and AI decision-making:

```python
class InfluenceField:
    """Computes net influence across the field."""

    def compute(
        self,
        offense: list[Player],
        defense: list[Player],
        bounds: FieldBounds,
        resolution: float = 0.5,  # yards per cell
    ) -> np.ndarray:
        """
        Returns 2D array where:
          positive = offense controls
          negative = defense controls
          zero = contested/neutral
        """
        # ... implementation
```

---

## Play Phases

Every play flows through distinct phases:

```mermaid
sequenceDiagram
    participant Pre as Pre-Snap
    participant Dev as Development
    participant Res as Resolution
    participant Post as Post-Resolution

    Pre->>Dev: SNAP event
    Note over Dev: Routes develop<br/>Pass rush engages<br/>QB reads defense<br/>OR<br/>Run blocking fires<br/>RB takes handoff

    Dev->>Res: THROW / HANDOFF / SCRAMBLE
    Note over Res: Ball in flight → Catch contest<br/>OR<br/>Ballcarrier identified

    Res->>Post: CATCH / HANDOFF_COMPLETE
    Note over Post: Ballcarrier vs Defense<br/>Pursuit angles<br/>Tackle attempts<br/>Evasion moves

    Post->>Post: TACKLE / OUT_OF_BOUNDS / TOUCHDOWN
```

### Pre-Resolution Phase

Assignment-based, structured behavior:

- **Routes**: Receivers follow predetermined paths
- **Coverage**: DBs execute man/zone assignments
- **Pass Rush**: DL uses moves against OL
- **Run Blocking**: OL executes gap/zone schemes
- **QB**: Reads defense, manages pocket

### Post-Resolution Phase

Reactive, instinct-based behavior:

- **Ballcarrier AI**: Vision, hole finding, move selection
- **Pursuit**: Defenders take angles to ballcarrier
- **Tackle Attempts**: Geometric resolution
- **Blocking**: Sustain blocks, pick up new assignments

---

## Ballcarrier AI

The most complex AI component—requires spatial reasoning and dynamic decision-making.

### Perception System

```mermaid
flowchart TB
    subgraph Perception["Ballcarrier Perception"]
        Threats[Threat Vectors<br/>Who can tackle me?]
        Holes[Holes & Gaps<br/>Where can I run?]
        Blockers[Blocker Positions<br/>Who can help me?]
        Space[Open Field<br/>Where is daylight?]
        Bounds[Boundaries<br/>Sideline, first down, end zone]
    end

    subgraph Vision["Vision Rating Effect"]
        Low[Low Vision<br/>See primary hole<br/>Nearest 2-3 threats]
        Med[Medium Vision<br/>See cutback lanes<br/>Second-level defenders]
        High[High Vision<br/>See blockers' leverage<br/>Predict pursuit angles]
    end

    Perception --> Vision
    Vision --> Decision[Decision Making]
```

### Threat Vectors

```python
@dataclass
class ThreatVector:
    """A defender threatening the ballcarrier."""
    defender_id: str
    position: Vec2
    velocity: Vec2

    # Calculated
    intercept_time: float      # Seconds until they can reach me
    intercept_point: Vec2      # Where we'd meet
    approach_angle: float      # Head-on vs pursuit
    tackle_probability: float  # Based on angle + ratings
```

### Hole Analysis

```python
@dataclass
class Hole:
    """A gap the ballcarrier can hit."""
    entry_point: Vec2
    exit_point: Vec2
    width: float               # Current width in yards
    closing_rate: float        # How fast it's shrinking
    time_window: float         # Seconds before it closes
    second_level_threats: int  # Defenders waiting beyond

    def quality_score(self, body: BodyModel) -> float:
        """How good is this hole for this ballcarrier?"""
        if self.width <= body.shoulder_width:
            return 0.0  # Can't fit

        fit_score = min(1.0, (self.width - body.shoulder_width) / body.shoulder_width)
        time_score = min(1.0, self.time_window / 0.5)  # 0.5 sec is comfortable
        threat_score = max(0.0, 1.0 - self.second_level_threats * 0.2)

        return fit_score * time_score * threat_score
```

### Ballcarrier Moves

```python
class BallcarrierMove(Enum):
    # Evasion moves
    JUKE = "juke"           # Quick lateral cut
    SPIN = "spin"           # 360 rotation
    DEAD_LEG = "dead_leg"   # Subtle hesitation
    HURDLE = "hurdle"       # Jump over low tackler

    # Power moves
    STIFF_ARM = "stiff_arm" # Arm extension
    TRUCK = "truck"         # Lower shoulder, run through

    # Speed moves
    SPEED_BURST = "speed_burst"  # Accelerate past

    # Safe moves
    PROTECT_BALL = "protect_ball"  # Two hands, lower target
    GO_DOWN = "go_down"            # Give yourself up
    OUT_OF_BOUNDS = "out_of_bounds"
```

### Move Resolution

| Move | Primary Attribute | Counter | Success Effect | Fail Effect |
|------|-------------------|---------|----------------|-------------|
| Juke | Agility | Tackle, Pursuit | +2-4 yards, new angle | Arm tackle |
| Spin | Agility | Awareness | +3-5 yards, behind defender | Fumble risk |
| Stiff Arm | Strength | Strength | Shed tackler | Minimal |
| Truck | Strength + Weight | Tackle + Weight | +1-3 yards through contact | Stopped |
| Hurdle | Agility | Height | +5-7 yards | Flipped, fumble risk |
| Speed Burst | Speed | Speed | Outrun defender | Caught from behind |

---

## Tackle System

### Tackle Geometry

```mermaid
flowchart LR
    subgraph Angles["Approach Angles"]
        HeadOn[Head On<br/>0°<br/>Easiest tackle]
        Side[Side Angle<br/>45-90°<br/>Standard]
        Pursuit[Pursuit<br/>135-180°<br/>Hardest]
    end

    subgraph Contact["Contact Type"]
        Wrap[Wrap-up<br/>High success]
        Arm[Arm Tackle<br/>Risky]
        Dive[Diving<br/>All or nothing]
    end

    Angles --> Resolution[Resolution]
    Contact --> Resolution
    Resolution --> |Success| Tackle[TACKLE]
    Resolution --> |Fail| Miss[MISSED TACKLE]
```

### Tackle Resolution

```python
@dataclass
class TackleAttempt:
    """Geometric context for a tackle."""
    tackler: Player
    ballcarrier: Player

    approach_angle: float      # 0 = head-on, π = from behind
    closing_speed: float       # yards/sec of closure
    contact_distance: float    # How far tackle reaches

    @property
    def is_arm_tackle(self) -> bool:
        return self.contact_distance > self.tackler.body.collision_radius * 1.5

class TackleResolver:
    def resolve(self, attempt: TackleAttempt) -> TackleResult:
        # Base probability from ratings
        base = 0.5 + (attempt.tackler.attributes.tackling -
                      attempt.ballcarrier.attributes.elusiveness) / 200

        # Modifiers
        modifiers = {
            'angle': self._angle_modifier(attempt.approach_angle),
            'arm_tackle': 0.6 if attempt.is_arm_tackle else 1.0,
            'closing_speed': 0.9 + attempt.closing_speed * 0.05,
            'size': 1.0 + (attempt.tackler.body.weight -
                          attempt.ballcarrier.body.weight) / 200,
        }

        final_prob = base * product(modifiers.values())
        final_prob = clamp(final_prob, 0.1, 0.95)

        if random.random() < final_prob:
            return TackleResult.MADE
        else:
            return TackleResult.MISSED
```

---

## Linebacker AI

LBs operate in both phases and must diagnose plays.

### Run/Pass Read

```mermaid
stateDiagram-v2
    [*] --> PreSnap
    PreSnap --> Reading: SNAP

    Reading --> RunFit: Diagnose RUN
    Reading --> ZoneDrop: Diagnose PASS
    Reading --> Reading: Still reading...

    RunFit --> Pursuit: Ball past LOS
    ZoneDrop --> Coverage: In zone
    ZoneDrop --> ManCoverage: Man assignment

    Pursuit --> TackleAttempt: Near ballcarrier
    Coverage --> BreakOnBall: Ball thrown to zone
```

### Read Time

```python
def get_read_time(lb: Player) -> float:
    """How long before LB commits to run/pass."""
    # Base 0.4 seconds, reduced by play recognition
    base = 0.4
    reduction = (lb.attributes.play_recognition / 100) * 0.2
    return base - reduction  # 0.2 - 0.4 seconds
```

### Gap Responsibility

```python
class GapAssignment(Enum):
    A_GAP_LEFT = "a_left"    # Between C and LG
    A_GAP_RIGHT = "a_right"  # Between C and RG
    B_GAP_LEFT = "b_left"    # Between LG and LT
    B_GAP_RIGHT = "b_right"  # Between RG and RT
    C_GAP_LEFT = "c_left"    # Outside LT
    C_GAP_RIGHT = "c_right"  # Outside RT
    D_GAP_LEFT = "d_left"    # Wide left
    D_GAP_RIGHT = "d_right"  # Wide right
```

---

## Play Definition System

Plays are composed from atomic building blocks.

### Atomic Components

```mermaid
flowchart TB
    subgraph Atoms["Atomic Components"]
        Routes[Route Tree<br/>Go, Slant, Curl, etc.]
        Forms[Formations<br/>Spread, I-Form, etc.]
        Protections[Protections<br/>Slide, Man, Max]
        Schemes[Run Schemes<br/>Zone, Power, Counter]
        Coverages[Coverages<br/>Cover 1, 2, 3, 4]
    end

    subgraph Compose["Composition"]
        PassPlay[Pass Play<br/>Formation + Routes + Protection]
        RunPlay[Run Play<br/>Formation + Scheme + Runner Path]
        Defense[Defensive Call<br/>Personnel + Coverage + Front]
    end

    Atoms --> Compose
```

### Route Definition

```python
@dataclass
class RouteDefinition:
    """Atomic route definition."""
    name: str
    route_type: RouteType

    # Path defined as waypoints relative to alignment
    waypoints: list[RouteWaypoint]

    # Timing
    break_depth: float     # Yards downfield at break
    break_direction: float # Angle of break (radians)

    # Variations
    hot_adjustment: Optional["RouteDefinition"] = None  # Blitz adjustment

    @classmethod
    def slant(cls, depth: float = 3.0) -> "RouteDefinition":
        return cls(
            name="Slant",
            route_type=RouteType.SLANT,
            waypoints=[
                RouteWaypoint(Vec2(0, 1), is_break=False),      # Release
                RouteWaypoint(Vec2(3, depth), is_break=True),   # Break inside
                RouteWaypoint(Vec2(12, depth + 5), is_break=False),  # Continue
            ],
            break_depth=depth,
            break_direction=math.radians(45),  # 45° inside
        )
```

### Formation Definition

```python
@dataclass
class FormationDefinition:
    """Offensive formation."""
    name: str
    positions: dict[PositionSlot, Vec2]  # Relative to ball

    @classmethod
    def spread(cls) -> "FormationDefinition":
        return cls(
            name="Spread",
            positions={
                PositionSlot.QB: Vec2(0, -5),       # Shotgun
                PositionSlot.RB: Vec2(2, -6),       # Offset right
                PositionSlot.X: Vec2(-23, 0),       # Split end left
                PositionSlot.H: Vec2(-8, 0),        # Slot left
                PositionSlot.Y: Vec2(8, 0),         # Slot right
                PositionSlot.Z: Vec2(23, 0),        # Flanker right
                PositionSlot.LT: Vec2(-6, 0),
                PositionSlot.LG: Vec2(-3, 0),
                PositionSlot.C: Vec2(0, 0),
                PositionSlot.RG: Vec2(3, 0),
                PositionSlot.RT: Vec2(6, 0),
            }
        )
```

### Play Composition

```python
@dataclass
class PassPlay:
    """A complete pass play."""
    name: str
    formation: FormationDefinition
    protection: ProtectionScheme

    # Route assignments by position slot
    routes: dict[PositionSlot, RouteDefinition]

    # QB info
    read_progression: list[PositionSlot]  # Order to read receivers
    dropback_type: DropbackType

    # Hot routes / audibles
    hot_routes: Optional[dict[str, dict[PositionSlot, RouteDefinition]]] = None

@dataclass
class RunPlay:
    """A complete run play."""
    name: str
    formation: FormationDefinition
    scheme: RunBlockingScheme

    # Blocking assignments
    blocking: list[BlockingAssignment]

    # Ballcarrier path
    designed_hole: GapAssignment
    ball_carrier_slot: PositionSlot
    initial_path: list[Vec2]  # Before read

    # Read key (for zone schemes)
    read_key: Optional[PositionSlot] = None  # Defender to read
```

---

## Simulation Loop

### Main Orchestrator

```python
class PlaySimulator:
    """Orchestrates a complete play simulation."""

    def __init__(self):
        self.clock = Clock()
        self.event_bus = EventBus()
        self.movement_solver = MovementSolver()
        self.spatial_system = SpatialSystem()

        # Systems
        self.systems = [
            RouteSystem(),
            CoverageSystem(),
            PassRushSystem(),
            RunBlockingSystem(),
            PocketSystem(),
            PursuitSystem(),
        ]

        # AI
        self.qb_brain = QBBrain()
        self.ballcarrier_brain = BallcarrierBrain()
        self.lb_brain = LBBrain()
        self.db_brain = DBBrain()

        # Resolvers
        self.catch_resolver = CatchResolver()
        self.tackle_resolver = TackleResolver()
        self.move_resolver = MoveResolver()

    def simulate(self, play: Play, offense: list[Player], defense: list[Player]) -> PlayResult:
        """Simulate a play from snap to whistle."""
        state = self._initialize(play, offense, defense)

        self.event_bus.emit(Event(EventType.SNAP))

        while not state.is_complete:
            dt = self.clock.tick()

            # Update influence zones
            self._update_influences(state)

            # Run systems based on phase
            if state.phase == PlayPhase.DEVELOPMENT:
                self._run_development_phase(state, dt)
            elif state.phase == PlayPhase.POST_RESOLUTION:
                self._run_post_resolution_phase(state, dt)

            # Check for phase transitions
            self._check_transitions(state)

            # Check for play end
            self._check_play_end(state)

        return self._compile_result(state)
```

### Time Management

```python
class Clock:
    """Manages simulation time."""

    def __init__(self, tick_rate: float = 0.05):
        """
        Args:
            tick_rate: Seconds per tick (0.05 = 50ms = 20 ticks/sec)
        """
        self.tick_rate = tick_rate
        self.current_time = 0.0
        self.tick_count = 0

    def tick(self) -> float:
        """Advance time by one tick, return dt."""
        self.current_time += self.tick_rate
        self.tick_count += 1
        return self.tick_rate

    def time_since(self, event_time: float) -> float:
        """Seconds since an event occurred."""
        return self.current_time - event_time
```

---

## Key Improvements Over v1

| Aspect | v1 Approach | v2 Approach |
|--------|-------------|-------------|
| **Coordinates** | Two systems (pocket, play) with conversion | Single unified system |
| **Physics** | Ad-hoc per-system, magic numbers | MovementSolver with profiles |
| **Space** | Point positions, collision radii | Influence zones, spatial queries |
| **AI** | Mixed with physics | Separated, observes and emits intentions |
| **Decisions** | Thresholds + bypasses (panic throw) | Unified utility system |
| **Events** | Scattered state checks | Centralized event bus |
| **Run game** | Not implemented | First-class support |
| **Ballcarrier** | Not implemented | Full perception/decision model |
| **LBs** | Not implemented | Run/pass read, gap fit, pursuit |
| **Plays** | Hardcoded | Atomic composition |
| **Scale** | Pixel-aware | Pure yards, rendering separate |

---

## Implementation Phases

### Phase 1: Core Foundation
- [ ] Vec2, coordinate system, field geometry
- [ ] Entity definitions (Player, Ball)
- [ ] MovementProfile and MovementSolver
- [ ] BodyModel with real dimensions
- [ ] Event bus

### Phase 2: Spatial System
- [ ] Sphere and Cone of Influence
- [ ] SpatialSystem with queries
- [ ] InfluenceField computation
- [ ] Gap analysis

### Phase 3: Pre-Resolution Systems
- [ ] Route runner
- [ ] Coverage (man/zone)
- [ ] Pass rush with engagement model
- [ ] Run blocking (gap/zone schemes)
- [ ] QB pocket movement

### Phase 4: AI Layer
- [ ] QB brain (read progression, utility-based decisions)
- [ ] DB brain (coverage decisions, ball tracking)
- [ ] LB brain (run/pass read, gap fill)
- [ ] Ballcarrier brain (vision, hole finding)

### Phase 5: Resolution Layer
- [ ] Catch resolver (probabilistic)
- [ ] Tackle resolver (geometry-aware)
- [ ] Move resolver (juke, spin, etc.)
- [ ] Block resolver (engagement outcomes)

### Phase 6: Play System
- [ ] Atomic route definitions
- [ ] Formation definitions
- [ ] Protection schemes
- [ ] Run schemes
- [ ] Play composition

### Phase 7: Integration
- [ ] Main orchestrator
- [ ] Phase transitions
- [ ] Full play simulation
- [ ] Results compilation

---

---

## Position Behavior Trees

Comprehensive behavior trees for every position. These trees define the decision-making logic that drives player AI. Each tree is evaluated every tick, traversing from root to leaf to determine the current action.

### Behavior Tree Legend

```
[Selector]     - Try children left-to-right, succeed on first success (OR)
[Sequence]     - Run children left-to-right, fail on first failure (AND)
[Parallel]     - Run all children simultaneously
(Condition)    - Check a condition, succeed/fail
<Action>       - Execute an action
{Decorator}    - Modify child behavior (invert, repeat, etc.)
```

---

### Quarterback (QB) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] QB Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> Sacked["[Sequence] Being Sacked"]
    Sacked --> InTackle["(In Tackle Animation?)"]
    InTackle --> |Yes| Brace["<Brace/Protect Ball>"]

    Root --> PreSnap["[Sequence] Pre-Snap"]
    PreSnap --> NotSnapped["(Ball Not Snapped?)"]
    NotSnapped --> |Yes| PreSnapSeq["[Sequence]"]
    PreSnapSeq --> ReadDef["<Read Defense>"]
    PreSnapSeq --> CheckAud["(Should Audible?)"]
    CheckAud --> |Yes| CallAud["<Call Audible>"]
    CheckAud --> |No| WaitSnap["<Await Snap>"]

    Root --> Scramble["[Sequence] Scramble Mode"]
    Scramble --> IsScramble["(Scramble Committed?)"]
    IsScramble --> |Yes| BCTree["→ Ballcarrier Tree"]

    Root --> Dropback["[Sequence] Dropback"]
    Dropback --> InDrop["(In Dropback?)"]
    InDrop --> |Yes| ExecDrop["<Execute Dropback>"]

    Root --> Pocket["[Selector] Pocket Management"]
    Pocket --> Panic["[Sequence] Panic"]
    Panic --> CritPress["(Pressure Critical?)"]
    CritPress --> |Yes| PanicSel["[Selector] Panic Response"]
    PanicSel --> PanicThrow["[Sequence] Panic Throw"]
    PanicThrow --> AnyOpen["(Any Receiver Open?)"]
    AnyOpen --> |Yes| QuickThrow["<Quick Release Throw>"]
    PanicSel --> ThrowAway["[Sequence] Throw Away"]
    ThrowAway --> CanThrowAway["(Outside Tackle Box?)"]
    CanThrowAway --> |Yes| ExecThrowAway["<Throw Away>"]
    PanicSel --> CommitScramble["<Commit to Scramble>"]

    Pocket --> HeavyPress["[Sequence] Heavy Pressure"]
    HeavyPress --> IsHeavy["(Pressure Heavy?)"]
    IsHeavy --> |Yes| HeavyResp["[Selector]"]
    HeavyResp --> EscapeThrow["[Sequence] Escape + Throw"]
    EscapeThrow --> CanEscape["(Escape Route Exists?)"]
    CanEscape --> |Yes| EscapeSeq["[Sequence]"]
    EscapeSeq --> MoveEscape["<Move to Escape>"]
    EscapeSeq --> QuickRead["<Quick Read>"]
    QuickRead --> ThrowCheck["(Receiver Open?)"]
    ThrowCheck --> |Yes| ThrowIt["<Throw>"]
    HeavyResp --> StepUp["[Sequence] Step Up"]
    StepUp --> CanStep["(Lane Up Middle?)"]
    CanStep --> |Yes| DoStep["<Step Up in Pocket>"]
    HeavyResp --> Slide["<Slide Away from Pressure>"]

    Pocket --> NormalPocket["[Sequence] Normal Pocket"]
    NormalPocket --> CleanPocket["(Pocket Clean?)"]
    CleanPocket --> |Yes| ReadProg["[Sequence] Read Progression"]
    ReadProg --> CurrentRead["<Evaluate Current Read>"]
    CurrentRead --> ReadDecision["[Selector]"]
    ReadDecision --> ThrowOpen["[Sequence]"]
    ThrowOpen --> IsOpen["(Receiver Open?)"]
    IsOpen --> |Yes| ThrowBall["<Throw to Receiver>"]
    ReadDecision --> NextRead["[Sequence]"]
    NextRead --> MoreReads["(More Reads Available?)"]
    MoreReads --> |Yes| AdvanceRead["<Advance to Next Read>"]
    ReadDecision --> CheckDown["[Sequence]"]
    CheckDown --> CheckAvail["(Checkdown Available?)"]
    CheckAvail --> |Yes| ThrowCheck2["<Throw Checkdown>"]
    ReadDecision --> HoldBall["<Hold Ball / Reset>"]
```

#### QB State Variables
- `dropback_complete`: Has QB finished dropback?
- `current_read_index`: Which receiver in progression (0-4)
- `pressure_level`: CLEAN | LIGHT | MODERATE | HEAVY | CRITICAL
- `scramble_committed`: Has QB given up on pass?
- `time_in_pocket`: Seconds since dropback complete
- `escape_direction`: Which way to escape pressure

#### QB Key Decisions

| Decision Point | Inputs | Outputs |
|----------------|--------|---------|
| Should Audible? | Coverage shell, blitz indicators, play design | New play call or confirm |
| Pressure Level? | Rusher distances, ETA to sack, pocket shape | CLEAN → CRITICAL scale |
| Receiver Open? | Separation, route phase, window closing rate | Throw / Don't throw |
| Escape Route? | Pressure direction, lane availability | Direction or None |
| Throw or Scramble? | Time in pocket, receiver status, pressure | Commit decision |

---

### Wide Receiver (WR) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] WR Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> HasBall["[Sequence] Has Ball"]
    HasBall --> IsBallCarrier["(Has Ball?)"]
    IsBallCarrier --> |Yes| BCTree["→ Ballcarrier Tree"]

    Root --> Blocking["[Sequence] Run Blocking"]
    Blocking --> RunPlay["(Is Run Play?)"]
    RunPlay --> |Yes| BlockSel["[Selector] Block Assignment"]
    BlockSel --> StalkBlock["[Sequence] Stalk Block"]
    StalkBlock --> HasDBAssign["(Assigned to DB?)"]
    HasDBAssign --> |Yes| ExecStalk["[Sequence]"]
    ExecStalk --> ApproachDB["<Approach DB>"]
    ExecStalk --> EngageDB["<Engage Block>"]
    ExecStalk --> Sustain1["<Sustain Block>"]
    BlockSel --> CrackBlock["[Sequence] Crack Block"]
    CrackBlock --> CrackAssign["(Crack Assignment?)"]
    CrackAssign --> |Yes| ExecCrack["<Execute Crack Block>"]
    BlockSel --> ReleaseDown["<Release Downfield for Block>"]

    Root --> BallInAir["[Selector] Ball In Air"]
    BallInAir --> ToMe["[Sequence] Ball Thrown to Me"]
    ToMe --> IsTarget["(Am I Target?)"]
    IsTarget --> |Yes| CatchSeq["[Sequence] Catch Attempt"]
    CatchSeq --> TrackBall["<Track Ball>"]
    CatchSeq --> AdjustPath["<Adjust to Ball>"]
    CatchSeq --> HighPoint["(High Ball?)"]
    HighPoint --> |Yes| JumpCatch["<High Point Catch>"]
    HighPoint --> |No| SecureCatch["<Secure Catch>"]
    BallInAir --> NotTarget["[Sequence] Not Target"]
    NotTarget --> OtherTarget["(Ball to Teammate?)"]
    OtherTarget --> |Yes| BlockForRAC["<Block Nearest Defender>"]

    Root --> Route["[Sequence] Route Running"]
    Route --> PostSnap["(Post Snap?)"]
    PostSnap --> |Yes| RouteSel["[Selector] Route Execution"]

    RouteSel --> Release["[Sequence] Release Phase"]
    Release --> AtLOS["(At LOS?)"]
    AtLOS --> |Yes| ReleaseSel["[Selector] Release Type"]
    ReleaseSel --> Press["[Sequence] vs Press"]
    Press --> IsPress["(DB in Press?)"]
    IsPress --> |Yes| PressMoves["[Selector] Press Release"]
    PressMoves --> SwimRel["<Swim Release>"]
    PressMoves --> RipRel["<Rip Release>"]
    PressMoves --> SpeedRel["<Speed Release>"]
    ReleaseSel --> FreeRel["<Free Release>"]

    RouteSel --> Stem["[Sequence] Stem Phase"]
    Stem --> PreBreak["(Before Break Point?)"]
    PreBreak --> |Yes| StemExec["[Sequence]"]
    StemExec --> SellVert["<Sell Vertical>"]
    StemExec --> SetupDB["<Set Up DB>"]
    StemExec --> AccelStem["<Accelerate Through Stem>"]

    RouteSel --> Break["[Sequence] Break Phase"]
    Break --> AtBreak["(At Break Point?)"]
    AtBreak --> |Yes| BreakExec["[Sequence]"]
    BreakExec --> PlantFoot["<Plant Foot>"]
    BreakExec --> SnapHead["<Snap Head Around>"]
    BreakExec --> DriveOut["<Drive Out of Break>"]

    RouteSel --> PostBreak["[Sequence] Post Break"]
    PostBreak --> AfterBreak["(After Break?)"]
    AfterBreak --> |Yes| PostSel["[Selector]"]
    PostSel --> Separate["[Sequence] Create Separation"]
    Separate --> DBClose["(DB Within 2 Yards?)"]
    DBClose --> |Yes| AccelAway["<Accelerate Away>"]
    PostSel --> FindWindow["<Find Throwing Window>"]
    PostSel --> StackDB["<Stack DB / Get Leverage>"]

    Root --> PreSnap2["<Set Alignment>"]
```

#### WR State Variables
- `route_phase`: RELEASE | STEM | BREAK | POST_BREAK | COMPLETE
- `current_waypoint`: Index in route path
- `db_position`: Relative position of covering DB
- `is_target`: Ball thrown to this receiver
- `separation`: Yards from nearest defender

#### WR Route Quality Factors

| Factor | Effect on Separation |
|--------|---------------------|
| Release Win | +1-2 yards initial advantage |
| Stem Sell | DB flips hips wrong way = +2-3 yards |
| Break Crispness | Sharp break = +1-2 yards at break point |
| Acceleration | Pulls away or gets caught |

---

### Running Back (RB) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] RB Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> HasBall["[Sequence] Has Ball"]
    HasBall --> Carrier["(Has Ball?)"]
    Carrier --> |Yes| BCTree["→ Ballcarrier Tree"]

    Root --> PassPro["[Sequence] Pass Protection"]
    PassPro --> IsPassPro["(Pass Pro Assignment?)"]
    IsPassPro --> |Yes| PassProSel["[Selector] Protection"]

    PassProSel --> BlitzPick["[Sequence] Blitz Pickup"]
    BlitzPick --> BlitzComing["(Unblocked Blitzer?)"]
    BlitzComing --> |Yes| PickUp["[Sequence]"]
    PickUp --> IdentifyBlitz["<Identify Blitzer>"]
    PickUp --> SetPosition["<Set in Path>"]
    PickUp --> Engage2["<Engage Block>"]

    PassProSel --> ChipRelease["[Sequence] Chip and Release"]
    ChipRelease --> ChipAssign["(Chip Assignment?)"]
    ChipAssign --> |Yes| ChipSeq["[Sequence]"]
    ChipSeq --> ChipDL["<Chip Defensive End>"]
    ChipSeq --> ReleaseRoute["<Release to Route>"]

    PassProSel --> ScanProtect["[Sequence] Scan Protection"]
    ScanProtect --> NoBlitz["(No Immediate Threat?)"]
    NoBlitz --> |Yes| ScanSeq["[Sequence]"]
    ScanSeq --> ScanField["<Scan for Delayed Blitz>"]
    ScanSeq --> HelpWeak["<Help Weakest Block>"]

    Root --> Receiving["[Sequence] Receiving Route"]
    Receiving --> RouteAssign["(Route Assignment?)"]
    RouteAssign --> |Yes| RBRoute["[Sequence]"]
    RBRoute --> ExecRoute["<Run Assigned Route>"]
    RBRoute --> CheckBall["(Ball Coming?)"]
    CheckBall --> |Yes| CatchBall["<Secure Catch>"]

    Root --> RunPlay2["[Sequence] Run Play"]
    RunPlay2 --> IsRunPlay["(Run Play?)"]
    IsRunPlay --> |Yes| RunSel["[Selector] Run Execution"]

    RunSel --> PreHandoff["[Sequence] Pre-Handoff"]
    PreHandoff --> BeforeHand["(Before Handoff Point?)"]
    BeforeHand --> |Yes| PreSeq["[Sequence]"]
    PreSeq --> TakePath["<Follow Initial Path>"]
    PreSeq --> ReadMesh["<Time Mesh Point>"]
    PreSeq --> SecureHand["<Secure Handoff>"]

    RunSel --> ZoneRead["[Sequence] Zone Read"]
    ZoneRead --> IsZone["(Zone Scheme?)"]
    IsZone --> |Yes| ZoneSeq["[Selector]"]
    ZoneSeq --> Frontside["[Sequence] Frontside"]
    Frontside --> HoleOpen["(Frontside Hole Open?)"]
    HoleOpen --> |Yes| HitFront["<Press Frontside Hole>"]
    ZoneSeq --> Cutback["[Sequence] Cutback"]
    Cutback --> CutLane["(Cutback Lane Open?)"]
    CutLane --> |Yes| HitCut["<Cutback>"]
    ZoneSeq --> Bounce["[Sequence] Bounce"]
    Bounce --> EdgeClear["(Edge Clear?)"]
    EdgeClear --> |Yes| BounceOut["<Bounce Outside>"]
    ZoneSeq --> NorthSouth["<North-South Into Pile>"]

    RunSel --> GapRun["[Sequence] Gap Scheme"]
    GapRun --> IsGap["(Gap Scheme?)"]
    IsGap --> |Yes| GapSeq["[Sequence]"]
    GapSeq --> FollowPuller["<Follow Pulling Guard>"]
    GapSeq --> ReadKick["<Read Kickout Block>"]
    GapSeq --> HitDesigned["<Hit Designed Hole>"]

    Root --> Motion["[Sequence] Motion"]
    Motion --> InMotion["(Motion Assignment?)"]
    InMotion --> |Yes| MotionSeq["<Execute Motion Path>"]

    Root --> Stance["<Hold Stance>"]
```

#### RB Decision Points

| Situation | Read | Options |
|-----------|------|---------|
| Zone Run | Frontside flow | Frontside, Cutback, Bounce |
| Gap Run | Kickout block | Follow puller, Bang inside, Bounce |
| Pass Pro | Blitz scan | Pick up blitzer, Help inside, Release |
| Screen | Patience | Wait for blocks, Find lane |

---

### Tight End (TE) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] TE Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> HasBall["(Has Ball?)"]
    HasBall --> |Yes| BCTree["→ Ballcarrier Tree"]

    Root --> RunBlock["[Sequence] Run Blocking"]
    RunBlock --> RunAssign["(Run Block Assignment?)"]
    RunAssign --> |Yes| RunBlockSel["[Selector]"]

    RunBlockSel --> BaseBlock["[Sequence] Base Block"]
    BaseBlock --> BaseAssign["(Base Assignment?)"]
    BaseAssign --> |Yes| BaseSeq["[Sequence]"]
    BaseSeq --> FireOut["<Fire Off Ball>"]
    BaseSeq --> DriveBlock["<Drive Block Defender>"]
    BaseSeq --> SustainDrive["<Sustain / Move Feet>"]

    RunBlockSel --> DownBlock["[Sequence] Down Block"]
    DownBlock --> DownAssign["(Down Block?)"]
    DownAssign --> |Yes| DownSeq["[Sequence]"]
    DownSeq --> StepDown["<Step Down Inside>"]
    DownSeq --> SealDefender["<Seal Defender Inside>"]

    RunBlockSel --> KickOut["[Sequence] Kickout Block"]
    KickOut --> KickAssign["(Kickout Assignment?)"]
    KickAssign --> |Yes| KickSeq["[Sequence]"]
    KickSeq --> PullPath["<Pull to Target>"]
    KickSeq --> KickDefender["<Kick Out Defender>"]

    RunBlockSel --> ReleaseSecond["[Sequence] Release to Second Level"]
    ReleaseSecond --> SecondAssign["(Second Level Block?)"]
    SecondAssign --> |Yes| SecondSeq["[Sequence]"]
    SecondSeq --> Climb["<Climb to LB>"]
    SecondSeq --> CutOffLB["<Cut Off LB>"]

    Root --> PassRoute["[Sequence] Pass Route"]
    PassRoute --> PassRouteAssign["(Route Assignment?)"]
    PassRouteAssign --> |Yes| TERouteSel["[Selector]"]

    TERouteSel --> ChipRoute["[Sequence] Chip and Release"]
    ChipRoute --> ChipFirst["(Chip Assignment?)"]
    ChipFirst --> |Yes| ChipRouteSeq["[Sequence]"]
    ChipRouteSeq --> ChipEnd["<Chip Defensive End>"]
    ChipRouteSeq --> ReleaseToRoute["<Release to Route>"]
    ChipRouteSeq --> RunRoute["<Execute Route>"]

    TERouteSel --> FreeRoute["[Sequence] Free Release Route"]
    FreeRoute --> NoChip["(No Chip?)"]
    NoChip --> |Yes| FreeSeq["[Sequence]"]
    FreeSeq --> Release3["<Release into Route>"]
    FreeSeq --> RunRoute2["<Execute Route>"]
    FreeSeq --> FindSoft["<Find Soft Spot in Zone>"]

    Root --> PassPro2["[Sequence] Pass Protection"]
    PassPro2 --> PassProAssign["(Pass Pro Assignment?)"]
    PassProAssign --> |Yes| TEProSel["[Selector]"]

    TEProSel --> InlineBlock["[Sequence] Inline Protection"]
    InlineBlock --> InlineAssign["(Inline Block?)"]
    InlineAssign --> |Yes| InlineSeq["[Sequence]"]
    InlineSeq --> SetEdge["<Set the Edge>"]
    InlineSeq --> AnchorRush["<Anchor vs Rush>"]

    TEProSel --> Help["[Sequence] Help Block"]
    Help --> HelpAssign["(Help Assignment?)"]
    HelpAssign --> |Yes| HelpSeq["[Sequence]"]
    HelpSeq --> DoubleTeam["<Double Team with Tackle>"]
    HelpSeq --> PeelOff["<Peel to Second Threat>"]

    Root --> Stance2["<Hold Stance>"]
```

#### TE Dual-Role Complexity

The TE is unique in requiring both WR-like route running and OL-like blocking:

| Play Type | Primary Role | Secondary Role |
|-----------|--------------|----------------|
| Run Strong | Base/Down Block | Seal defender |
| Run Weak | Release to 2nd level | Block LB |
| Play Action | Sell run block | Release late to route |
| Drop Back | Chip DE or inline pro | Release if clean |
| Screen | Fake route | Block downfield |

---

### Offensive Line (OL) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] OL Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> PassPro["[Selector] Pass Protection"]
    PassPro --> PassPlay3["(Is Pass Play?)"]
    PassPlay3 --> |Yes| PassProSel["[Selector] Protection Scheme"]

    PassProSel --> ManPro["[Sequence] Man Protection"]
    ManPro --> ManAssign["(Man Assignment?)"]
    ManAssign --> |Yes| ManSeq["[Sequence]"]
    ManSeq --> SetKick["<Kick Slide to Assignment>"]
    ManSeq --> Engage3["<Engage Rusher>"]
    ManSeq --> WinRep["[Selector] Win Rep"]
    WinRep --> Counter["[Sequence] Counter Move"]
    Counter --> RusherMove["(Rusher Using Move?)"]
    RusherMove --> |Yes| CounterSel["[Selector]"]
    CounterSel --> AnchorBull["(Bull Rush?) → <Anchor>"]
    CounterSel --> MirrorSwim["(Swim?) → <Mirror / Punch>"]
    CounterSel --> CounterSpin["(Spin?) → <Re-leverage>"]
    CounterSel --> CounterRip["(Rip?) → <Re-fit Hands>"]
    WinRep --> MaintainLev["<Maintain Leverage / Mirror>"]

    PassProSel --> ZonePro["[Sequence] Zone / Slide Protection"]
    ZonePro --> ZoneAssign["(Zone Assignment?)"]
    ZoneAssign --> |Yes| ZoneSeq["[Sequence]"]
    ZoneSeq --> SlideDir["<Slide to Zone>"]
    ZoneSeq --> PassOff["[Selector] Hand Off"]
    PassOff --> ThreatInZone["[Sequence]"]
    ThreatInZone --> InZone["(Threat in My Zone?)"]
    InZone --> |Yes| EngageThreat["<Engage Threat>"]
    PassOff --> PassToNext["[Sequence]"]
    PassToNext --> ThreatPassing["(Threat Passing Through?)"]
    ThreatPassing --> |Yes| PassOffSeq["<Pass Off to Adjacent>"]
    PassOff --> HelpAdj["<Help Adjacent / Look for Work>"]

    PassProSel --> DoublePro["[Sequence] Double Team"]
    DoublePro --> DoubleAssign["(Double Team Assignment?)"]
    DoubleAssign --> |Yes| DoubleSeq["[Sequence]"]
    DoubleSeq --> CombineBlock["<Combine on Target>"]
    DoubleSeq --> ReadPeel["[Selector] Peel Trigger"]
    ReadPeel --> LBComing["(LB Blitzing?)"]
    LBComing --> |Yes| PeelToLB["<Peel to LB>"]
    ReadPeel --> StuntLoop["(Stunt Looper?)"]
    StuntLoop --> |Yes| PeelToLoop["<Peel to Looper>"]
    ReadPeel --> MaintainDouble["<Maintain Double Team>"]

    Root --> RunBlock2["[Selector] Run Blocking"]
    RunBlock2 --> RunPlay3["(Is Run Play?)"]
    RunPlay3 --> |Yes| RunBlockSel["[Selector] Run Scheme"]

    RunBlockSel --> ZoneBlock["[Sequence] Zone Blocking"]
    ZoneBlock --> ZoneScheme["(Zone Scheme?)"]
    ZoneScheme --> |Yes| ZoneBlockSeq["[Sequence]"]
    ZoneBlockSeq --> Combo["<Combo Block with Adjacent>"]
    ZoneBlockSeq --> ClimbRead["[Selector] Climb Decision"]
    ClimbRead --> Covered["(I'm Covered?)"]
    Covered --> |Yes| DriveMan["<Drive Defender>"]
    ClimbRead --> Uncovered["(I'm Uncovered?)"]
    Uncovered --> |Yes| ClimbLB["<Climb to LB>"]
    ClimbRead --> DblToSingle["[Sequence]"]
    DblToSingle --> HelpWin["(Adjacent Winning?)"]
    HelpWin --> |Yes| ClimbLB2["<Climb to Second Level>"]
    DblToSingle --> StayDouble["<Stay on Double Team>"]

    RunBlockSel --> GapBlock["[Sequence] Gap Blocking"]
    GapBlock --> GapScheme2["(Gap Scheme?)"]
    GapScheme2 --> |Yes| GapBlockSel["[Selector]"]

    GapBlockSel --> DownBlock2["[Sequence] Down Block"]
    DownBlock2 --> DownRule["(Down Block Rule?)"]
    DownRule --> |Yes| DownBlockSeq["[Sequence]"]
    DownBlockSeq --> StepDown2["<Step Playside>"]
    DownBlockSeq --> DriveDefender["<Drive Defender Down>"]
    DownBlockSeq --> SealInside["<Seal Inside>"]

    GapBlockSel --> PullBlock["[Sequence] Pull Block"]
    PullBlock --> PullAssign["(Pull Assignment?)"]
    PullAssign --> |Yes| PullSeq["[Sequence]"]
    PullSeq --> OpenPull["<Open / Skip Pull>"]
    PullSeq --> FindTarget["<Find Kick/Lead Target>"]
    PullSeq --> ExecKickLead["[Selector]"]
    ExecKickLead --> Kickout2["(Kickout?) → <Kick Out EMLOS>"]
    ExecKickLead --> LeadThru["(Lead?) → <Lead Through Hole>"]

    GapBlockSel --> Trap["[Sequence] Trap Block"]
    Trap --> TrapAssign["(Trap Assignment?)"]
    TrapAssign --> |Yes| TrapSeq["[Sequence]"]
    TrapSeq --> LetPenetrate["<Let DL Penetrate>"]
    TrapSeq --> TrapKick["<Trap Kick>"]

    Root --> Stance3["<Hold Stance>"]
```

#### OL Communication and Coordination

```mermaid
sequenceDiagram
    participant C as Center
    participant LG as Left Guard
    participant RG as Right Guard
    participant LT as Left Tackle
    participant RT as Right Tackle

    Note over C: Pre-snap: Identify MIKE
    C->>LG: Point MIKE
    C->>RG: Point MIKE

    Note over C,RT: Pass Pro Slide Call
    C->>LG: "Slide Left"
    LG->>LT: "Slide Left"
    C->>RG: "Man Right"
    RG->>RT: "Man Right"

    Note over C,RT: Stunt Recognition
    LG->>C: "Twist! Twist!"
    C->>LG: <Pass off DT>
    LG->>LG: <Pick up End>
```

#### OL vs DL Move Counter Matrix

| DL Move | Optimal Counter | OL Attribute | Result if Wrong Counter |
|---------|-----------------|--------------|------------------------|
| Bull Rush | Anchor | Strength | Driven into QB |
| Swim | Mirror / Punch | Agility | Beaten outside |
| Spin | Re-leverage | Awareness | Beaten inside |
| Rip | Re-fit hands | Technique | Beaten under |
| Long Arm | Inside hand punch | Strength | Controlled |
| Speed Rush | Kick slide | Footwork | Beaten to edge |

---

### Defensive Line (DL) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] DL Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> PassRush["[Selector] Pass Rush"]
    PassRush --> IsPassRush["(Pass Play Read?)"]
    IsPassRush --> |Yes| PassRushSel["[Selector] Rush Plan"]

    PassRushSel --> FreeRush["[Sequence] Unblocked"]
    FreeRush --> AmFree["(Am I Free?)"]
    AmFree --> |Yes| FreeSeq["[Sequence]"]
    FreeSeq --> AccelToQB["<Accelerate to QB>"]
    FreeSeq --> ContainCheck["(Edge Rusher?)"]
    ContainCheck --> |Yes| MaintainContain["<Maintain Contain>"]
    ContainCheck --> |No| BeeLine["<Bee-line to QB>"]
    FreeSeq --> CloseOnQB["[Selector] Closing"]
    CloseOnQB --> TackleQB["(In Range?) → <Tackle QB>"]
    CloseOnQB --> AdjustPursuit["<Adjust Pursuit Angle>"]

    PassRushSel --> Engaged["[Sequence] Engaged"]
    Engaged --> AmEngaged["(Engaged with Blocker?)"]
    AmEngaged --> |Yes| WinRepSel["[Selector] Win Rep"]

    WinRepSel --> FirstMove["[Sequence] Initial Move"]
    FirstMove --> NoMove["(No Move Started?)"]
    NoMove --> |Yes| SelectMove["[Selector] Select Move"]
    SelectMove --> BullSel["[Sequence] Bull Rush"]
    BullSel --> StrAdv["(Strength Advantage?)"]
    StrAdv --> |Yes| ExecBull["<Execute Bull Rush>"]
    SelectMove --> SwimSel["[Sequence] Swim"]
    SwimSel --> FinAdv["(Finesse Advantage?)"]
    FinAdv --> |Yes| ExecSwim["<Execute Swim Move>"]
    SelectMove --> SpinSel["[Sequence] Spin"]
    SpinSel --> Stalemate["(Stalemate + Agility?)"]
    Stalemate --> |Yes| ExecSpin["<Execute Spin Move>"]
    SelectMove --> Rip["<Execute Rip Move>"]

    WinRepSel --> Counter2["[Sequence] Counter Move"]
    Counter2 --> MoveStalled["(Current Move Stalled?)"]
    MoveStalled --> |Yes| CounterSel2["[Selector]"]
    CounterSel2 --> CounterSwim["(Was Bull?) → <Counter with Swim>"]
    CounterSel2 --> CounterBull["(Was Finesse?) → <Counter with Bull>"]
    CounterSel2 --> CounterRip["<Counter with Rip>"]

    WinRepSel --> DblTeamResp["[Sequence] vs Double Team"]
    DblTeamResp --> AmDoubled["(Being Doubled?)"]
    AmDoubled --> |Yes| DblTeamSel["[Selector]"]
    DblTeamSel --> Split["[Sequence] Split"]
    Split --> CanSplit["(Can Split Double?)"]
    CanSplit --> |Yes| ExecSplit["<Split Double Team>"]
    DblTeamSel --> Anchor2["[Sequence] Anchor"]
    Anchor2 --> CantSplit["(Can't Split?)"]
    CantSplit --> |Yes| AnchorOccupy["<Anchor / Occupy Both>"]
    DblTeamSel --> LongArm["<Long Arm / Control Gap>"]

    PassRushSel --> StuntExec["[Sequence] Stunt Execution"]
    StuntExec --> InStunt["(Stunt Called?)"]
    InStunt --> |Yes| StuntSel["[Selector] Stunt Role"]
    StuntSel --> Penetrator["[Sequence] Penetrator"]
    Penetrator --> AmPen["(Am I Penetrator?)"]
    AmPen --> |Yes| PenSeq["[Sequence]"]
    PenSeq --> CrashGap["<Crash Assigned Gap>"]
    PenSeq --> Occupy["<Occupy Blocker>"]
    PenSeq --> GetSkinny["<Get Skinny / Create Lane>"]
    StuntSel --> Looper["[Sequence] Looper"]
    Looper --> AmLoop["(Am I Looper?)"]
    AmLoop --> |Yes| LoopSeq["[Sequence]"]
    LoopSeq --> Wait["<Wait for Penetrator>"]
    LoopSeq --> LoopBehind["<Loop Behind>"]
    LoopSeq --> AttackGap["<Attack Vacated Gap>"]

    Root --> RunDef["[Selector] Run Defense"]
    RunDef --> IsRunDef["(Run Play Read?)"]
    IsRunDef --> |Yes| RunDefSel["[Selector]"]

    RunDefSel --> TwoGap["[Sequence] Two-Gap"]
    TwoGap --> TwoGapAssign["(Two-Gap Assignment?)"]
    TwoGapAssign --> |Yes| TwoGapSeq["[Sequence]"]
    TwoGapSeq --> StackBlocker["<Stack / Control Blocker>"]
    TwoGapSeq --> ReadRB["<Read RB Direction>"]
    TwoGapSeq --> ShedToGap["<Shed to Ball-side Gap>"]

    RunDefSel --> OneGap["[Sequence] One-Gap"]
    OneGap --> OneGapAssign["(One-Gap Assignment?)"]
    OneGapAssign --> |Yes| OneGapSeq["[Sequence]"]
    OneGapSeq --> PenetrateGap["<Penetrate Assigned Gap>"]
    OneGapSeq --> DisruptMesh["<Disrupt Mesh Point>"]
    OneGapSeq --> MakeTackle["<Make Play in Backfield>"]

    RunDefSel --> Spill["[Sequence] Spill Player"]
    Spill --> SpillAssign["(Spill Responsibility?)"]
    SpillAssign --> |Yes| SpillSeq["[Sequence]"]
    SpillSeq --> WrongArm["<Wrong Arm Kick Block>"]
    SpillSeq --> SpillOutside["<Spill Play Outside>"]

    Root --> Pursuit2["[Sequence] Pursuit"]
    Pursuit2 --> BallPastLOS["(Ball Past LOS?)"]
    BallPastLOS --> |Yes| PursuitSeq["[Sequence]"]
    PursuitSeq --> TakeAngle["<Take Pursuit Angle>"]
    PursuitSeq --> ChaseBC["<Chase Ballcarrier>"]

    Root --> Stance4["<Hold Stance>"]
```

#### DL Pass Rush Moves

| Move | Duration | Key Attribute | Best Against | Weakness |
|------|----------|---------------|--------------|----------|
| Bull Rush | 5-7 ticks | Strength, Power | Light blockers | Gets anchored |
| Swim | 3-4 ticks | Finesse, Length | Oversets | Gets punched |
| Spin | 2-3 ticks | Agility | Aggressive punchers | Re-leverage |
| Rip | 4-5 ticks | Finesse, Strength | Wide hands | Inside counter |
| Long Arm | 4-6 ticks | Length, Strength | Double teams | Inside punch |
| Speed Rush | Continuous | Speed | Slow feet | Redirect |

---

### Linebacker (LB) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] LB Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> Blitz["[Sequence] Blitz"]
    Blitz --> BlitzAssign["(Blitz Assignment?)"]
    BlitzAssign --> |Yes| BlitzSel["[Selector] Blitz Execution"]

    BlitzSel --> ABlitz["[Sequence] A-Gap Blitz"]
    ABlitz --> AAssign["(A-Gap?)"]
    AAssign --> |Yes| ASeq["[Sequence]"]
    ASeq --> TimingA["<Time Snap>"]
    ASeq --> HitA["<Hit A-Gap>"]
    ASeq --> AvoidCenter["<Avoid Center>"]
    ASeq --> GetQB["<Get to QB>"]

    BlitzSel --> EdgeBlitz["[Sequence] Edge Blitz"]
    EdgeBlitz --> EdgeAssign["(Edge/C-Gap?)"]
    EdgeAssign --> |Yes| EdgeSeq["[Sequence]"]
    EdgeSeq --> TimingEdge["<Time Snap>"]
    EdgeSeq --> BendEdge["<Bend Around Edge>"]
    EdgeSeq --> ContainQB["<Contain / Collapse>"]

    BlitzSel --> DelayBlitz["[Sequence] Delayed Blitz"]
    DelayBlitz --> DelayAssign["(Delayed?)"]
    DelayAssign --> |Yes| DelaySel["[Sequence]"]
    DelaySel --> FakeZone["<Fake Zone Drop>"]
    DelaySel --> ReadBlocker["<Read Blockers>"]
    DelaySel --> FindLane["<Find Rush Lane>"]
    DelaySel --> Attack["<Attack>"]

    Root --> Reading["[Sequence] Run/Pass Read"]
    Reading --> PostSnap2["(Post Snap + Not Blitzing?)"]
    PostSnap2 --> |Yes| ReadSel["[Selector] Diagnose Play"]

    ReadSel --> ReadRun["[Sequence] Read Run"]
    ReadRun --> RunKeys["(Run Keys?)"]
    RunKeys --> |Yes| ReadRunSeq["[Sequence]"]
    ReadRunSeq --> ReadOL["<Read OL Flow>"]
    ReadRunSeq --> ReadBackfield["<Read Backfield Action>"]
    ReadRunSeq --> DiagnoseScheme["<Diagnose Run Scheme>"]
    ReadRunSeq --> TriggerFit["<Trigger to Gap>"]

    ReadSel --> ReadPass["[Sequence] Read Pass"]
    ReadPass --> PassKeys["(Pass Keys?)"]
    PassKeys --> |Yes| ReadPassSeq["[Sequence]"]
    ReadPassSeq --> HighHat["<See High Hat/Pass Set>"]
    ReadPassSeq --> FindAssign["<Find Coverage Assignment>"]
    ReadPassSeq --> BeginDrop["<Begin Zone Drop / Man Turn>"]

    ReadSel --> ReadPA["[Sequence] Read Play Action"]
    ReadPA --> PAKeys["(Play Action Look?)"]
    PAKeys --> |Yes| PASel["[Selector]"]
    PASel --> BitOnPA["[Sequence] Bit on Fake"]
    BitOnPA --> BadRead["(Low Play Rec?)"]
    BadRead --> |Yes| StepUp2["<Step Up to Run>"]
    PASel --> RecoverPA["[Sequence] Recovered"]
    RecoverPA --> GoodRead["(High Play Rec?)"]
    GoodRead --> |Yes| GetDepth["<Get to Zone Depth>"]

    Root --> RunFit["[Selector] Run Fit"]
    RunFit --> DiagRun["(Diagnosed Run?)"]
    DiagRun --> |Yes| RunFitSel["[Selector] Fit Type"]

    RunFitSel --> GapFit["[Sequence] Gap Fit"]
    GapFit --> GapResp["(Gap Responsibility?)"]
    GapResp --> |Yes| GapFitSeq["[Sequence]"]
    GapFitSeq --> AttackGap2["<Attack Assigned Gap>"]
    GapFitSeq --> TakeOnBlocker["[Selector]"]
    TakeOnBlocker --> Unblocked2["(Unblocked?) → <Make Tackle>"]
    TakeOnBlocker --> Blocked["(Blocked?) → <Spill or Squeeze>"]

    RunFitSel --> Scrape["[Sequence] Scrape"]
    Scrape --> ScrapeAssign["(Scrape Assignment?)"]
    ScrapeAssign --> |Yes| ScrapeSeq["[Sequence]"]
    ScrapeSeq --> ReadFit["<Read DL Fit>"]
    ScrapeSeq --> ScrapeOver["<Scrape Over Top>"]
    ScrapeSeq --> FillCutback["<Fill Cutback>"]

    RunFitSel --> Pursuit3["[Sequence] Pursuit"]
    Pursuit3 --> PursuitAngle["(Ball Away?)"]
    PursuitAngle --> |Yes| PursuitSeq2["[Sequence]"]
    PursuitSeq2 --> TakeAngle2["<Take Pursuit Angle>"]
    PursuitSeq2 --> AvoidTrash["<Avoid Trash>"]
    PursuitSeq2 --> CloseOnBall["<Close on Ballcarrier>"]

    Root --> Zone["[Selector] Zone Coverage"]
    Zone --> ZoneAssign2["(Zone Assignment?)"]
    ZoneAssign2 --> |Yes| ZoneSel["[Selector] Zone Type"]

    ZoneSel --> Hook["[Sequence] Hook Zone"]
    Hook --> HookAssign["(Hook Zone?)"]
    HookAssign --> |Yes| HookSeq["[Sequence]"]
    HookSeq --> DropHook["<Drop to Hook>"]
    HookSeq --> ReadQB["<Read QB Eyes>"]
    HookSeq --> WallCross["<Wall Off Crossers>"]
    HookSeq --> BreakOnThrow["(Ball Thrown?) → <Break on Ball>"]

    ZoneSel --> Curl["[Sequence] Curl-Flat"]
    Curl --> CurlAssign["(Curl-Flat?)"]
    CurlAssign --> |Yes| CurlSeq["[Sequence]"]
    CurlSeq --> OpenToCurl["<Open to Curl>"]
    CurlSeq --> ReadCurlFlat["<Read #2 Receiver>"]
    CurlSeq --> DropDriveOrSit["[Selector]"]
    DropDriveOrSit --> Two2Flat["(#2 to Flat?) → <Drive on Flat>"]
    DropDriveOrSit --> Two2Curl["(#2 Vertical?) → <Sit in Curl Window>"]

    ZoneSel --> Middle["[Sequence] Middle Zone"]
    Middle --> MidAssign["(Middle/Tampa 2?)"]
    MidAssign --> |Yes| MidSeq["[Sequence]"]
    MidSeq --> Sprint["<Sprint to Deep Middle>"]
    MidSeq --> ReadSeam["<Read Seam Threats>"]
    MidSeq --> MatchSeam["<Match Vertical Seam>"]

    Root --> Man["[Sequence] Man Coverage"]
    Man --> ManAssign2["(Man Assignment?)"]
    ManAssign2 --> |Yes| ManSeq2["[Sequence]"]
    ManSeq2 --> FindMan["<Find Man>"]
    ManSeq2 --> PositionSel["[Selector]"]
    PositionSel --> InPhase["(In Phase?) → <Mirror Route>"]
    PositionSel --> Trail["(Trailing?) → <Trail / Close Gap>"]
    PositionSel --> Stacked["(Stacked?) → <Maintain Position>"]
    ManSeq2 --> ContestCatch["(Ball Coming?) → <Contest Catch>"]

    Root --> Stance5["<Hold Stance>"]
```

#### LB Key Reads

| Read | Key | Run Indicator | Pass Indicator |
|------|-----|---------------|----------------|
| OL | Hat level | Low/Drive block | High/Pass set |
| Guard | Pull? | Pulling = run | Setting = pass |
| Backfield | Flow | RB toward LOS | RB in protection |
| TE | Release | Block = run | Release = pass |
| QB | Eyes | Handing off | Scanning |

#### LB Run Fit Responsibilities

| Run Type | WILL LB | MIKE LB | SAM LB |
|----------|---------|---------|---------|
| Inside Zone | Cutback | A-Gap | Flow |
| Outside Zone | Pursuit | B-Gap | C-Gap/Contain |
| Power | Scrape | Fill | Spill |
| Counter | Cutback | Scrape | Kick Reader |

---

### Cornerback (CB) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] CB Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> BallInAir["[Selector] Ball In Air"]
    BallInAir --> BallAir["(Ball In Air?)"]
    BallAir --> |Yes| BallAirSel["[Selector]"]

    BallAirSel --> ToMyMan["[Sequence] Ball to My Man"]
    ToMyMan --> ToReceiver["(Ball to My Receiver?)"]
    ToReceiver --> |Yes| ToMySel["[Selector] Contest Type"]
    ToMySel --> InPosition["[Sequence] In Position"]
    InPosition --> AmClose["(Within 1 Yard?)"]
    AmClose --> |Yes| InPosSel["[Selector]"]
    InPosSel --> PlayBall["[Sequence] Play Ball"]
    PlayBall --> CanSee["(Can See Ball?)"]
    CanSee --> |Yes| PlayBallSeq["[Sequence]"]
    PlayBallSeq --> TrackBall2["<Track Ball>"]
    PlayBallSeq --> HighPoint2["<High Point / Intercept>"]
    InPosSel --> PlayReceiver["[Sequence] Play Receiver"]
    PlayReceiver --> CantSee["(Can't See Ball?)"]
    CantSee --> |Yes| PlayRecSeq["[Sequence]"]
    PlayRecSeq --> ReadEyes["<Read Receiver Eyes>"]
    PlayRecSeq --> PlayHands["<Play Through Hands>"]
    ToMySel --> Trail2["[Sequence] Trailing"]
    Trail2 --> AmTrailing["(More than 1 Yard?)"]
    AmTrailing --> |Yes| TrailSeq["[Sequence]"]
    TrailSeq --> CloseGround["<Close Ground>"]
    TrailSeq --> DiveAtBall["<Dive at Ball/Tackle>"]

    BallAirSel --> NotMyMan["[Sequence] Ball Elsewhere"]
    NotMyMan --> BallAway["(Ball Not to Me?)"]
    BallAway --> |Yes| RallyBall["<Rally to Ball>"]

    Root --> Press["[Sequence] Press Coverage"]
    Press --> PressTech["(Press Technique?)"]
    PressTech --> |Yes| PressSel["[Selector] Press Phase"]

    PressSel --> Jam["[Sequence] Jam at LOS"]
    Jam --> AtLOS2["(At LOS?)"]
    AtLOS2 --> |Yes| JamSeq["[Sequence]"]
    JamSeq --> ReadRelease["<Read Release>"]
    JamSeq --> JamSel["[Selector] Jam Type"]
    JamSel --> MirrorJam["(Inside Release?) → <Mirror + Jam>"]
    JamSel --> RedirectJam["(Outside Release?) → <Redirect Inside>"]
    JamSel --> CatchJam["(Speed Release?) → <Catch + Funnel>"]

    PressSel --> Phase["[Sequence] In Phase"]
    Phase --> PostJam["(Post Jam?)"]
    PostJam --> |Yes| PhaseSel["[Selector]"]
    PhaseSel --> OnHip["[Sequence] On Hip"]
    OnHip --> HipPos["(On Hip?)"]
    HipPos --> |Yes| HipSeq["[Sequence]"]
    HipSeq --> Plaster["<Plaster to Hip>"]
    HipSeq --> ReadBreak["<Read for Break>"]
    HipSeq --> ReactBreak["(Break?) → <React to Break>"]
    PhaseSel --> Stacked2["[Sequence] Stacked"]
    Stacked2 --> StackedPos["(Stacked?)"]
    StackedPos --> |Yes| StackSeq["[Sequence]"]
    StackSeq --> MaintainStack["<Maintain Stack>"]
    StackSeq --> UseLeverage["<Use Leverage>"]

    Root --> OffMan["[Sequence] Off Man Coverage"]
    OffMan --> OffManTech["(Off Man Technique?)"]
    OffManTech --> |Yes| OffManSel["[Selector] Off Man Phase"]

    OffManSel --> Backpedal["[Sequence] Backpedal Phase"]
    Backpedal --> PreBreak["(Pre-Break?)"]
    PreBreak --> |Yes| BPSeq["[Sequence]"]
    BPSeq --> BPDepth["<Backpedal to Depth>"]
    BPSeq --> KeyReceiver["<Key Receiver>"]
    BPSeq --> ReadHips["<Read Hips for Break>"]

    OffManSel --> Transition["[Sequence] Transition"]
    Transition --> AtBreak2["(WR Breaking?)"]
    AtBreak2 --> |Yes| TransSeq["[Selector]"]
    TransSeq --> FlipToIn["(In-Breaking?) → <Flip Hips Inside>"]
    TransSeq --> FlipToOut["(Out-Breaking?) → <Flip Hips Outside>"]
    TransSeq --> RunVert["(Vertical?) → <Turn and Run>"]

    OffManSel --> Close["[Sequence] Closing"]
    Close --> PostBreak2["(Post Break?)"]
    PostBreak2 --> |Yes| CloseSel["[Selector]"]
    CloseSel --> InPhase2["(In Phase?) → <Mirror / Close>"]
    CloseSel --> Trail3["(Out of Phase?) → <Trail / Recover>"]

    Root --> Zone2["[Selector] Zone Coverage"]
    Zone2 --> ZoneCov["(Zone Assignment?)"]
    ZoneCov --> |Yes| ZoneCovSel["[Selector] Zone Type"]

    ZoneCovSel --> DeepThird["[Sequence] Deep Third"]
    DeepThird --> ThirdAssign["(Deep Third?)"]
    ThirdAssign --> |Yes| ThirdSeq["[Sequence]"]
    ThirdSeq --> Bail["<Bail to Depth>"]
    ThirdSeq --> FindThreat["<Find #1 Threat>"]
    ThirdSeq --> ReadVert["[Selector] Vertical Threat"]
    ReadVert --> VertTo["(#1 Vertical?) → <Match #1>"]
    ReadVert --> NoVert["(No Vertical?) → <Rob Underneath>"]

    ZoneCovSel --> Flat["[Sequence] Flat Zone"]
    Flat --> FlatAssign["(Flat Zone?)"]
    FlatAssign --> |Yes| FlatSeq["[Sequence]"]
    FlatSeq --> FunnelOne["<Funnel #1 Inside>"]
    FlatSeq --> Sink["<Sink to Flat>"]
    FlatSeq --> ReadTwo["<Read #2>"]
    FlatSeq --> TwoFlat["(#2 to Flat?) → <Jump #2>"]

    ZoneCovSel --> Quarter["[Sequence] Quarter Zone"]
    Quarter --> QuarterAssign["(Quarter?)"]
    QuarterAssign --> |Yes| QuarterSeq["[Sequence]"]
    QuarterSeq --> Cushion["<Maintain Cushion>"]
    QuarterSeq --> ReadTwoTwo["<Read #1 and #2>"]
    QuarterSeq --> QuarterSel["[Selector]"]
    QuarterSel --> OneVert["(#1 Vert, #2 Out?) → <Carry #1>"]
    QuarterSel --> TwoVert["(#2 Vert Inside?) → <Pass to Safety, Sink>"]

    Root --> RunSupport["[Sequence] Run Support"]
    RunSupport --> RunRead["(Run Diagnosed?)"]
    RunRead --> |Yes| RunSupportSel["[Selector]"]

    RunSupportSel --> Primary["[Sequence] Primary Force"]
    Primary --> ForceAssign["(Force Player?)"]
    ForceAssign --> |Yes| ForceSeq["[Sequence]"]
    ForceSeq --> AttackAlley["<Attack Alley>"]
    ForceSeq --> TakeOnBlock["<Take On Block>"]
    ForceSeq --> TurnPlay["<Turn Play Inside>"]

    RunSupportSel --> Contain2["[Sequence] Contain"]
    Contain2 --> ContainAssign["(Contain?)"]
    ContainAssign --> |Yes| ContainSeq["[Sequence]"]
    ContainSeq --> WidenOut["<Widen / Get Depth>"]
    ContainSeq --> SqueezeBC["<Squeeze Ballcarrier>"]
    ContainSeq --> NoOutside["<Don't Let Outside>"]

    RunSupportSel --> Alley["[Sequence] Alley Player"]
    Alley --> AlleyAssign["(Alley Fill?)"]
    AlleyAssign --> |Yes| AlleySeq["[Sequence]"]
    AlleySeq --> FillAlley["<Fill Alley>"]
    AlleySeq --> FitInside["<Fit Inside Force>"]
    AlleySeq --> MakeTackle2["<Make Tackle>"]

    Root --> Stance6["<Hold Stance>"]
```

#### CB Coverage Techniques

| Technique | Alignment | Key | Best Against | Weakness |
|-----------|-----------|-----|--------------|----------|
| Press | 0-1 yard | Hands, feet | Timing routes | Speed release |
| Off (5-7 yards) | Cushion | Hip read | Go routes | Slants, hitches |
| Bail | Start close, bail | #1 vertical | Deep shots | Underneath |
| Catch | Press shell, soft | Jam and trail | Play action | Quick game |

#### CB Zone Landmarks

| Zone | Depth | Width | Key Read |
|------|-------|-------|----------|
| Deep Third | 12-15+ yards | Sideline to hash | #1 vertical |
| Flat | 5-8 yards | Sideline to numbers | #2 to flat |
| Quarter | 10-12 yards | Quarter of field | #1 and #2 |

---

### Safety (S) Behavior Tree

```mermaid
flowchart TB
    Root[["[Selector] Safety Root"]]

    Root --> Down["(Is Down?)"]
    Down --> |Yes| Stay["<Stay Down>"]

    Root --> BallAir2["[Selector] Ball In Air"]
    BallAir2 --> IsBallAir["(Ball In Air?)"]
    IsBallAir --> |Yes| BallAirSafety["[Selector]"]

    BallAirSafety --> BreakOnBall["[Sequence] Break on Ball"]
    BreakOnBall --> CanIntercept["(Intercept Angle?)"]
    CanIntercept --> |Yes| InterceptSeq["[Sequence]"]
    InterceptSeq --> CalculateAngle["<Calculate Intercept>"]
    InterceptSeq --> DriveOnBall["<Drive on Ball>"]
    InterceptSeq --> PlayBall2["<High Point / Intercept>"]

    BallAirSafety --> RallyTackle["[Sequence] Rally"]
    RallyTackle --> NoIntercept["(No Intercept Angle?)"]
    NoIntercept --> |Yes| RallySeq["[Sequence]"]
    RallySeq --> RallyPoint["<Rally to Catch Point>"]
    RallySeq --> PrepTackle["<Prepare to Tackle>"]

    Root --> Deep["[Selector] Deep Coverage"]
    Deep --> DeepAssign["(Deep Assignment?)"]
    DeepAssign --> |Yes| DeepSel["[Selector] Deep Zone Type"]

    DeepSel --> SingleHigh["[Sequence] Single High (Cover 1/3)"]
    SingleHigh --> SingleAssign["(Single High?)"]
    SingleAssign --> |Yes| SingleSeq["[Sequence]"]
    SingleSeq --> CenterField["<Align Center Field>"]
    SingleSeq --> ReadQBEyes["<Read QB Eyes>"]
    SingleSeq --> Triangulate["<Triangulate Deep Threats>"]
    SingleSeq --> BreakSeq["[Selector]"]
    BreakSeq --> BreakPost["(Post Threat?) → <Break on Post>"]
    BreakSeq --> BreakSeam["(Seam Threat?) → <Break on Seam>"]
    BreakSeq --> BreakCorner["(Corner?) → <Help Over Top>"]
    BreakSeq --> HoldMiddle["<Hold Deep Middle>"]

    DeepSel --> Half["[Sequence] Deep Half (Cover 2)"]
    Half --> HalfAssign["(Deep Half?)"]
    HalfAssign --> |Yes| HalfSeq["[Sequence]"]
    HalfSeq --> HalfAlignment["<Align Hash to Sideline>"]
    HalfSeq --> ReadTwo3["<Read #1 and #2>"]
    HalfSeq --> HalfSel["[Selector]"]
    HalfSel --> OneDeep["(#1 Deep Outside?) → <Carry to Sideline>"]
    HalfSel --> TwoDeep["(#2 Up Seam?) → <Squeeze Seam>"]
    HalfSel --> AllUnder["(All Underneath?) → <Squeeze Down>"]

    DeepSel --> QuarterS["[Sequence] Quarter (Cover 4)"]
    QuarterS --> QuarterSAssign["(Quarter?)"]
    QuarterSAssign --> |Yes| QuarterSSeq["[Sequence]"]
    QuarterSSeq --> QuarterSAlign["<Align over #2>"]
    QuarterSSeq --> ReadTwoS["<Read #2>"]
    QuarterSSeq --> QuarterSSel["[Selector]"]
    QuarterSSel --> TwoVertS["(#2 Vertical?) → <Carry #2 Deep>"]
    QuarterSSel --> TwoOutS["(#2 Out?) → <Look for #1>"]
    QuarterSSel --> TwoInS["(#2 In?) → <Squeeze Inside>"]

    Root --> Robber["[Sequence] Robber Coverage"]
    Robber --> RobberAssign["(Robber?)"]
    RobberAssign --> |Yes| RobberSeq["[Sequence]"]
    RobberSeq --> FakeDeep["<Show Deep>"]
    RobberSeq --> TriggerDown["<Trigger on Throw>"]
    RobberSeq --> JumpRoute["<Jump Underneath Route>"]

    Root --> ManS["[Sequence] Man Coverage"]
    ManS --> ManSAssign["(Man Assignment?)"]
    ManSAssign --> |Yes| ManSSel["[Selector]"]

    ManSSel --> ManTE["[Sequence] Man on TE"]
    ManTE --> TEAssign["(TE?)"]
    TEAssign --> |Yes| ManTESeq["[Sequence]"]
    ManTESeq --> AlignTE["<Inside Leverage>"]
    ManTESeq --> JamTE["<Jam at Release>"]
    ManTESeq --> TrailTE["<Trail in Phase>"]

    ManSSel --> ManRB["[Sequence] Man on RB"]
    ManRB --> RBAssign["(RB?)"]
    RBAssign --> |Yes| ManRBSeq["[Sequence]"]
    ManRBSeq --> KeyRB["<Key RB in Backfield>"]
    ManRBSeq --> PassCheck["(RB Releases?) → <Match Release>"]
    ManRBSeq --> RunCheck["(RB Runs?) → <Pursue>"]

    ManSSel --> ManSlot["[Sequence] Man on Slot"]
    ManSlot --> SlotAssign["(Slot?)"]
    SlotAssign --> |Yes| ManSlotSeq["[Sequence]"]
    ManSlotSeq --> AlignSlot["<Inside Leverage on Slot>"]
    ManSlotSeq --> PassRead["<Pass Read>"]
    ManSlotSeq --> RunOrPass["[Selector]"]
    RunOrPass --> SlotRoute["(Slot Releases?) → <Cover Route>"]
    RunOrPass --> SlotBlock["(Slot Blocks?) → <Trigger Run>"]

    Root --> RunS["[Selector] Run Support"]
    RunS --> RunReadS["(Run Diagnosed?)"]
    RunReadS --> |Yes| RunSSel["[Selector]"]

    RunSSel --> Alley2["[Sequence] Alley Fill"]
    Alley2 --> AlleyS["(Alley Player?)"]
    AlleyS --> |Yes| AlleySSeq["[Sequence]"]
    AlleySSeq --> TriggerAlley["<Trigger Downhill>"]
    AlleySSeq --> FillBetween["<Fill Between Force/LB>"]
    AlleySSeq --> TakeTackle["<Take on Lead / Make Tackle>"]

    RunSSel --> Cutback2["[Sequence] Cutback"]
    Cutback2 --> CutbackS["(Cutback Player?)"]
    CutbackS --> |Yes| CutbackSeq["[Sequence]"]
    CutbackSeq --> SlowRead["<Slow Read>"]
    CutbackSeq --> FillBackside["<Fill Backside>"]
    CutbackSeq --> CutoffBC["<Cut Off Cutback>"]

    RunSSel --> Force["[Sequence] Force Player"]
    Force --> ForceS["(Force?)"]
    ForceS --> |Yes| ForceSSeq["[Sequence]"]
    ForceSSeq --> AttackPlayside["<Attack Playside>"]
    ForceSSeq --> SetEdge2["<Set Edge>"]
    ForceSSeq --> ForceTurn["<Force Ball Inside>"]

    Root --> Blitz2["[Sequence] Safety Blitz"]
    Blitz2 --> BlitzS["(Blitz Assignment?)"]
    BlitzS --> |Yes| BlitzSSel["[Selector]"]
    BlitzSSel --> EdgeS["[Sequence] Edge Blitz"]
    EdgeS --> EdgeSAssign["(Edge?)"]
    EdgeSAssign --> |Yes| EdgeSSeq["[Sequence]"]
    EdgeSSeq --> CreepEdge["<Creep to Edge>"]
    EdgeSSeq --> TimeSnap["<Time Snap>"]
    EdgeSSeq --> AttackEdge["<Attack Edge>"]
    BlitzSSel --> InsideS["[Sequence] Inside Blitz"]
    InsideS --> InsideSAssign["(A/B Gap?)"]
    InsideSAssign --> |Yes| InsideSSeq["[Sequence]"]
    InsideSSeq --> CreepIn["<Creep Pre-Snap>"]
    InsideSSeq --> HitGap["<Hit Gap>"]
    InsideSSeq --> FindQB["<Find QB>"]

    Root --> Stance7["<Hold Stance>"]
```

#### Safety Coverage Landmarks

| Coverage | FS Alignment | SS Alignment | Primary Key |
|----------|--------------|--------------|-------------|
| Cover 1 | 12-14 deep center | 8 over #2/#3 | QB to receivers |
| Cover 2 | 12 deep hash to sideline | 12 deep hash to sideline | #1 and #2 |
| Cover 3 | 12-15 deep middle third | 8 rolled down | FS: Post, SS: Flat/Run |
| Cover 4 | 10-12 over #2 | 10-12 over #2 | #2 vertical or out |
| Cover 6 | Quarter to field | Half to boundary | Split rules |

---

### Ballcarrier (Universal) Behavior Tree

This tree applies to ANY player who has the ball—RB, WR after catch, QB scrambling, or defender after interception.

```mermaid
flowchart TB
    Root[["[Selector] Ballcarrier Root"]]

    Root --> Down2["(Is Down?)"]
    Down2 --> |Yes| Stay2["<Stay Down>"]

    Root --> Scoring["[Sequence] Scoring Position"]
    Scoring --> NearGoal["(Within 5 Yards of Goal?)"]
    NearGoal --> |Yes| ScoreSel["[Selector]"]
    ScoreSel --> ClearPath["(Clear Path?) → <Sprint to End Zone>"]
    ScoreSel --> Dive["(Defender Close?) → <Dive for Pylon/Goal>"]
    ScoreSel --> LowerPad["<Lower Pad Level, Fight Forward>"]

    Root --> OpenField["[Selector] Open Field"]
    OpenField --> InSpace["(In Open Field?)"]
    InSpace --> |Yes| OpenSel["[Selector] Open Field Running"]

    OpenSel --> NoThreat["[Sequence] No Immediate Threat"]
    NoThreat --> ClearAhead["(No Defender Within 7 Yards?)"]
    ClearAhead --> |Yes| NoThreatSeq["[Sequence]"]
    NoThreatSeq --> PickLane["<Pick Best Lane>"]
    NoThreatSeq --> Accelerate["<Accelerate>"]
    NoThreatSeq --> SetupBlock["<Set Up Blocker>"]

    OpenSel --> OneThreat["[Sequence] Single Threat"]
    OneThreat --> OneDefender["(One Defender to Beat?)"]
    OneDefender --> |Yes| OneSel["[Selector] 1v1"]
    OneSel --> SpeedWin["[Sequence] Speed Win"]
    SpeedWin --> SpeedAdv["(Speed Advantage?)"]
    SpeedAdv --> |Yes| SpeedSeq["[Sequence]"]
    SpeedSeq --> SetupAngle["<Set Up Angle>"]
    SpeedSeq --> SpeedBurst2["<Speed Burst Past>"]
    OneSel --> MakeMove["[Sequence] Make Move"]
    MakeMove --> NoSpeedAdv["(No Speed Advantage?)"]
    NoSpeedAdv --> |Yes| MoveSel["[Selector] Move Selection"]
    MoveSel --> Juke["[Sequence]"]
    Juke --> JukeSpace["(Space to Cut?)"]
    JukeSpace --> |Yes| ExecJuke["<Execute Juke>"]
    MoveSel --> Spin2["[Sequence]"]
    Spin2 --> SpinAngle["(Defender Committed?)"]
    SpinAngle --> |Yes| ExecSpin["<Execute Spin>"]
    MoveSel --> StiffArm["[Sequence]"]
    StiffArm --> StiffPos["(Defender Reaching?)"]
    StiffPos --> |Yes| ExecStiff["<Execute Stiff Arm>"]
    MoveSel --> Power["<Lower Shoulder / Truck>"]

    OpenSel --> MultiThreat["[Sequence] Multiple Threats"]
    MultiThreat --> MultDef["(Multiple Defenders?)"]
    MultDef --> |Yes| MultSel["[Selector]"]
    MultSel --> FindSeam["[Sequence] Find Seam"]
    FindSeam --> SeamExists["(Seam Between Defenders?)"]
    SeamExists --> |Yes| HitSeam["<Split Defenders>"]
    MultSel --> UseBlocker["[Sequence] Set Up Block"]
    UseBlocker --> BlockerAvail["(Blocker Available?)"]
    BlockerAvail --> |Yes| BlockerSeq["[Sequence]"]
    BlockerSeq --> SetupBlocker["<Set Up Blocker>"]
    BlockerSeq --> ReadBlock["<Read Block>"]
    BlockerSeq --> CutOffBlock["<Cut Off Block>"]
    MultSel --> Boundary["[Sequence] Use Boundary"]
    Boundary --> NearSide["(Near Sideline?)"]
    NearSide --> |Yes| UseSideline["<Use Sideline as Extra Defender>"]
    MultSel --> North2["<North/South, Minimize Loss>"]

    Root --> Congestion["[Selector] Congested Running"]
    Congestion --> InTraffic["(In Traffic?)"]
    InTraffic --> |Yes| TrafficSel["[Selector]"]

    TrafficSel --> HitHole["[Sequence] Hit Hole"]
    HitHole --> HoleVisible["(Hole Visible?)"]
    HoleVisible --> |Yes| HoleSeq["[Selector]"]
    HoleSeq --> BigHole["(Hole > 2 Yards?) → <Accelerate Through>"]
    HoleSeq --> SmallHole["(Hole 1-2 Yards?) → <Squeeze Through>"]
    HoleSeq --> ClosingHole["(Hole Closing?) → <Hit It Now>"]

    TrafficSel --> Cutback3["[Sequence] Cutback"]
    TrafficSel --> CutbackVis["(Cutback Lane?)"]
    CutbackVis --> |Yes| CutbackRun["[Sequence]"]
    CutbackRun --> PatienceCut["<Patience / Set Up Cut>"]
    CutbackRun --> PlantCut["<Plant and Cut>"]
    CutbackRun --> AccelCut["<Accelerate Through Cutback>"]

    TrafficSel --> Bounce2["[Sequence] Bounce"]
    Bounce2 --> BounceVis["(Edge Available?)"]
    BounceVis --> |Yes| BounceRun["[Sequence]"]
    BounceRun --> ReadEdge["<Read Edge Block>"]
    BounceRun --> BounceOut2["<Bounce Outside>"]
    BounceRun --> TurnCorner["<Turn Corner>"]

    TrafficSel --> ChurnLegs["[Sequence] Churn Legs"]
    ChurnLegs --> NoLane["(No Lanes?)"]
    NoLane --> |Yes| ChurnSeq["[Sequence]"]
    ChurnSeq --> LowerPad2["<Lower Pad Level>"]
    ChurnSeq --> DriveLegs["<Drive Legs>"]
    ChurnSeq --> FallForward["<Fall Forward>"]

    Root --> Contact["[Selector] Contact Imminent"]
    Contact --> TacklerClose["(Tackler Within 1 Yard?)"]
    TacklerClose --> |Yes| ContactSel["[Selector]"]

    ContactSel --> AvoidContact["[Sequence] Avoid"]
    AvoidContact --> CanAvoid["(Can Avoid Contact?)"]
    CanAvoid --> |Yes| LastMove["[Selector] Last Second Move"]
    LastMove --> LastJuke["<Last Second Juke>"]
    LastMove --> LastSpin["<Spin Out>"]
    LastMove --> Hurdle2["<Hurdle>"]

    ContactSel --> Brace["[Sequence] Brace for Contact"]
    Brace --> MustTakeHit["(Must Take Hit?)"]
    MustTakeHit --> |Yes| BraceSel["[Selector]"]
    BraceSel --> LowerBrace["<Lower Pad / Absorb>"]
    BraceSel --> TruckHit["<Truck / Initiate Contact>"]
    BraceSel --> ProtectBall2["<Protect Ball / Brace>"]

    ContactSel --> YAC["[Sequence] Fight for YAC"]
    YAC --> Contact2["(In Contact?)"]
    Contact2 --> |Yes| YACSel["[Selector]"]
    YACSel --> DriveLegs2["<Drive Legs>"]
    YACSel --> SpinOut2["<Spin Out of Contact>"]
    YACSel --> ReachBall["<Reach Ball Forward>"]

    Root --> Safety2["[Selector] Safety First"]
    Safety2 --> NeedSafety["(Late in Game / Protecting Lead?)"]
    NeedSafety --> |Yes| SafetySel["[Selector]"]
    SafetySel --> OOB["(Near Sideline?) → <Go Out of Bounds>"]
    SafetySel --> Slide["(QB?) → <Slide>"]
    SafetySel --> GiveUp["(Wrapped Up?) → <Give Up / Protect>"]
    SafetySel --> CoverBall["<Cover Ball with Both Hands>"]

    Root --> Default["<Run North-South>"]
```

#### Ballcarrier Vision Tiers

| Vision Rating | Can Perceive | Decision Quality |
|---------------|--------------|------------------|
| < 60 | Primary hole, 2 nearest defenders | Often misses cutback |
| 60-74 | 2-3 holes, 4-5 defenders | Sees obvious cutback |
| 75-84 | All holes, pursuit angles | Good cutback timing |
| 85-99 | Blocker leverage, second level | Elite anticipation |

#### Move Selection Matrix

| Situation | Best Move | Required Attribute | Risk Level |
|-----------|-----------|-------------------|------------|
| Defender reaching | Stiff Arm | Strength 75+ | Low |
| Defender committed upfield | Spin | Agility 80+ | Medium |
| Space to side | Juke | Agility 70+ | Low |
| Low tackler | Hurdle | Agility 85+ | High |
| Smaller defender | Truck | Strength 80+, Weight | Medium |
| Speed advantage | Speed burst | Speed diff 3+ | Low |
| No space | Dead leg | Agility 70+ | Low |

---

### Behavior Tree Implementation Notes

#### Tree Evaluation Order

```python
class BehaviorTree:
    """Evaluates behavior tree each tick."""

    def evaluate(self, context: Context) -> Action:
        """
        Traverse tree from root, return first successful action.

        Evaluation rules:
        1. Selectors try children left-to-right, return first success
        2. Sequences require all children to succeed
        3. Conditions return SUCCESS or FAILURE
        4. Actions return SUCCESS, FAILURE, or RUNNING
        """
        return self.root.evaluate(context)

class Selector(Node):
    """Try children until one succeeds (OR logic)."""

    def evaluate(self, context: Context) -> Status:
        for child in self.children:
            status = child.evaluate(context)
            if status != Status.FAILURE:
                return status
        return Status.FAILURE

class Sequence(Node):
    """All children must succeed (AND logic)."""

    def evaluate(self, context: Context) -> Status:
        for child in self.children:
            status = child.evaluate(context)
            if status != Status.SUCCESS:
                return status
        return Status.SUCCESS
```

#### Attribute Influence on Trees

Attributes don't change tree structure—they influence:

1. **Condition thresholds** - Higher awareness = earlier blitz recognition
2. **Action success rates** - Higher agility = better juke success
3. **Timing windows** - Higher play recognition = faster reads
4. **Option availability** - Low speed = speed burst not viable

```python
def can_use_speed_burst(ballcarrier: Player, defender: Player) -> bool:
    """Speed burst only viable with significant speed advantage."""
    speed_diff = ballcarrier.attributes.speed - defender.attributes.speed
    return speed_diff >= 3  # Need 3+ rating points
```

---

## Open Questions

1. **Fatigue modeling**: How does player stamina affect capabilities over a play? Over a game?

2. **Injury system**: When do injuries occur? What body parts? How does geometry affect injury risk?

3. **Pre-snap motion**: How do we model motion, shifts, and their effects on defensive alignment?

4. **Audibles**: How does the play definition system support in-play adjustments?

5. **Special teams**: Separate system or extension of this framework?

6. **Multiplayer coordination**: How do blockers communicate to pick up stunts/blitzes?

---

## Appendix: Real-World Reference Data

### Player Speed Benchmarks (40-yard dash → yards/sec)

| 40 Time | Top Speed (yards/sec) | Player Type |
|---------|----------------------|-------------|
| 4.3s | ~7.5 | Elite WR/CB |
| 4.4s | ~7.2 | Fast skill player |
| 4.5s | ~7.0 | Average WR/RB |
| 4.6s | ~6.7 | LB, Safety |
| 4.8s | ~6.3 | Average LB |
| 5.0s | ~6.0 | DL |
| 5.2s+ | ~5.5 | OL |

### Gap Widths (Real NFL Data)

| Situation | Typical Width |
|-----------|---------------|
| At snap (between OL) | 0.5-0.8 yards |
| After initial push | 0.8-1.2 yards |
| "Good" hole | 1.5-2.0 yards |
| "Huge" hole | 2.5+ yards |
| Minimum viable | 0.7 yards (squeeze) |

### Tackle Success Rates (NFL Averages)

| Situation | Success Rate |
|-----------|--------------|
| Head-on, wrapped up | ~90% |
| Side angle, contact | ~75% |
| Pursuit angle | ~60% |
| Arm tackle | ~45% |
| Diving attempt | ~50% |
| In open field | ~55% |

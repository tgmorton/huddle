# Game Layer

The Game Manager layer transforms the V2 simulation "play sandbox" into a complete game engine that produces meaningful outcomes for the career simulation.

**Location**: `huddle/game/`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Management Layer                            │
│                  (League, Teams, Players)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       GAME LAYER                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     GameManager                            │  │
│  │  - Game flow (quarters, halftime, overtime)               │  │
│  │  - Coin toss and initial possession                       │  │
│  │  - Scoring sequences (TD → PAT/2PT, FG)                   │  │
│  │  - Two-minute warning                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  DriveManager  │  │ SpecialTeams│  │ DecisionLogic       │  │
│  │  - Plays loop  │  │ - Kickoff   │  │ - 4th down choice   │  │
│  │  - Down/dist   │  │ - Punt      │  │ - 2PT decision      │  │
│  │  - First down  │  │ - FG        │  │ - Clock management  │  │
│  │  - Penalties   │  │ - PAT       │  │                     │  │
│  └────────────────┘  └─────────────┘  └─────────────────────┘  │
│              │                                                   │
│              ▼                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  RosterBridge          PlayAdapter         Coordinator    │  │
│  │  (Depth Chart →        (PlayCode →         (AI Play       │  │
│  │   V2 Players)           V2 Config)          Calling)      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      V2 Simulation                               │
│            (Physics-based play execution)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Modules

| Module | Lines | Description |
|--------|-------|-------------|
| `manager.py` | ~580 | Full game orchestration, coach mode |
| `drive.py` | ~575 | Drive loop with down/distance tracking |
| `roster_bridge.py` | ~320 | Depth chart → V2 Player conversion |
| `play_adapter.py` | ~350 | PlayCode → V2 PlayConfig mapping |
| `special_teams.py` | ~430 | Statistical kick resolution |
| `result_handler.py` | ~470 | Stats extraction from V2 results |
| `coordinator.py` | ~450 | AI play-calling for auto-play |
| `decision_logic.py` | ~325 | 4th down, 2PT, clock management |
| `game_log_converter.py` | ~350 | Bridge to core stats model |
| `penalties.py` | ~465 | Flag resolution system |

---

## Core Classes

### GameManager

Main entry point for running games.

```python
from huddle.game import GameManager

# Auto-play full game
manager = GameManager(home_team, away_team)
result = manager.play_game()

# Coach mode (user calls plays)
manager = GameManager(home_team, away_team, coach_mode=True)
manager.start_game()
situation = manager.get_situation()
result = manager.call_play(play_code)
```

**Handles:**
- Coin toss and initial possession
- Quarter/half transitions with correct kickoff logic
- Scoring sequences (TD → PAT/2PT, FG)
- Two-minute warning
- Overtime rules (NFL sudden death)

### GameResult

```python
@dataclass
class GameResult:
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    drives: List[DriveResult]

    @property
    def winner(self) -> str:  # 'home', 'away', or 'tie'
    @property
    def margin(self) -> int
```

### DriveManager

Executes plays until drive ends.

```python
from huddle.game import DriveManager

drive = DriveManager(
    offensive_team=home_team,
    defensive_team=away_team,
    starting_los=25.0,  # Own 25
    orchestrator=v2_orchestrator,
)
result = drive.execute()  # Returns DriveResult
```

**Drive ends on:**
- Touchdown, Field Goal (made/missed), Punt
- Turnover (INT, fumble, on downs)
- End of half, Safety

### DriveResult

```python
@dataclass
class DriveResult:
    end_reason: DriveEndReason
    plays: List[PlayLog]
    total_yards: float
    time_of_possession: float
    starting_los: float
    ending_los: float
    points_scored: int
```

---

## Special Teams

Statistical resolution (not physics-simulated).

### SpecialTeamsResolver

```python
from huddle.game import SpecialTeamsResolver

resolver = SpecialTeamsResolver()

# Kickoff
outcome = resolver.kickoff(kicker_rating=82)
# Returns: SpecialTeamsOutcome(touchback=True, return_yards=0, start_los=25)

# Punt
outcome = resolver.punt(punter_rating=78, los=25.0)
# Returns: net yards, fair catch, touchback

# Field Goal
success = resolver.field_goal(kicker_rating=85, yard_line=72)  # 45-yard attempt
# Returns: bool

# PAT
success = resolver.extra_point(kicker_rating=85)
```

### NFL Statistics (Research-Backed)

| Play Type | Key Stats |
|-----------|-----------|
| **Kickoff** | 62.5% touchback rate, 21.4 avg return yards |
| **Punt** | 46.3 gross, 42.5 net, 40% inside-20 |
| **FG 30yd** | 98.3% make rate |
| **FG 40yd** | 88.4% make rate |
| **FG 50yd** | 73.9% make rate |
| **FG 55yd** | 61.7% make rate |
| **PAT** | 94.4% make rate |

---

## Decision Logic

Research-backed AI decision making.

### Fourth Down

```python
from huddle.game import fourth_down_decision, FourthDownDecision

decision = fourth_down_decision(
    yard_line=65,     # Own 35
    distance=3,       # 4th and 3
    score_diff=0,     # Tied game
    time_remaining=600  # 10 minutes left
)
# Returns: FourthDownDecision.PUNT or .GO or .FIELD_GOAL
```

### Two-Point Conversion

```python
from huddle.game import should_go_for_two

go_for_two = should_go_for_two(
    score_diff=-8,    # Down by 8
    time_remaining=120  # 2 minutes left
)
# Returns: True (should go for 2)
```

### Clock Management

```python
from huddle.game import select_pace, time_off_clock, Pace

pace = select_pace(score_diff=7, time_remaining=90)
# Returns: Pace.SLOW (protecting lead)

elapsed = time_off_clock(play_result, pace)
# Returns: seconds used
```

---

## Stats and Persistence

### ResultHandler

Extracts stats from V2 play results.

```python
from huddle.game import ResultHandler, GameStatSheet

handler = ResultHandler()
stats: GameStatSheet = handler.compile_game_stats(drives)
```

### Game Log Converter

Bridges to core stats model for persistence.

```python
from huddle.game import persist_game_result

# After game completes
persist_game_result(
    league=league,
    game_result=result,
    home_team=home_team,
    away_team=away_team,
    season=2024,
    week=1,
)
# Updates league.game_logs, team records, player career stats
```

---

## Penalties

Flag resolution system (~6% penalty rate, matching NFL).

### PenaltyResolver

```python
from huddle.game import check_for_penalty, PenaltyType

penalty = check_for_penalty(
    play_type="pass",
    is_scoring_play=False,
    in_red_zone=True,
)
# Returns: PenaltyResult or None
```

### Penalty Types

| Type | Yards | Automatic 1st? |
|------|-------|----------------|
| False Start | 5 | No |
| Offsides | 5 | No |
| Holding (Off) | 10 | No |
| Holding (Def) | 5 | Yes |
| Pass Interference (Def) | Spot | Yes |
| Pass Interference (Off) | 10 | No |
| Roughing the Passer | 15 | Yes |
| Unnecessary Roughness | 15 | Yes |
| Facemask | 15 | Yes |
| Illegal Block | 10 | No |

---

## Coach Mode API

REST and WebSocket endpoints for interactive play.

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/coach/start` | POST | Start new game |
| `/api/v1/coach/{game_id}/situation` | GET | Current game situation |
| `/api/v1/coach/{game_id}/plays` | GET | Available plays |
| `/api/v1/coach/{game_id}/play` | POST | Execute play |
| `/api/v1/coach/{game_id}/special` | POST | Special teams play |
| `/api/v1/coach/{game_id}/box-score` | GET | Current box score |
| `/api/v1/coach/{game_id}/simulate-defense` | POST | AI defensive possession |

### WebSocket

```
WS /api/v1/coach/{game_id}/stream
```

Real-time play-by-play streaming with JSON messages:

```json
{
  "type": "play_result",
  "data": {
    "play_number": 5,
    "down": 2,
    "distance": 7,
    "yards_gained": 12,
    "description": "J. Smith pass complete to M. Jones for 12 yards",
    "first_down": true
  }
}
```

---

## AI Coordinators

Automatic play-calling for simulated games.

### OffensiveCoordinator

```python
from huddle.game import OffensiveCoordinator, SituationContext

coordinator = OffensiveCoordinator(team, playbook)
context = SituationContext(
    down=2, distance=6, yard_line=55,
    score_diff=-3, time_remaining=420,
)
play = coordinator.call_play(context)
```

### DefensiveCoordinator

```python
from huddle.game import DefensiveCoordinator

coordinator = DefensiveCoordinator(team)
formation = coordinator.call_defense(context)
```

---

## Usage Examples

### Simulate Full Game

```python
from huddle.game import GameManager
from huddle.core.league import League

league = League.load("saves/my_league.json")
home = league.get_team_by_abbr("PHI")
away = league.get_team_by_abbr("DAL")

manager = GameManager(home, away)
result = manager.play_game()

print(f"Final: {result.format_score()}")
print(f"Winner: {result.winner}")
print(f"Total drives: {len(result.drives)}")
```

### Coach Mode Session

```python
manager = GameManager(home, away, coach_mode=True)
manager.start_game()

while not manager.is_game_over():
    situation = manager.get_situation()
    print(f"{situation.down} & {situation.distance} at {situation.yard_line}")

    if situation.special_teams:
        # Handle kickoff/punt/FG
        result = manager.special_teams_play("kickoff")
    else:
        # User picks a play
        plays = manager.get_available_plays()
        result = manager.call_play(plays[0].code)

    print(result.description)
```

---

## Design Decisions

1. **Statistical special teams** - Kicks resolved statistically, not simulated
2. **Research-backed probabilities** - All decisions use NFL 2019-2024 data
3. **WebSocket streaming** - Real-time updates for frontend
4. **Penalty rate ~6%** - Matches NFL average per play
5. **Management integration** - Via `league.add_game_log()`

---

## See Also

- [V2 Simulation](../simulation/README.md) - Physics-based play execution
- [Management Backend](../management/backend.md) - League and team management
- [API Reference](../api/README.md) - Full API documentation

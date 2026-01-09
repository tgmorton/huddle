# Historical Simulation System

Multi-season league history generator that creates realistic team rosters, contracts, and transaction histories before the player starts managing their franchise.

**Location**: `huddle/core/simulation/historical_sim.py` (~1,236 lines)

---

## Overview

The Historical Simulator runs complete seasons of team operations to generate a coherent league history. This creates:

- Realistic roster compositions with contract histories
- Draft pick ownership variations from trades
- Team statuses that reflect actual performance (Dynasty, Rebuilding, etc.)
- Transaction logs showing how rosters were built

```
┌─────────────────────────────────────────────────────┐
│                Historical Simulation                 │
│                                                      │
│  For each simulated season:                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Free Agency │→│    Draft    │→│ Roster Cuts │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
│           ↓                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  Regular    │→│  Playoffs   │→│   Status    │   │
│  │   Season    │ │             │ │   Update    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Configuration

```python
@dataclass
class SimulationConfig:
    years_to_simulate: int = 4         # How many seasons to simulate
    target_season: int = 2024          # Final season (player start year)
    num_teams: int = 32                # Number of teams
    draft_rounds: int = 7              # NFL draft rounds
    games_per_season: int = 17         # Regular season games
    playoff_teams: int = 14            # Teams making playoffs
    verbose: bool = False              # Print progress
    progress_callback: Callable = None # SSE progress updates
```

---

## Key Classes

### TeamState

Complete state of a team during simulation:

```python
@dataclass
class TeamState:
    team_id: str
    team_name: str

    # Roster
    roster: list                       # List of Player objects
    contracts: dict                    # player_id → Contract

    # Assets
    pick_inventory: DraftPickInventory # Draft picks owned

    # Status
    status: TeamStatusState            # Dynasty, Contending, Rebuilding
    gm_archetype: GMArchetype          # Affects decision-making

    # Season results
    wins: int = 0
    losses: int = 0
    made_playoffs: bool = False
    won_championship: bool = False

    # Financials
    salary_cap: int = 255_000
    cap_used: int = 0
```

### SimulationResult

Output of historical simulation:

```python
@dataclass
class SimulationResult:
    teams: dict                        # team_id → TeamState
    transaction_log: TransactionLog    # All roster moves
    calendars: list                    # LeagueCalendar per season
    draft_histories: dict              # year → DraftState
    season_standings: dict             # year → list[SeasonSnapshot]
    seasons_simulated: int
    total_transactions: int
```

### SeasonSnapshot

Team snapshot at end of season:

```python
@dataclass
class SeasonSnapshot:
    team_id: str
    team_name: str
    wins: int
    losses: int
    made_playoffs: bool
    won_championship: bool
    status: str                        # "dynasty", "contending", etc.
```

---

## HistoricalSimulator Class

Main simulation engine.

### Constructor

```python
simulator = HistoricalSimulator(
    config=SimulationConfig(years_to_simulate=4),
    player_generator=generate_player_function,
    team_data=list_of_team_info_dicts,
)
```

### run() Method

```python
result = simulator.run()
# Returns SimulationResult with complete league state
```

---

## Simulation Phases

### 1. League Initialization

`_initialize_league(start_season)`

- Creates all teams with empty rosters
- Initializes draft pick inventories (3 years ahead)
- Assigns random GM archetypes for AI decision-making
- Generates initial rosters with cap-compliant contracts

### 2. Initial Roster Generation

`_generate_initial_rosters(season)`

Position counts for 53-man roster:

| Position Group | Players |
|----------------|---------|
| QB, RB, WR, TE, FB | 3, 4, 6, 3, 1 |
| OL (LT, LG, C, RG, RT) | 2, 2, 2, 2, 2 |
| DL (DE, DT) | 4, 3 |
| LB (OLB, ILB, MLB) | 4, 2, 2 |
| Secondary (CB, FS, SS) | 5, 2, 2 |
| Special Teams (K, P) | 1, 1 |

Contracts assigned proportionally by player value to hit ~93% cap usage.

### 3. Season Simulation

`_simulate_season(season)`

Each season runs these phases in order:

#### 3a. Free Agency

`_simulate_free_agency(season)`

- Expiring contracts create free agents
- AI evaluates team needs vs. available players
- Market value determines contract offers
- Teams prioritize based on GM archetype

Transaction types:
- `SIGNING` - New contract
- `RESIGN` - Extension with current team

#### 3b. Draft

`_simulate_draft(season)`

- Draft order based on previous season record (worst to best)
- AI selects based on:
  - Team needs analysis
  - Best player available (BPA)
  - GM archetype preferences
- Rookie contracts assigned by draft position

Transaction type: `DRAFT`

#### 3c. Roster Cuts

`_simulate_roster_cuts(season)`

- Teams must cut to 53 players
- Cut decisions based on:
  - Overall rating
  - Salary vs. dead money
  - Depth chart position

Transaction type: `CUT`

#### 3d. Regular Season

`_simulate_regular_season(season)` or `_simulate_regular_season_statistical(season)`

Two simulation modes:
- **Full simulation**: Uses game engine for each game
- **Statistical**: Quick results based on team strength

Records wins/losses for all teams.

#### 3e. Playoffs

`_simulate_playoffs(season)` or `_simulate_playoffs_simplified(season)`

- Top 14 teams qualify (7 per conference)
- Single elimination bracket
- Champion recorded in standings

### 4. Status Updates

After each season:
- Team status evaluated (Dynasty, Contending, Rebuilding, etc.)
- Status affects future AI decisions
- Championship and playoff appearances tracked

---

## AI Decision Systems

### GM Archetypes

Different GM personalities affect team-building strategy:

```python
class GMArchetype(Enum):
    ANALYTICS           # Data-driven, value contracts
    OLD_SCHOOL         # Trust veterans, proven players
    YOUTH_MOVEMENT     # Draft and develop
    WIN_NOW            # Aggressive free agency
    BALANCED           # Mix of approaches
```

### Team Needs Analysis

`calculate_team_needs(roster, contracts)` returns:

```python
@dataclass
class TeamNeeds:
    critical: list[Position]    # Must address immediately
    moderate: list[Position]    # Should improve
    depth: list[Position]       # Nice to have
```

### Draft AI

`DraftAI` selects players based on:
- Team needs priority
- Best player available
- Position value
- GM archetype preferences

### Free Agency AI

`FreeAgencyAI` evaluates:
- Player fit for team needs
- Market value vs. available cap
- Contract length preferences
- Age/prime window

### Roster AI

`RosterAI` handles:
- Starter selection
- Depth chart management
- Cut decisions

---

## Transaction Logging

All roster moves recorded in `TransactionLog`:

```python
@dataclass
class Transaction:
    type: TransactionType    # DRAFT, SIGNING, CUT, TRADE
    player_id: str
    player_name: str
    from_team: Optional[str]
    to_team: str
    season: int
    date: date
    details: dict           # Contract terms, pick info, etc.
```

Transaction types:
- `DRAFT` - Player drafted
- `SIGNING` - Free agent signed
- `CUT` - Player released
- `TRADE` - Player traded (future)
- `RESIGN` - Contract extension

---

## API Endpoints

**Base URL**: `/api/v1/history`

### Run Simulation

```http
POST /history/simulate
```

**Request Body**:
```json
{
  "num_teams": 32,
  "years_to_simulate": 4,
  "start_year": 2021
}
```

**Response** `200`:
```json
{
  "sim_id": "sim_abc123",
  "seasons_simulated": 4,
  "total_transactions": 2847,
  "teams": 32
}
```

### Stream Simulation Progress (SSE)

```http
GET /history/simulate-stream?num_teams=32&years_to_simulate=3&start_year=2021
```

Returns Server-Sent Events with progress messages.

### List Simulations

```http
GET /history/simulations
```

### Get Full Simulation

```http
GET /history/simulations/{sim_id}
```

Returns complete simulation data including all teams, standings, and transactions.

### Get Season Data

```http
GET /history/simulations/{sim_id}/seasons/{season}/teams
GET /history/simulations/{sim_id}/seasons/{season}/standings
GET /history/simulations/{sim_id}/seasons/{season}/draft
```

### Get Transactions

```http
GET /history/simulations/{sim_id}/transactions?season=2023&team_id=PHI&transaction_type=DRAFT
```

Filter by season, team, and transaction type.

### Get Team Roster

```http
GET /history/simulations/{sim_id}/teams/{team_id}/roster?season=2023
```

---

## Usage Example

```python
from huddle.core.simulation.historical_sim import (
    HistoricalSimulator,
    SimulationConfig,
)
from huddle.generators.player import generate_player
from huddle.core.league.nfl_data import NFL_TEAMS

# Configure simulation
config = SimulationConfig(
    years_to_simulate=4,
    target_season=2024,
    num_teams=32,
    verbose=True,
)

# Run simulation
simulator = HistoricalSimulator(
    config=config,
    player_generator=generate_player,
    team_data=NFL_TEAMS,
)

result = simulator.run()

# Access results
print(f"Simulated {result.seasons_simulated} seasons")
print(f"Total transactions: {result.total_transactions}")

# Get specific team
eagles = result.teams["PHI"]
print(f"Eagles: {eagles.wins}-{eagles.losses}")
print(f"Cap space: ${eagles.cap_space:,}")

# Browse transactions
for txn in result.transaction_log.transactions[-10:]:
    print(f"{txn.date}: {txn.type.value} - {txn.player_name} to {txn.to_team}")
```

---

## Integration Points

### With Management System

Historical simulation runs before franchise mode starts, creating:
- Realistic roster with contract years remaining
- Draft pick inventory with potential traded picks
- Team status reflecting recent performance
- Transaction history for context

### With Draft System

Draft results stored in `draft_histories`:
```python
draft_state = result.draft_histories[2023]
for pick in draft_state.picks:
    print(f"Pick {pick.overall}: {pick.player.name} to {pick.team_id}")
```

### With Calendar System

Each simulated season creates a `LeagueCalendar` with:
- Key dates (free agency, draft, training camp)
- Schedule of games
- Phase transitions

---

## Performance

| Teams | Years | Transactions | Time (approx) |
|-------|-------|--------------|---------------|
| 32 | 1 | ~700 | 2-5 seconds |
| 32 | 4 | ~2,800 | 8-20 seconds |
| 32 | 10 | ~7,000 | 20-50 seconds |

Use streaming endpoint for real-time progress on longer simulations.

---

## See Also

- [Draft System](../core/draft.md) - Draft picks and draft AI
- [Contracts](../core/contracts.md) - Contract creation and management
- [Team Identity](../core/team-identity.md) - Team status and archetypes
- [Transaction System](../core/transactions.md) - Transaction logging

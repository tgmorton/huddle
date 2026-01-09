# Huddle

American Football Simulation Engine with Franchise Management

A comprehensive football simulation featuring play-by-play simulation, franchise management, and AI-driven gameplay.

## Features

- **V2 Simulation Engine** - Tick-based play simulation with AI-controlled players
- **Franchise Management** - Full franchise mode with contracts, drafts, free agency
- **AI Player Brains** - Position-specific decision-making (QB reads, route running, coverage, blocking)
- **React Frontend** - Modern web interface for management and simulation visualization

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### Backend Setup

```bash
# Install Python package
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running the Application

**Terminal 1 - Start API Server:**
```bash
uvicorn huddle.api.main:create_app --factory --reload --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

- **API**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## Project Structure

```
huddle/
├── huddle/                    # Python backend
│   ├── api/                   # FastAPI application
│   │   ├── routers/           # REST endpoints
│   │   │   ├── management/    # Franchise management (modular)
│   │   │   ├── v2_sim.py      # Simulation control
│   │   │   └── ...
│   │   ├── schemas/           # Pydantic models
│   │   └── services/          # Business logic
│   ├── core/                  # Domain models
│   │   ├── ai/                # GM AI, draft AI, cap management
│   │   ├── contracts/         # Contract system, FA auctions
│   │   ├── models/            # Player, Team, League
│   │   └── ...
│   ├── management/            # Franchise mode logic
│   │   ├── calendar.py        # Season calendar
│   │   ├── events.py          # Management events
│   │   ├── health.py          # Injuries, fatigue
│   │   └── league.py          # League state orchestration
│   ├── simulation/            # Game simulation
│   │   ├── v2/                # V2 simulation engine
│   │   │   ├── ai/            # Player brains (QB, WR, DB, etc.)
│   │   │   ├── core/          # Entities, world state
│   │   │   ├── orchestrator.py
│   │   │   └── ...
│   │   └── arms_prototype/    # Blocking/tackling physics
│   └── game/                  # Game flow management
├── frontend/                  # React + TypeScript
│   └── src/
│       ├── components/
│       │   ├── ManagementV2/  # Franchise management UI
│       │   ├── V2Sim/         # Simulation visualizer
│       │   └── SimExplorer/   # Historical sim explorer
│       ├── stores/            # Zustand state management
│       └── hooks/             # WebSocket, API hooks
├── docs/                      # Documentation
│   ├── simulation/            # V2 sim architecture, brains
│   ├── management/            # Backend, API, frontend docs
│   ├── api/                   # Endpoint reference
│   └── ai/                    # AI decision systems
├── research/                  # NFL data analysis
│   ├── exports/               # Calibration data (JSON)
│   ├── models/                # Statistical models
│   └── reports/               # Analysis reports
├── agentmail/                 # Inter-agent communication
└── tests/                     # Test suites
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System overview |
| [Quick Start](docs/QUICK_START.md) | Getting started guide |
| [Simulation](docs/simulation/README.md) | V2 simulation engine |
| [Management](docs/management/README.md) | Franchise management system |
| [API Reference](docs/api/README.md) | REST endpoint documentation |

## Key Systems

### V2 Simulation Engine

Tick-based football simulation with:
- **Player Brains**: QB read progressions, receiver route running, DB coverage
- **Physics**: Movement, blocking engagements, tackle resolution
- **Play Concepts**: Pass/run plays, formations, route trees

### Franchise Management

Full franchise mode featuring:
- **Calendar System**: Day-based progression through NFL season
- **Contracts**: Negotiations, restructures, cap management
- **Draft**: Scouting, draft board, prospect evaluation
- **Free Agency**: Auction-based bidding for elite players

### AI Systems

- **GM Archetypes**: Different team-building philosophies
- **Draft AI**: Value-based pick selection
- **Cap Management**: Salary allocation optimization
- **Player Development**: Age curves, potential systems

## Development

### Running Tests

```bash
pytest
```

### Code Style

The project uses standard Python conventions. Run linting with:

```bash
ruff check huddle/
```

## AgentMail

The project includes an inter-agent communication system for coordinating AI development work. See [agentmail/README.md](agentmail/README.md) for details.

## License

Private project - All rights reserved

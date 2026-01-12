# Huddle Documentation

Welcome to the Huddle project documentation. This is a football simulation game with realistic AI decision-making, franchise management, and a modern React frontend.

## Quick Links

| I want to... | Go to |
|--------------|-------|
| Run the project | [Quick Start](QUICK_START.md) |
| Understand the system | [Architecture](ARCHITECTURE.md) |
| Work on simulation | [Simulation](simulation/README.md) |
| Work on game layer | [Game Layer](game/README.md) |
| Work on management UI | [Management](management/README.md) |
| Use the API | [API Reference](api/README.md) |
| Contribute as an agent | [AgentMail](agentmail/README.md) |

---

## Documentation Structure

```
docs/
├── README.md              ← You are here
├── QUICK_START.md         # How to run the project
├── ARCHITECTURE.md        # System overview
├── DESIGN_PHILOSOPHY.md   # Game vision and goals
│
├── simulation/            # V2 simulation engine
│   ├── README.md          # Simulation overview
│   ├── architecture.md    # Engine design
│   ├── orchestrator.md    # Game loop and phases
│   ├── physics.md         # Movement and bodies
│   ├── resolution.md      # Blocking, tackling
│   ├── plays.md           # Routes and concepts
│   ├── events.md          # Event bus system
│   ├── variance.md        # Randomness and outcomes
│   ├── improvements.md    # Known gaps and priorities
│   └── brains/            # AI decision-making
│       ├── README.md      # Brain system overview
│       ├── qb.md          # QB read progression
│       ├── ballcarrier.md # Run decisions
│       ├── receiver.md    # Route running
│       └── ...            # Other positions
│
├── game/                  # Game manager layer
│   └── README.md          # Bridges management ↔ simulation
│
├── management/            # Franchise management
│   ├── README.md          # Management overview
│   ├── backend.md         # Backend systems
│   └── frontend.md        # UI components
│
├── api/                   # REST API
│   ├── README.md          # API overview
│   └── endpoints.md       # Endpoint reference
│
├── agentmail/             # Agent communication system
│   ├── README.md          # Protocol overview
│   ├── NEW_AGENT_ONBOARDING.md
│   └── ...
│
└── reference/             # External references
    ├── fof9-ui.md         # FOF9 UI inspiration
    └── ui-ux-design.md    # Design patterns
```

---

## Key Concepts

### Simulation Engine

The v2 simulation models football plays from snap to whistle:

- **Orchestrator** - Manages game loop and phase transitions
- **Brains** - Position-specific AI decision-making
- **Physics** - Movement profiles and collision
- **Resolution** - Block/tackle/catch outcomes

See [simulation/README.md](simulation/README.md).

### Game Layer

Bridges management and simulation to run complete games:

- **GameManager** - Full game orchestration (quarters, halftime, overtime)
- **DriveManager** - Down/distance tracking, play execution
- **SpecialTeams** - Statistical kick resolution (NFL-backed rates)
- **DecisionLogic** - 4th down, 2PT, clock management AI
- **Coach Mode API** - REST + WebSocket for interactive play

See [game/README.md](game/README.md).

### Management System

Front-office operations with a workspace grid UI:

- **League/Franchise** - Season structure, team ownership
- **Roster Management** - Contracts, depth charts, trades
- **Draft System** - Scouting, prospects, draft day
- **Development** - Practice, player growth

See [management/README.md](management/README.md).

### AgentMail

Asynchronous communication system for AI agents working on the codebase:

- Markdown-based messages
- Git-friendly (no database)
- API-driven (not file manipulation)

See [agentmail/README.md](agentmail/README.md).

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI |
| Frontend | React, TypeScript |
| Simulation | Custom Python engine |
| API | REST + WebSocket |
| Styling | CSS (ops-center aesthetic) |

---

## Getting Started

```bash
# Backend
cd huddle
pip install -e .
python -m huddle

# Frontend
cd frontend
npm install
npm run dev
```

See [QUICK_START.md](QUICK_START.md) for detailed setup.

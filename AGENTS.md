# AGENTS.md - Coding Agent Instructions

This document provides essential information for AI coding agents working in the Huddle codebase.

## Project Overview

Huddle is an American football simulation engine with:
- **Backend**: Python 3.11+ with FastAPI (`/huddle`)
- **Frontend**: React 19 + TypeScript + Vite (`/frontend`)
- **Tests**: pytest (`/tests`)

## Build & Run Commands

### Backend (Python)

```bash
# Install dependencies
pip install -e ".[dev]"

# Run API server (development)
uvicorn huddle.api.main:create_app --factory --reload --port 8000

# Run via CLI
python -m huddle --api
```

### Frontend (React/TypeScript)

```bash
cd frontend
npm install
npm run dev      # Development server (port 5173)
npm run build    # Production build
npm run lint     # ESLint
```

## Test Commands

```bash
# Run all tests
pytest

# Run single test file
pytest tests/test_blocking_behaviors.py

# Run single test function
pytest tests/test_blocking_behaviors.py::test_specific_function

# Run tests matching pattern
pytest -k "test_blocking"

# Run with verbose output
pytest -v tests/test_play_sim_scenarios.py

# Run with coverage
pytest --cov=huddle tests/
```

## Lint & Type Check

```bash
# Python linting (ruff)
ruff check huddle/
ruff check --fix huddle/   # Auto-fix

# Python type checking (mypy - strict mode)
mypy huddle/

# Frontend linting
cd frontend && npm run lint
```

## Code Style Guidelines

### Python

**Line length**: 100 characters  
**Python version**: 3.11+  
**Type checking**: Strict (mypy)

**Import Order** (enforced by ruff):
```python
"""Module docstring."""

from __future__ import annotations  # If needed

# 1. Standard library
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

# 2. Third-party
from fastapi import APIRouter, HTTPException

# 3. Local imports
from huddle.core.models.player import Player
from huddle.core.enums import Position

# 4. TYPE_CHECKING block (for circular imports)
if TYPE_CHECKING:
    from huddle.core.contracts.contract import Contract
```

**Naming Conventions**:
| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `Player`, `GameState` |
| Functions/methods | snake_case | `calculate_market_value()` |
| Constants | UPPER_SNAKE | `EMPTY_EVENTS`, `MAX_ROSTER_SIZE` |
| Private | _leading_underscore | `_resolve_blocks()` |
| Type aliases | PascalCase | `BrainFunc = Callable[...]` |
| Enum values | UPPER_SNAKE | `PlayPhase.DEVELOPMENT` |

**Type Annotations** - Always use full annotations:
```python
@dataclass
class Player:
    """Represents a football player."""
    
    id: UUID = field(default_factory=uuid4)
    first_name: str = ""
    position: Position = Position.QB
    contract: Optional["Contract"] = None  # Forward ref for circular imports

def get_player_value(player: Player, market: MarketConditions) -> int:
    """Calculate player market value."""
    ...
```

**Error Handling**:
```python
# FastAPI endpoints - use HTTPException
if not player:
    raise HTTPException(status_code=404, detail="Player not found")

# Simulation/AI code - catch and log, don't crash
try:
    decision = brain(world_state)
except Exception as e:
    event_bus.emit_error(f"Brain error: {e}")
    return default_decision()
```

**Docstrings** - Use for modules, classes, and public functions:
```python
def get_trait(self, trait: Trait, default: float = 0.5) -> float:
    """
    Get a personality trait value.

    Args:
        trait: The trait to query
        default: Value if no personality assigned

    Returns:
        Trait value between 0.0 and 1.0
    """
```

### TypeScript/React

**ESLint**: typescript-eslint recommended + React Hooks plugin

**Component Pattern**:
```typescript
interface PlayerCardProps {
  player: Player;
  onSelect?: (id: string) => void;
}

export const PlayerCard: React.FC<PlayerCardProps> = ({ player, onSelect }) => {
  // hooks first
  const { isLoading } = usePlayerData(player.id);
  
  // early returns
  if (isLoading) return <Spinner />;
  
  return <div className="player-card">...</div>;
};
```

**Zustand Stores** - Use selectors with stable references:
```typescript
const EMPTY_EVENTS: Event[] = [];

export const selectPendingEvents = (state: Store) =>
  state.events?.pending ?? EMPTY_EVENTS;
```

## Test Patterns

**File naming**: `test_*.py`  
**Test location**: Mirror source structure in `tests/`

**Fixtures** (in `tests/conftest.py`):
```python
@pytest.fixture
def qb_player(default_attributes) -> Player:
    """Create a test quarterback."""
    return Player(
        id=uuid4(),
        first_name="Tom",
        last_name="Brady",
        position=Position.QB,
        attributes=default_attributes,
    )
```

## Project Structure

```
huddle/
├── huddle/           # Python backend
│   ├── api/          # FastAPI app (routers/, schemas/, services/)
│   ├── core/         # Domain models, enums, attributes
│   ├── management/   # Franchise mode (calendar, contracts, draft)
│   └── simulation/   # Game simulation engine
├── frontend/src/     # React frontend
│   ├── components/   # React components
│   ├── stores/       # Zustand state management
│   └── hooks/        # Custom React hooks
├── tests/            # pytest test suite
└── docs/             # Documentation
```

## AgentMail System

This project uses an inter-agent communication system. See `CLAUDE.md` for API details.

**Key rules**:
- Always use the API (`http://localhost:8000/api/v1/agentmail/`) - never edit message files directly
- Agent names use snake_case with `_agent` suffix: `live_sim_agent`, `qa_agent`
- Update your status file at `agentmail/status/{agent_name}_status.md`

## Common Pitfalls

1. **Circular imports**: Use `TYPE_CHECKING` blocks for type-only imports
2. **Mutable defaults**: Always use `field(default_factory=list)` in dataclasses
3. **Test isolation**: Use fixtures, don't share state between tests
4. **API changes**: Update both router and schema when modifying endpoints

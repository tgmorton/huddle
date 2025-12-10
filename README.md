# Huddle

American Football Simulator - A management game simulation engine with web interface.

## Installation

```bash
pip install -e .
```

## Running the API

```bash
python -m huddle.api.main
```

Or via the CLI:

```bash
huddle --api
```

Then visit http://localhost:8000/docs for the API documentation.

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## Architecture

- `huddle/core/` - Core data models (GameState, Team, Player, Play)
- `huddle/simulation/` - Simulation engine
- `huddle/api/` - FastAPI backend
- `frontend/` - React + TypeScript frontend (coming soon)

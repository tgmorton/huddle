# Quick Start Guide

Get Huddle running locally in under 5 minutes.

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

## Installation

### Backend

```bash
# From project root
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

### Frontend

```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Full Stack (API + Frontend)

**Terminal 1 - Start API Server:**
```bash
uvicorn huddle.api.main:create_app --factory --reload --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

- API available at: http://localhost:8000
- Frontend available at: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs

### Option 2: CLI Demo Mode

For quick testing without the full UI:

```bash
huddle --demo
```

This runs a quick simulation and outputs results to the terminal.

## Environment Variables

Currently none required. The application runs with defaults.

## Database

The project includes `aiosqlite` as a dependency but persistence is not yet implemented. All data is in-memory during runtime.

## Project Structure

```
huddle/
├── huddle/           # Python backend
│   ├── api/          # FastAPI application
│   ├── core/         # Domain models
│   ├── management/   # Franchise mode logic
│   └── simulation/   # Game simulation engines
├── frontend/         # React frontend
└── docs/             # Documentation
```

## Next Steps

- [Architecture Overview](./ARCHITECTURE.md)
- [API Reference](./api/README.md)
- [Design Philosophy](./DESIGN_PHILOSOPHY.md)

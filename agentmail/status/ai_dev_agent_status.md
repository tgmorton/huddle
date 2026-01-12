# AI Dev Agent - Status

**Last Updated:** 2026-01-10
**Agent Role:** Research and develop agentic AI integration for the football game

---

## Domain Overview

I explore solutions for integrating agentic AI into the Huddle football game. This project serves as a research testbed for novel AI-gaming integration, led by a PhD researcher focused on AI.

**Core Research Direction:** Dual-process AI architecture (Think Fast/Slow)
- **Slow Process (Agentic):** Curious agents that explore game ontology, discover narratives, build context
- **Fast Process (Generative):** Lightweight LLMs that consume context and produce real-time output

---

## ASSIGNMENT RECEIVED (2026-01-10)

### Vision: AI Integration Categories

**1. Text Generation (Straightforward)**
- News reports
- Scouting reports
- Press conferences
- Social media/ticker content

**2. Agentic Assistants (Player-Facing)**
- Statistician - query game data, surface insights
- Scout - evaluate players, provide opinions
- Coach assistant - explain strategy, suggest plays

**3. Behind-the-Scenes Agentic AI (Novel Research)**
- **Commentary System** - The flagship use case
  - Agentic layer: explores history, stats, matchups, narratives
  - Generative layer: produces fluent real-time commentary from context
  - Key insight: Color commentary requires *understanding*, not just generation

---

## TODAY'S WORK (2026-01-10)

### Phase 0: Coordination - COMPLETE
- Sent AgentMail to management_agent (`management_agent_to_052`)
- Proposed data model improvements: `team_id` on Player, standardized keys, player→stats index
- Awaiting response

### Phase 1: Infrastructure Setup - COMPLETE

**Files created:**
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Neo4j container definition |
| `huddle/graph/__init__.py` | Module exports |
| `huddle/graph/config.py` | Feature flag, connection settings |
| `huddle/graph/connection.py` | Neo4j driver management, session handling |
| `huddle/graph/schema.py` | Node labels, relationship types, constraints, indexes |
| `huddle/graph/sync/__init__.py` | Sync module exports |
| `huddle/graph/sync/base.py` | Core sync utilities, full_sync entry point |
| `huddle/graph/explore/__init__.py` | Exploration module (stub) |

**Dependency added:**
- `neo4j>=5.15.0` in `pyproject.toml`

**Quick start:**
```bash
# Start Neo4j
docker compose up -d neo4j

# Enable graph
export GRAPH_ENABLED=true

# Sync data (once Phase 2 complete)
python -c "from huddle.graph.sync import full_sync; full_sync(league)"

# Browse graph
open http://localhost:7474
```

---

## IN PROGRESS

| Component | Location | Notes |
|-----------|----------|-------|
| Graph Ontology Phase 2 | `huddle/graph/` | Core entity sync (Player, Team, relationships) |

---

## RESEARCH QUESTIONS

1. **What data/ontology exists?** Player stats, histories, team records, game logs?
2. **What are the technical constraints?** API costs, latency requirements, local vs cloud?
3. **What existing AI systems?** behavior_tree_agent work, researcher_agent models?
4. **Priority ordering?** Commentary system vs assistants vs text generation?

---

## NEXT UP

1. Explore codebase to understand data ontology
2. Review existing AI systems (docs/ai/, behavior_tree_agent work)
3. Draft architecture proposal for dual-process commentary system
4. Identify quick wins vs longer-term research projects

---

## COORDINATION

| Agent | Overlap |
|-------|---------|
| behavior_tree_agent | Player AI brains, decision systems |
| researcher_agent | NFL data analysis, statistical models |
| management_agent | GM/coach AI decisions |
| game_layer_agent | Game Manager layer, event streams |
| live_sim_agent | Real-time simulation data |

---

## NOTES

User is PhD researcher - this is academic research as much as game development. Novel approaches and publishable insights are valued.

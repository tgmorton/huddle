# Ontology Design Thinking

**Date:** 2026-01-10
**Status:** Early exploration

---

## The Question

How do we make Huddle's football world "natively explorable" by AI agents?

Not: "How do we add AI features to the game?"
But: "How do we structure the world so AI exploration is natural?"

---

## Palantir's Model (Reference)

Their Ontology layer provides:
- **Objects**: Semantic entities (not just data rows)
- **Links**: Traversable relationships (not just foreign keys)
- **Actions**: Meaningful operations (not just CRUD)
- **Functions**: Computed insights (not just raw properties)

An AI exploring their ontology doesn't need to understand databases or APIs - it understands the *domain*.

---

## Huddle's Current State

**Entities exist but aren't connected semantically:**

```
Player (models/player.py)
  - Has attributes, personality, contracts
  - But: relationships are UUIDs, not traversable links

Team (models/team.py)
  - Has roster, depth chart, tendencies
  - But: players are just IDs, games aren't linked

Game (models/game.py)
  - Has play-by-play, scores, stats
  - But: isolated from career arcs, historical context
```

**An AI exploring this would need to:**
1. Know the codebase structure
2. Write Python to query/join data
3. Understand implementation details

**This is the opposite of "natively explorable".**

---

## What Would "Natively Explorable" Look Like?

### Entity Graph

```
Player ──plays_for──▶ Team
   │                    │
   ├──has_personality   ├──has_tendency
   ├──has_contract      ├──plays_in_division
   ├──played_in────────▶ Game ◀──played_in────── Team
   │                      │
   ├──drafted_by          ├──contains_drives
   ├──traded_from         ├──contains_plays
   ├──injured_in          │
   │                      ▼
   │                    Play
   │                      │
   └──performed_in────────┘
```

### Semantic Properties (Beyond Raw Data)

**Player:**
- `career_phase`: "rising" | "peak" | "declining" | "twilight"
- `clutch_rating`: computed from late-game/high-pressure performance
- `chemistry_with(player)`: how well they perform together
- `historical_comps`: similar players from history
- `narrative_threads`: ongoing storylines (comeback, rivalry, etc.)

**Team:**
- `momentum`: recent form trajectory
- `identity`: what they're known for (ground-and-pound, air raid, etc.)
- `championship_window`: contending | rebuilding | emerging
- `historical_significance`: rivalries, legendary games, records

**Matchup (computed entity):**
- `historical_edge`: who has the advantage
- `key_battles`: which individual matchups matter most
- `scheme_fit`: how styles interact
- `narrative_context`: what makes this game meaningful

**Situation (computed entity):**
- `pressure_level`: how critical is this moment
- `historical_parallels`: similar situations and their outcomes
- `optimal_play`: what analytics suggests
- `tendency_vs_optimal`: what this team usually does

---

## The Exploration Interface

An AI should be able to:

```python
# Start anywhere
player = explore("Jalen Hurts")

# Traverse relationships
team = player.team
recent_games = player.games.last(5)
division_rivals = team.division.teams.exclude(team)

# Access computed properties
trend = player.performance_trend  # "improving"
comps = player.historical_comps   # ["Russell Wilson", "Cam Newton"]

# Discover narratives
narratives = player.active_narratives
# ["MVP candidate", "Leading Eagles playoff push", "Rivalry with Cowboys"]

# Ask semantic questions
similar = find_similar(player, scope="all_time")
matchup = get_matchup(player, opponent_player)
situation = current_situation(game)
```

**The AI doesn't call APIs or write SQL. It explores a world.**

---

## Implementation Questions

### Option A: Graph Database
Store entities and relationships in Neo4j or similar. Native graph traversal.
- Pro: True graph exploration
- Con: Another infrastructure component, sync with game state

### Option B: Semantic Layer
Build a Python abstraction over existing models that provides graph-like interface.
- Pro: Uses existing data, no new infrastructure
- Con: Need to build and maintain the abstraction

### Option C: Knowledge Graph Export
Periodically export game state to a knowledge graph format (RDF, JSON-LD).
- Pro: Standard formats, tooling exists
- Con: Not real-time, sync issues

### Option D: LLM-Native Exploration
Build tools that let the LLM explore via function calls, but design the tools semantically.
- Pro: Flexible, LLM handles ambiguity
- Con: Relies on LLM understanding, token costs

---

## Open Questions

1. **Real-time vs. Periodic**: Does the AI need live game state or can it work with snapshots?

2. **Depth vs. Breadth**: How deep should exploration go? (Full play-by-play vs. game summaries)

3. **Computed Properties**: Where do they live? Pre-computed or on-demand?

4. **Historical Scope**: How far back? Current season? All-time?

5. **Narrative Layer**: Who generates the narratives? Pre-defined or AI-discovered?

---

## Next Steps

1. Map existing entities and their natural relationships
2. Identify the most valuable computed properties
3. Design the exploration interface
4. Prototype with a single use case (e.g., "Tell me about this player")
5. Iterate based on what the AI finds interesting

---

## The Bet

If we build the ontology right, AI capabilities will **emerge** rather than needing to be engineered. The commentary system, the scout, the statistician - they're all just different **perspectives** on the same explorable world.

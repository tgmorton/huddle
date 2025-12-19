# Research Plan: AI Team Tendencies & UX Reality Check

**Author:** Researcher Agent
**Date:** 2025-12-18
**Status:** Planned - Ready to Execute
**Context:** Post-Inner Weather implementation, exploring adjacent domains

---

## Overview

Two exploration areas before returning to team dynamics / social contagion:

1. **AI Team Tendencies** - Do the 32 AI teams feel like different organizations?
2. **UX Reality Check** - Does my conceptual work connect to what players actually experience?

Both are reconnaissance - understanding what exists before proposing changes.

---

## Part 1: AI Team Tendencies

### The Question

The codebase has `core/models/tendencies.py` defining AI team behavior. But:
- Is it actually used in decision-making?
- Do teams feel different in practice?
- Is there room for "organizational psychology" - teams as cognitive agents?

### What To Explore

#### Files to Read
```
huddle/core/models/tendencies.py       # The tendencies model
huddle/core/contracts/ai_decisions.py  # How AI makes contract decisions
huddle/core/contracts/negotiation.py   # Negotiation - does tendency affect it?
huddle/core/scouting/                  # Do teams scout differently?
huddle/management/                     # LeagueState, event handling
```

#### Questions to Answer
1. **What tendencies exist?** (Draft strategy, trade aggression, negotiation style, etc.)
2. **Where are they consumed?** (Which systems actually read tendencies?)
3. **How do they affect behavior?** (Concrete examples of tendency → different outcome)
4. **What's missing?** (Tendencies defined but not used, or behaviors with no tendency)

#### The Deeper Question
Can we think of AI teams as having their own "organizational inner weather"?
- **Stable:** Franchise identity, owner personality, organizational culture
- **Seasonal:** Current regime philosophy, win-now vs rebuild
- **Situational:** Desperation level, cap health, draft position

A team that's 2-10 with a fired coach should behave differently than a 10-2 contender.

### Potential Outputs
- Map of tendency → behavior connections
- Gaps where tendencies exist but aren't used
- Proposal for "organizational psychology" if warranted
- Notes to relevant agents (management_agent likely)

---

## Part 2: UX Reality Check

### The Question

I've written conceptual models about mental state, signals vs numbers, body language, staff dialogue. But:
- What does the actual UI look like?
- What can players currently see and do?
- Does my conceptual work have a path to implementation?

### What To Explore

#### Files to Read
```
docs/UI_UX_DESIGN.md                   # 210KB design doc - the big one
frontend/src/components/Management/   # Management screen components
frontend/src/components/              # All UI components
frontend/src/types/                   # Data structures frontend expects
frontend/src/stores/                  # State management
```

#### Questions to Answer
1. **What screens exist?** (Management, game day, scouting, etc.)
2. **What information is displayed?** (Stats, ratings, or qualitative?)
3. **How is player state shown?** (Numbers? Descriptions? Visuals?)
4. **What's the interaction model?** (Turn-based? Real-time? Calendar-driven?)
5. **Where could Inner Weather surface?** (Specific screens, moments)

#### The Deeper Question
Is the UX designed for "signals not numbers" or for spreadsheet optimization?

The design philosophy says:
> "You're not reading spreadsheets; you're forming judgments with incomplete data"

Does the actual UI support that, or does it expose raw numbers?

### Potential Outputs
- Map of existing screens and what they show
- Assessment of "signals vs numbers" in current design
- Specific recommendations for where Inner Weather could surface
- Notes to frontend_agent (future) with concrete integration points

---

## Execution Order

### Step 1: AI Team Tendencies (Faster)
- Read tendencies.py and ai_decisions.py
- Trace where tendencies are consumed
- Assess if teams feel different
- Write findings

### Step 2: UX Reality Check (Slower, Big Doc)
- Read UI_UX_DESIGN.md (this is the big lift)
- Skim frontend components for structure
- Assess alignment with design philosophy
- Write findings

### Step 3: Synthesize
- How do these connect to Inner Weather?
- What agents need to know?
- What's the next research direction?

---

## Connection to Previous Work

### Inner Weather Model
- **Tendencies:** Could extend to "organizational inner weather" for AI teams
- **UX:** Determines how Inner Weather surfaces to players

### Earlier Research Notes
- Scout biases (management_agent) - connects to AI team scouting behavior
- Narrative hooks (narrative_agent) - connects to UX presentation
- Frontend brief (frontend_agent) - needs grounding in actual UI

---

## Success Criteria

After this exploration, I should be able to answer:

1. **Tendencies:** "AI teams [do/don't] feel meaningfully different because [reasons]. The system [is/isn't] used for [specific behaviors]. Opportunity exists for [specific enhancement]."

2. **UX:** "The current UI [does/doesn't] support signals-over-numbers because [specific examples]. Inner Weather could surface at [specific locations]. The gap between design philosophy and implementation is [assessment]."

---

## Notes for Post-Compaction

If resuming after context compaction:

1. **Start with tendencies.py** - it's smaller and faster
2. **The big read is UI_UX_DESIGN.md** - 210KB, budget time
3. **You're looking for connections** - how do systems talk to each other?
4. **Inner Weather is implemented** - Stable/Weekly layers done, In-Game ready for simulation
5. **Your role is conceptual** - don't write code, write insights and connections

Key files already explored:
- `core/personality/` - done, extended for Inner Weather
- `core/approval.py` - done, feeds Weekly layer
- `core/playbook/learning.py` - done, affects cognitive load
- `simulation/v2/ai/` - done, brains will consume mental state

Key files NOT yet explored:
- `core/models/tendencies.py` - this exploration
- `docs/UI_UX_DESIGN.md` - this exploration
- `core/contracts/ai_decisions.py` - related to tendencies

---

## After This Exploration

The next major research area is likely **Team Dynamics / Social Contagion**:
- Does confidence spread between players?
- Do veterans stabilize rookies?
- Is there collective momentum?

But that depends on what these explorations reveal.

---

**End of Plan**

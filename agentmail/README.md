# Agentmail - Inter-Agent Communication Protocol

This folder enables asynchronous communication between AI agents working on the Huddle codebase. Agents may work in parallel on orthogonal systems and need a reliable way to coordinate, share context, and avoid conflicts.

---

## Quick Start: API Access

Agents can communicate programmatically using the REST API or Python SDK.

### Using the Python SDK

```python
from agentmail.sdk import AgentMailClient

# Initialize with your agent identity
client = AgentMailClient("qa_agent")

# Get full context when starting a session
context = client.get_context()
print(f"You have {context['inbox']['unread_count']} messages")

# Send a message to another agent
client.send_message(
    to_agent="live_sim_agent",
    subject="Bug: Pursuit angles not calculating",
    message_type="bug",
    severity="MAJOR",
    content="## Summary\n\nThe pursuit system is not calculating intercept angles..."
)

# Update your status
client.update_status(
    role="Quality assurance, integration testing",
    in_progress=[{"component": "Pursuit bug", "location": "db_brain.py", "notes": "Investigating"}],
    next_up=["Test tackle resolution", "Run regression suite"]
)
```

### Using the REST API directly

```bash
# Get your inbox
curl http://localhost:8000/api/v1/agentmail/inbox/qa_agent

# Get full context (recommended first call)
curl http://localhost:8000/api/v1/agentmail/context/qa_agent

# Send a message
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "qa_agent",
    "to_agent": "live_sim_agent",
    "subject": "Bug found",
    "message_type": "bug",
    "severity": "MAJOR",
    "content": "## Summary\n\nBug details here..."
  }'

# Update status
curl -X POST http://localhost:8000/api/v1/agentmail/status/update \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "qa_agent",
    "in_progress": [{"component": "Bug fix", "location": "file.py", "notes": "Working"}]
  }'
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agentmail/context/{agent}` | Full context for starting a session |
| GET | `/agentmail/inbox/{agent}` | Get messages addressed to agent |
| GET | `/agentmail/outbox/{agent}` | Get messages sent by agent |
| POST | `/agentmail/send` | Send a message to another agent |
| POST | `/agentmail/status/update` | Update agent's status |
| POST | `/agentmail/tuning-notes/add` | Add a shared tuning note |
| GET | `/agentmail/dashboard` | Full dashboard data |
| GET | `/agentmail/messages` | All messages (with filters) |
| GET | `/agentmail/kanban` | Messages grouped by status (Kanban view) |
| POST | `/agentmail/search` | Search across messages, notes, status |
| GET | `/agentmail/agents/{agent}/notes` | Get agent's notes |
| POST | `/agentmail/agents/{agent}/notes/add` | Add a note |
| GET | `/agentmail/file-preview` | Preview file content |
| GET | `/agentmail/threads/{thread_id}` | Get thread with all replies |
| WS | `/ws/agentmail` | WebSocket for real-time updates |

### Dashboard

The AgentMail dashboard is available at `http://localhost:5173` when the frontend is running. Features:
- **List View**: Traditional message list with filtering
- **Kanban View**: Drag messages between status columns (Open → In Progress → Resolved → Closed)
- **Agent Notes**: Per-agent knowledge base
- **Thread View**: See full conversation threads
- **Search**: Full-text search across all content (Cmd+K)
- **Real-time Updates**: WebSocket connection for live updates

---

## Principles

1. **Async by default** - Agents work independently; don't assume immediate response
2. **Self-contained messages** - Include enough context that the recipient can act without reading the entire codebase
3. **Clear ownership** - Each agent has a defined domain; respect boundaries
4. **Status transparency** - Keep your status file updated so others know what's in flight
5. **No blocking** - If waiting on another agent, continue with other work

---

## Folder Structure

```
agentmail/
├── README.md                          # This file - protocol documentation
├── CLAUDE_AGENT_GUIDE.md              # Tool definitions for Claude agents
├── <agent>/                           # Agent-specific folder
│   ├── to/                            # Messages TO this agent
│   │   └── NNN_<topic>.md             # Numbered incoming messages/tasks
│   ├── from/                          # Messages FROM this agent
│   │   └── NNN_<response>.md          # Numbered outgoing responses
│   ├── plans/                         # Implementation plans & specs
│   │   └── NNN_<plan>.md              # Numbered plans, contracts, specs
│   └── notes/                         # Agent's personal knowledge base
│       └── NNN_<topic>.md             # Technical notes, learnings
├── status/                            # Current status of all active agents
│   └── <agent>_status.md              # What's done, in progress, blocked
└── tuning_notes/                      # Shared technical notes (cross-agent)
    └── NNN_<topic>.md                 # Numbered for ordering
```

---

## Naming Conventions

### Agent Names (use snake_case)
- `live_sim_agent` - Core simulation, physics, orchestration
- `behavior_tree_agent` - AI brains for players (QB, ballcarrier, etc.)
- `documentation_agent` - Codebase documentation
- `management_agent` - Management systems (contracts, scouting, etc.)
- `frontend_agent` - React/TypeScript UI
- `data_generation_agent` - Player/roster/draft class generation

### File Types

| Pattern | Location | Purpose | Example |
|---------|----------|---------|---------|
| `NNN_<topic>.md` | `<agent>/to/` | Task/message to agent | `behavior_tree_agent/to/001_task.md` |
| `NNN_<response>.md` | `<agent>/from/` | Agent's response/update | `behavior_tree_agent/from/001_status.md` |
| `NNN_<plan>.md` | `<agent>/plans/` | Implementation plans/specs | `behavior_tree_agent/plans/001_interface_contract.md` |
| `<agent>_status.md` | `status/` | Current work status | `status/live_sim_agent_status.md` |
| `NNN_<topic>.md` | `tuning_notes/` | Shared technical notes | `tuning_notes/001_coverage_separation.md` |

---

## Message Format

### Task Brief (`<agent>/to/NNN_<topic>.md`)

```markdown
# <Agent Name> Brief

## Your Mission
[Clear, actionable objective]

## Context
[What the agent needs to know about the project state]

## Key Reference Documents
[Files to read first]

## Deliverables
[Specific outputs expected]

## Coordination
[How to communicate back, who else is involved]
```

### Response (`<agent>/from/NNN_<response>.md`)

```markdown
# Response from <Agent Name>

**From:** <Agent Name>
**To:** <Requesting Agent or "All">
**Date:** YYYY-MM-DD
**Re:** <Topic>

---

## Acknowledgment
[Confirm receipt, summarize understanding]

## Plan/Approach
[How you'll tackle it]

## Questions
[What you need clarified]

## Timeline
[When to expect deliverables]
```

### Agent Note (`<agent>/notes/NNN_<topic>.md`)

```markdown
# Note Title

**Date:** YYYY-MM-DD
**Tags:** tag1, tag2
**Domain:** simulation

---

[Note content - technical learnings, implementation details, reference material]
```

### Status Update (`status/<agent>_status.md`)

```markdown
# <Agent Name> - Status

**Last Updated:** YYYY-MM-DD
**Agent Role:** [Brief description]

---

## COMPLETE
| Component | Location | Notes |
|-----------|----------|-------|
| ... | ... | ... |

## IN PROGRESS
| Component | Location | ETA | Notes |
|-----------|----------|-----|-------|
| ... | ... | ... | ... |

## BLOCKED
| Issue | Waiting On | Notes |
|-------|-----------|-------|
| ... | ... | ... |

## NEXT UP
[Prioritized list of upcoming work]

## Coordination Notes
[Who you're working with, dependencies]
```

---

## Coordination Patterns

### Pattern 1: Interface Contract
When agents need to integrate, define the interface first:

1. Agent A creates `<agent_b>/plans/NNN_interface_contract.md`
2. Agent B responds in `<agent_b>/from/NNN_response.md` with questions/confirmation
3. Both build to the agreed interface
4. Integration happens when both sides ready

### Pattern 2: Handoff
When work moves from one agent to another:

1. Completing agent updates their status file
2. Creates `<next_agent>/to/NNN_handoff.md` with context
3. Next agent acknowledges in `<next_agent>/from/NNN_acknowledgment.md`

### Pattern 3: Shared Notes
For technical insights that benefit all agents:

1. Add to `tuning_notes/NNN_<topic>.md`
2. Reference in your status file
3. Other agents check tuning_notes periodically

### Pattern 4: Status Check
Before starting work that might conflict:

1. Check `status/` for all active agents
2. Check relevant agent folders for recent activity (especially `<agent>/from/`)
3. If overlap detected, coordinate via `<agent>/to/NNN_coordination.md`

---

## Active Agents Registry

Update this section when new agents come online:

| Agent | Domain | Folder | Status File | Last Active |
|-------|--------|--------|-------------|-------------|
| `claude_code_agent` | Bug reports, feature requests, AgentMail tooling | `claude_code_agent/` | `status/claude_code_agent_status.md` | Active |
| `live_sim_agent` | V2 simulation core, physics, orchestrator | `live_sim_agent/` | `status/live_sim_agent_status.md` | Active |
| `live_sim_frontend_agent` | V2 sim visualization, V2SimScreen/Canvas | `live_sim_frontend_agent/` | `status/live_sim_frontend_agent_status.md` | Active |
| `qa_agent` | Integration testing, bug finding | `qa_agent/` | `status/qa_agent_status.md` | Active |
| `behavior_tree_agent` | AI player brains (QB, WR, DB, etc.) | `behavior_tree_agent/` | `status/behavior_tree_agent_status.md` | Active |
| `documentation_agent` | Codebase docs, API docs | `documentation_agent/` | `status/documentation_agent_status.md` | Active |
| `management_agent` | Management systems, contracts, draft | `management_agent/` | `status/management_agent_status.md` | Active |
| `frontend_agent` | React UI (ManagementV2, general) | `frontend_agent/` | `status/frontend_agent_status.md` | Active |
| `researcher_agent` | Cross-domain research, NFL data | `researcher_agent/` | `status/researcher_agent_status.md` | Active |
| `auditor_agent` | Code quality, dead code, TODOs | `auditor_agent/` | `status/auditor_agent_status.md` | Active |
| `narrative_agent` | Commentary, story generation | `narrative_agent/` | - | Future |
| `data_generation_agent` | Player/roster/draft generation | `data_generation_agent/` | - | Future |

---

## Best Practices

### DO
- Update your status file after completing significant work
- Include file paths in all references
- Ask clarifying questions before assuming
- Check for existing work before starting something new
- Keep messages focused and actionable

### DON'T
- Modify files in another agent's domain without coordination
- Leave stale status (update or mark inactive)
- Create circular dependencies between agents
- Assume synchronous communication
- Duplicate work already done by another agent

---

## Reading Order for New Agents

1. This README
2. `docs/DESIGN_PHILOSOPHY.md` - Game vision
3. `NFLHEADCOACH09DETAILS.md` - Reference game systems
4. `status/` - See what's in flight
5. Your agent folder `<your_agent>/to/` - Check for incoming tasks
6. Your agent folder `<your_agent>/plans/` - Review any existing plans

---

## Questions?

If the protocol needs updating, add a note to `tuning_notes/` proposing changes. The next agent to encounter the issue can implement improvements.

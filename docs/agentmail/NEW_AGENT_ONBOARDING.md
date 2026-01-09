# New Agent Onboarding

Welcome to the Huddle project. This guide gets you oriented with AgentMail and ready to collaborate.

## Step 1: Understand AgentMail

AgentMail is how agents communicate asynchronously. All messages are stored as markdown files - no database, fully git-friendly.

**Read these first:**
- `CLAUDE.md` (project root) - **API cheatsheet - ALWAYS USE API, NOT FILES**
- `agentmail/README.md` - Protocol overview

## Step 2: Check Your Previous Status

If you've worked on this project before, your status file contains what you were doing:

```
agentmail/status/{your_agent_name}_status.md
```

This file shows:
- What you completed
- What was in progress
- What you were blocked on
- Your next priorities

**If it exists, read it to restore context.**

## Step 3: Check Your Inbox

Your inbox contains messages and tasks from other agents:

```
agentmail/{your_agent_name}/to/
```

Files are numbered (001, 002, etc.) - read them in order or check the most recent.

Also check:
- `agentmail/{your_agent_name}/plans/` - Implementation specs
- `agentmail/{your_agent_name}/notes/` - Your personal knowledge base

## Step 4: Check Team Status

See what other agents are working on to avoid conflicts:

```
agentmail/status/
```

Read status files for agents whose work might overlap with yours.

## Step 5: Update Your Status

Create or update your status file to let others know you're active:

```markdown
# Your Agent Name - Status

**Last Updated:** YYYY-MM-DD
**Agent Role:** Your domain/responsibility

---

## IN PROGRESS
| Component | Location | Notes |
|-----------|----------|-------|
| Task name | file.py | What you're doing |

## NEXT UP
1. First priority
2. Second priority

## Coordination Notes
Working with X agent on Y feature.
```

---

## Dos and Don'ts

### Do

- **Use threading** - Always include `in_reply_to` and `thread_id` when replying
- **Be verbose** - Other agents have no shared memory; include full context
- **Include file paths** - Reference specific files and line numbers
- **Update your status** - After completing significant work
- **Check before modifying shared code** - Coordinate with the owning agent first
- **Continue when blocked** - Find other tasks instead of waiting idle

### Don't

- **Don't modify files directly in `agentmail/`** - Use the API for sending messages
- **Don't skip threading** - It breaks conversation history
- **Don't leave stale status** - Update or mark as inactive
- **Don't assume synchronous communication** - Agents work independently
- **Don't duplicate work** - Check status files and recent messages first

---

## Key Docs

| Document | Location | Purpose |
|----------|----------|---------|
| **API Cheatsheet** | `CLAUDE.md` (project root) | **curl commands - USE THIS** |
| Protocol overview | `agentmail/README.md` | Folder structure, patterns |
| Architecture | `docs/ARCHITECTURE.md` | System components |
| Design philosophy | `docs/DESIGN_PHILOSOPHY.md` | Game vision |
| Agent workflows | `docs/agentmail/AGENT_WORKFLOWS.md` | Common patterns |

---

## Agent Directory

| Agent | Domain |
|-------|--------|
| `live_sim_agent` | Core simulation, physics |
| `live_sim_frontend_agent` | V2 sim visualization, V2SimScreen/Canvas |
| `game_layer_agent` | Game Manager layer, bridges management ↔ v2 sim |
| `qa_agent` | Testing, bug finding |
| `behavior_tree_agent` | AI player brains |
| `management_agent` | Contracts, scouting |
| `researcher_agent` | Cross-domain research |
| `frontend_agent` | React UI (general) |
| `documentation_agent` | Documentation |
| `auditor_agent` | Code quality, dead code detection |
| `claude_code_agent` | AgentMail issues, tooling |

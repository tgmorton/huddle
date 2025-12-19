# AgentMail Workflows for AI Agents

This guide covers common patterns for AI agents using the AgentMail system.

## Session Lifecycle

### Starting a Session

1. **Get your briefing**
   ```bash
   curl -s http://localhost:8000/api/v1/agentmail/briefing/your_agent_name
   ```
   Returns plain text with inbox summary and useful commands.

2. **Send a heartbeat** (marks you as online)
   ```bash
   curl -X POST http://localhost:8000/api/v1/agentmail/heartbeat \
     -H "Content-Type: application/json" \
     -d '{"agent_name": "your_agent_name"}'
   ```

3. **Update your status file**
   Write to: `agentmail/status/your_agent_name_status.md`
   ```markdown
   # Your Agent Status

   Starting new session. Reviewing inbox.

   ## IN PROGRESS
   - Catching up on messages

   ## NEXT UP
   - [Your planned work]
   ```

### During a Session

- **Poll for new messages** periodically:
  ```bash
  curl -s "http://localhost:8000/api/v1/agentmail/inbox/your_agent/since/2024-01-15T10:00:00"
  ```

- **Send heartbeats** every few minutes to stay marked as online

- **Update your status file** after completing significant work

### Ending a Session

Update your status file to reflect completed work:
```markdown
# Your Agent Status

Session complete.

## COMPLETE
| Component | Location | Notes |
|-----------|----------|-------|
| Bug fix | db_brain.py:100 | Fixed pursuit calculation |

## NEXT UP
- Continue with remaining tests
```

---

## Message Types

| Type | When to Use | Example |
|------|-------------|---------|
| `task` | Assign work to another agent | "Please implement X" |
| `response` | Reply to a message | "Re: Your question about..." |
| `bug` | Report an issue found | "Bug: Pursuit angles broken" |
| `plan` | Share an implementation plan | "Plan: Cognitive state model" |
| `handoff` | Transfer work to another agent | "Handoff: API complete, ready for frontend" |
| `question` | Ask for clarification | "Question: Interface contract" |

### Severity Levels (for bugs)

| Severity | Meaning |
|----------|---------|
| `BLOCKING` | Cannot continue work, needs immediate attention |
| `MAJOR` | Significant issue but work can continue |
| `MINOR` | Small issue, low priority |
| `INFO` | Informational, no action required |

---

## Common Workflows

### Workflow 1: Reporting a Bug

```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "qa_agent",
    "to_agent": "live_sim_agent",
    "subject": "Bug: Pursuit angles not calculating",
    "message_type": "bug",
    "severity": "MAJOR",
    "content": "## Summary\n\nThe pursuit system is not calculating intercept angles.\n\n## Steps to Reproduce\n1. Run test_passing_integration.py\n2. Observe defender behavior\n\n## Expected\nDefenders intercept ballcarrier\n\n## Actual\nDefenders chase current position",
    "file_references": [{"path": "db_brain.py", "lines": [100, 120]}]
  }'
```

### Workflow 2: Replying to a Message (Threading)

**Always include `in_reply_to` and `thread_id` when replying.**

```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "live_sim_agent",
    "to_agent": "qa_agent",
    "subject": "Re: Bug: Pursuit angles not calculating",
    "message_type": "response",
    "content": "## Fix Applied\n\nI found the root cause and pushed a fix.\n\n## Changes\n- db_brain.py:105 - Fixed angle calculation\n\nPlease verify.",
    "in_reply_to": "qa_agent_from_001",
    "thread_id": "pursuit_bug_001"
  }'
```

### Workflow 3: Handing Off Work

```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "live_sim_agent",
    "to_agent": "frontend_agent",
    "subject": "Handoff: API endpoints ready",
    "message_type": "handoff",
    "content": "## Context\n\nI have completed the API work for the dashboard.\n\n## Files Changed\n- api/routes.py - New endpoints\n- api/models.py - Data models\n\n## Your Next Steps\n1. Create React components\n2. Wire up to endpoints\n\n## Testing\n`curl http://localhost:8000/api/v1/agentmail/dashboard`"
  }'
```

### Workflow 4: Coordinating on Shared Code

Before modifying code another agent owns:

1. **Check their status**
   ```bash
   curl -s http://localhost:8000/api/v1/agentmail/agents/target_agent/status
   ```

2. **Send coordination message**
   ```bash
   curl -X POST http://localhost:8000/api/v1/agentmail/send \
     -H "Content-Type: application/json" \
     -d '{
       "from_agent": "your_agent",
       "to_agent": "interface_owner",
       "subject": "Coordination: Planning changes to PlayerState",
       "message_type": "plan",
       "content": "## Proposed Changes\n\nI need to add a momentum field to PlayerState.\n\n## Impact\nAffects: physics.py, movement.py\n\n## Questions\nWill this conflict with your current work?"
     }'
   ```

3. **Wait for response** before making changes (continue other work)

### Workflow 5: Multi-Agent Discussion (CC)

```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "qa_agent",
    "to_agent": "live_sim_agent",
    "cc": ["behavior_tree_agent", "researcher_agent"],
    "subject": "Coordination: Physics-AI interface",
    "message_type": "plan",
    "thread_id": "physics_ai_interface",
    "content": "## Discussion\n\nWe need to coordinate changes to the physics-AI interface.\n\n## Participants Needed\n- live_sim_agent: Physics side\n- behavior_tree_agent: AI side\n- researcher_agent: Design review"
  }'
```

When replying to a CC'd message, include all participants:
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "behavior_tree_agent",
    "to_agent": "qa_agent",
    "cc": ["live_sim_agent", "researcher_agent"],
    "subject": "Re: Coordination: Physics-AI interface",
    "message_type": "response",
    "in_reply_to": "qa_agent_from_010",
    "thread_id": "physics_ai_interface",
    "content": "## My Input\n\nFrom the AI side, we need..."
  }'
```

### Workflow 6: Updating Message Status

Track your progress on tasks:

```bash
# Mark as started
curl -X POST http://localhost:8000/api/v1/agentmail/messages/status \
  -H "Content-Type: application/json" \
  -d '{"message_id": "your_agent_to_001", "status": "in_progress"}'

# Mark as done
curl -X POST http://localhost:8000/api/v1/agentmail/messages/status \
  -H "Content-Type: application/json" \
  -d '{"message_id": "your_agent_to_001", "status": "resolved"}'
```

Status flow: `open` → `in_progress` → `resolved` → `closed`

---

## Status File Format

Your status file (`agentmail/status/your_agent_name_status.md`) should include:

```markdown
# Your Agent Name - Status

**Last Updated:** 2024-01-15
**Agent Role:** Your domain/responsibility

---

## COMPLETE
| Component | Location | Notes |
|-----------|----------|-------|
| Feature X | file.py | Working |

## IN PROGRESS
| Component | Location | ETA | Notes |
|-----------|----------|-----|-------|
| Bug fix | other.py | Today | Investigating |

## BLOCKED
| Issue | Waiting On | Notes |
|-------|-----------|-------|
| Interface change | live_sim_agent | Sent message |

## NEXT UP
1. First priority task
2. Second priority task

## Coordination Notes
Working with live_sim_agent on physics integration.
```

---

## Best Practices

### Do

- **Always use threading** for replies (`in_reply_to` and `thread_id`)
- **Include file references** when discussing code
- **Update your status file** after completing significant work
- **Check agent status** before modifying shared code
- **Continue working when blocked** - find other tasks

### Don't

- **Don't wait idle** for responses - continue with unblocked work
- **Don't modify shared code** without coordination
- **Don't leave stale status** - update or mark as inactive
- **Don't assume synchronous communication** - agents work independently
- **Don't skip threading** - it breaks conversation history

### Message Content Guidelines

1. **Be verbose** - other agents have no shared memory
2. **Include file paths** with line numbers when relevant
3. **Structure with markdown** - use headers, lists, code blocks
4. **Include reproduction steps** for bugs
5. **Propose specific solutions** rather than just reporting problems

---

## Agent Directory

| Agent | Domain | When to Contact |
|-------|--------|-----------------|
| `claude_code_agent` | AgentMail system | Bug reports, feature requests |
| `live_sim_agent` | Core simulation, physics | Physics bugs, movement issues |
| `qa_agent` | Testing, integration | Test failures, verification |
| `behavior_tree_agent` | AI player brains | Decision logic, player behavior |
| `management_agent` | Contracts, scouting | Management systems |
| `frontend_agent` | React UI | Visual bugs, UX issues |
| `documentation_agent` | Documentation | Doc gaps or errors |
| `researcher_agent` | Cross-domain research | Complex design problems |

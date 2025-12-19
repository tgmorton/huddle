# Claude Agent Integration Guide

This document provides everything a Claude model needs to participate in the AgentMail inter-agent communication system.

---

## Quick Start

> **IMPORTANT: Use the API, Not File Operations**
>
> Always use `curl` commands to interact with AgentMail. Do NOT directly create or edit files in the `agentmail/` folder unless absolutely necessary.
>
> - **Sending messages**: Use `POST /send` (not creating files in `to/` folders)
> - **Updating status**: Use `POST /messages/status` (not editing message files)
> - **Reading messages**: Use `GET /messages/{id}` (not reading files directly)
>
> The only exception is your **status file** (`agentmail/status/{agent}_status.md`) which you update by overwriting directly.
>
> Why? The API handles message IDs, timestamps, routing, and dashboard updates automatically.

> **MANDATORY: Always Use Threading**
>
> When replying to ANY message, you MUST include threading headers:
>
> ```json
> {
>   "in_reply_to": "original_message_id",
>   "thread_id": "the_thread_id_from_original"
> }
> ```
>
> **Why?** Without threading:
> - Conversations appear as disconnected messages
> - Reply-All functionality breaks
> - The Manager cannot track related discussions
> - Context is lost when reviewing past work
>
> See [Workflow 7](#workflow-7-using-threads-for-related-messages) for detailed examples.

### 1. Get Your Briefing
```bash
curl -s http://localhost:8000/api/v1/agentmail/briefing/{your_agent_name}
```
Returns plain text with inbox summary and copy-paste commands.

### 2. See All Agents (Who Can I Message?)
```bash
curl -s http://localhost:8000/api/v1/agentmail/agents/list | python3 -c "import sys,json; [print(f'{a[\"name\"]}: {a[\"role\"]}') for a in json.load(sys.stdin)['agents']]"
```

### 3. Read a Message
```bash
curl -s http://localhost:8000/api/v1/agentmail/messages/{message_id}
```
**Note:** Use `/messages/{id}` NOT `/messages/{id}/content`

### 4. Send a Message
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{"from_agent": "your_agent", "to_agent": "target_agent", "subject": "Subject", "message_type": "response", "content": "Message body"}'
```

### 4b. Send with CC (Multiple Recipients)
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{"from_agent": "your_agent", "to_agent": "primary_recipient", "cc": ["agent2", "agent3"], "subject": "Subject", "message_type": "task", "content": "Message body"}'
```

### 5. Send Message from File (Recommended for Long Content)
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{"from_agent": "your_agent", "to_agent": "target_agent", "subject": "My Plan", "message_type": "plan", "content_file": "your_agent/plans/001_plan.md"}'
```

### 6. Update Message Status
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/messages/status \
  -H "Content-Type: application/json" \
  -d '{"message_id": "agent_to_001", "status": "in_progress"}'
```
Statuses: `open` → `in_progress` → `resolved` → `closed`

### 7. Acknowledge a Message
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/messages/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"message_id": "live_sim_agent_to_011", "agent_name": "your_agent_name"}'
```
Marks that you've received/read a message without changing its status.

### 8. Get Full Context (JSON)
```bash
curl -s http://localhost:8000/api/v1/agentmail/context/{your_agent_name}
```
Returns: inbox, outbox, plans, notes, team_statuses, tuning_notes

---

## System Prompt Template

Add this to your Claude agent's system prompt to enable AgentMail participation:

```
You are an AI agent participating in a multi-agent development environment for the Huddle football simulation project.

## AgentMail Communication

You have access to the AgentMail system for coordinating with other agents. The API runs at http://localhost:8000/api/v1/agentmail

### Your Agent Identity
- Agent Name: {YOUR_AGENT_NAME}
- Role: {YOUR_ROLE_DESCRIPTION}
- Domain: {YOUR_DOMAIN_OWNERSHIP}

### Communication Protocol

**CRITICAL: Always use curl/API commands. Do NOT create or edit files in agentmail/ folders directly (except your status file).**

1. **Quick Start**: Get a text briefing with your inbox summary and useful commands:
   ```
   curl -s http://localhost:8000/api/v1/agentmail/briefing/{your_agent_name}
   ```

2. **Full Context**: For complete JSON data, call GET /context/{your_agent_name} to get:
   - Your inbox (unread messages and tasks)
   - Current status
   - Other agents' statuses
   - Shared tuning notes

3. **Send Messages via API**: Use POST /send - never write message files directly

4. **Update Message Status via API**: Use POST /messages/status to mark messages as in_progress/resolved

5. **Check Messages Regularly**: Poll your inbox periodically during long sessions

6. **Update Status File**: The ONE exception - keep your status file current (`agentmail/status/{your_agent_name}_status.md`) by overwriting it with your current state in freeform markdown

7. **Coordinate Before Acting**: Check status files before modifying shared code

### Message Types
- `task`: Assign work to another agent
- `response`: Reply to a message
- `bug`: Report an issue found
- `plan`: Share an implementation plan
- `handoff`: Transfer work to another agent
- `question`: Ask for clarification

### Severity Levels (for bugs)
- `BLOCKING`: Prevents progress, needs immediate attention
- `MAJOR`: Significant issue but work can continue
- `MINOR`: Small issue, low priority
- `INFO`: Informational, no action required
```

---

## Tool Definitions

Define these tools for your Claude agent to use the AgentMail API:

### Tool 1: Get Agent Context

```json
{
  "name": "agentmail_get_context",
  "description": "Get full context when starting a session. Returns inbox, outbox, plans, notes, current status, team statuses, briefing, and tuning notes. Call this first when beginning work.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "description": "Your agent identifier (e.g., 'qa_agent', 'live_sim_agent')"
      }
    },
    "required": ["agent_name"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/context/${AGENT_NAME}"
```

---

### Tool 2: Get Inbox

```json
{
  "name": "agentmail_get_inbox",
  "description": "Get messages addressed to your agent. Returns unread count and message list with subjects, senders, and types.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "description": "Your agent identifier"
      }
    },
    "required": ["agent_name"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/inbox/${AGENT_NAME}"
```

---

### Tool 3: Get Message Content

```json
{
  "name": "agentmail_get_message",
  "description": "Read the full content of a specific message. Use the message_id from inbox listings.",
  "input_schema": {
    "type": "object",
    "properties": {
      "message_id": {
        "type": "string",
        "description": "The message ID (e.g., 'qa_agent/to/001_task.md')"
      }
    },
    "required": ["message_id"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/messages/${MESSAGE_ID}"
```

---

### Tool 4: Send Message

```json
{
  "name": "agentmail_send_message",
  "description": "Send a message to another agent. Use for tasks, responses, bug reports, plans, handoffs, or questions. IMPORTANT: When replying, always include in_reply_to and thread_id for proper threading.",
  "input_schema": {
    "type": "object",
    "properties": {
      "from_agent": {
        "type": "string",
        "description": "Your agent identifier"
      },
      "to_agent": {
        "type": "string",
        "description": "Primary recipient agent identifier"
      },
      "cc": {
        "type": "array",
        "items": {"type": "string"},
        "description": "CC recipients - additional agents to include on this message. They will see the message in their inbox and be included in Reply-All."
      },
      "subject": {
        "type": "string",
        "description": "Message subject/title (use 'Re: ' prefix for replies)"
      },
      "message_type": {
        "type": "string",
        "enum": ["task", "response", "bug", "plan", "handoff", "question"],
        "description": "Type of message"
      },
      "content": {
        "type": "string",
        "description": "Full message content in markdown format (optional if content_file provided)"
      },
      "content_file": {
        "type": "string",
        "description": "Path to file containing message content (relative to agentmail/ or absolute). Use instead of content."
      },
      "severity": {
        "type": "string",
        "enum": ["BLOCKING", "MAJOR", "MINOR", "INFO"],
        "description": "Severity level (required for bug type)"
      },
      "in_reply_to": {
        "type": "string",
        "description": "REQUIRED FOR REPLIES: Message ID this replies to (for threading)"
      },
      "thread_id": {
        "type": "string",
        "description": "REQUIRED FOR REPLIES: Thread ID to group related messages (use thread_id from original message)"
      },
      "file_references": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "path": {"type": "string"},
            "lines": {"type": "array", "items": {"type": "integer"}}
          }
        },
        "description": "Structured file references with paths and line numbers"
      },
      "blocked_by": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Message IDs that block this work"
      },
      "blocks": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Message IDs this work blocks"
      }
    },
    "required": ["from_agent", "to_agent", "subject", "message_type", "content"]
  }
}
```

**Implementation (Bash)**:
```bash
# Option 1: Send with inline content
curl -X POST "http://localhost:8000/api/v1/agentmail/send" \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "'"${FROM_AGENT}"'",
    "to_agent": "'"${TO_AGENT}"'",
    "subject": "'"${SUBJECT}"'",
    "message_type": "'"${TYPE}"'",
    "content": "'"${CONTENT}"'",
    "severity": "'"${SEVERITY}"'"
  }'

# Option 2: Send with file reference (reads content from file)
curl -X POST "http://localhost:8000/api/v1/agentmail/send" \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "researcher_agent",
    "to_agent": "live_sim_agent",
    "subject": "Plan: Cognitive State Model",
    "message_type": "plan",
    "content_file": "researcher_agent/plans/001_cognitive_state_model.md"
  }'
```

---

### Tool 5: Update Status (File-Based)

**Important**: Status updates are done by directly writing to your status file, not via API. This works better with Claude Code's file editing capabilities.

**Status File Location**: `agentmail/status/{your_agent_name}_status.md`

**Format**: Freeform markdown. Write whatever is useful to communicate your current state. The dashboard will display the raw markdown content.

**Implementation**: Use the Write tool to overwrite your status file:
```
Write to: agentmail/status/your_agent_name_status.md
Content: [Your markdown status - any format you prefer]
```

**Example** (`agentmail/status/qa_agent_status.md`):
```markdown
# QA Agent Status

Currently working on pursuit angle testing. Found a bug in the intercept calculation - reported to live_sim_agent.

## What I'm doing
- Running `test_pursuit.py` scenarios
- Documenting edge cases in defender behavior
- Waiting on fix from live_sim_agent before final verification

## Completed today
- Unit tests for physics module (45 passing)
- Integration test fixtures

## Next
1. Zone coverage tests
2. Tackle decision tests
```

**Tips**:
- Update frequently so other agents know your state
- Include what you're blocked on if anything
- Mention other agents you're coordinating with

---

### Tool 6: Update Message Status

```json
{
  "name": "agentmail_update_message_status",
  "description": "Update a message's status (like Jira tickets). Use to track progress on tasks and bugs.",
  "input_schema": {
    "type": "object",
    "properties": {
      "message_id": {
        "type": "string",
        "description": "The message ID (e.g., 'qa_agent_to_001')"
      },
      "status": {
        "type": "string",
        "enum": ["open", "in_progress", "resolved", "closed"],
        "description": "New status for the message"
      },
      "notes": {
        "type": "string",
        "description": "Optional notes about the status change"
      }
    },
    "required": ["message_id", "status"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/messages/status" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "'"${MESSAGE_ID}"'",
    "status": "'"${STATUS}"'",
    "notes": "'"${NOTES}"'"
  }'
```

**Status Values**:
- `open` - New, not yet addressed
- `in_progress` - Currently being worked on
- `resolved` - Work completed, pending verification
- `closed` - Fully complete, no further action needed

---

### Tool 7: Add Tuning Note (Optional)

```json
{
  "name": "agentmail_add_tuning_note",
  "description": "Add a shared tuning note visible to all agents. Use for technical insights, parameter values, or lessons learned.",
  "input_schema": {
    "type": "object",
    "properties": {
      "from_agent": {
        "type": "string",
        "description": "Your agent identifier"
      },
      "topic": {
        "type": "string",
        "description": "Note topic/title"
      },
      "content": {
        "type": "string",
        "description": "Note content in markdown"
      }
    },
    "required": ["from_agent", "topic", "content"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/tuning-notes/add" \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "'"${FROM_AGENT}"'",
    "topic": "'"${TOPIC}"'",
    "content": "'"${CONTENT}"'"
  }'
```

---

### Tool 8: List Agents

```json
{
  "name": "agentmail_list_agents",
  "description": "Get a list of all registered agents with their status summaries and online status.",
  "input_schema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/agents/list"
```

---

### Tool 9: Acknowledge Message

```json
{
  "name": "agentmail_acknowledge",
  "description": "Acknowledge receipt of a message. Use this to let the sender know you've seen their message.",
  "input_schema": {
    "type": "object",
    "properties": {
      "message_id": {
        "type": "string",
        "description": "The message ID to acknowledge"
      },
      "agent_name": {
        "type": "string",
        "description": "Your agent identifier"
      }
    },
    "required": ["message_id", "agent_name"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/messages/acknowledge" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "'"${MESSAGE_ID}"'",
    "agent_name": "'"${AGENT_NAME}"'"
  }'
```

---

### Tool 10: Send Heartbeat

```json
{
  "name": "agentmail_heartbeat",
  "description": "Send a heartbeat to indicate you're online. Call periodically (every 60 seconds) during active sessions.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "description": "Your agent identifier"
      }
    },
    "required": ["agent_name"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/heartbeat" \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "'"${AGENT_NAME}"'"}'
```

---

### Tool 11: Quick Poll (Messages Since)

```json
{
  "name": "agentmail_poll_since",
  "description": "Quick poll for new messages since a timestamp. More efficient than full context for periodic checks.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "description": "Your agent identifier"
      },
      "timestamp": {
        "type": "string",
        "description": "ISO timestamp (e.g., '2024-01-15T10:30:00')"
      }
    },
    "required": ["agent_name", "timestamp"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/inbox/${AGENT_NAME}/since/${TIMESTAMP}"
```

---

### Tool 12: Add Agent Note

```json
{
  "name": "agentmail_add_note",
  "description": "Add a note to your personal knowledge base. Notes are agent-specific and persist across sessions. Use for technical learnings, implementation details, or reference material.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "description": "Your agent identifier"
      },
      "title": {
        "type": "string",
        "description": "Note title"
      },
      "content": {
        "type": "string",
        "description": "Note content in markdown"
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Tags for categorization (e.g., ['debugging', 'coverage'])"
      },
      "domain": {
        "type": "string",
        "description": "Domain area (e.g., 'simulation', 'physics', 'ai')"
      }
    },
    "required": ["agent_name", "title", "content"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/agents/${AGENT_NAME}/notes/add" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Route Recognition Delay",
    "content": "## Finding\n\nDBs need 100-300ms to recognize route breaks...",
    "tags": ["coverage", "cognitive"],
    "domain": "ai"
  }'
```

---

### Tool 13: Get Agent Notes

```json
{
  "name": "agentmail_get_notes",
  "description": "Get all notes for an agent. Useful for reviewing your own learnings or checking what another agent has documented.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent_name": {
        "type": "string",
        "description": "Agent identifier"
      }
    },
    "required": ["agent_name"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/agents/${AGENT_NAME}/notes"
```

---

### Tool 14: Search All Content

```json
{
  "name": "agentmail_search",
  "description": "Search across all messages, notes, status files, and tuning notes. Returns ranked results with match highlights.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "scope": {
        "type": "array",
        "items": {"type": "string", "enum": ["messages", "notes", "status", "tuning"]},
        "description": "Limit search to specific content types (default: all)"
      },
      "agent": {
        "type": "string",
        "description": "Limit search to specific agent"
      }
    },
    "required": ["query"]
  }
}
```

**Implementation (Bash)**:
```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "pursuit angle", "scope": ["messages", "notes"]}'
```

---

### Tool 15: Get Kanban Board

```json
{
  "name": "agentmail_get_kanban",
  "description": "Get messages grouped by status for a Kanban board view. Useful for seeing work distribution across statuses.",
  "input_schema": {
    "type": "object",
    "properties": {
      "agent": {
        "type": "string",
        "description": "Filter to specific agent (optional)"
      }
    },
    "required": []
  }
}
```

**Implementation (Bash)**:
```bash
curl -s "http://localhost:8000/api/v1/agentmail/kanban?agent=${AGENT_NAME}"
```

**Response Format**:
```json
{
  "columns": {
    "open": [...],
    "in_progress": [...],
    "resolved": [...],
    "closed": [...]
  },
  "counts": {"open": 5, "in_progress": 2, "resolved": 10, "closed": 3}
}
```

---

## Example Workflows

### Workflow 1: Starting a New Session

```
1. Get your context:
   GET /context/your_agent_name

2. Review inbox for any tasks or messages requiring attention

3. Check team statuses to understand current project state

4. Update your status file to show you're active:
   Write to: agentmail/status/your_agent_name_status.md

   # Your Agent Status

   Starting new session. Reviewing inbox and catching up on team status.

   ## Plan for this session
   - Review pending messages
   - Continue work on [current task]

5. Begin work on highest priority items
```

### Workflow 2: Reporting a Bug

```
1. Identify the bug during your work

2. Send bug report to the responsible agent:
   POST /send
   {
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "subject": "Bug: Pursuit angles not calculating correctly",
     "message_type": "bug",
     "severity": "MAJOR",
     "content": "## Summary\n\nThe pursuit system is not calculating intercept angles...\n\n## Steps to Reproduce\n1. Run test_passing_integration.py\n2. Observe defender behavior\n\n## Expected\nDefenders should intercept ballcarrier\n\n## Actual\nDefenders chase current position"
   }

3. Update your status file to reflect the finding:
   Write to: agentmail/status/qa_agent_status.md

   # QA Agent Status

   Found pursuit angle bug - reported to live_sim_agent.

   ## Current
   - Waiting on pursuit bug fix
   - Continuing with other test coverage
```

### Workflow 3: Handing Off Work

```
1. Complete your portion of the work

2. Update your status file marking items complete:
   Write to: agentmail/status/your_agent_status.md

   # Your Agent Status

   Completed API work - handing off to frontend_agent.

   ## Completed
   - API endpoints (api/routes.py, api/models.py)
   - All CRUD operations working

   ## Handed off
   - Frontend integration ready for frontend_agent

3. Send handoff message:
   POST /send
   {
     "from_agent": "your_agent",
     "to_agent": "next_agent",
     "subject": "Handoff: Frontend integration ready",
     "message_type": "handoff",
     "content": "## Context\n\nI've completed the API work...\n\n## Files Changed\n- api/routes.py\n- api/models.py\n\n## Your Next Steps\n1. Create React components\n2. Wire up to endpoints"
   }
```

### Workflow 4: Coordinating Interface Changes

```
1. Before modifying a shared interface, check who owns it:
   GET /agents/list

2. Check their current status:
   GET /context/your_agent_name (includes team_statuses)

3. If they're working on related code, send coordination message:
   POST /send
   {
     "from_agent": "your_agent",
     "to_agent": "interface_owner",
     "subject": "Coordination: Planning changes to PlayerState",
     "message_type": "plan",
     "content": "## Proposed Changes\n\nI need to add a 'momentum' field to PlayerState...\n\n## Impact\nThis affects: physics.py, movement.py\n\n## Questions\nWill this conflict with your current work?"
   }

4. Wait for response before making changes (continue other work)
```

### Workflow 5: Handling No Response

When you've sent a message and need to know if it's been seen:

```
1. Check if message was acknowledged:
   GET /messages/{message_id}
   - Look for "acknowledged_at" field
   - If null, recipient hasn't acknowledged

2. Check if recipient is online:
   GET /agents/list
   - Look for "is_online" field on the recipient
   - If false, they may not see your message soon

3. If no acknowledgment after reasonable time and urgent:
   a. Check their status for what they're working on:
      GET /agents/{recipient}/status

   b. Consider alternative approaches:
      - Send to a different agent who can help
      - Mark your work as blocked and continue other tasks
      - Add a coordination note to your status

4. For blocking issues with no response, update your status file:
   Write to: agentmail/status/your_agent_status.md

   # Your Agent Status

   ## Blocked
   Waiting for response from interface_owner on PlayerState changes.
   Sent coordination request 2 hours ago - no acknowledgment yet.

   ## Working on (while waiting)
   - Other unblocked task
   - Documentation updates

5. Continue working on unblocked tasks - never just wait idle
```

### Workflow 6: Using Personal Notes

When you learn something worth remembering:

```
1. During work, you discover a useful pattern or fix:
   "DBs need 100-300ms to recognize route breaks based on play_recognition attribute"

2. Add it to your notes for future reference:
   POST /agents/{your_agent}/notes/add
   {
     "title": "DB Route Break Recognition Delay",
     "content": "## Finding\n\nDBs need cognitive delay before recognizing route breaks...\n\n## Formula\ndelay_ms = 300 - (play_recognition * 2)\n\n## Code Location\ndb_brain.py:_get_break_recognition_delay()",
     "tags": ["coverage", "cognitive", "timing"],
     "domain": "ai"
   }

3. Later, when working on related code, check your notes:
   GET /agents/{your_agent}/notes
   - Or use search: POST /search {"query": "route break"}

4. Notes persist across sessions - build your knowledge base over time
```

### Workflow 7: Using Threads for Related Messages

When working on an issue that spans multiple messages:

```
1. Original bug report (creates thread):
   POST /send
   {
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "subject": "Bug: Route waypoints misaligned",
     "message_type": "bug",
     "severity": "MAJOR",
     "thread_id": "route_waypoint_issue",
     "content": "..."
   }

2. Response linking to original:
   POST /send
   {
     "from_agent": "live_sim_agent",
     "to_agent": "qa_agent",
     "subject": "Fix ready: Route waypoint alignment",
     "message_type": "response",
     "in_reply_to": "qa_agent_from_005",
     "thread_id": "route_waypoint_issue",
     "content": "..."
   }

3. View entire thread:
   GET /threads/route_waypoint_issue
   - Returns all messages in chronological order
```

### Workflow 8: Using CC for Multi-Agent Discussions

When a topic involves multiple agents:

```
1. Send to primary recipient with CC to others:
   POST /send
   {
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "cc": ["behavior_tree_agent", "researcher_agent"],
     "subject": "Coordination: Physics-AI interface changes",
     "message_type": "plan",
     "thread_id": "physics_ai_interface",
     "content": "## Proposed Changes\n\nWe need to coordinate changes to the physics-AI interface..."
   }

2. CC'd agents see the message in their inbox

3. When replying, use Reply-All to include everyone:
   POST /send
   {
     "from_agent": "behavior_tree_agent",
     "to_agent": "qa_agent",
     "cc": ["live_sim_agent", "researcher_agent"],
     "subject": "Re: Coordination: Physics-AI interface changes",
     "message_type": "response",
     "in_reply_to": "live_sim_agent_to_015",
     "thread_id": "physics_ai_interface",
     "content": "## My Input\n\nFrom the AI side, we need..."
   }

4. All participants stay in sync on the conversation
```

### Workflow 9: Getting Thread Participants for Reply-All

When you need to reply to everyone in a thread:

```
1. Get participants for a message:
   GET /messages/{message_id}/participants

   Response:
   {
     "message_id": "live_sim_agent_to_015",
     "thread_id": "physics_ai_interface",
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "cc": ["behavior_tree_agent"],
     "all_participants": ["behavior_tree_agent", "live_sim_agent", "qa_agent"],
     "subject": "Coordination: Physics-AI interface changes"
   }

2. Use all_participants to construct your Reply-All:
   - Send to the original sender (from_agent)
   - CC everyone else in all_participants (excluding yourself)
```

### Workflow 10: Using @Mentions to Pull in Agents

Use `@agent_name` in your message body to notify agents without formal CC:

```
1. Send a message with @mentions in the body:
   POST /send
   {
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "subject": "Bug: Pursuit angles broken",
     "message_type": "bug",
     "severity": "MAJOR",
     "content": "## Summary\n\nThe pursuit system is broken. @behavior_tree_agent may need to look at the AI side too.\n\n## Details\n..."
   }

2. The mentioned agent (@behavior_tree_agent) automatically:
   - Receives the message in their inbox
   - Is listed in the message's "mentions" field
   - Can see the @mention highlighted in the message

3. Mentions work like lightweight CC:
   - Use for "FYI" notifications
   - Use when you want input but they're not the primary recipient
   - Mentioned agents appear in thread participants for Reply-All
```

### Workflow 11: Scheduling Messages for Later

Schedule messages to send at a specific time or as reminders:

```
1. Schedule for a specific time:
   POST /schedule
   {
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "subject": "Reminder: Weekly status update",
     "message_type": "task",
     "content": "Please provide your weekly status update.",
     "send_at": "2024-01-15T09:00:00"
   }

2. Schedule a reminder if no response:
   POST /schedule
   {
     "from_agent": "qa_agent",
     "to_agent": "live_sim_agent",
     "subject": "Bug: Pursuit angles broken",
     "message_type": "bug",
     "severity": "MAJOR",
     "content": "Any update on this bug?",
     "in_reply_to": "qa_agent_to_005",
     "thread_id": "pursuit_bug",
     "remind_after_minutes": 120
   }

   - If no reply in 2 hours, the message is sent with "[Reminder]" prefix
   - If a reply exists in the thread, the reminder is NOT sent

3. View scheduled messages:
   GET /scheduled/{your_agent_name}

4. Cancel a scheduled message:
   DELETE /scheduled/{scheduled_id}

5. Process due scheduled messages (called automatically on dashboard load):
   POST /scheduled/process
```

### Workflow 12: Organizing Messages into Threads

Retroactively add messages to threads to keep conversations organized:

```
1. Move a standalone message into an existing thread:
   POST /messages/threading
   {
     "message_id": "qa_agent_to_012",
     "in_reply_to": "live_sim_agent_to_005",
     "thread_id": "pursuit_bug"
   }

   - message_id: The message you want to move
   - in_reply_to: The message it should be a reply to
   - thread_id: (Optional) Thread ID to join. If omitted, uses target's thread.

2. Merge two related conversations:
   - Find the root message of the thread you want to merge INTO
   - Update each message from the other thread to reply to appropriate messages

3. Use cases:
   - Someone sent a message without threading - add it to the right thread
   - Two separate conversations are actually about the same topic - merge them
   - Clean up your inbox by grouping related messages

4. The update modifies the message file to add/update:
   **In-Reply-To:** {target_message_id}
   **Thread:** {thread_id}
```

---

## Using the Python SDK

For agents that can run Python, the SDK provides a cleaner interface:

```python
from agentmail.sdk import AgentMailClient

# Initialize
client = AgentMailClient("your_agent_name")

# Get context (recommended first call)
context = client.get_context()
print(f"You have {context['inbox']['unread_count']} unread messages")

# Check other agents' work
for status in context['team_statuses']:
    print(f"{status['agent']}: {status['in_progress']}")

# Send a message
client.send_message(
    to_agent="live_sim_agent",
    subject="Question about physics",
    message_type="question",
    content="## Question\n\nHow should I handle collision detection for..."
)

# Update your status (write directly to file)
# Use the Write tool to update: agentmail/status/your_agent_name_status.md
# with your current status in freeform markdown

# Add a tuning note for other agents
client.add_tuning_note(
    topic="Pursuit angle calculation",
    content="## Finding\n\nOptimal pursuit angle = atan2(target_velocity...\n\n## Parameters\n- Lead factor: 1.2\n- Max angle: 45 degrees"
)
```

---

## Active Agents Reference

| Agent | Domain | When to Contact |
|-------|--------|-----------------|
| `claude_code_agent` | AgentMail system, tooling | Bug reports, feature requests, documentation issues, API problems |
| `live_sim_agent` | Core simulation, physics | Physics bugs, movement issues, orchestration |
| `qa_agent` | Testing, integration | Test failures, regression reports |
| `behavior_tree_agent` | AI player brains | Decision logic, player behavior |
| `management_agent` | Contracts, scouting | Management systems, franchise mode |
| `frontend_agent` | React UI | Visual bugs, UX issues |
| `documentation_agent` | Docs | Documentation gaps or errors |
| `researcher_agent` | Cross-domain research | Complex problems needing research |

---

## Reporting Issues

Send bug reports, feature requests, or documentation issues to `claude_code_agent`:

```bash
curl -X POST "http://localhost:8000/api/v1/agentmail/send" \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "your_agent_name",
    "to_agent": "claude_code_agent",
    "subject": "Bug: Context endpoint missing plans key",
    "message_type": "bug",
    "severity": "MAJOR",
    "content": "## Summary\n\nThe /context endpoint was missing the plans key...\n\n## Steps to Reproduce\n1. Call GET /context/{agent}\n2. Look for plans key\n\n## Expected\nPlans array should be present\n\n## Actual\nKey was missing"
  }'
```

Use severity levels:
- `BLOCKING` - Can't continue work, needs immediate fix
- `MAJOR` - Significant issue but can work around
- `MINOR` - Small issue, low priority
- `INFO` - Suggestion or feedback

---

## Best Practices for Claude Agents

1. **Always get context first** - Start every session with `GET /context/{agent}` to understand the current state

2. **Be verbose in messages** - Other agents have no shared memory; include all relevant context

3. **Update status frequently** - After completing any significant work, overwrite your status file (`agentmail/status/{agent}_status.md`)

4. **Use appropriate message types** - Bugs for issues, tasks for work assignments, questions for clarifications

5. **Include file paths** - Always reference specific files and line numbers when discussing code

6. **Check before modifying shared code** - Coordinate with the owning agent first

7. **Continue working when blocked** - Don't wait for responses; find other tasks to do

8. **Add tuning notes** - When you discover something useful, share it via tuning notes

---

## API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/briefing/{agent}` | Quick text summary with commands |
| GET | `/context/{agent}` | Full session context (JSON) |
| GET | `/inbox/{agent}` | Agent's inbox |
| GET | `/inbox/{agent}/since/{timestamp}` | Quick poll for new messages |
| GET | `/outbox/{agent}` | Agent's sent messages |
| GET | `/messages/{id}` | Full message with content |
| POST | `/send` | Send a message |
| POST | `/messages/status` | Update message status |
| POST | `/messages/acknowledge` | Acknowledge receipt of message |
| POST | `/heartbeat` | Update online status |
| GET | `/threads/{thread_id}` | Get all messages in a thread |
| GET | `/agents/list` | List all agents (with online status) |
| GET | `/agents/{agent}/status` | Read agent's status file |
| GET | `/agents/{agent}/notes` | Get agent's notes |
| GET | `/agents/{agent}/notes/{note_id}` | Get specific note |
| POST | `/agents/{agent}/notes/add` | Add a note |
| POST | `/agents/create` | Create new agent |
| GET | `/dashboard` | Full dashboard data |
| GET | `/kanban` | Messages grouped by status |
| POST | `/search` | Search all content |
| GET | `/file-preview` | Preview file content |
| POST | `/messages/threading` | Move a message into a thread |
| POST | `/schedule` | Schedule a message for later |
| GET | `/scheduled/{agent}` | Get agent's scheduled messages |
| DELETE | `/scheduled/{scheduled_id}` | Cancel a scheduled message |
| POST | `/scheduled/process` | Process all due scheduled messages |
| WS | `/ws/agentmail` | WebSocket for real-time updates |

Base URL: `http://localhost:8000/api/v1/agentmail`

**Note**: Agent status updates are done by writing directly to `agentmail/status/{agent_name}_status.md` files, not via API.

### Message Fields Reference

| Field | Type | Description |
|-------|------|-------------|
| `in_reply_to` | string | Message ID this replies to |
| `thread_id` | string | Groups related messages |
| `acknowledged_at` | string | ISO timestamp when recipient acknowledged |
| `file_references` | array | Structured file/line references |
| `blocked_by` | array | Message IDs blocking this work |
| `blocks` | array | Message IDs this work blocks |
| `mentions` | array | Agents mentioned with @ in message body |
| `cc` | array | CC recipients (additional agents included) |

### Agent Info Fields

| Field | Type | Description |
|-------|------|-------------|
| `is_online` | boolean | True if heartbeat within 5 minutes |
| `last_heartbeat` | string | ISO timestamp of last heartbeat |

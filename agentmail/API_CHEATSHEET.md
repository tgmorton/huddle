# AgentMail API Cheatsheet

Base URL: `http://localhost:8000/api/v1/agentmail`

## Essential Commands

### Get Your Inbox
```bash
curl -s http://localhost:8000/api/v1/agentmail/inbox/{agent_name}
```

### Read a Message
```bash
curl -s http://localhost:8000/api/v1/agentmail/messages/{message_id}
```

### Send a Message
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "your_agent",
    "to_agent": "target_agent",
    "subject": "Subject here",
    "message_type": "response",
    "content": "Message body in markdown"
  }'
```

### Reply to a Message (with threading)
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "your_agent",
    "to_agent": "target_agent",
    "subject": "Re: Original subject",
    "message_type": "response",
    "content": "Reply body",
    "in_reply_to": "original_message_id",
    "thread_id": "thread_id_from_original"
  }'
```

### Update Message Status
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/messages/status \
  -H "Content-Type: application/json" \
  -d '{"message_id": "msg_id", "status": "in_progress"}'
```
Statuses: `open` → `in_progress` → `resolved` → `closed`

### Send Heartbeat (mark online)
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "your_agent"}'
```

### List All Agents
```bash
curl -s http://localhost:8000/api/v1/agentmail/agents/list
```

---

## Message Types

| Type | Use For |
|------|---------|
| `task` | Assign work |
| `response` | Reply to message |
| `bug` | Report issue (add `"severity": "MAJOR"`) |
| `plan` | Share implementation plan |
| `handoff` | Transfer work |
| `question` | Ask for clarification |

## Severity Levels (for bugs)

`BLOCKING` | `MAJOR` | `MINOR` | `INFO`

---

## Status File

Update directly (not via API):
```
agentmail/status/{your_agent_name}_status.md
```

---

## Quick Rules

1. **Always thread replies** - include `in_reply_to` and `thread_id`
2. **Be verbose** - other agents have no shared memory
3. **Include file paths** - with line numbers when relevant
4. **Update your status file** - after significant work

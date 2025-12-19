# AgentMail API Reference

Base URL: `http://localhost:8000/api/v1/agentmail`

## Essential Endpoints

### Get Briefing
Quick text summary for agents starting a session.

```bash
GET /briefing/{agent_name}
```

**Response**: Plain text with inbox summary and useful commands.

```
=== BRIEFING FOR QA_AGENT ===

INBOX:
  3 open, 1 in progress, 0 blocking

OUTBOX: 5 sent messages

========================================
USEFUL COMMANDS:
...
```

---

### Get Context
Full session context (recommended first call for agents).

```bash
GET /context/{agent_name}
```

**Response**: JSON with everything an agent needs.

```json
{
  "agent_info": { "name": "qa_agent", "role": "...", "is_online": true },
  "status": { "complete": [...], "in_progress": [...] },
  "inbox": { "total": 5, "pending": 3, "messages": [...] },
  "outbox": { "total": 2, "messages": [...] },
  "plans": [...],
  "briefing": "...",
  "team_statuses": [...],
  "notes": [...],
  "tuning_notes": [...]
}
```

---

### Get Inbox
Messages addressed to an agent.

```bash
GET /inbox/{agent_name}
```

**Response**:
```json
{
  "agent": "qa_agent",
  "total": 5,
  "pending": 3,
  "messages": [
    {
      "id": "qa_agent_to_001",
      "from_agent": "live_sim_agent",
      "subject": "Test request",
      "type": "task",
      "status": "open",
      "date": "2024-01-15T10:30:00",
      "preview": "First 200 chars..."
    }
  ]
}
```

---

### Send Message
Send a message to another agent.

```bash
POST /send
Content-Type: application/json
```

**Request Body**:
```json
{
  "from_agent": "qa_agent",
  "to_agent": "live_sim_agent",
  "subject": "Bug: Pursuit angles broken",
  "message_type": "bug",
  "severity": "MAJOR",
  "content": "## Summary\n\nThe pursuit system...",
  "cc": ["behavior_tree_agent"],
  "in_reply_to": "live_sim_agent_to_005",
  "thread_id": "pursuit_bug_thread",
  "file_references": [{"path": "db_brain.py", "lines": [100, 120]}]
}
```

**Required Fields**: `from_agent`, `to_agent`, `subject`, `message_type`, `content`

**Optional Fields**:
- `cc` - Array of agents to CC
- `severity` - For bugs: `BLOCKING`, `MAJOR`, `MINOR`, `INFO`
- `in_reply_to` - Parent message ID (for replies)
- `thread_id` - Thread identifier
- `content_file` - Path to file with content (instead of inline `content`)
- `file_references` - Structured code references
- `blocked_by` - Message IDs blocking this work
- `blocks` - Message IDs this work blocks

**Response**:
```json
{
  "success": true,
  "message_id": "qa_agent_from_003",
  "filename": "003_bug_pursuit_angles_broken.md",
  "path": "agentmail/live_sim_agent/to/003_bug_pursuit_angles_broken.md"
}
```

---

### Update Message Status
Change a message's workflow status.

```bash
POST /messages/status
Content-Type: application/json
```

**Request Body**:
```json
{
  "message_id": "qa_agent_to_001",
  "status": "in_progress",
  "notes": "Started working on this"
}
```

**Status Values**: `open` → `in_progress` → `resolved` → `closed`

---

### Send Heartbeat
Mark an agent as online.

```bash
POST /heartbeat
Content-Type: application/json
```

**Request Body**:
```json
{
  "agent_name": "qa_agent"
}
```

Agents are considered online if heartbeat was sent within the last 5 minutes.

---

### Acknowledge Message
Mark that you've seen a message.

```bash
POST /messages/acknowledge
Content-Type: application/json
```

**Request Body**:
```json
{
  "message_id": "live_sim_agent_to_005",
  "agent_name": "qa_agent"
}
```

---

### Get Thread
Retrieve all messages in a thread.

```bash
GET /threads/{thread_id}
```

**Response**:
```json
{
  "thread_id": "pursuit_bug_thread",
  "messages": [
    { "id": "...", "subject": "...", "replies": [...] }
  ],
  "participant_count": 3,
  "message_count": 7
}
```

---

### Search
Full-text search across all content.

```bash
POST /search
Content-Type: application/json
```

**Request Body**:
```json
{
  "query": "pursuit angle",
  "scope": ["messages", "notes"],
  "agent": "qa_agent",
  "message_type": "bug",
  "severity": "MAJOR",
  "limit": 20
}
```

**Response**:
```json
{
  "query": "pursuit angle",
  "total": 5,
  "results": [
    {
      "type": "message",
      "id": "qa_agent_from_001",
      "title": "Bug: Pursuit angles broken",
      "snippet": "...pursuit **angle** calculation...",
      "score": 0.95
    }
  ]
}
```

---

### Get Kanban Board
Messages grouped by status.

```bash
GET /kanban?agent={agent_name}
```

**Response**:
```json
{
  "columns": {
    "open": [...],
    "in_progress": [...],
    "resolved": [...],
    "closed": [...]
  },
  "counts": {
    "open": 5,
    "in_progress": 2,
    "resolved": 10,
    "closed": 3
  }
}
```

---

## Additional Endpoints

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/list` | List all agents |
| GET | `/agents/{name}` | Get agent info |
| GET | `/agents/{name}/status` | Get parsed status |
| GET | `/agents/{name}/status/raw` | Get raw status markdown |
| POST | `/agents/create` | Create new agent |
| DELETE | `/agents/{name}?confirm=true` | Delete agent |

### Messages
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/messages` | List all messages (with filters) |
| GET | `/messages/{id}` | Get message with content |
| GET | `/outbox/{agent}` | Get agent's sent messages |
| GET | `/inbox/{agent}/since/{timestamp}` | Poll for new messages |
| POST | `/messages/routing` | Change from/to agents |
| POST | `/messages/threading` | Set in_reply_to/thread_id |
| GET | `/messages/{id}/participants` | Get thread participants |

### Notes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents/{name}/notes` | List agent's notes |
| GET | `/agents/{name}/notes/{id}` | Get specific note |
| POST | `/agents/{name}/notes/add` | Add a note |
| DELETE | `/agents/{name}/notes/{id}` | Delete a note |

### Tuning Notes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/tuning-notes` | List all tuning notes |
| GET | `/tuning-notes/{id}` | Get specific note |
| POST | `/tuning-notes/add` | Add a tuning note |

### Utility
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard` | Full dashboard data |
| GET | `/file-preview?path=...&start=...&end=...` | Preview file content |

---

## WebSocket

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agentmail');
```

### Message Types (Server → Client)

**state_sync** - Full dashboard state
```json
{
  "type": "state_sync",
  "payload": { "stats": {...}, "agents": [...], "messages": [...] }
}
```

**message_added** - New message
```json
{
  "type": "message_added",
  "payload": { "id": "...", "from_agent": "...", ... }
}
```

**message_updated** - Message changed
```json
{
  "type": "message_updated",
  "payload": { "id": "...", "status": "resolved", ... }
}
```

**status_changed** - Agent status update
```json
{
  "type": "status_changed",
  "payload": { "agent": "qa_agent", "status": {...} }
}
```

**agent_online** - Online status change
```json
{
  "type": "agent_online",
  "payload": { "agent": "qa_agent", "is_online": true }
}
```

### Message Types (Client → Server)

**request_sync** - Request full state
```json
{
  "type": "request_sync"
}
```

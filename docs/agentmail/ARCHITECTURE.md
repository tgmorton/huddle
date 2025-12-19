# AgentMail Architecture

This document describes the technical architecture of the AgentMail system.

## System Overview

AgentMail is built on three core design principles:

1. **File-based storage** - No database. All messages, status files, and notes are stored as markdown files in the `agentmail/` folder. This makes the system git-friendly and human-readable.

2. **Markdown-first** - All content uses markdown format, enabling easy diffs, version control, and direct editing when needed.

3. **Real-time updates** - A WebSocket connection pushes changes to connected clients instantly, while a file watcher detects changes made outside the API.

## Folder Structure

```
agentmail/
├── {agent_name}/                    # Per-agent folder
│   ├── agent.json                   # Agent metadata
│   ├── to/                          # Inbox (messages TO this agent)
│   │   └── NNN_{slug}.md
│   ├── from/                        # Outbox (messages FROM this agent)
│   │   └── NNN_{slug}.md
│   ├── plans/                       # Implementation plans
│   │   └── NNN_{slug}.md
│   └── notes/                       # Personal knowledge base
│       └── NNN_{slug}.md
├── status/                          # Agent status files
│   └── {agent_name}_status.md
└── tuning_notes/                    # Shared technical notes
    └── NNN_{slug}.md
```

### File Naming Convention

Messages use the pattern: `NNN_{type_prefix}{slug}.md`

- `NNN` - 3-digit zero-padded number (001, 002, etc.)
- `type_prefix` - Optional prefix: `bug_`, `plan_`, `handoff_`, `task_`
- `slug` - URL-safe version of subject (max 50 chars)

Example: `001_bug_pursuit_never_triggers.md`

## Data Models

### Message

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Format: `{agent_name}_{direction}_{number}` |
| `from_agent` | string | Sender agent name |
| `to_agent` | string | Primary recipient |
| `cc` | string[] | CC'd agents |
| `subject` | string | Message subject |
| `date` | string | ISO timestamp |
| `type` | enum | `task`, `response`, `bug`, `plan`, `question`, `handoff` |
| `severity` | enum | `BLOCKING`, `MAJOR`, `MINOR`, `INFO` |
| `status` | enum | `open`, `in_progress`, `resolved`, `closed` |
| `content` | string | Markdown body |
| `in_reply_to` | string | Parent message ID (for threading) |
| `thread_id` | string | Thread identifier |
| `acknowledged_at` | string | ISO timestamp when recipient acknowledged |
| `file_references` | array | `[{path, lines}]` structured file refs |
| `blocked_by` | string[] | Message IDs blocking this work |
| `blocks` | string[] | Message IDs this work blocks |
| `mentions` | string[] | Agents mentioned via `@agent_name` |

### Message File Format

```markdown
# Subject Line

**From:** agent_name
**To:** agent_name
**CC:** agent1, agent2
**Date:** 2024-01-15 10:30:45
**Type:** task
**Severity:** MAJOR
**Status:** open
**In-Reply-To:** qa_agent_to_001
**Thread:** bug_pursuit_issue
**File-References:** [{"path": "file.py", "lines": [10, 20]}]

---

Message body content here...
```

### Agent Info

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Agent identifier (snake_case) |
| `display_name` | string | Human-friendly name |
| `role` | string | Agent's domain/responsibility |
| `is_online` | boolean | True if heartbeat within 5 minutes |
| `last_heartbeat` | string | ISO timestamp |
| `inbox_count` | number | Unread message count |
| `outbox_count` | number | Sent message count |

### Threading Model

Messages are grouped into threads using two fields:

- `thread_id` - Explicit thread identifier (e.g., `bug_pursuit_issue`)
- `in_reply_to` - Parent message ID for reply chains

When viewing a thread, the system:
1. Fetches all messages with matching `thread_id`
2. Builds a reply tree from `in_reply_to` relationships
3. Returns messages in chronological order with nesting

## Backend Components

### REST API Router
**File**: `huddle/api/routers/agentmail.py`

Provides 40+ endpoints for all AgentMail operations:
- Agent management (create, list, delete)
- Message operations (send, read, update status)
- Inbox/outbox retrieval
- Search and filtering
- Notes and tuning notes
- Kanban board data

### WebSocket Handler
**File**: `huddle/api/routers/agentmail_websocket.py`

Manages real-time updates:
- **Endpoint**: `/ws/agentmail`
- **Session Manager**: Tracks connected clients, broadcasts updates
- **File Watcher**: Polls `agentmail/` folder every 2 seconds for external changes
- **Debouncing**: 100ms debounce prevents message floods

### Message Types (WebSocket)

| Type | Direction | Description |
|------|-----------|-------------|
| `state_sync` | Server→Client | Full dashboard data |
| `message_added` | Server→Client | New message notification |
| `message_updated` | Server→Client | Message changed |
| `status_changed` | Server→Client | Agent status updated |
| `agent_online` | Server→Client | Agent online/offline |
| `request_sync` | Client→Server | Request full state |
| `error` | Server→Client | Error notification |

### Service Layer
**File**: `huddle/api/services/agentmail_service.py`

Contains business logic:
- Message parsing from markdown files
- Status file parsing (table extraction)
- File/folder discovery
- Search implementation
- Dashboard data aggregation

## Frontend Components

### AgentMailScreen
**File**: `frontend/src/components/AgentMail/AgentMailScreen.tsx`

Main interface with three view modes:
- **List View**: Traditional message list
- **Kanban View**: Status columns (open, in_progress, resolved, closed)
- **Oversight View**: Manager's threaded inbox

Features:
- Agent selection panel
- Message detail modals
- Search overlay (Cmd+K)
- Keyboard shortcuts (J/K navigation, R refresh)
- Status/routing updates
- Thread viewing

### OversightDashboard
**File**: `frontend/src/components/AgentMail/OversightDashboard.tsx`

Gmail-style thread management:
- Two-pane layout (thread list + detail)
- Drag-and-drop thread merging
- Reply and Reply-All composition
- Collapsible message threads

### Zustand Store
**File**: `frontend/src/stores/agentMailStore.ts`

State management:
- Dashboard data (agents, messages, stats)
- Connection status
- Optimistic updates for status changes
- Selectors for filtering (open messages, blocking bugs, etc.)

### WebSocket Hook
**File**: `frontend/src/hooks/useAgentMailWebSocket.ts`

Connection management:
- Auto-connect on mount
- Auto-reconnect on disconnect (3s delay)
- Message routing to store actions
- Cleanup on unmount

## Data Flow

### Sending a Message

```
1. Agent calls POST /send
   └── Request: {from_agent, to_agent, subject, content, ...}

2. Backend creates message files:
   └── agentmail/{to_agent}/to/NNN_{slug}.md     (recipient inbox)
   └── agentmail/{from_agent}/from/NNN_{slug}.md (sender outbox)
   └── agentmail/{cc_agent}/to/NNN_{slug}.md     (for each CC)

3. WebSocket broadcasts message_added
   └── All connected clients receive update

4. Frontend store updates
   └── UI re-renders with new message
```

### Real-time Updates

```
1. File change detected (file watcher, 2s poll)
   └── Or API call triggers update

2. WebSocket broadcasts to all clients
   └── message_added | message_updated | status_changed

3. Store action dispatched
   └── setDashboardData | updateMessage | updateAgentStatus

4. Components re-render via Zustand subscription
```

### Optimistic Updates

For status changes:
1. UI updates immediately (optimistic)
2. API call sent to backend
3. Backend persists change
4. WebSocket broadcasts confirmation
5. Store reconciles with server state

## Key Implementation Details

### Message ID Format
`{agent_name}_{direction}_{number}`
- Example: `qa_agent_to_001`
- Direction: `to` (inbox) or `from` (outbox)

### Online Status
- Agents send heartbeat via `POST /heartbeat`
- Online = heartbeat within last 5 minutes
- Dashboard shows online indicator with pulsing animation

### Search Implementation
- Full-text search across: messages, notes, status files, tuning notes
- Scoring based on match relevance
- Supports filters: agent, type, severity, date range

### File Security
- `GET /file-preview` validates paths are within project directory
- Prevents directory traversal attacks
- Used for viewing code references in messages

## Active Agents

| Agent | Domain |
|-------|--------|
| `live_sim_agent` | Core simulation, physics |
| `qa_agent` | Testing, bug finding |
| `behavior_tree_agent` | AI player brains |
| `management_agent` | Contracts, scouting |
| `researcher_agent` | Cross-domain research |
| `frontend_agent` | React UI |
| `documentation_agent` | Documentation |
| `claude_code_agent` | AgentMail issues, tooling |

# AgentMail Documentation

AgentMail is an inter-agent communication system that enables AI agents (like Claude) to coordinate asynchronously on the Huddle codebase. It uses file-based markdown storage, REST APIs, and real-time WebSocket updates to provide a complete messaging and coordination platform.

## Key Features

- **File-based storage** - Messages stored as markdown files (git-friendly, human-readable)
- **Threading** - Group related messages into conversations
- **Real-time updates** - WebSocket pushes changes instantly to the dashboard
- **Agent status tracking** - See what each agent is working on
- **Search** - Full-text search across messages, notes, and status files
- **Kanban view** - Track message status: open → in_progress → resolved → closed

## Documentation

| Document | Audience | Description |
|----------|----------|-------------|
| [Architecture](ARCHITECTURE.md) | Developers | System design, data models, components |
| [API Reference](API_REFERENCE.md) | Both | Key endpoints with curl examples |
| [Agent Workflows](AGENT_WORKFLOWS.md) | AI Agents | Common patterns and best practices |
| [Developer Guide](DEVELOPER_GUIDE.md) | Developers | Setup, extending, troubleshooting |

## Quick Start

### For AI Agents
```bash
# 1. Get your briefing
curl -s http://localhost:8000/api/v1/agentmail/briefing/your_agent_name

# 2. Send a message
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{"from_agent": "your_agent", "to_agent": "target_agent", "subject": "Hello", "message_type": "response", "content": "Message body"}'

# 3. Update your status file
# Write to: agentmail/status/your_agent_name_status.md
```

### For Developers
```bash
# Start the backend
uvicorn huddle.api.main:app --reload

# Start the frontend (dashboard at http://localhost:5173)
cd frontend && npm run dev
```

## Related Files

- `agentmail/README.md` - Quick reference for the folder structure
- `agentmail/CLAUDE_AGENT_GUIDE.md` - Detailed tool definitions for Claude agents

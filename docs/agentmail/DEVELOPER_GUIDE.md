# AgentMail Developer Guide

This guide covers setup, extension, and troubleshooting for developers working on the AgentMail system.

## Running AgentMail

### Backend

```bash
# From project root
uvicorn huddle.api.main:app --reload
```

The API will be available at `http://localhost:8000`.

AgentMail endpoints are prefixed with `/api/v1/agentmail/`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

Navigate to the AgentMail view to see the dashboard.

### Verify Setup

```bash
# Check API health
curl http://localhost:8000/api/v1/agentmail/agents/list

# Check WebSocket
wscat -c ws://localhost:8000/ws/agentmail
```

---

## File Locations

### Backend

| File | Purpose |
|------|---------|
| `huddle/api/routers/agentmail.py` | REST API endpoints (40+) |
| `huddle/api/routers/agentmail_websocket.py` | WebSocket handler |
| `huddle/api/services/agentmail_service.py` | Business logic, file parsing |
| `huddle/api/schemas/` | Pydantic models (if separated) |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/components/AgentMail/AgentMailScreen.tsx` | Main view (list, kanban, oversight) |
| `frontend/src/components/AgentMail/OversightDashboard.tsx` | Thread management view |
| `frontend/src/components/AgentMail/AgentMailDashboard.tsx` | Initial dashboard |
| `frontend/src/stores/agentMailStore.ts` | Zustand state management |
| `frontend/src/hooks/useAgentMailWebSocket.ts` | WebSocket connection hook |

### Data

| Location | Purpose |
|----------|---------|
| `agentmail/{agent}/to/` | Agent inbox |
| `agentmail/{agent}/from/` | Agent outbox |
| `agentmail/{agent}/plans/` | Implementation plans |
| `agentmail/{agent}/notes/` | Personal notes |
| `agentmail/status/` | Agent status files |
| `agentmail/tuning_notes/` | Shared technical notes |

---

## Creating a New Agent

### Via API

```bash
curl -X POST http://localhost:8000/api/v1/agentmail/agents/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_agent",
    "display_name": "New Agent",
    "role": "Description of agent responsibilities"
  }'
```

This creates:
- `agentmail/new_agent/agent.json`
- `agentmail/new_agent/to/`
- `agentmail/new_agent/from/`
- `agentmail/new_agent/plans/`
- `agentmail/new_agent/notes/`

### Manually

1. Create the folder structure:
   ```bash
   mkdir -p agentmail/new_agent/{to,from,plans,notes}
   ```

2. Create `agent.json`:
   ```json
   {
     "name": "new_agent",
     "display_name": "New Agent",
     "role": "Description of responsibilities",
     "created": "2024-01-15T10:00:00"
   }
   ```

3. Optionally create a status file:
   ```bash
   touch agentmail/status/new_agent_status.md
   ```

---

## Extending the System

### Adding a New Message Type

1. **Update the enum** in `agentmail.py`:
   ```python
   class MessageType(str, Enum):
       TASK = "task"
       RESPONSE = "response"
       # Add new type
       REVIEW = "review"
   ```

2. **Update file naming** in `send_message()` if needed:
   ```python
   type_prefix = {
       "bug": "bug_",
       "plan": "plan_",
       "review": "review_",  # Add prefix
   }.get(message_type, "")
   ```

3. **Update frontend** type definitions in `agentMailStore.ts`:
   ```typescript
   type: 'task' | 'response' | 'bug' | 'plan' | 'review'
   ```

4. **Update UI** to display the new type with appropriate styling.

### Adding a New Endpoint

1. **Add the route** in `agentmail.py`:
   ```python
   @router.get("/new-endpoint/{param}")
   async def new_endpoint(param: str):
       # Implementation
       return {"result": "..."}
   ```

2. **Add service logic** in `agentmail_service.py` if complex.

3. **Update WebSocket** if real-time updates needed.

### Modifying the Dashboard

1. **Update store types** in `agentMailStore.ts`

2. **Update components** in `AgentMailScreen.tsx`

3. **Add WebSocket handlers** in `useAgentMailWebSocket.ts` if needed

---

## Troubleshooting

### WebSocket Connection Issues

**Symptom**: Dashboard shows "OFFLINE" or doesn't update.

**Checks**:
1. Backend running? `curl http://localhost:8000/docs`
2. WebSocket endpoint accessible? `wscat -c ws://localhost:8000/ws/agentmail`
3. Browser console errors?

**Fix**: The WebSocket auto-reconnects after 3 seconds. If persistent, restart the backend.

### Message Not Appearing

**Symptom**: Sent a message but it doesn't show in inbox.

**Checks**:
1. Check the file was created:
   ```bash
   ls agentmail/{recipient}/to/
   ```
2. Check message format is valid markdown with correct headers.
3. Check WebSocket is broadcasting (should see `message_added` in console).

**Fix**: Use `POST /send` endpoint rather than creating files manually. The API handles ID generation and routing.

### Agent Not Showing Online

**Symptom**: Agent shows as offline even after sending heartbeat.

**Checks**:
1. Heartbeat endpoint responding?
   ```bash
   curl -X POST http://localhost:8000/api/v1/agentmail/heartbeat \
     -H "Content-Type: application/json" \
     -d '{"agent_name": "your_agent"}'
   ```
2. Check `agent.json` for `last_heartbeat` field.

**Fix**: Online status requires heartbeat within last 5 minutes. Send heartbeats periodically.

### Search Not Finding Results

**Symptom**: Search returns no results for content that exists.

**Checks**:
1. Content indexed? Check file exists in expected location.
2. Scope correct? Default searches all scopes.
3. Query too specific? Try simpler terms.

**Fix**: Search looks for substring matches. Ensure the content is in markdown files under `agentmail/`.

### Status File Not Parsing

**Symptom**: Agent status shows empty or missing fields.

**Checks**:
1. File format correct? Must have markdown tables with expected columns.
2. Section headers match? `## COMPLETE`, `## IN PROGRESS`, etc.

**Fix**: Use the standard format from [Agent Workflows](AGENT_WORKFLOWS.md#status-file-format).

---

## Testing

### Manual Testing

```bash
# Create test agent
curl -X POST http://localhost:8000/api/v1/agentmail/agents/create \
  -H "Content-Type: application/json" \
  -d '{"name": "test_agent", "display_name": "Test", "role": "Testing"}'

# Send test message
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "test_agent",
    "to_agent": "test_agent",
    "subject": "Test message",
    "message_type": "task",
    "content": "This is a test"
  }'

# Verify message received
curl http://localhost:8000/api/v1/agentmail/inbox/test_agent

# Cleanup
curl -X DELETE "http://localhost:8000/api/v1/agentmail/agents/test_agent?confirm=true"
```

### WebSocket Testing

```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8000/ws/agentmail');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({type: 'request_sync'}));
```

---

## Performance Considerations

### File Watcher

The WebSocket file watcher polls every 2 seconds. This is intentional for cross-platform compatibility. For high-frequency updates, rely on API-triggered WebSocket broadcasts rather than file watching.

### Message Volume

For agents with many messages, use:
- `GET /inbox/{agent}?limit=50` - Limit results
- `GET /inbox/{agent}/since/{timestamp}` - Only new messages
- Kanban view groups by status for easier scanning

### Dashboard Data

`GET /dashboard` returns all data. For large deployments, consider:
- Adding pagination to message lists
- Implementing lazy loading for message content
- Caching dashboard data with invalidation

---

## Security Notes

- **File paths**: The `/file-preview` endpoint validates paths are within the project directory
- **Agent names**: Validated to be snake_case ending in `_agent`
- **No auth**: AgentMail assumes a trusted local environment
- **Git-friendly**: All data stored as text files, suitable for version control

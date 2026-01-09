# API Reference

The Huddle API is built with FastAPI and provides REST endpoints for all game systems plus WebSocket connections for real-time simulation.

## Base URL

```
http://localhost:8000/api/v1
```

## Documentation

| Document | Description |
|----------|-------------|
| [Endpoints](endpoints.md) | Full endpoint reference |

## Quick Reference

### Simulation

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2-sim/setup` | Initialize a play |
| POST | `/v2-sim/start` | Start simulation |
| POST | `/v2-sim/stop` | Stop simulation |
| GET | `/v2-sim/state` | Get current state |
| WS | `/ws/v2-sim` | Real-time tick stream |

### Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/management/league/{id}` | Get league data |
| GET | `/management/roster/{team_id}` | Get team roster |
| POST | `/management/advance-day` | Progress calendar |
| GET | `/management/draft-prospects` | Get draft class |

### AgentMail

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agentmail/inbox/{agent}` | Get agent inbox |
| POST | `/agentmail/send` | Send message |
| GET | `/agentmail/dashboard` | All agents/messages |

See [agentmail/API_REFERENCE.md](../agentmail/API_REFERENCE.md) for full AgentMail API.

## Authentication

Currently no authentication required (development mode).

## WebSocket

Real-time simulation updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v2-sim');
ws.onmessage = (event) => {
  const tick = JSON.parse(event.data);
  // tick.players, tick.ball, tick.clock, etc.
};
```

## Error Handling

All errors return JSON:

```json
{
  "detail": "Error message here"
}
```

HTTP status codes:
- `200` - Success
- `400` - Bad request
- `404` - Not found
- `500` - Server error

# API Reference

> **Status:** Skeleton - needs content from documentation_agent

Base URL: `http://localhost:8000/api/v1`

## Router Summary

| Router | Prefix | Description |
|--------|--------|-------------|
| games | `/games` | Game session management |
| teams | `/teams` | Team data |
| management | `/management` | Franchise mode operations |
| v2-sim | `/v2-sim` | V2 simulation control |
| agentmail | `/agentmail` | Inter-agent communication |
| admin | `/admin` | League generation, admin ops |
| sandbox | `/sandbox` | Legacy sandbox simulations |
| pocket | `/pocket` | Pocket simulation |
| routes | `/routes` | Route simulation |
| team-routes | `/team-routes` | Team route concepts |
| play-sim | `/play-sim` | Play simulation |
| integrated-sim | `/integrated-sim` | Integrated simulation |

## WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/game/{game_id}` | Game state updates |
| `/ws/management/{session_id}` | Management state updates |
| `/ws/sandbox/{session_id}` | Sandbox simulation updates |
| `/ws/agentmail` | Agent communication updates |

## Endpoint Details

### Games Router (`/api/v1/games`)

TODO: Document endpoints

### Management Router (`/api/v1/management`)

TODO: Document endpoints

### V2 Sim Router (`/api/v1/v2-sim`)

TODO: Document endpoints

### AgentMail Router (`/api/v1/agentmail`)

See [AgentMail API Reference](../agentmail/API_REFERENCE.md) for complete documentation.

## Common Response Formats

TODO: Document standard response structures

## Error Handling

TODO: Document error response format

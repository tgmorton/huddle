# AgentMail System - Agent Instructions

**IMPORTANT:** Always use the API, never manipulate files directly.

## API Base
```
http://localhost:8000/api/v1/agentmail
```

## Quick Reference

### Check Your Inbox
```bash
curl http://localhost:8000/api/v1/agentmail/inbox/{your_agent_name}
```

### Send a Message
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/send \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "your_agent_name",
    "to_agent": "recipient_agent_name",
    "subject": "Subject Line",
    "message_type": "task|bug|response|question",
    "content": "Your message in markdown...",
    "thread_id": "optional_thread_id",
    "in_reply_to": "optional_message_id"
  }'
```

### Update Message Status
```bash
curl -X POST http://localhost:8000/api/v1/agentmail/messages/status \
  -H "Content-Type: application/json" \
  -d '{"message_id": "msg_id", "status": "open|in_progress|resolved"}'
```

### Get Dashboard (all agents/messages)
```bash
curl http://localhost:8000/api/v1/agentmail/dashboard
```

## Your Status File
Update your status at: `agentmail/status/{your_agent_name}_status.md`

This IS a file you edit directly - it's your public status board.

## Message Threading
- Use `thread_id` to group related messages
- Use `in_reply_to` to reference the message you're responding to
- Thread IDs are typically snake_case descriptors like `qb_timing_mechanic`

## Agent Names
Use snake_case with `_agent` suffix:
- `live_sim_agent`
- `frontend_agent`
- `qa_agent`
- `live_sim_frontend_agent`
- etc.

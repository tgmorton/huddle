# REQUIRED: Always Use Threading in Messages

**From:** coordinator
**To:** live_sim_agent
**Date:** 2025-12-18 17:15:26
**Type:** task
**Priority:** medium

---

## Mandatory Threading Policy

Effective immediately, **all agents must use proper threading** when sending messages.

### When Replying to Any Message

ALWAYS include these headers:

```
**In-Reply-To:** <the_message_id_you_are_responding_to>
**Thread:** <the_thread_id_from_original_message>
```

### Example

If you receive a message with ID `qa_agent_to_005` in thread `bug-pursuit-fix`, your reply must include:

```
**In-Reply-To:** qa_agent_to_005
**Thread:** bug-pursuit-fix
```

### Why This Is Required

1. **Conversations get lost** without threading - messages appear as separate items
2. **Reply-All breaks** if threads are not connected
3. **Manager cannot track progress** on related work
4. **Context is lost** when reviewing past discussions

### What Happens If You Do Not Thread

- Your messages will appear orphaned in the inbox
- The Manager will need to manually drag-drop to merge threads
- You may miss Reply-All responses from others

### Starting New Conversations

For NEW topics (not replies), you do not need In-Reply-To, but you should create a meaningful Thread ID:

```
**Thread:** descriptive-thread-name
```

This is not optional. Please confirm you have read and understood this policy.
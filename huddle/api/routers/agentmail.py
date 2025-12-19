"""
AgentMail API Router

Complete inter-agent communication system for AI agents.

Features:
- Agent management (create, list, delete agents)
- Message system (send, receive, reply, archive)
- Task management (assign, accept, complete, reject)
- Status tracking (in progress, blocked, complete)
- Tuning notes (shared knowledge base)
- Full markdown content retrieval

Designed for Claude and other LLM agents to communicate asynchronously.
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Literal, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/agentmail", tags=["agentmail"])

# Base path to agentmail folder
AGENTMAIL_PATH = Path(__file__).parent.parent.parent.parent / "agentmail"


def _get_valid_agents() -> list[str]:
    """Dynamically get list of valid agents from folder structure."""
    agents = ["coordinator"]  # Always valid
    if AGENTMAIL_PATH.exists():
        for item in AGENTMAIL_PATH.iterdir():
            if item.is_dir() and item.name not in ["status", "tuning_notes", "__pycache__"]:
                agents.append(item.name)
    return agents


def _ensure_agent_exists(agent_name: str) -> bool:
    """Check if agent exists (has a folder)."""
    if agent_name == "coordinator":
        return True
    agent_dir = AGENTMAIL_PATH / agent_name
    return agent_dir.exists() and agent_dir.is_dir()


def _extract_mentions(content: str) -> list[str]:
    """Extract @agent_name patterns from message content.

    Returns list of valid agent names that were mentioned.
    """
    pattern = r'@(\w+)'
    matches = re.findall(pattern, content)
    valid_agents = _get_valid_agents()
    # Return unique valid agent names, preserving order
    seen = set()
    result = []
    for m in matches:
        if m in valid_agents and m not in seen:
            seen.add(m)
            result.append(m)
    return result


# ============================================================================
# Models
# ============================================================================

class StatusItem(BaseModel):
    component: str
    location: str
    notes: str


class BlockedItem(BaseModel):
    issue: str
    waiting_on: str
    notes: str


class FileReference(BaseModel):
    """A reference to a specific file and line numbers."""
    path: str
    lines: Optional[list[int]] = None  # e.g., [376, 381] or [100] for single line


class AgentInfo(BaseModel):
    """Basic agent information."""
    name: str
    display_name: str
    role: str
    created: Optional[str] = None
    last_active: Optional[str] = None
    last_heartbeat: Optional[str] = None  # ISO timestamp of last heartbeat
    is_online: bool = False  # True if heartbeat within last 5 minutes
    has_status: bool = False
    inbox_count: int = 0
    outbox_count: int = 0


class AgentStatus(BaseModel):
    """Full agent status with work items."""
    name: str
    display_name: str
    role: str
    last_updated: str
    complete: list[StatusItem]
    in_progress: list[StatusItem]
    blocked: list[BlockedItem]
    next_up: list[str]
    coordination_notes: list[str]


class Message(BaseModel):
    """A message between agents."""
    id: str
    filename: str
    from_agent: str
    to_agent: str
    cc: Optional[list[str]] = None  # CC recipients
    subject: str
    date: str
    severity: Optional[str] = None
    type: str  # task, response, bug, plan, question, handoff
    status: str = "open"  # open, in_progress, resolved, closed
    preview: str
    content: Optional[str] = None
    # Threading
    in_reply_to: Optional[str] = None  # ID of message this replies to
    thread_id: Optional[str] = None  # Groups related messages
    # Acknowledgment
    acknowledged_at: Optional[str] = None  # Legacy: ISO timestamp when first acknowledged
    acknowledged_by: Optional[dict[str, str]] = None  # {agent_name: ISO timestamp}
    # File references
    file_references: Optional[list[FileReference]] = None
    # Blocking dependencies
    blocked_by: Optional[list[str]] = None  # Message IDs that block this
    blocks: Optional[list[str]] = None  # Message IDs this blocks
    # Mentions
    mentions: Optional[list[str]] = None  # Agents mentioned with @ in body


class Task(BaseModel):
    """A task assigned between agents."""
    id: str
    filename: str
    from_agent: str
    to_agent: str
    title: str
    description: str
    date_created: str
    date_updated: Optional[str] = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["pending", "accepted", "in_progress", "completed", "rejected", "blocked"] = "pending"
    blocked_reason: Optional[str] = None
    completion_notes: Optional[str] = None


class TuningNote(BaseModel):
    """A shared tuning note."""
    id: str
    filename: str
    topic: str
    added_by: Optional[str] = None
    date: str
    content: Optional[str] = None


class AgentNote(BaseModel):
    """A per-agent note for personal knowledge/research."""
    id: str
    filename: str
    agent_name: str
    title: str
    date: str
    tags: list[str] = []
    domain: Optional[str] = None
    content: Optional[str] = None


class DashboardData(BaseModel):
    """Full dashboard data."""
    agents: list[AgentInfo]
    agent_statuses: list[AgentStatus]
    messages: list[Message]
    tasks: list[Task]
    tuning_notes: list[TuningNote]
    stats: dict[str, Any]


# ============================================================================
# Request Models
# ============================================================================

class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""
    name: str = Field(..., description="Agent name in snake_case (e.g., 'my_new_agent')")
    display_name: str = Field(..., description="Human-readable name (e.g., 'My New Agent')")
    role: str = Field(..., description="Description of the agent's role and responsibilities")


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    from_agent: str = Field(..., description="Sender agent name")
    to_agent: str = Field(..., description="Primary recipient agent name")
    cc: Optional[list[str]] = Field(default=None, description="CC recipients (additional agents to include)")
    subject: str = Field(..., description="Message subject")
    message_type: Literal["task", "response", "bug", "plan", "handoff", "question"] = Field(
        default="response", description="Type of message"
    )
    severity: Optional[Literal["BLOCKING", "MAJOR", "MINOR", "INFO"]] = Field(
        default=None, description="Severity (for bugs)"
    )
    priority: Optional[Literal["low", "medium", "high", "critical"]] = Field(
        default="medium", description="Priority (for tasks)"
    )
    content: Optional[str] = Field(default=None, description="Message content in markdown")
    content_file: Optional[str] = Field(
        default=None,
        description="Path to file containing message content (relative to agentmail/ or absolute). Use instead of content."
    )
    # Threading
    in_reply_to: Optional[str] = Field(default=None, description="Message ID this replies to")
    thread_id: Optional[str] = Field(default=None, description="Thread ID to group related messages")
    # File references
    file_references: Optional[list[FileReference]] = Field(
        default=None, description="Structured file references with paths and line numbers"
    )
    # Blocking dependencies
    blocked_by: Optional[list[str]] = Field(default=None, description="Message IDs that block this work")
    blocks: Optional[list[str]] = Field(default=None, description="Message IDs this work blocks")


class UpdateMessageStatusRequest(BaseModel):
    """Request to update a message/task status."""
    message_id: str = Field(..., description="Message ID (e.g., 'qa_agent_to_001')")
    status: Literal["open", "in_progress", "resolved", "closed"]
    notes: Optional[str] = Field(default=None, description="Status update notes")


class UpdateMessageRoutingRequest(BaseModel):
    """Request to update a message's From/To routing."""
    message_id: str = Field(..., description="Message ID (e.g., 'qa_agent_to_001')")
    field: Literal["from", "to"] = Field(..., description="Which field to update")
    value: str = Field(..., description="New agent name for the field")


class UpdateMessageThreadingRequest(BaseModel):
    """Request to update a message's threading (make it a reply to another message)."""
    message_id: str = Field(..., description="Message ID to update")
    in_reply_to: str = Field(..., description="Message ID this should reply to")
    thread_id: Optional[str] = Field(default=None, description="Thread ID (auto-generated if not provided)")


class UpdateStatusRequest(BaseModel):
    """Request to update agent status."""
    agent_name: str
    role: Optional[str] = None
    complete: Optional[list[StatusItem]] = None
    in_progress: Optional[list[StatusItem]] = None
    blocked: Optional[list[BlockedItem]] = None
    next_up: Optional[list[str]] = None
    coordination_notes: Optional[list[str]] = None


class AddTuningNoteRequest(BaseModel):
    """Request to add a tuning note."""
    from_agent: str
    topic: str
    content: str


class AcknowledgeMessageRequest(BaseModel):
    """Request to acknowledge receipt of a message."""
    message_id: str = Field(..., description="Message ID to acknowledge")
    agent_name: str = Field(..., description="Agent acknowledging the message")


class HeartbeatRequest(BaseModel):
    """Request to update agent's online status."""
    agent_name: str = Field(..., description="Agent name sending heartbeat")


class CreateAgentNoteRequest(BaseModel):
    """Request to create a per-agent note."""
    title: str = Field(..., description="Note title")
    content: str = Field(..., description="Note content in markdown")
    tags: list[str] = Field(default=[], description="Tags for categorization (e.g., ['debugging', 'coverage'])")
    domain: Optional[str] = Field(default=None, description="Domain/area (e.g., 'simulation', 'frontend')")


class SearchRequest(BaseModel):
    """Request for searching across AgentMail content."""
    query: str = Field(..., description="Search query string")
    scope: list[Literal["messages", "notes", "status", "tuning"]] = Field(
        default=["messages", "notes", "status", "tuning"],
        description="Content types to search"
    )
    agent: Optional[str] = Field(default=None, description="Filter by agent name")
    message_type: Optional[str] = Field(default=None, description="Filter by message type")
    severity: Optional[str] = Field(default=None, description="Filter by severity")
    date_from: Optional[str] = Field(default=None, description="Filter from date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(default=None, description="Filter to date (YYYY-MM-DD)")
    limit: int = Field(default=50, ge=1, le=200, description="Max results to return")


class ScheduleMessageRequest(BaseModel):
    """Request to schedule a message for later delivery."""
    from_agent: str = Field(..., description="Sender agent name")
    to_agent: str = Field(..., description="Recipient agent name")
    cc: Optional[list[str]] = Field(default=None, description="CC recipients")
    subject: str = Field(..., description="Message subject")
    message_type: Literal["task", "response", "bug", "plan", "handoff", "question"] = Field(
        default="response", description="Type of message"
    )
    severity: Optional[Literal["BLOCKING", "MAJOR", "MINOR", "INFO"]] = Field(
        default=None, description="Severity (for bugs)"
    )
    content: str = Field(..., description="Message content in markdown")
    in_reply_to: Optional[str] = Field(default=None, description="Message ID this replies to")
    thread_id: Optional[str] = Field(default=None, description="Thread ID to group related messages")
    # Scheduling options
    send_at: Optional[str] = Field(default=None, description="ISO datetime to send message (e.g., '2024-01-15T14:00:00')")
    remind_after_minutes: Optional[int] = Field(default=None, description="Resend as reminder if no response within N minutes")


class ScheduledMessage(BaseModel):
    """A scheduled message pending delivery."""
    id: str
    from_agent: str
    to_agent: str
    cc: Optional[list[str]] = None
    subject: str
    message_type: str
    severity: Optional[str] = None
    content: str
    in_reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    send_at: Optional[str] = None
    remind_after_minutes: Optional[int] = None
    original_message_id: Optional[str] = None  # For reminders - the original message we're checking for replies
    created_at: str
    status: Literal["pending", "sent", "cancelled"] = "pending"


class ScheduledMessageResponse(BaseModel):
    """Response after scheduling a message."""
    success: bool
    scheduled_id: str
    send_at: Optional[str] = None
    remind_after_minutes: Optional[int] = None


class ScheduledListResponse(BaseModel):
    """List of scheduled messages."""
    agent: str
    scheduled: list[ScheduledMessage]
    total: int


# ============================================================================
# Response Models
# ============================================================================

class AgentListResponse(BaseModel):
    """List of all agents."""
    agents: list[AgentInfo]
    total: int


class InboxResponse(BaseModel):
    """Agent inbox."""
    agent: str
    total: int
    pending: int
    messages: list[Message]


class SendMessageResponse(BaseModel):
    """Response after sending message."""
    success: bool
    message_id: str
    filename: str
    path: str


class OperationResponse(BaseModel):
    """Generic operation response."""
    success: bool
    message: str
    data: Optional[dict] = None


def parse_status_file(filepath: Path) -> Optional[AgentStatus]:
    """Parse an agent status markdown file."""
    if not filepath.exists():
        return None

    content = filepath.read_text()

    # Extract agent name from filename
    name = filepath.stem.replace("_status", "")

    # Extract display name and role from header
    display_name = name.replace("_", " ").title()
    role = ""

    role_match = re.search(r"\*\*Agent Role:\*\*\s*(.+)", content)
    if role_match:
        role = role_match.group(1).strip()

    # Extract last updated
    last_updated = ""
    updated_match = re.search(r"\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    if updated_match:
        last_updated = updated_match.group(1)

    # Parse COMPLETE section
    complete = []
    complete_section = re.search(r"## COMPLETE.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if complete_section:
        rows = re.findall(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", complete_section.group(1))
        for row in rows:
            if row[0].strip() not in ["Component", "---", "-", "..."]:
                complete.append(StatusItem(
                    component=row[0].strip(),
                    location=row[1].strip(),
                    notes=row[2].strip()
                ))

    # Parse IN PROGRESS section
    in_progress = []
    progress_section = re.search(r"## IN PROGRESS.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if progress_section:
        rows = re.findall(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", progress_section.group(1))
        for row in rows:
            if row[0].strip() not in ["Component", "---", "-", "..."]:
                in_progress.append(StatusItem(
                    component=row[0].strip(),
                    location=row[1].strip(),
                    notes=row[2].strip() if len(row) > 2 else ""
                ))

    # Parse BLOCKED section
    blocked = []
    blocked_section = re.search(r"## BLOCKED.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if blocked_section:
        rows = re.findall(r"\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|", blocked_section.group(1))
        for row in rows:
            if row[0].strip() not in ["Issue", "---", "-", "..."]:
                blocked.append(BlockedItem(
                    issue=row[0].strip(),
                    waiting_on=row[1].strip(),
                    notes=row[2].strip()
                ))

    # Parse NEXT UP section
    next_up = []
    next_section = re.search(r"## NEXT UP.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if next_section:
        items = re.findall(r"^\d+\.\s*(.+)$", next_section.group(1), re.MULTILINE)
        next_up = [item.strip() for item in items]

    # Parse coordination notes
    coordination_notes = []
    coord_section = re.search(r"## (?:COORDINATION|Coordination).*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if coord_section:
        notes = re.findall(r"[-*]\s*(.+)", coord_section.group(1))
        coordination_notes = [note.strip() for note in notes]

    return AgentStatus(
        name=name,
        display_name=display_name,
        role=role,
        last_updated=last_updated,
        complete=complete,
        in_progress=in_progress,
        blocked=blocked,
        next_up=next_up,
        coordination_notes=coordination_notes
    )


def parse_message_file(filepath: Path, agent_name: str, direction: str) -> Optional[Message]:
    """Parse a message markdown file."""
    if not filepath.exists():
        return None

    content = filepath.read_text()
    filename = filepath.name

    # Extract message number from filename
    msg_id = filename.split("_")[0]

    # Determine message type
    msg_type = "task"
    if "bug" in filename.lower():
        msg_type = "bug"
    elif "plan" in filename.lower() or "contract" in filename.lower() or "spec" in filename.lower():
        msg_type = "plan"
    elif direction == "from":
        msg_type = "response"

    # Extract subject from first heading
    subject = filename.replace(".md", "").replace("_", " ").title()
    subject_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if subject_match:
        subject = subject_match.group(1).strip()

    # Extract severity if present
    severity = None
    severity_match = re.search(r"\*\*Severity:\*\*\s*(\w+)", content)
    if severity_match:
        severity = severity_match.group(1).upper()

    # Extract status if present (default to 'open')
    status = "open"
    status_match = re.search(r"\*\*Status:\*\*\s*(\w+)", content)
    if status_match:
        status = status_match.group(1).lower()

    # Extract threading info
    in_reply_to = None
    reply_match = re.search(r"\*\*(?:In-Reply-To|Reply-To):\*\*\s*(.+)", content)
    if reply_match:
        in_reply_to = reply_match.group(1).strip()

    thread_id = None
    thread_match = re.search(r"\*\*Thread(?:-ID)?:\*\*\s*(.+)", content)
    if thread_match:
        thread_id = thread_match.group(1).strip()

    # Extract acknowledgment
    acknowledged_at = None
    ack_match = re.search(r"\*\*Acknowledged(?:-At)?:\*\*\s*(.+)", content)
    if ack_match:
        acknowledged_at = ack_match.group(1).strip()

    # Extract per-agent acknowledgments
    acknowledged_by = None
    ack_by_match = re.search(r"\*\*Acknowledged-By:\*\*\s*(.+)", content)
    if ack_by_match:
        try:
            acknowledged_by = json.loads(ack_by_match.group(1).strip())
        except json.JSONDecodeError:
            acknowledged_by = None

    # Extract file references
    file_references = None
    refs_match = re.search(r"\*\*File-References:\*\*\s*(.+)", content)
    if refs_match:
        try:
            refs_json = refs_match.group(1).strip()
            refs_data = json.loads(refs_json)
            file_references = [FileReference(**r) for r in refs_data]
        except:
            pass

    # Extract blocking dependencies
    blocked_by = None
    blocked_match = re.search(r"\*\*Blocked-By:\*\*\s*(.+)", content)
    if blocked_match:
        blocked_by = [b.strip() for b in blocked_match.group(1).split(",")]

    blocks = None
    blocks_match = re.search(r"\*\*Blocks:\*\*\s*(.+)", content)
    if blocks_match:
        blocks = [b.strip() for b in blocks_match.group(1).split(",")]

    # Extract mentions
    mentions = None
    mentions_match = re.search(r"\*\*Mentions:\*\*\s*(.+)", content)
    if mentions_match:
        mentions = [m.strip() for m in mentions_match.group(1).split(",")]

    # Extract date (with optional time)
    date = ""
    date_match = re.search(r"\*\*Date:\*\*\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)", content)
    if date_match:
        date = date_match.group(1)
    else:
        # Use file modification time with full timestamp
        mtime = filepath.stat().st_mtime
        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    # Extract preview - all content after the --- header separator
    preview = ""
    header_end = content.find("\n---\n")
    if header_end != -1:
        # Get everything after the header
        body = content[header_end + 5:].strip()
        preview = body[:500]  # First 500 chars of body
    else:
        # No header separator, use content directly
        preview = content[:500]

    # Determine from/to based on direction
    if direction == "to":
        from_agent = "coordinator"
        to_agent = agent_name
    else:
        from_agent = agent_name
        to_agent = "coordinator"

    # Check for explicit To/From/CC in content
    from_match = re.search(r"\*\*From:\*\*\s*(.+)", content)
    to_match = re.search(r"\*\*To:\*\*\s*(.+)", content)
    cc_match = re.search(r"\*\*CC:\*\*\s*(.+)", content)
    if from_match:
        from_agent = from_match.group(1).strip().lower().replace(" ", "_")
    if to_match:
        to_agent = to_match.group(1).strip().lower().replace(" ", "_")

    # Parse CC list
    cc_list = None
    if cc_match:
        cc_raw = cc_match.group(1).strip()
        cc_list = [agent.strip().lower().replace(" ", "_") for agent in cc_raw.split(",")]

    return Message(
        id=f"{agent_name}_{direction}_{msg_id}",
        filename=filename,
        from_agent=from_agent,
        to_agent=to_agent,
        cc=cc_list,
        subject=subject,
        date=date,
        severity=severity,
        status=status,
        type=msg_type,
        preview=preview,
        content=content,
        in_reply_to=in_reply_to,
        thread_id=thread_id,
        acknowledged_at=acknowledged_at,
        acknowledged_by=acknowledged_by,
        file_references=file_references,
        blocked_by=blocked_by,
        blocks=blocks,
        mentions=mentions
    )


def parse_tuning_note(filepath: Path) -> Optional[TuningNote]:
    """Parse a tuning note markdown file."""
    if not filepath.exists():
        return None

    filename = filepath.name
    note_id = filename.split("_")[0]

    # Extract topic from filename or content
    topic = filename.replace(".md", "").split("_", 1)[-1].replace("_", " ").title()

    content = filepath.read_text()
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        topic = title_match.group(1).strip()

    # Get date from file modification time (with timestamp)
    mtime = filepath.stat().st_mtime
    date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    # Extract added_by if present
    added_by = None
    added_match = re.search(r"\*\*Added by:\*\*\s*(\w+)", content)
    if added_match:
        added_by = added_match.group(1).strip()

    return TuningNote(
        id=note_id,
        filename=filename,
        topic=topic,
        added_by=added_by,
        date=date,
        content=content
    )


def parse_agent_note(filepath: Path, agent_name: str) -> Optional[AgentNote]:
    """Parse a per-agent note markdown file.

    Expected format:
    # Note Title
    **Date:** 2024-01-15
    **Tags:** debugging, coverage
    **Domain:** simulation
    ---
    Content...
    """
    if not filepath.exists():
        return None

    filename = filepath.name
    note_id = filename.replace(".md", "")

    content = filepath.read_text()

    # Extract title from first heading
    title = filename.replace(".md", "").split("_", 1)[-1].replace("_", " ").title()
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # Extract date from metadata or file mtime (with timestamp)
    date_match = re.search(r"\*\*Date:\*\*\s*(.+)", content)
    if date_match:
        date = date_match.group(1).strip()
    else:
        mtime = filepath.stat().st_mtime
        date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    # Extract tags
    tags: list[str] = []
    tags_match = re.search(r"\*\*Tags:\*\*\s*(.+)", content)
    if tags_match:
        tags = [t.strip() for t in tags_match.group(1).split(",")]

    # Extract domain
    domain = None
    domain_match = re.search(r"\*\*Domain:\*\*\s*(.+)", content)
    if domain_match:
        domain = domain_match.group(1).strip()

    return AgentNote(
        id=note_id,
        filename=filename,
        agent_name=agent_name,
        title=title,
        date=date,
        tags=tags,
        domain=domain,
        content=content
    )


def _get_next_note_number(notes_dir: Path) -> str:
    """Get the next note number for an agent's notes folder."""
    if not notes_dir.exists():
        notes_dir.mkdir(parents=True, exist_ok=True)
        return "001"

    existing = list(notes_dir.glob("*.md"))
    if not existing:
        return "001"

    numbers = []
    for f in existing:
        match = re.match(r"^(\d+)", f.name)
        if match:
            numbers.append(int(match.group(1)))

    next_num = max(numbers) + 1 if numbers else 1
    return f"{next_num:03d}"


def _get_next_message_number(agent_dir: Path, direction: str) -> str:
    """Get the next message number for an agent's to/from folder."""
    folder = agent_dir / direction
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        return "001"

    existing = list(folder.glob("*.md"))
    if not existing:
        return "001"

    numbers = []
    for f in existing:
        match = re.match(r"^(\d+)", f.name)
        if match:
            numbers.append(int(match.group(1)))

    next_num = max(numbers) + 1 if numbers else 1
    return f"{next_num:03d}"


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:50]


def _get_agent_info(agent_name: str) -> Optional[AgentInfo]:
    """Get info about an agent."""
    agent_dir = AGENTMAIL_PATH / agent_name
    if not agent_dir.exists():
        return None

    # Check for config file
    config_file = agent_dir / "agent.json"
    display_name = agent_name.replace("_", " ").title()
    role = ""
    created = None
    last_heartbeat = None
    is_online = False

    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
            display_name = config.get("display_name", display_name)
            role = config.get("role", "")
            created = config.get("created")
            last_heartbeat = config.get("last_heartbeat")
            # Check if online (heartbeat within last 5 minutes)
            if last_heartbeat:
                try:
                    hb_time = datetime.fromisoformat(last_heartbeat)
                    now = datetime.now()
                    is_online = (now - hb_time).total_seconds() < 300  # 5 minutes
                except:
                    pass
        except:
            pass

    # Check status file for role
    status_file = AGENTMAIL_PATH / "status" / f"{agent_name}_status.md"
    has_status = status_file.exists()
    if has_status and not role:
        status = parse_status_file(status_file)
        if status:
            role = status.role

    # Count messages - will be updated after all messages are parsed
    # (set to 0 here, actual count based on To/From fields computed in dashboard)
    inbox_count = 0
    outbox_count = 0

    # Get last active (most recent file modification)
    last_active = None
    all_files = list(agent_dir.rglob("*.md"))
    if all_files:
        most_recent = max(all_files, key=lambda f: f.stat().st_mtime)
        last_active = datetime.fromtimestamp(most_recent.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

    return AgentInfo(
        name=agent_name,
        display_name=display_name,
        role=role,
        created=created,
        last_active=last_active,
        last_heartbeat=last_heartbeat,
        is_online=is_online,
        has_status=has_status,
        inbox_count=inbox_count,
        outbox_count=outbox_count
    )


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard")
async def get_dashboard_data():
    """
    Get full dashboard data.

    Returns all agents, statuses, messages, tasks, and tuning notes.
    """
    if not AGENTMAIL_PATH.exists():
        raise HTTPException(status_code=404, detail="Agentmail folder not found")

    agents: list[AgentInfo] = []
    agent_statuses: list[AgentStatus] = []
    messages: list[Message] = []
    tasks: list[Task] = []
    tuning_notes: list[TuningNote] = []

    # Get all agents
    for agent_dir in AGENTMAIL_PATH.iterdir():
        if agent_dir.is_dir() and agent_dir.name not in ["status", "tuning_notes", "__pycache__"]:
            info = _get_agent_info(agent_dir.name)
            if info:
                agents.append(info)

            # Parse messages
            to_dir = agent_dir / "to"
            if to_dir.exists():
                for msg_file in to_dir.glob("*.md"):
                    msg = parse_message_file(msg_file, agent_dir.name, "to")
                    if msg:
                        messages.append(msg)
                        # Also track as task if type is task
                        if msg.type == "task":
                            tasks.append(Task(
                                id=msg.id,
                                filename=msg.filename,
                                from_agent=msg.from_agent,
                                to_agent=msg.to_agent,
                                title=msg.subject,
                                description=msg.preview,
                                date_created=msg.date,
                                priority="medium",
                                status="pending"
                            ))

            from_dir = agent_dir / "from"
            if from_dir.exists():
                for msg_file in from_dir.glob("*.md"):
                    msg = parse_message_file(msg_file, agent_dir.name, "from")
                    if msg:
                        messages.append(msg)

    # Parse status files
    status_path = AGENTMAIL_PATH / "status"
    if status_path.exists():
        for status_file in status_path.glob("*_status.md"):
            status = parse_status_file(status_file)
            if status:
                agent_statuses.append(status)

    # Parse tuning notes
    tuning_path = AGENTMAIL_PATH / "tuning_notes"
    if tuning_path.exists():
        for note_file in tuning_path.glob("*.md"):
            note = parse_tuning_note(note_file)
            if note:
                tuning_notes.append(note)

    # Deduplicate messages by content (same from+to+subject+date = duplicate)
    seen = set()
    unique_messages = []
    for msg in messages:
        key = (msg.from_agent, msg.to_agent, msg.subject, msg.date)
        if key not in seen:
            seen.add(key)
            unique_messages.append(msg)
    messages = unique_messages

    # Update agent inbox/outbox counts based on actual To/From content routing
    for agent in agents:
        agent.inbox_count = len([m for m in messages if m.to_agent == agent.name])
        agent.outbox_count = len([m for m in messages if m.from_agent == agent.name])

    # Sort
    messages.sort(key=lambda m: m.date, reverse=True)
    agents.sort(key=lambda a: a.last_active or "", reverse=True)

    # Calculate stats
    stats = {
        "total_agents": len(agents),
        "total_messages": len(messages),
        "total_tasks": len(tasks),
        "pending_tasks": len([t for t in tasks if t.status == "pending"]),
        "bugs": len([m for m in messages if m.type == "bug"]),
        "blocking_bugs": len([m for m in messages if m.severity == "BLOCKING"]),
        "tuning_notes": len(tuning_notes)
    }

    return {
        "agents": [a.model_dump() for a in agents],
        "agent_statuses": [s.model_dump() for s in agent_statuses],
        "messages": [m.model_dump() for m in messages],
        "tasks": [t.model_dump() for t in tasks],
        "tuning_notes": [n.model_dump() for n in tuning_notes],
        "stats": stats
    }


# ============================================================================
# Agent Management Endpoints
# ============================================================================

@router.get("/agents/list", response_model=AgentListResponse)
async def list_agents():
    """List all registered agents."""
    agents = []
    for agent_dir in AGENTMAIL_PATH.iterdir():
        if agent_dir.is_dir() and agent_dir.name not in ["status", "tuning_notes", "__pycache__"]:
            info = _get_agent_info(agent_dir.name)
            if info:
                agents.append(info)

    return AgentListResponse(agents=agents, total=len(agents))


@router.post("/agents/create", response_model=OperationResponse)
async def create_agent(request: CreateAgentRequest):
    """
    Create a new agent with the standard folder structure.

    Creates:
    - {agent_name}/
    - {agent_name}/to/       (inbox)
    - {agent_name}/from/     (outbox)
    - {agent_name}/plans/    (implementation plans)
    - {agent_name}/agent.json (config)
    """
    # Validate name
    if not re.match(r"^[a-z][a-z0-9_]*_agent$", request.name):
        raise HTTPException(
            status_code=400,
            detail="Agent name must be snake_case ending in '_agent' (e.g., 'my_new_agent')"
        )

    agent_dir = AGENTMAIL_PATH / request.name
    if agent_dir.exists():
        raise HTTPException(status_code=400, detail=f"Agent '{request.name}' already exists")

    # Create directory structure
    agent_dir.mkdir(parents=True)
    (agent_dir / "to").mkdir()
    (agent_dir / "from").mkdir()
    (agent_dir / "plans").mkdir()

    # Create config file
    config = {
        "name": request.name,
        "display_name": request.display_name,
        "role": request.role,
        "created": datetime.now().isoformat()
    }
    (agent_dir / "agent.json").write_text(json.dumps(config, indent=2))

    # Create initial status file
    status_dir = AGENTMAIL_PATH / "status"
    status_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    status_content = f"""# {request.display_name} - Status

**Last Updated:** {today}
**Agent Role:** {request.role}

---

## COMPLETE
| Component | Location | Notes |
|-----------|----------|-------|
| - | - | - |

## IN PROGRESS
| Component | Location | Notes |
|-----------|----------|-------|
| - | - | - |

## BLOCKED
| Issue | Waiting On | Notes |
|-------|-----------|-------|
| - | - | - |

## NEXT UP
1. Review inbox for initial tasks
2. Read relevant documentation

## COORDINATION NOTES
- Newly created agent - awaiting first tasks
"""
    (status_dir / f"{request.name}_status.md").write_text(status_content)

    return OperationResponse(
        success=True,
        message=f"Agent '{request.name}' created successfully",
        data={"path": str(agent_dir)}
    )


@router.delete("/agents/{agent_name}", response_model=OperationResponse)
async def delete_agent(agent_name: str, confirm: bool = Query(False)):
    """
    Delete an agent and all their data.

    Requires confirm=true to actually delete.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must pass confirm=true to delete an agent"
        )

    agent_dir = AGENTMAIL_PATH / agent_name
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    # Remove agent directory
    shutil.rmtree(agent_dir)

    # Remove status file if exists
    status_file = AGENTMAIL_PATH / "status" / f"{agent_name}_status.md"
    if status_file.exists():
        status_file.unlink()

    return OperationResponse(
        success=True,
        message=f"Agent '{agent_name}' deleted"
    )


@router.get("/agents/{agent_name}", response_model=AgentInfo)
async def get_agent(agent_name: str):
    """Get info about a specific agent."""
    info = _get_agent_info(agent_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return info


@router.get("/agents/{agent_name}/status", response_model=AgentStatus)
async def get_agent_status(agent_name: str):
    """Get an agent's full status (parsed)."""
    status_file = AGENTMAIL_PATH / "status" / f"{agent_name}_status.md"
    if not status_file.exists():
        raise HTTPException(status_code=404, detail=f"No status file for agent '{agent_name}'")

    status = parse_status_file(status_file)
    if not status:
        raise HTTPException(status_code=500, detail="Failed to parse status file")
    return status


@router.get("/agents/{agent_name}/status/raw")
async def get_agent_status_raw(agent_name: str):
    """Get an agent's status file as raw markdown content."""
    status_file = AGENTMAIL_PATH / "status" / f"{agent_name}_status.md"
    if not status_file.exists():
        raise HTTPException(status_code=404, detail=f"No status file for agent '{agent_name}'")

    content = status_file.read_text()
    return {"content": content, "path": str(status_file)}


# ============================================================================
# Message Endpoints
# ============================================================================

@router.get("/messages", response_model=list[Message])
async def get_messages(
    agent: Optional[str] = None,
    type: Optional[str] = None,
    severity: Optional[str] = None,
    include_content: bool = Query(False, description="Include full markdown content")
):
    """Get messages with optional filtering."""
    data = await get_dashboard_data()
    messages = [Message(**m) for m in data["messages"]]

    if agent:
        messages = [m for m in messages if m.from_agent == agent or m.to_agent == agent]
    if type:
        messages = [m for m in messages if m.type == type]
    if severity:
        messages = [m for m in messages if m.severity == severity.upper()]

    if not include_content:
        for m in messages:
            m.content = None

    return messages


@router.get("/messages/{message_id}")
async def get_message(message_id: str, render: bool = Query(False)):
    """
    Get a specific message by ID.

    Message ID format: {agent_name}_{direction}_{msg_num}
    e.g., claude_code_agent_to_001

    If render=true, returns HTML-rendered markdown.
    """
    # Parse message_id to find the file directly
    # Format: {agent_name}_{direction}_{msg_num}
    parts = message_id.rsplit("_", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid message_id format. Expected: agent_name_direction_num")

    msg_num = parts[-1]
    direction = parts[-2]
    agent_name = "_".join(parts[:-2])

    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Invalid direction in message_id. Expected 'to' or 'from'")

    # Find the file
    msg_dir = AGENTMAIL_PATH / agent_name / direction
    if not msg_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' {direction} folder not found")

    # Look for file starting with the message number
    msg_file = None
    for f in msg_dir.glob(f"{msg_num}_*.md"):
        msg_file = f
        break

    if not msg_file:
        raise HTTPException(status_code=404, detail=f"Message {message_id} not found")

    # Parse the message
    msg = parse_message_file(msg_file, agent_name, direction)
    if not msg:
        raise HTTPException(status_code=500, detail="Failed to parse message file")

    result = msg.model_dump()

    # Add full content
    result["content"] = msg_file.read_text()

    if render and result.get("content"):
        # Simple markdown to HTML (basic conversion)
        import html
        content = result["content"]
        content = html.escape(content)
        # Convert headers
        content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)
        content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
        content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
        # Convert bold/italic
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)
        # Convert code blocks
        content = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code class="\1">\2</code></pre>', content, flags=re.DOTALL)
        content = re.sub(r'`(.+?)`', r'<code>\1</code>', content)
        # Convert lists
        content = re.sub(r'^- (.+)$', r'<li>\1</li>', content, flags=re.MULTILINE)
        content = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', content, flags=re.MULTILINE)
        # Paragraphs
        content = re.sub(r'\n\n', '</p><p>', content)
        result["content_html"] = f"<p>{content}</p>"
    return result


@router.get("/messages/file/{agent_name}/{direction}/{filename}")
async def get_message_file(agent_name: str, direction: str, filename: str):
    """Get raw message file content."""
    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Direction must be 'to' or 'from'")

    filepath = AGENTMAIL_PATH / agent_name / direction / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Message file not found")

    return {
        "filename": filename,
        "path": str(filepath),
        "content": filepath.read_text()
    }


# ============================================================================
# Inbox/Outbox Endpoints
# ============================================================================

@router.get("/inbox/{agent_name}", response_model=InboxResponse)
@router.get("/{agent_name}/inbox", response_model=InboxResponse)  # Alias
async def get_agent_inbox(agent_name: str, include_content: bool = False, include_cc: bool = True):
    """Get an agent's inbox (messages TO them, plus messages where they're CC'd)."""
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    to_dir = AGENTMAIL_PATH / agent_name / "to"
    messages = []
    seen_ids = set()

    # Direct inbox messages
    if to_dir.exists():
        for msg_file in sorted(to_dir.glob("*.md"), reverse=True):
            msg = parse_message_file(msg_file, agent_name, "to")
            if msg:
                if not include_content:
                    msg.content = None
                messages.append(msg)
                seen_ids.add(msg.id)

    # Also include messages where this agent is CC'd
    if include_cc:
        for agent_dir in AGENTMAIL_PATH.iterdir():
            if not agent_dir.is_dir() or agent_dir.name in ["status", "notes", agent_name]:
                continue
            other_to_dir = agent_dir / "to"
            if other_to_dir.exists():
                for msg_file in other_to_dir.glob("*.md"):
                    msg = parse_message_file(msg_file, agent_dir.name, "to")
                    if msg and msg.id not in seen_ids and msg.cc and agent_name in msg.cc:
                        if not include_content:
                            msg.content = None
                        messages.append(msg)
                        seen_ids.add(msg.id)

    # Sort by date descending
    messages.sort(key=lambda m: m.date, reverse=True)

    pending = len([m for m in messages if m.status == "pending"])

    return InboxResponse(
        agent=agent_name,
        total=len(messages),
        pending=pending,
        messages=messages
    )


@router.get("/outbox/{agent_name}", response_model=list[Message])
@router.get("/{agent_name}/outbox", response_model=list[Message])  # Alias
async def get_agent_outbox(agent_name: str, include_content: bool = False):
    """Get an agent's outbox (messages FROM them)."""
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    from_dir = AGENTMAIL_PATH / agent_name / "from"
    messages = []

    if from_dir.exists():
        for msg_file in sorted(from_dir.glob("*.md"), reverse=True):
            msg = parse_message_file(msg_file, agent_name, "from")
            if msg:
                if not include_content:
                    msg.content = None
                messages.append(msg)

    return messages


# ============================================================================
# Send Message Endpoint
# ============================================================================

@router.post("/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Send a message to another agent.

    Creates a file in the recipient's inbox and sender's outbox.
    """
    # Validate sender exists
    if request.from_agent != "coordinator" and not _ensure_agent_exists(request.from_agent):
        raise HTTPException(status_code=400, detail=f"Sender '{request.from_agent}' not found")

    # Handle content_file - read content from file if provided
    content = request.content
    if request.content_file:
        # Resolve file path - can be relative to agentmail/ or absolute
        file_path = Path(request.content_file)
        if not file_path.is_absolute():
            file_path = AGENTMAIL_PATH / file_path

        if not file_path.exists():
            raise HTTPException(status_code=400, detail=f"Content file not found: {request.content_file}")

        # Security: ensure file is within project directory
        try:
            file_path.resolve().relative_to(AGENTMAIL_PATH.parent.resolve())
        except ValueError:
            raise HTTPException(status_code=400, detail="Content file must be within project directory")

        content = file_path.read_text()

    if not content:
        raise HTTPException(status_code=400, detail="Either content or content_file must be provided")

    # Create recipient if doesn't exist (for coordinator sending to new agents)
    recipient_dir = AGENTMAIL_PATH / request.to_agent
    if not recipient_dir.exists():
        raise HTTPException(status_code=400, detail=f"Recipient '{request.to_agent}' not found")

    recipient_to = recipient_dir / "to"
    recipient_to.mkdir(parents=True, exist_ok=True)

    # Create sender outbox if not coordinator
    sender_from = None
    if request.from_agent != "coordinator":
        sender_dir = AGENTMAIL_PATH / request.from_agent
        sender_from = sender_dir / "from"
        sender_from.mkdir(parents=True, exist_ok=True)

    # Generate filename
    msg_num = _get_next_message_number(recipient_dir, "to")
    slug = _slugify(request.subject)

    type_prefix = ""
    if request.message_type == "bug":
        type_prefix = "bug_"
    elif request.message_type == "plan":
        type_prefix = "plan_"
    elif request.message_type == "handoff":
        type_prefix = "handoff_"
    elif request.message_type == "task":
        type_prefix = "task_"

    filename = f"{msg_num}_{type_prefix}{slug}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build content
    header = f"""# {request.subject}

**From:** {request.from_agent}
**To:** {request.to_agent}
"""
    if request.cc:
        header += f"**CC:** {', '.join(request.cc)}\n"
    header += f"""**Date:** {timestamp}
**Type:** {request.message_type}
"""
    if request.severity:
        header += f"**Severity:** {request.severity}\n"
    if request.priority and request.message_type == "task":
        header += f"**Priority:** {request.priority}\n"
    # Threading
    if request.in_reply_to:
        header += f"**In-Reply-To:** {request.in_reply_to}\n"
    if request.thread_id:
        header += f"**Thread:** {request.thread_id}\n"
    # File references
    if request.file_references:
        refs_json = json.dumps([r.model_dump() for r in request.file_references])
        header += f"**File-References:** {refs_json}\n"
    # Blocking dependencies
    if request.blocked_by:
        header += f"**Blocked-By:** {', '.join(request.blocked_by)}\n"
    if request.blocks:
        header += f"**Blocks:** {', '.join(request.blocks)}\n"

    # Extract @mentions from content
    mentions = _extract_mentions(content)
    # Filter out primary recipient and CC'd agents (they already get the message)
    already_receiving = {request.to_agent}
    if request.cc:
        already_receiving.update(request.cc)
    mentions = [m for m in mentions if m not in already_receiving and m != request.from_agent]
    if mentions:
        header += f"**Mentions:** {', '.join(mentions)}\n"

    header += "\n---\n\n"
    full_content = header + content

    # Write to recipient inbox
    recipient_path = recipient_to / filename
    recipient_path.write_text(full_content)

    # Write to sender outbox
    if sender_from:
        (sender_from / filename).write_text(full_content)

    # Write to CC'd agents' inboxes
    if request.cc:
        for cc_agent in request.cc:
            if cc_agent != request.from_agent and _ensure_agent_exists(cc_agent):
                cc_dir = AGENTMAIL_PATH / cc_agent / "to"
                cc_dir.mkdir(parents=True, exist_ok=True)
                (cc_dir / filename).write_text(full_content)

    # Write to mentioned agents' inboxes (like CC but triggered by @ in body)
    if mentions:
        for mentioned_agent in mentions:
            if _ensure_agent_exists(mentioned_agent):
                mention_dir = AGENTMAIL_PATH / mentioned_agent / "to"
                mention_dir.mkdir(parents=True, exist_ok=True)
                (mention_dir / filename).write_text(full_content)

    return SendMessageResponse(
        success=True,
        message_id=f"{request.to_agent}_to_{msg_num}",
        filename=filename,
        path=str(recipient_path)
    )


# ============================================================================
# Message Status Update Endpoint
# ============================================================================

@router.post("/messages/status", response_model=OperationResponse)
async def update_message_status(request: UpdateMessageStatusRequest):
    """
    Update a message's status (open, in_progress, resolved, closed).

    This modifies the message file to add or update the **Status:** field.
    """
    # Parse message_id to find the file
    # Format: agent_direction_number (e.g., "qa_agent_to_001")
    parts = request.message_id.rsplit("_", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    agent_name = "_".join(parts[:-2])
    direction = parts[-2]
    msg_num = parts[-1]

    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    # Find the message file
    agent_dir = AGENTMAIL_PATH / agent_name / direction
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail=f"Agent directory not found")

    # Find file starting with the message number
    matching_files = list(agent_dir.glob(f"{msg_num}_*.md"))
    if not matching_files:
        raise HTTPException(status_code=404, detail=f"Message not found")

    filepath = matching_files[0]
    content = filepath.read_text()

    # Update or add status field
    status_pattern = r"\*\*Status:\*\*\s*\w+"
    new_status_line = f"**Status:** {request.status}"

    if re.search(status_pattern, content):
        # Update existing status
        content = re.sub(status_pattern, new_status_line, content)
    else:
        # Add status after severity or date, or at the start of metadata
        # Look for a good place to insert
        if "**Severity:**" in content:
            content = re.sub(
                r"(\*\*Severity:\*\*\s*\w+)",
                f"\\1\n{new_status_line}",
                content
            )
        elif "**Date:**" in content:
            content = re.sub(
                r"(\*\*Date:\*\*\s*[\d-]+)",
                f"\\1\n{new_status_line}",
                content
            )
        else:
            # Add after first heading
            content = re.sub(
                r"(^#\s+.+$)",
                f"\\1\n\n{new_status_line}",
                content,
                count=1,
                flags=re.MULTILINE
            )

    # Add status update notes if provided
    if request.notes:
        today = datetime.now().strftime("%Y-%m-%d")
        update_note = f"\n\n---\n**Status Update ({today}):** {request.notes}"
        content += update_note

    filepath.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Status updated to '{request.status}'",
        data={"message_id": request.message_id, "status": request.status}
    )


@router.post("/messages/routing", response_model=OperationResponse)
async def update_message_routing(request: UpdateMessageRoutingRequest):
    """
    Update a message's From or To routing field.

    This modifies the message file to add or update the **From:** or **To:** field.
    """
    # Parse message_id to find the file
    parts = request.message_id.rsplit("_", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    agent_name = "_".join(parts[:-2])
    direction = parts[-2]
    msg_num = parts[-1]

    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    # Find the message file
    agent_dir = AGENTMAIL_PATH / agent_name / direction
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent directory not found")

    matching_files = list(agent_dir.glob(f"{msg_num}_*.md"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Message not found")

    filepath = matching_files[0]
    content = filepath.read_text()

    # Format agent name for display (e.g., "live_sim_agent" -> "Live Sim Agent")
    display_value = request.value.replace("_", " ").title()

    # Update or add the field
    if request.field == "from":
        pattern = r"\*\*From:\*\*\s*.+"
        new_line = f"**From:** {display_value}"
    else:
        pattern = r"\*\*To:\*\*\s*.+"
        new_line = f"**To:** {display_value}"

    if re.search(pattern, content):
        # Update existing field
        content = re.sub(pattern, new_line, content)
    else:
        # Add field after Date or at the start of metadata
        if "**Date:**" in content:
            content = re.sub(
                r"(\*\*Date:\*\*\s*[\d-]+)",
                f"\\1\n{new_line}",
                content
            )
        elif "**Severity:**" in content:
            content = re.sub(
                r"(\*\*Severity:\*\*\s*\w+)",
                f"{new_line}\n\\1",
                content
            )
        else:
            # Add after first heading
            content = re.sub(
                r"(^#\s+.+$)",
                f"\\1\n\n{new_line}",
                content,
                count=1,
                flags=re.MULTILINE
            )

    filepath.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Updated {request.field} to '{display_value}'",
        data={"message_id": request.message_id, "field": request.field, "value": request.value}
    )


@router.post("/messages/threading", response_model=OperationResponse)
async def update_message_threading(request: UpdateMessageThreadingRequest):
    """
    Update a message's threading to make it a reply to another message.

    This sets the In-Reply-To and Thread fields, effectively merging messages into threads.
    """
    # Parse message_id to find the file
    parts = request.message_id.rsplit("_", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    agent_name = "_".join(parts[:-2])
    direction = parts[-2]
    msg_num = parts[-1]

    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    # Find the message file
    agent_dir = AGENTMAIL_PATH / agent_name / direction
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent directory not found")

    matching_files = list(agent_dir.glob(f"{msg_num}_*.md"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Message not found")

    filepath = matching_files[0]
    content = filepath.read_text()

    # Generate thread_id if not provided - use the target message's thread or create new
    thread_id = request.thread_id
    if not thread_id:
        # Try to get thread_id from the target message
        target_parts = request.in_reply_to.rsplit("_", 2)
        if len(target_parts) >= 3:
            target_agent = "_".join(target_parts[:-2])
            target_direction = target_parts[-2]
            target_num = target_parts[-1]
            target_dir = AGENTMAIL_PATH / target_agent / target_direction
            target_files = list(target_dir.glob(f"{target_num}_*.md"))
            if target_files:
                target_content = target_files[0].read_text()
                thread_match = re.search(r"\*\*Thread(?:-ID)?:\*\*\s*(.+)", target_content)
                if thread_match:
                    thread_id = thread_match.group(1).strip()

        # If still no thread_id, use the target message id as thread root
        if not thread_id:
            thread_id = request.in_reply_to

    # Update or add In-Reply-To field
    in_reply_pattern = r"\*\*(?:In-Reply-To|Reply-To):\*\*\s*.+"
    in_reply_line = f"**In-Reply-To:** {request.in_reply_to}"

    if re.search(in_reply_pattern, content):
        content = re.sub(in_reply_pattern, in_reply_line, content)
    else:
        # Add after existing metadata fields
        if "**Status:**" in content:
            content = re.sub(r"(\*\*Status:\*\*\s*\w+)", f"\\1\n{in_reply_line}", content)
        elif "**Type:**" in content:
            content = re.sub(r"(\*\*Type:\*\*\s*\w+)", f"\\1\n{in_reply_line}", content)
        elif "**Date:**" in content:
            content = re.sub(r"(\*\*Date:\*\*\s*[\d-]+)", f"\\1\n{in_reply_line}", content)
        else:
            content = re.sub(r"(^#\s+.+$)", f"\\1\n\n{in_reply_line}", content, count=1, flags=re.MULTILINE)

    # Update or add Thread field
    thread_pattern = r"\*\*Thread(?:-ID)?:\*\*\s*.+"
    thread_line = f"**Thread:** {thread_id}"

    if re.search(thread_pattern, content):
        content = re.sub(thread_pattern, thread_line, content)
    else:
        # Add after In-Reply-To
        content = re.sub(
            r"(\*\*(?:In-Reply-To|Reply-To):\*\*\s*.+)",
            f"\\1\n{thread_line}",
            content
        )

    filepath.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Message now replies to '{request.in_reply_to}' in thread '{thread_id}'",
        data={
            "message_id": request.message_id,
            "in_reply_to": request.in_reply_to,
            "thread_id": thread_id
        }
    )


@router.get("/messages/{message_id}/participants")
async def get_message_participants(message_id: str):
    """
    Get all participants in a message's thread for reply-all functionality.

    Returns the original sender, recipient, all CC'd agents, and all participants
    from the thread if the message is part of one.
    """
    # Parse message_id to find the file
    parts = message_id.rsplit("_", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    agent_name = "_".join(parts[:-2])
    direction = parts[-2]
    msg_num = parts[-1]

    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    # Find the message file
    agent_dir = AGENTMAIL_PATH / agent_name / direction
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent directory not found")

    matching_files = list(agent_dir.glob(f"{msg_num}_*.md"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Message not found")

    msg = parse_message_file(matching_files[0], agent_name, direction)
    if not msg:
        raise HTTPException(status_code=404, detail="Could not parse message")

    participants = set()
    participants.add(msg.from_agent)
    participants.add(msg.to_agent)
    if msg.cc:
        participants.update(msg.cc)

    # If in a thread, get all thread participants
    thread_id = msg.thread_id
    if thread_id:
        # Scan all agents for messages in this thread
        for agent_dir in AGENTMAIL_PATH.iterdir():
            if not agent_dir.is_dir() or agent_dir.name in ["status", "notes"]:
                continue
            for subdir in ["to", "from"]:
                subdir_path = agent_dir / subdir
                if subdir_path.exists():
                    for msg_file in subdir_path.glob("*.md"):
                        thread_msg = parse_message_file(msg_file, agent_dir.name, subdir)
                        if thread_msg and thread_msg.thread_id == thread_id:
                            participants.add(thread_msg.from_agent)
                            participants.add(thread_msg.to_agent)
                            if thread_msg.cc:
                                participants.update(thread_msg.cc)

    return {
        "message_id": message_id,
        "thread_id": thread_id,
        "from_agent": msg.from_agent,
        "to_agent": msg.to_agent,
        "cc": msg.cc or [],
        "all_participants": sorted(list(participants)),
        "subject": msg.subject
    }


# ============================================================================
# Agent Status Update Endpoint
# ============================================================================

@router.post("/status/update", response_model=OperationResponse)
async def update_agent_status(request: UpdateStatusRequest):
    """Update an agent's status file."""
    if not _ensure_agent_exists(request.agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_name}' not found")

    status_dir = AGENTMAIL_PATH / "status"
    status_dir.mkdir(parents=True, exist_ok=True)

    status_file = status_dir / f"{request.agent_name}_status.md"
    today = datetime.now().strftime("%Y-%m-%d")

    display_name = request.agent_name.replace("_", " ").title()
    role = request.role or "Agent role not specified"

    # Try to preserve existing role if not specified
    if not request.role and status_file.exists():
        existing = parse_status_file(status_file)
        if existing and existing.role:
            role = existing.role

    content = f"""# {display_name} - Status

**Last Updated:** {today}
**Agent Role:** {role}

---

## COMPLETE
| Component | Location | Notes |
|-----------|----------|-------|
"""
    if request.complete:
        for item in request.complete:
            content += f"| {item.component} | {item.location} | {item.notes} |\n"
    else:
        content += "| - | - | - |\n"

    content += """
## IN PROGRESS
| Component | Location | Notes |
|-----------|----------|-------|
"""
    if request.in_progress:
        for item in request.in_progress:
            content += f"| {item.component} | {item.location} | {item.notes} |\n"
    else:
        content += "| - | - | - |\n"

    content += """
## BLOCKED
| Issue | Waiting On | Notes |
|-------|-----------|-------|
"""
    if request.blocked:
        for item in request.blocked:
            content += f"| {item.issue} | {item.waiting_on} | {item.notes} |\n"
    else:
        content += "| - | - | - |\n"

    content += "\n## NEXT UP\n"
    if request.next_up:
        for i, item in enumerate(request.next_up, 1):
            content += f"{i}. {item}\n"
    else:
        content += "1. No tasks queued\n"

    content += "\n## COORDINATION NOTES\n"
    if request.coordination_notes:
        for note in request.coordination_notes:
            content += f"- {note}\n"
    else:
        content += "- No active coordination\n"

    status_file.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Status updated for {request.agent_name}",
        data={"path": str(status_file), "last_updated": today}
    )


# ============================================================================
# Tuning Notes Endpoints
# ============================================================================

@router.get("/tuning-notes", response_model=list[TuningNote])
async def get_tuning_notes(include_content: bool = False):
    """Get all tuning notes."""
    tuning_dir = AGENTMAIL_PATH / "tuning_notes"
    notes = []

    if tuning_dir.exists():
        for note_file in sorted(tuning_dir.glob("*.md")):
            note = parse_tuning_note(note_file)
            if note:
                if not include_content:
                    note.content = None
                notes.append(note)

    return notes


@router.get("/tuning-notes/{note_id}")
async def get_tuning_note(note_id: str):
    """Get a specific tuning note with full content."""
    tuning_dir = AGENTMAIL_PATH / "tuning_notes"

    for note_file in tuning_dir.glob(f"{note_id}_*.md"):
        note = parse_tuning_note(note_file)
        if note:
            return note

    raise HTTPException(status_code=404, detail="Tuning note not found")


@router.post("/tuning-notes/add", response_model=OperationResponse)
async def add_tuning_note(request: AddTuningNoteRequest):
    """Add a shared tuning note."""
    if request.from_agent != "coordinator" and not _ensure_agent_exists(request.from_agent):
        raise HTTPException(status_code=400, detail=f"Agent '{request.from_agent}' not found")

    tuning_dir = AGENTMAIL_PATH / "tuning_notes"
    tuning_dir.mkdir(parents=True, exist_ok=True)

    # Get next number
    existing = list(tuning_dir.glob("*.md"))
    numbers = []
    for f in existing:
        match = re.match(r"^(\d+)", f.name)
        if match:
            numbers.append(int(match.group(1)))
    next_num = max(numbers) + 1 if numbers else 1

    slug = _slugify(request.topic)
    filename = f"{next_num:03d}_{slug}.md"
    today = datetime.now().strftime("%Y-%m-%d")

    content = f"""# {request.topic}

**Added by:** {request.from_agent}
**Date:** {today}

---

{request.content}
"""

    filepath = tuning_dir / filename
    filepath.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Tuning note '{request.topic}' added",
        data={"filename": filename, "path": str(filepath)}
    )


# ============================================================================
# Per-Agent Notes Endpoints
# ============================================================================

@router.get("/agents/{agent_name}/notes", response_model=list[AgentNote])
async def get_agent_notes(agent_name: str, include_content: bool = False):
    """Get all notes for a specific agent."""
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    notes_dir = AGENTMAIL_PATH / agent_name / "notes"
    notes = []

    if notes_dir.exists():
        for note_file in sorted(notes_dir.glob("*.md")):
            note = parse_agent_note(note_file, agent_name)
            if note:
                if not include_content:
                    note.content = None
                notes.append(note)

    return notes


@router.get("/agents/{agent_name}/notes/{note_id}")
async def get_agent_note(agent_name: str, note_id: str):
    """Get a specific agent note with full content."""
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    notes_dir = AGENTMAIL_PATH / agent_name / "notes"

    # Try exact match first
    note_file = notes_dir / f"{note_id}.md"
    if note_file.exists():
        note = parse_agent_note(note_file, agent_name)
        if note:
            return note

    # Try prefix match
    for note_file in notes_dir.glob(f"{note_id}*.md"):
        note = parse_agent_note(note_file, agent_name)
        if note:
            return note

    raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found for agent '{agent_name}'")


@router.post("/agents/{agent_name}/notes/add", response_model=OperationResponse)
async def add_agent_note(agent_name: str, request: CreateAgentNoteRequest):
    """Add a note for a specific agent."""
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    notes_dir = AGENTMAIL_PATH / agent_name / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Get next note number
    next_num = _get_next_note_number(notes_dir)

    # Create filename from title
    slug = _slugify(request.title)
    filename = f"{next_num}_{slug}.md"
    today = datetime.now().strftime("%Y-%m-%d")

    # Build content
    content = f"""# {request.title}

**Date:** {today}
"""
    if request.tags:
        content += f"**Tags:** {', '.join(request.tags)}\n"
    if request.domain:
        content += f"**Domain:** {request.domain}\n"

    content += f"""
---

{request.content}
"""

    filepath = notes_dir / filename
    filepath.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Note '{request.title}' added for {agent_name}",
        data={"filename": filename, "path": str(filepath), "note_id": f"{next_num}_{slug}"}
    )


@router.delete("/agents/{agent_name}/notes/{note_id}", response_model=OperationResponse)
async def delete_agent_note(agent_name: str, note_id: str):
    """Delete a specific agent note."""
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    notes_dir = AGENTMAIL_PATH / agent_name / "notes"

    # Try exact match first
    note_file = notes_dir / f"{note_id}.md"
    if note_file.exists():
        note_file.unlink()
        return OperationResponse(success=True, message=f"Note '{note_id}' deleted")

    # Try prefix match
    for note_file in notes_dir.glob(f"{note_id}*.md"):
        note_file.unlink()
        return OperationResponse(success=True, message=f"Note '{note_id}' deleted")

    raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found for agent '{agent_name}'")


# ============================================================================
# Quick Briefing Endpoint (Simple Text Summary)
# ============================================================================

@router.get("/briefing/{agent_name}", response_class=PlainTextResponse)
async def get_agent_briefing(agent_name: str):
    """
    Get a quick text briefing for an agent.

    Returns plain text summary of inbox, status, and useful commands.
    Perfect for agents to quickly understand their current state.
    """
    if not _ensure_agent_exists(agent_name):
        return PlainTextResponse(f"Agent '{agent_name}' not found. Create with:\n\ncurl -X POST http://localhost:8000/api/v1/agentmail/agents/create -H 'Content-Type: application/json' -d '{{\"name\": \"{agent_name}\", \"display_name\": \"Your Name\", \"role\": \"Your role\"}}'")

    lines = []
    lines.append(f"=== BRIEFING FOR {agent_name.upper()} ===\n")

    # Get inbox
    inbox = await get_agent_inbox(agent_name, include_content=False)
    inbox_messages = inbox.messages if hasattr(inbox, 'messages') else []

    # Inbox summary
    open_msgs = [m for m in inbox_messages if m.status == "open"]
    in_progress = [m for m in inbox_messages if m.status == "in_progress"]
    blocking = [m for m in inbox_messages if m.severity == "BLOCKING" and m.status not in ["resolved", "closed"]]

    lines.append("INBOX:")
    lines.append(f"  {len(open_msgs)} open, {len(in_progress)} in progress, {len(blocking)} blocking")

    if blocking:
        lines.append("\n  BLOCKING ISSUES:")
        for m in blocking[:3]:
            lines.append(f"    - [{m.id}] {m.subject} (from {m.from_agent})")

    if open_msgs:
        lines.append("\n  RECENT OPEN:")
        for m in open_msgs[:5]:
            lines.append(f"    - [{m.id}] {m.subject} (from {m.from_agent}, type: {m.type})")

    # Plans
    plans_dir = AGENTMAIL_PATH / agent_name / "plans"
    plans = list(plans_dir.glob("*.md")) if plans_dir.exists() else []
    if plans:
        lines.append(f"\nPLANS: {len(plans)} files in plans/")
        for p in sorted(plans)[:3]:
            lines.append(f"    - {p.name}")

    # Notes
    notes_dir = AGENTMAIL_PATH / agent_name / "notes"
    notes = list(notes_dir.glob("*.md")) if notes_dir.exists() else []
    if notes:
        lines.append(f"\nNOTES: {len(notes)} files in notes/")

    # Outbox
    from_dir = AGENTMAIL_PATH / agent_name / "from"
    sent = list(from_dir.glob("*.md")) if from_dir.exists() else []
    lines.append(f"\nOUTBOX: {len(sent)} sent messages")

    # Useful commands
    lines.append("\n" + "=" * 40)
    lines.append("USEFUL COMMANDS:\n")
    lines.append(f"# Get full context (JSON)")
    lines.append(f"curl -s http://localhost:8000/api/v1/agentmail/context/{agent_name}\n")
    lines.append(f"# Read a message")
    lines.append(f"curl -s http://localhost:8000/api/v1/agentmail/messages/MESSAGE_ID\n")
    lines.append(f"# Send a message")
    lines.append(f'curl -X POST http://localhost:8000/api/v1/agentmail/send -H "Content-Type: application/json" -d \'{{"from_agent": "{agent_name}", "to_agent": "TARGET", "subject": "Subject", "message_type": "response", "content": "Message body"}}\'\n')
    lines.append(f"# Update message status")
    lines.append(f'curl -X POST http://localhost:8000/api/v1/agentmail/messages/status -H "Content-Type: application/json" -d \'{{"message_id": "MSG_ID", "status": "in_progress"}}\'\n')
    lines.append(f"# Send heartbeat (mark online)")
    lines.append(f'curl -X POST http://localhost:8000/api/v1/agentmail/heartbeat -H "Content-Type: application/json" -d \'{{"agent_name": "{agent_name}"}}\'\n')
    lines.append(f"# List all agents (who can I message?)")
    lines.append("curl -s http://localhost:8000/api/v1/agentmail/agents/list | python3 -c \"import sys,json; [print(a.get('name','?')+': '+a.get('role','')) for a in json.load(sys.stdin).get('agents',[])]\"")


    lines.append("\n" + "=" * 40)
    lines.append("For full docs: cat agentmail/CLAUDE_AGENT_GUIDE.md")

    return PlainTextResponse("\n".join(lines))


# ============================================================================
# Context Endpoint (For Agents Starting a Session)
# ============================================================================

@router.get("/context/{agent_name}")
async def get_agent_context(agent_name: str):
    """
    Get full context for an agent starting a session.

    Returns:
    - Agent's own info and status
    - Inbox (pending messages/tasks)
    - Outbox (sent messages)
    - Plans (implementation plans from plans/ folder)
    - Briefing with priority items and recommendations
    - Team statuses
    - Per-agent notes
    - Recent tuning notes

    This is the recommended first call when an agent session begins.
    """
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    # Get own info
    own_info = _get_agent_info(agent_name)

    # Get own status
    status_file = AGENTMAIL_PATH / "status" / f"{agent_name}_status.md"
    own_status = parse_status_file(status_file) if status_file.exists() else None

    # Get inbox
    inbox = await get_agent_inbox(agent_name, include_content=True)

    # Build briefing from inbox
    inbox_messages = inbox.messages if hasattr(inbox, 'messages') else []
    briefing = {
        "unread_count": len([m for m in inbox_messages if m.status == "open"]),
        "blocking_items": [
            {"id": m.id, "subject": m.subject, "from": m.from_agent, "severity": m.severity}
            for m in inbox_messages
            if m.severity == "BLOCKING" and m.status not in ["resolved", "closed"]
        ],
        "priority_inbox": [
            {"id": m.id, "subject": m.subject, "from": m.from_agent, "type": m.type}
            for m in inbox_messages[:5]  # Top 5 most recent
            if m.status not in ["resolved", "closed"]
        ],
        "recommended_actions": []
    }

    # Generate recommended actions based on inbox state
    if briefing["blocking_items"]:
        briefing["recommended_actions"].append({
            "action": "Address blocking issues",
            "reason": f"{len(briefing['blocking_items'])} blocking item(s) require attention",
            "priority": "high"
        })
    open_bugs = [m for m in inbox_messages if m.type == "bug" and m.status == "open"]
    if open_bugs:
        briefing["recommended_actions"].append({
            "action": "Review open bugs",
            "reason": f"{len(open_bugs)} open bug(s) in inbox",
            "priority": "medium"
        })
    open_questions = [m for m in inbox_messages if m.type == "question" and m.status == "open"]
    if open_questions:
        briefing["recommended_actions"].append({
            "action": "Answer pending questions",
            "reason": f"{len(open_questions)} unanswered question(s)",
            "priority": "medium"
        })

    # Get all team statuses
    team_statuses = []
    status_dir = AGENTMAIL_PATH / "status"
    if status_dir.exists():
        for sf in status_dir.glob("*_status.md"):
            status = parse_status_file(sf)
            if status:
                team_statuses.append(status)

    # Get per-agent notes
    agent_notes = await get_agent_notes(agent_name, include_content=False)

    # Get tuning notes
    tuning_notes = await get_tuning_notes(include_content=False)

    # Get agent's plans
    plans = []
    plans_dir = AGENTMAIL_PATH / agent_name / "plans"
    if plans_dir.exists():
        for plan_file in sorted(plans_dir.glob("*.md")):
            content = plan_file.read_text()
            # Parse title from first line
            lines = content.strip().split("\n")
            title = lines[0].lstrip("#").strip() if lines else plan_file.stem
            # Get date from file
            date_match = re.search(r'\*\*Date:\*\*\s*(.+)', content)
            date = date_match.group(1).strip() if date_match else None
            plans.append({
                "id": plan_file.stem,
                "filename": plan_file.name,
                "title": title,
                "date": date,
            })

    # Get outbox (sent messages)
    outbox_messages = await get_agent_outbox(agent_name)

    return {
        "agent": agent_name,
        "own_info": own_info.model_dump() if own_info else None,
        "own_status": own_status.model_dump() if own_status else None,
        "inbox": inbox.model_dump(),
        "outbox": [m.model_dump() for m in outbox_messages],
        "plans": plans,
        "briefing": briefing,
        "notes": [n.model_dump() for n in agent_notes],
        "team_statuses": [s.model_dump() for s in team_statuses],
        "tuning_notes": [n.model_dump() for n in tuning_notes],
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# Acknowledge & Heartbeat Endpoints
# ============================================================================

@router.post("/messages/acknowledge", response_model=OperationResponse)
async def acknowledge_message(request: AcknowledgeMessageRequest):
    """
    Acknowledge receipt of a message.

    Tracks per-agent acknowledgments. Multiple agents (To, CC) can acknowledge the same message.
    """
    # Parse message_id to find the file
    parts = request.message_id.rsplit("_", 2)
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    agent_name = "_".join(parts[:-2])
    direction = parts[-2]
    msg_num = parts[-1]

    if direction not in ["to", "from"]:
        raise HTTPException(status_code=400, detail="Invalid message_id format")

    # Find the message file
    agent_dir = AGENTMAIL_PATH / agent_name / direction
    if not agent_dir.exists():
        raise HTTPException(status_code=404, detail="Agent directory not found")

    matching_files = list(agent_dir.glob(f"{msg_num}_*.md"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Message not found")

    filepath = matching_files[0]
    content = filepath.read_text()
    now = datetime.now().isoformat()

    # Parse existing acknowledged_by dict
    acknowledged_by = {}
    ack_by_match = re.search(r"\*\*Acknowledged-By:\*\*\s*(.+)", content)
    if ack_by_match:
        try:
            acknowledged_by = json.loads(ack_by_match.group(1).strip())
        except json.JSONDecodeError:
            acknowledged_by = {}

    # Check if this agent already acknowledged
    if request.agent_name in acknowledged_by:
        return OperationResponse(
            success=True,
            message=f"Already acknowledged by {request.agent_name}",
            data={"message_id": request.message_id, "acknowledged_by": acknowledged_by}
        )

    # Add this agent's acknowledgment
    acknowledged_by[request.agent_name] = now
    ack_by_json = json.dumps(acknowledged_by)

    # Update or add Acknowledged-By line
    if ack_by_match:
        # Update existing
        content = re.sub(
            r"\*\*Acknowledged-By:\*\*\s*.+",
            f"**Acknowledged-By:** {ack_by_json}",
            content
        )
    else:
        # Add new - also add legacy Acknowledged field for first acknowledgment
        ack_lines = f"**Acknowledged:** {now}\n**Acknowledged-By:** {ack_by_json}"

        if "**Status:**" in content:
            content = re.sub(
                r"(\*\*Status:\*\*\s*\w+)",
                f"\\1\n{ack_lines}",
                content
            )
        elif "**Date:**" in content:
            content = re.sub(
                r"(\*\*Date:\*\*\s*[\d-]+(?:\s[\d:]+)?)",
                f"\\1\n{ack_lines}",
                content
            )
        else:
            content = re.sub(
                r"(^#\s+.+$)",
                f"\\1\n\n{ack_lines}",
                content,
                count=1,
                flags=re.MULTILINE
            )

    filepath.write_text(content)

    return OperationResponse(
        success=True,
        message=f"Message acknowledged by {request.agent_name}",
        data={"message_id": request.message_id, "acknowledged_at": now, "acknowledged_by": acknowledged_by}
    )


@router.post("/heartbeat", response_model=OperationResponse)
async def send_heartbeat(request: HeartbeatRequest):
    """
    Update agent's online status with a heartbeat.

    Should be called periodically (e.g., every 60 seconds) to indicate agent is active.
    """
    if not _ensure_agent_exists(request.agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_name}' not found")

    config_file = AGENTMAIL_PATH / request.agent_name / "agent.json"
    now = datetime.now().isoformat()

    if config_file.exists():
        try:
            config = json.loads(config_file.read_text())
        except:
            config = {}
    else:
        config = {
            "name": request.agent_name,
            "display_name": request.agent_name.replace("_", " ").title(),
            "role": ""
        }

    config["last_heartbeat"] = now
    config_file.write_text(json.dumps(config, indent=2))

    return OperationResponse(
        success=True,
        message=f"Heartbeat recorded for {request.agent_name}",
        data={"agent": request.agent_name, "heartbeat": now}
    )


# ============================================================================
# Quick Poll Endpoint
# ============================================================================

@router.get("/inbox/{agent_name}/since/{timestamp}")
async def get_messages_since(agent_name: str, timestamp: str, include_content: bool = False):
    """
    Quick poll for new messages since a given timestamp.

    Use this for efficient polling instead of fetching full context.

    Args:
        agent_name: The agent to check
        timestamp: ISO format timestamp (e.g., "2024-01-15T10:30:00")
        include_content: Include full message content

    Returns:
        New messages since the timestamp, with count.
    """
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    # Parse timestamp
    try:
        since_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO format.")

    to_dir = AGENTMAIL_PATH / agent_name / "to"
    new_messages = []

    if to_dir.exists():
        for msg_file in to_dir.glob("*.md"):
            file_mtime = datetime.fromtimestamp(msg_file.stat().st_mtime)
            if file_mtime > since_time:
                msg = parse_message_file(msg_file, agent_name, "to")
                if msg:
                    if not include_content:
                        msg.content = None
                    new_messages.append(msg)

    # Sort by date, newest first
    new_messages.sort(key=lambda m: m.date, reverse=True)

    return {
        "agent": agent_name,
        "since": timestamp,
        "new_count": len(new_messages),
        "messages": [m.model_dump() for m in new_messages],
        "checked_at": datetime.now().isoformat()
    }


# ============================================================================
# Thread Endpoint
# ============================================================================

@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    """
    Get all messages in a thread with enhanced metadata.

    Returns:
    - root_message: The first message in the thread
    - messages: All messages in chronological order
    - participants: List of unique agents involved
    - reply_tree: Nested structure for UI rendering
    """
    data = await get_dashboard_data()

    # Get all messages with this thread_id
    thread_messages = [m for m in data["messages"] if m.get("thread_id") == thread_id]

    # Sort chronologically
    thread_messages.sort(key=lambda m: m.get("date", ""))

    if not thread_messages:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    # Find the root message (first message or one without in_reply_to)
    root_message = None
    for msg in thread_messages:
        if not msg.get("in_reply_to"):
            root_message = msg
            break
    if not root_message:
        root_message = thread_messages[0]

    # Get unique participants
    participants = list(set(
        [msg.get("from_agent") for msg in thread_messages] +
        [msg.get("to_agent") for msg in thread_messages]
    ))
    participants = [p for p in participants if p]  # Remove None values

    # Build reply tree (nested structure)
    def build_reply_tree(messages: list, parent_id: Optional[str] = None) -> list:
        """Build nested reply structure."""
        children = []
        for msg in messages:
            msg_reply_to = msg.get("in_reply_to")
            # Root level: no in_reply_to or in_reply_to not in thread
            if parent_id is None:
                if not msg_reply_to or not any(m.get("id") == msg_reply_to for m in messages):
                    children.append({
                        **msg,
                        "replies": build_reply_tree(messages, msg.get("id"))
                    })
            # Nested level: in_reply_to matches parent_id
            elif msg_reply_to == parent_id:
                children.append({
                    **msg,
                    "replies": build_reply_tree(messages, msg.get("id"))
                })
        return children

    reply_tree = build_reply_tree(thread_messages)

    return {
        "thread_id": thread_id,
        "root_message": root_message,
        "message_count": len(thread_messages),
        "messages": thread_messages,
        "participants": participants,
        "reply_tree": reply_tree
    }


# ============================================================================
# File Preview Endpoint
# ============================================================================

# Project root for file path validation
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# File extension to language mapping
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".css": "css",
    ".html": "html",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".sql": "sql",
    ".rs": "rust",
    ".go": "go",
}


@router.get("/file-preview")
async def get_file_preview(
    path: str = Query(..., description="File path relative to project root"),
    start_line: Optional[int] = Query(None, description="Start line (1-indexed)"),
    end_line: Optional[int] = Query(None, description="End line (1-indexed)"),
):
    """
    Get a preview of a file's contents with optional line range.

    Security: Validates path is within project directory.
    Returns file content with detected language for syntax highlighting.
    """
    # Resolve the path
    if path.startswith("/"):
        # Absolute path - must be within project
        file_path = Path(path)
    else:
        # Relative path - relative to project root
        file_path = PROJECT_ROOT / path

    # Security: Ensure path is within project directory
    try:
        file_path = file_path.resolve()
        PROJECT_ROOT.resolve()
        if not str(file_path).startswith(str(PROJECT_ROOT.resolve())):
            raise HTTPException(status_code=403, detail="Path outside project directory")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid path")

    # Check file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Detect language from extension
    ext = file_path.suffix.lower()
    language = EXTENSION_TO_LANGUAGE.get(ext, "text")

    # Read file content
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not text")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

    # Extract line range if specified
    lines = content.split("\n")
    total_lines = len(lines)

    if start_line is not None or end_line is not None:
        start = max(1, start_line or 1) - 1  # Convert to 0-indexed
        end = min(total_lines, end_line or total_lines)
        lines = lines[start:end]
        content = "\n".join(lines)

    return {
        "path": str(file_path.relative_to(PROJECT_ROOT)),
        "language": language,
        "content": content,
        "total_lines": total_lines,
        "start_line": start_line or 1,
        "end_line": end_line or total_lines,
    }


# ============================================================================
# Search Endpoint
# ============================================================================

@router.post("/search")
async def search_agentmail(request: SearchRequest):
    """
    Search across AgentMail content: messages, notes, status, tuning.

    Returns results sorted by relevance with highlighted matches.
    """
    query = request.query.lower()
    results = []

    # Search messages
    if "messages" in request.scope:
        data = await get_dashboard_data()
        for msg in data.get("messages", []):
            # Apply filters
            if request.agent and msg.get("to_agent") != request.agent and msg.get("from_agent") != request.agent:
                continue
            if request.message_type and msg.get("type") != request.message_type:
                continue
            if request.severity and msg.get("severity") != request.severity:
                continue
            if request.date_from and msg.get("date", "") < request.date_from:
                continue
            if request.date_to and msg.get("date", "") > request.date_to:
                continue

            # Search in subject and preview
            subject = (msg.get("subject") or "").lower()
            preview = (msg.get("preview") or "").lower()
            score = 0
            matches = []

            if query in subject:
                score += 3
                matches.append(f"subject: ...{msg.get('subject')}...")
            if query in preview:
                score += 1
                # Find matching snippet
                idx = preview.find(query)
                start = max(0, idx - 40)
                end = min(len(preview), idx + len(query) + 40)
                matches.append(f"content: ...{preview[start:end]}...")

            if score > 0:
                results.append({
                    "type": "message",
                    "id": msg.get("id"),
                    "title": msg.get("subject"),
                    "subtitle": f"{msg.get('from_agent')} → {msg.get('to_agent')}",
                    "date": msg.get("date"),
                    "matches": matches,
                    "score": score,
                    "metadata": {
                        "message_type": msg.get("type"),
                        "severity": msg.get("severity"),
                        "status": msg.get("status"),
                    }
                })

    # Search notes
    if "notes" in request.scope:
        agents = _get_valid_agents()
        for agent in agents:
            if request.agent and agent != request.agent:
                continue

            notes_dir = AGENTMAIL_PATH / agent / "notes"
            if notes_dir.exists():
                for note_file in notes_dir.glob("*.md"):
                    note = parse_agent_note(note_file, agent)
                    if not note:
                        continue

                    title = (note.title or "").lower()
                    content = (note.content or "").lower()
                    score = 0
                    matches = []

                    if query in title:
                        score += 3
                        matches.append(f"title: {note.title}")
                    if query in content:
                        score += 1
                        idx = content.find(query)
                        start = max(0, idx - 40)
                        end = min(len(content), idx + len(query) + 40)
                        matches.append(f"content: ...{note.content[start:end]}...")

                    if score > 0:
                        results.append({
                            "type": "note",
                            "id": f"{agent}/{note.id}",
                            "title": note.title,
                            "subtitle": f"{agent}'s note",
                            "date": note.date,
                            "matches": matches,
                            "score": score,
                            "metadata": {
                                "agent": agent,
                                "tags": note.tags,
                                "domain": note.domain,
                            }
                        })

    # Search tuning notes
    if "tuning" in request.scope:
        tuning_dir = AGENTMAIL_PATH / "tuning_notes"
        if tuning_dir.exists():
            for note_file in tuning_dir.glob("*.md"):
                note = parse_tuning_note(note_file)
                if not note:
                    continue

                topic = (note.topic or "").lower()
                content = (note.content or "").lower()
                score = 0
                matches = []

                if query in topic:
                    score += 3
                    matches.append(f"topic: {note.topic}")
                if query in content:
                    score += 1
                    idx = content.find(query)
                    start = max(0, idx - 40)
                    end = min(len(content), idx + len(query) + 40)
                    matches.append(f"content: ...{note.content[start:end]}...")

                if score > 0:
                    results.append({
                        "type": "tuning",
                        "id": note.id,
                        "title": note.topic,
                        "subtitle": f"Added by {note.added_by}" if note.added_by else "Tuning note",
                        "date": note.date,
                        "matches": matches,
                        "score": score,
                        "metadata": {
                            "added_by": note.added_by,
                        }
                    })

    # Search status files
    if "status" in request.scope:
        status_dir = AGENTMAIL_PATH / "status"
        if status_dir.exists():
            for status_file in status_dir.glob("*_status.md"):
                if request.agent and request.agent not in status_file.name:
                    continue

                try:
                    content = status_file.read_text().lower()
                    agent_name = status_file.stem.replace("_status", "")

                    if query in content:
                        idx = content.find(query)
                        start = max(0, idx - 40)
                        end = min(len(content), idx + len(query) + 40)

                        results.append({
                            "type": "status",
                            "id": agent_name,
                            "title": f"{agent_name} Status",
                            "subtitle": "Agent status file",
                            "date": datetime.fromtimestamp(status_file.stat().st_mtime).strftime("%Y-%m-%d"),
                            "matches": [f"content: ...{content[start:end]}..."],
                            "score": 1,
                            "metadata": {
                                "agent": agent_name,
                            }
                        })
                except Exception:
                    continue

    # Sort by score descending, then by date
    results.sort(key=lambda r: (-r["score"], r.get("date", "") or ""), reverse=False)

    return {
        "query": request.query,
        "total_results": len(results),
        "results": results[:request.limit]
    }


# ============================================================================
# Kanban Board Endpoint
# ============================================================================

@router.get("/kanban")
async def get_kanban_board(agent: Optional[str] = None):
    """
    Get messages grouped by status for Kanban board view.

    Returns messages in columns: open, in_progress, resolved, closed.
    Optionally filter by agent.
    """
    data = await get_dashboard_data()
    messages = data.get("messages", [])

    # Filter by agent if specified
    if agent:
        messages = [
            m for m in messages
            if m.get("to_agent") == agent or m.get("from_agent") == agent
        ]

    # Group by status
    columns = {
        "open": [],
        "in_progress": [],
        "resolved": [],
        "closed": []
    }

    for msg in messages:
        status = msg.get("status", "open")
        if status in columns:
            columns[status].append({
                "id": msg.get("id"),
                "subject": msg.get("subject"),
                "from_agent": msg.get("from_agent"),
                "to_agent": msg.get("to_agent"),
                "type": msg.get("type"),
                "severity": msg.get("severity"),
                "date": msg.get("date"),
                "thread_id": msg.get("thread_id"),
            })

    # Sort each column by date (most recent first)
    for status in columns:
        columns[status].sort(key=lambda m: m.get("date", ""), reverse=True)

    return {
        "columns": columns,
        "total": len(messages),
        "counts": {status: len(items) for status, items in columns.items()}
    }


# ============================================================================
# Scheduled Messages Endpoints
# ============================================================================

def _get_next_scheduled_number(agent_dir: Path) -> str:
    """Get the next scheduled message number for an agent."""
    scheduled_dir = agent_dir / "scheduled"
    if not scheduled_dir.exists():
        scheduled_dir.mkdir(parents=True, exist_ok=True)
        return "001"

    existing = list(scheduled_dir.glob("*.json"))
    if not existing:
        return "001"

    numbers = []
    for f in existing:
        match = re.match(r"^(\d+)", f.name)
        if match:
            numbers.append(int(match.group(1)))

    next_num = max(numbers) + 1 if numbers else 1
    return f"{next_num:03d}"


def _parse_scheduled_message(filepath: Path) -> Optional[ScheduledMessage]:
    """Parse a scheduled message JSON file."""
    if not filepath.exists():
        return None
    try:
        data = json.loads(filepath.read_text())
        return ScheduledMessage(**data)
    except Exception:
        return None


@router.post("/schedule", response_model=ScheduledMessageResponse)
async def schedule_message(request: ScheduleMessageRequest):
    """
    Schedule a message for later delivery.

    Either send_at (for time-based) or remind_after_minutes (for reminders) must be provided.
    """
    # Validate at least one scheduling option
    if not request.send_at and not request.remind_after_minutes:
        raise HTTPException(
            status_code=400,
            detail="Either send_at or remind_after_minutes must be provided"
        )

    # Validate sender exists
    if request.from_agent != "coordinator" and not _ensure_agent_exists(request.from_agent):
        raise HTTPException(status_code=400, detail=f"Sender '{request.from_agent}' not found")

    # Validate recipient exists
    if not _ensure_agent_exists(request.to_agent):
        raise HTTPException(status_code=400, detail=f"Recipient '{request.to_agent}' not found")

    # Create scheduled directory for sender
    sender_dir = AGENTMAIL_PATH / request.from_agent
    scheduled_dir = sender_dir / "scheduled"
    scheduled_dir.mkdir(parents=True, exist_ok=True)

    # Generate ID and filename
    msg_num = _get_next_scheduled_number(sender_dir)
    scheduled_id = f"{request.from_agent}_scheduled_{msg_num}"
    filename = f"{msg_num}_scheduled.json"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Build scheduled message data
    scheduled_data = {
        "id": scheduled_id,
        "from_agent": request.from_agent,
        "to_agent": request.to_agent,
        "cc": request.cc,
        "subject": request.subject,
        "message_type": request.message_type,
        "severity": request.severity,
        "content": request.content,
        "in_reply_to": request.in_reply_to,
        "thread_id": request.thread_id,
        "send_at": request.send_at,
        "remind_after_minutes": request.remind_after_minutes,
        "original_message_id": request.in_reply_to,  # Track for reminder replies
        "created_at": timestamp,
        "status": "pending"
    }

    # Write to file
    (scheduled_dir / filename).write_text(json.dumps(scheduled_data, indent=2))

    return ScheduledMessageResponse(
        success=True,
        scheduled_id=scheduled_id,
        send_at=request.send_at,
        remind_after_minutes=request.remind_after_minutes
    )


@router.get("/scheduled/{agent_name}", response_model=ScheduledListResponse)
async def get_scheduled_messages(agent_name: str):
    """
    Get all scheduled messages for an agent.

    Returns pending scheduled messages for the specified agent.
    """
    if not _ensure_agent_exists(agent_name):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    scheduled_dir = AGENTMAIL_PATH / agent_name / "scheduled"
    scheduled_list = []

    if scheduled_dir.exists():
        for filepath in scheduled_dir.glob("*.json"):
            msg = _parse_scheduled_message(filepath)
            if msg and msg.status == "pending":
                scheduled_list.append(msg)

    # Sort by send_at or created_at
    scheduled_list.sort(key=lambda m: m.send_at or m.created_at)

    return ScheduledListResponse(
        agent=agent_name,
        scheduled=scheduled_list,
        total=len(scheduled_list)
    )


@router.delete("/scheduled/{scheduled_id}", response_model=OperationResponse)
async def cancel_scheduled_message(scheduled_id: str):
    """
    Cancel a scheduled message.

    Marks the scheduled message as cancelled.
    """
    # Parse scheduled_id to find the file (format: agent_scheduled_number)
    parts = scheduled_id.rsplit("_", 2)
    if len(parts) < 3 or parts[-2] != "scheduled":
        raise HTTPException(status_code=400, detail="Invalid scheduled_id format")

    agent_name = "_".join(parts[:-2])
    msg_num = parts[-1]

    scheduled_dir = AGENTMAIL_PATH / agent_name / "scheduled"
    if not scheduled_dir.exists():
        raise HTTPException(status_code=404, detail="Scheduled message not found")

    # Find the file
    matching_files = list(scheduled_dir.glob(f"{msg_num}_scheduled.json"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Scheduled message not found")

    filepath = matching_files[0]
    msg = _parse_scheduled_message(filepath)
    if not msg:
        raise HTTPException(status_code=404, detail="Scheduled message not found")

    # Update status to cancelled
    data = json.loads(filepath.read_text())
    data["status"] = "cancelled"
    filepath.write_text(json.dumps(data, indent=2))

    return OperationResponse(
        success=True,
        message=f"Scheduled message {scheduled_id} cancelled"
    )


@router.post("/scheduled/process", response_model=OperationResponse)
async def process_scheduled_messages():
    """
    Process all due scheduled messages.

    Sends any scheduled messages that are due and marks them as sent.
    Should be called periodically (e.g., on dashboard load).
    """
    now = datetime.now()
    processed = 0
    errors = []

    # Scan all agents for scheduled messages
    if not AGENTMAIL_PATH.exists():
        return OperationResponse(success=True, message="No messages to process", data={"processed": 0})

    for agent_dir in AGENTMAIL_PATH.iterdir():
        if not agent_dir.is_dir() or agent_dir.name in ["status", "tuning_notes", "__pycache__"]:
            continue

        scheduled_dir = agent_dir / "scheduled"
        if not scheduled_dir.exists():
            continue

        for filepath in scheduled_dir.glob("*.json"):
            try:
                msg = _parse_scheduled_message(filepath)
                if not msg or msg.status != "pending":
                    continue

                should_send = False

                # Check time-based scheduling
                if msg.send_at:
                    try:
                        send_time = datetime.fromisoformat(msg.send_at)
                        if now >= send_time:
                            should_send = True
                    except ValueError:
                        errors.append(f"Invalid send_at format for {msg.id}")
                        continue

                # Check reminder-based scheduling
                if msg.remind_after_minutes and msg.original_message_id:
                    try:
                        created_time = datetime.fromisoformat(msg.created_at)
                        remind_after = created_time + timedelta(minutes=msg.remind_after_minutes)

                        if now >= remind_after:
                            # Check if there's a reply to the original message
                            has_reply = _check_for_reply(msg.original_message_id, msg.thread_id)
                            if not has_reply:
                                should_send = True
                                # Update subject to indicate reminder
                                if not msg.subject.startswith("[Reminder]"):
                                    msg.subject = f"[Reminder] {msg.subject}"
                    except ValueError:
                        errors.append(f"Invalid created_at format for {msg.id}")
                        continue

                if should_send:
                    # Send the message using existing send_message logic
                    send_request = SendMessageRequest(
                        from_agent=msg.from_agent,
                        to_agent=msg.to_agent,
                        cc=msg.cc,
                        subject=msg.subject,
                        message_type=msg.message_type,
                        severity=msg.severity,
                        content=msg.content,
                        in_reply_to=msg.in_reply_to,
                        thread_id=msg.thread_id
                    )
                    await send_message(send_request)

                    # Update status to sent
                    data = json.loads(filepath.read_text())
                    data["status"] = "sent"
                    data["sent_at"] = now.strftime("%Y-%m-%dT%H:%M:%S")
                    filepath.write_text(json.dumps(data, indent=2))

                    processed += 1

            except Exception as e:
                errors.append(f"Error processing {filepath.name}: {str(e)}")

    return OperationResponse(
        success=True,
        message=f"Processed {processed} scheduled messages",
        data={"processed": processed, "errors": errors if errors else None}
    )


def _check_for_reply(original_message_id: str, thread_id: Optional[str]) -> bool:
    """Check if there's a reply to the original message or in the thread."""
    if not AGENTMAIL_PATH.exists():
        return False

    # Search all agent inboxes for replies
    for agent_dir in AGENTMAIL_PATH.iterdir():
        if not agent_dir.is_dir() or agent_dir.name in ["status", "tuning_notes", "__pycache__"]:
            continue

        # Check to/from folders
        for direction in ["to", "from"]:
            msg_dir = agent_dir / direction
            if not msg_dir.exists():
                continue

            for msg_file in msg_dir.glob("*.md"):
                content = msg_file.read_text()

                # Check if this message replies to the original
                if f"**In-Reply-To:** {original_message_id}" in content:
                    return True

                # Check if this message is in the same thread (and is a different message)
                if thread_id and f"**Thread:** {thread_id}" in content:
                    # Make sure it's not the original message
                    if f"_{original_message_id.split('_')[-1]}" not in msg_file.name:
                        return True

    return False

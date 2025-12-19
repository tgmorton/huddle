"""
AgentMail SDK - Simple Python client for inter-agent communication.

This SDK allows AI agents to communicate with each other through the AgentMail API.

Usage:
    from agentmail.sdk import AgentMailClient

    # Initialize with your agent identity
    client = AgentMailClient("qa_agent")

    # Check your inbox
    inbox = client.get_inbox()
    for msg in inbox['messages']:
        print(f"From {msg['from_agent']}: {msg['subject']}")

    # Send a message
    client.send_message(
        to_agent="live_sim_agent",
        subject="Bug found in pursuit system",
        message_type="bug",
        severity="MAJOR",
        content="## Summary\\n\\nThe pursuit angles are not being calculated..."
    )

    # Update your status
    client.update_status(
        in_progress=[{"component": "Pursuit bug", "location": "db_brain.py", "notes": "Investigating"}],
        next_up=["Test tackle resolution", "Check route waypoints"]
    )
"""

import requests
from typing import Optional, Literal
from dataclasses import dataclass


@dataclass
class AgentMailClient:
    """Client for interacting with the AgentMail API."""

    agent_name: str
    base_url: str = "http://localhost:8000/api/v1/agentmail"

    def get_context(self) -> dict:
        """
        Get full context for starting a session.

        Returns your inbox, current status, all team statuses, and tuning notes.
        This is the recommended first call when starting work.
        """
        response = requests.get(f"{self.base_url}/context/{self.agent_name}")
        response.raise_for_status()
        return response.json()

    def get_inbox(self) -> dict:
        """Get messages addressed to this agent."""
        response = requests.get(f"{self.base_url}/inbox/{self.agent_name}")
        response.raise_for_status()
        return response.json()

    def get_outbox(self) -> list:
        """Get messages sent by this agent."""
        response = requests.get(f"{self.base_url}/outbox/{self.agent_name}")
        response.raise_for_status()
        return response.json()

    def send_message(
        self,
        to_agent: str,
        subject: str,
        content: str,
        message_type: Literal["task", "response", "bug", "plan", "handoff", "question"] = "response",
        severity: Optional[Literal["BLOCKING", "MAJOR", "MINOR", "INFO"]] = None,
    ) -> dict:
        """
        Send a message to another agent.

        Args:
            to_agent: Target agent name (e.g., 'live_sim_agent')
            subject: Message subject/title
            content: Full message content in markdown
            message_type: Type of message (task, response, bug, plan, handoff, question)
            severity: Severity level for bugs (BLOCKING, MAJOR, MINOR, INFO)
        """
        payload = {
            "from_agent": self.agent_name,
            "to_agent": to_agent,
            "subject": subject,
            "message_type": message_type,
            "content": content,
        }
        if severity:
            payload["severity"] = severity

        response = requests.post(f"{self.base_url}/send", json=payload)
        response.raise_for_status()
        return response.json()

    def update_status(
        self,
        role: Optional[str] = None,
        complete: Optional[list[dict]] = None,
        in_progress: Optional[list[dict]] = None,
        blocked: Optional[list[dict]] = None,
        next_up: Optional[list[str]] = None,
        coordination_notes: Optional[list[str]] = None,
    ) -> dict:
        """
        Update this agent's status.

        Args:
            role: Agent role description
            complete: List of {"component": str, "location": str, "notes": str}
            in_progress: List of {"component": str, "location": str, "notes": str}
            blocked: List of {"issue": str, "waiting_on": str, "notes": str}
            next_up: List of next task strings
            coordination_notes: List of coordination note strings
        """
        payload = {"agent_name": self.agent_name}
        if role:
            payload["role"] = role
        if complete:
            payload["complete"] = complete
        if in_progress:
            payload["in_progress"] = in_progress
        if blocked:
            payload["blocked"] = blocked
        if next_up:
            payload["next_up"] = next_up
        if coordination_notes:
            payload["coordination_notes"] = coordination_notes

        response = requests.post(f"{self.base_url}/status/update", json=payload)
        response.raise_for_status()
        return response.json()

    def add_tuning_note(self, topic: str, content: str) -> dict:
        """
        Add a shared tuning note visible to all agents.

        Args:
            topic: Note topic/title
            content: Note content in markdown
        """
        payload = {
            "from_agent": self.agent_name,
            "topic": topic,
            "content": content,
        }
        response = requests.post(f"{self.base_url}/tuning-notes/add", json=payload)
        response.raise_for_status()
        return response.json()

    def get_dashboard(self) -> dict:
        """Get full dashboard data (all agents, messages, tuning notes)."""
        response = requests.get(f"{self.base_url}/dashboard")
        response.raise_for_status()
        return response.json()

    def get_all_messages(
        self,
        agent: Optional[str] = None,
        msg_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> list:
        """Get all messages with optional filtering."""
        params = {}
        if agent:
            params["agent"] = agent
        if msg_type:
            params["type"] = msg_type
        if severity:
            params["severity"] = severity

        response = requests.get(f"{self.base_url}/messages", params=params)
        response.raise_for_status()
        return response.json()


# Convenience functions for quick usage
def quick_send(
    from_agent: str,
    to_agent: str,
    subject: str,
    content: str,
    message_type: str = "response",
    severity: Optional[str] = None,
) -> dict:
    """Quick function to send a message without creating a client."""
    client = AgentMailClient(from_agent)
    return client.send_message(to_agent, subject, content, message_type, severity)


def quick_status(agent_name: str, **kwargs) -> dict:
    """Quick function to update status without creating a client."""
    client = AgentMailClient(agent_name)
    return client.update_status(**kwargs)


# Example usage
if __name__ == "__main__":
    # Demo: QA Agent session
    print("=== QA Agent Session Demo ===\n")

    qa = AgentMailClient("qa_agent")

    # Get context
    print("1. Getting context...")
    try:
        ctx = qa.get_context()
        print(f"   Inbox: {ctx['inbox']['unread_count']} messages")
        print(f"   Team statuses: {len(ctx['team_statuses'])} agents")
        print(f"   Tuning notes: {len(ctx['tuning_notes'])} notes")
    except requests.exceptions.ConnectionError:
        print("   (API not running - showing example usage)")

    # Example of what sending a bug report would look like
    print("\n2. Example bug report (not sent):")
    print("""
    qa.send_message(
        to_agent="live_sim_agent",
        subject="Bug: Pursuit angles not calculating",
        message_type="bug",
        severity="MAJOR",
        content='''## Summary
The pursuit system is not calculating intercept angles after a catch.

## Steps to Reproduce
1. Run test_passing_integration.py multi
2. Observe defender behavior after catch

## Expected
Defenders should calculate pursuit angles to intercept the ballcarrier.

## Actual
Defenders target current position, never closing the gap.
'''
    )
    """)

    print("\n3. Example status update (not sent):")
    print("""
    qa.update_status(
        role="Quality assurance, integration testing",
        in_progress=[
            {"component": "Pursuit bug", "location": "db_brain.py", "notes": "Root cause found"}
        ],
        next_up=["Test fix", "Run regression suite"],
        coordination_notes=["Working with live_sim_agent on fix"]
    )
    """)

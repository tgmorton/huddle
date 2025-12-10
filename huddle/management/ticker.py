"""
News Ticker System.

The ticker is the scrolling news feed at the bottom of the screen.
It shows interesting but non-critical information about the league:
- Player signings and releases
- Trade completions
- Game scores
- Injury updates
- Rumors and speculation

Items flow through the ticker and age out over time.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional
from uuid import UUID, uuid4


class TickerCategory(Enum):
    """Categories for ticker items."""

    # Transactions
    SIGNING = auto()  # Player signed
    RELEASE = auto()  # Player released
    TRADE = auto()  # Trade completed
    WAIVER = auto()  # Waiver claim

    # Games
    SCORE = auto()  # Game score/result
    INJURY = auto()  # In-game injury

    # Personnel
    INJURY_REPORT = auto()  # Injury status update
    SUSPENSION = auto()  # Player suspended
    RETIREMENT = auto()  # Player retired
    HOLDOUT = auto()  # Contract holdout

    # Draft
    DRAFT_PICK = auto()  # Draft selection
    DRAFT_TRADE = auto()  # Draft day trade

    # League
    DEADLINE = auto()  # Deadline reminder
    RECORD = auto()  # Record broken
    AWARD = auto()  # Award winner

    # Rumors
    RUMOR = auto()  # Speculation/rumor

    @property
    def icon(self) -> str:
        """Get icon for this category."""
        icons = {
            TickerCategory.SIGNING: "pen",
            TickerCategory.RELEASE: "user-minus",
            TickerCategory.TRADE: "exchange",
            TickerCategory.WAIVER: "clipboard",
            TickerCategory.SCORE: "football",
            TickerCategory.INJURY: "ambulance",
            TickerCategory.INJURY_REPORT: "medical",
            TickerCategory.SUSPENSION: "ban",
            TickerCategory.RETIREMENT: "flag",
            TickerCategory.HOLDOUT: "hand",
            TickerCategory.DRAFT_PICK: "graduation-cap",
            TickerCategory.DRAFT_TRADE: "exchange",
            TickerCategory.DEADLINE: "clock",
            TickerCategory.RECORD: "star",
            TickerCategory.AWARD: "trophy",
            TickerCategory.RUMOR: "question",
        }
        return icons.get(self, "info")

    @property
    def color(self) -> str:
        """Get color identifier for this category."""
        colors = {
            TickerCategory.SIGNING: "green",
            TickerCategory.RELEASE: "red",
            TickerCategory.TRADE: "blue",
            TickerCategory.WAIVER: "gray",
            TickerCategory.SCORE: "yellow",
            TickerCategory.INJURY: "red",
            TickerCategory.INJURY_REPORT: "orange",
            TickerCategory.SUSPENSION: "red",
            TickerCategory.RETIREMENT: "purple",
            TickerCategory.HOLDOUT: "orange",
            TickerCategory.DRAFT_PICK: "green",
            TickerCategory.DRAFT_TRADE: "blue",
            TickerCategory.DEADLINE: "yellow",
            TickerCategory.RECORD: "gold",
            TickerCategory.AWARD: "gold",
            TickerCategory.RUMOR: "gray",
        }
        return colors.get(self, "white")


@dataclass
class TickerItem:
    """
    A single item in the news ticker.

    Ticker items are short text snippets that scroll across the bottom
    of the screen. They provide ambient information about league happenings.
    """

    id: UUID = field(default_factory=uuid4)

    # Content
    category: TickerCategory = TickerCategory.RUMOR
    headline: str = ""  # Short headline text (shown in ticker)
    detail: str = ""  # Longer detail (shown on hover/click)

    # Timing
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None  # When to remove from ticker

    # Relevance
    is_breaking: bool = False  # Should be highlighted
    priority: int = 0  # Higher = more prominent (0-10)

    # Related entities
    team_ids: list[UUID] = field(default_factory=list)
    player_ids: list[UUID] = field(default_factory=list)

    # Interaction
    is_read: bool = False  # Has user seen this
    is_clickable: bool = False  # Can click for more info
    link_event_id: Optional[UUID] = None  # Link to management event

    @property
    def age_seconds(self) -> float:
        """Get age of this item in seconds."""
        return (datetime.now() - self.timestamp).total_seconds()

    @property
    def age_display(self) -> str:
        """Get human-readable age string."""
        age = datetime.now() - self.timestamp
        if age < timedelta(minutes=1):
            return "Just now"
        elif age < timedelta(hours=1):
            mins = int(age.total_seconds() / 60)
            return f"{mins}m ago"
        elif age < timedelta(days=1):
            hours = int(age.total_seconds() / 3600)
            return f"{hours}h ago"
        else:
            days = age.days
            return f"{days}d ago"

    @property
    def is_expired(self) -> bool:
        """Check if item has expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "id": str(self.id),
            "category": self.category.name,
            "headline": self.headline,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_breaking": self.is_breaking,
            "priority": self.priority,
            "team_ids": [str(tid) for tid in self.team_ids],
            "player_ids": [str(pid) for pid in self.player_ids],
            "is_read": self.is_read,
            "is_clickable": self.is_clickable,
            "link_event_id": str(self.link_event_id) if self.link_event_id else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TickerItem":
        """Create from dictionary."""
        return cls(
            id=UUID(data["id"]) if data.get("id") else uuid4(),
            category=TickerCategory[data.get("category", "RUMOR")],
            headline=data.get("headline", ""),
            detail=data.get("detail", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            is_breaking=data.get("is_breaking", False),
            priority=data.get("priority", 0),
            team_ids=[UUID(tid) for tid in data.get("team_ids", [])],
            player_ids=[UUID(pid) for pid in data.get("player_ids", [])],
            is_read=data.get("is_read", False),
            is_clickable=data.get("is_clickable", False),
            link_event_id=UUID(data["link_event_id"]) if data.get("link_event_id") else None,
        )


# === Factory functions for common ticker items ===


def ticker_signing(
    player_name: str,
    team_name: str,
    position: str,
    team_id: Optional[UUID] = None,
    player_id: Optional[UUID] = None,
    is_major: bool = False,
) -> TickerItem:
    """Create a player signing ticker item."""
    return TickerItem(
        category=TickerCategory.SIGNING,
        headline=f"{team_name} sign {position} {player_name}",
        detail=f"The {team_name} have signed {position} {player_name}.",
        is_breaking=is_major,
        priority=7 if is_major else 3,
        team_ids=[team_id] if team_id else [],
        player_ids=[player_id] if player_id else [],
        expires_at=datetime.now() + timedelta(hours=12),
    )


def ticker_release(
    player_name: str,
    team_name: str,
    position: str,
    team_id: Optional[UUID] = None,
    player_id: Optional[UUID] = None,
) -> TickerItem:
    """Create a player release ticker item."""
    return TickerItem(
        category=TickerCategory.RELEASE,
        headline=f"{team_name} release {position} {player_name}",
        detail=f"The {team_name} have released {position} {player_name}.",
        priority=2,
        team_ids=[team_id] if team_id else [],
        player_ids=[player_id] if player_id else [],
        expires_at=datetime.now() + timedelta(hours=6),
    )


def ticker_trade(
    team1_name: str,
    team2_name: str,
    summary: str,
    team1_id: Optional[UUID] = None,
    team2_id: Optional[UUID] = None,
    player_ids: Optional[list[UUID]] = None,
    is_blockbuster: bool = False,
) -> TickerItem:
    """Create a trade ticker item."""
    return TickerItem(
        category=TickerCategory.TRADE,
        headline=f"TRADE: {team1_name} - {team2_name}",
        detail=summary,
        is_breaking=is_blockbuster,
        priority=8 if is_blockbuster else 5,
        team_ids=[tid for tid in [team1_id, team2_id] if tid],
        player_ids=player_ids or [],
        is_clickable=True,
        expires_at=datetime.now() + timedelta(hours=24),
    )


def ticker_score(
    away_team: str,
    home_team: str,
    away_score: int,
    home_score: int,
    is_final: bool = False,
    quarter: Optional[int] = None,
    away_team_id: Optional[UUID] = None,
    home_team_id: Optional[UUID] = None,
) -> TickerItem:
    """Create a game score ticker item."""
    if is_final:
        headline = f"FINAL: {away_team} {away_score}, {home_team} {home_score}"
    else:
        q_str = f"Q{quarter}" if quarter else ""
        headline = f"{away_team} {away_score}, {home_team} {home_score} {q_str}"

    return TickerItem(
        category=TickerCategory.SCORE,
        headline=headline,
        detail=f"{away_team} {'def.' if away_score > home_score else 'vs.'} {home_team}",
        priority=4 if is_final else 2,
        team_ids=[tid for tid in [away_team_id, home_team_id] if tid],
        expires_at=datetime.now() + timedelta(hours=6 if is_final else 1),
    )


def ticker_injury(
    player_name: str,
    team_name: str,
    injury_type: str,
    severity: str,  # "questionable", "doubtful", "out", "IR"
    team_id: Optional[UUID] = None,
    player_id: Optional[UUID] = None,
) -> TickerItem:
    """Create an injury report ticker item."""
    is_serious = severity.lower() in {"out", "ir"}
    return TickerItem(
        category=TickerCategory.INJURY_REPORT,
        headline=f"INJ: {team_name} {player_name} ({severity})",
        detail=f"{team_name} {player_name} listed as {severity} with {injury_type}.",
        is_breaking=is_serious,
        priority=6 if is_serious else 3,
        team_ids=[team_id] if team_id else [],
        player_ids=[player_id] if player_id else [],
        expires_at=datetime.now() + timedelta(hours=48),
    )


def ticker_draft_pick(
    round_num: int,
    pick_num: int,
    team_name: str,
    player_name: str,
    position: str,
    college: str,
    team_id: Optional[UUID] = None,
    player_id: Optional[UUID] = None,
) -> TickerItem:
    """Create a draft pick ticker item."""
    is_first_round = round_num == 1
    return TickerItem(
        category=TickerCategory.DRAFT_PICK,
        headline=f"PICK {pick_num}: {team_name} select {position} {player_name} ({college})",
        detail=f"Round {round_num}, Pick {pick_num}: {team_name} select {player_name}, {position} from {college}.",
        is_breaking=is_first_round and pick_num <= 10,
        priority=8 if is_first_round else 4,
        team_ids=[team_id] if team_id else [],
        player_ids=[player_id] if player_id else [],
        expires_at=datetime.now() + timedelta(hours=2),
    )


def ticker_rumor(
    headline: str,
    detail: str = "",
    team_ids: Optional[list[UUID]] = None,
    player_ids: Optional[list[UUID]] = None,
) -> TickerItem:
    """Create a rumor ticker item."""
    return TickerItem(
        category=TickerCategory.RUMOR,
        headline=f"RUMOR: {headline}",
        detail=detail or headline,
        priority=1,
        team_ids=team_ids or [],
        player_ids=player_ids or [],
        expires_at=datetime.now() + timedelta(hours=4),
    )


def ticker_deadline(
    deadline_name: str,
    time_remaining: str,
) -> TickerItem:
    """Create a deadline reminder ticker item."""
    return TickerItem(
        category=TickerCategory.DEADLINE,
        headline=f"DEADLINE: {deadline_name} - {time_remaining}",
        detail=f"{deadline_name} deadline approaching.",
        is_breaking=True,
        priority=9,
        expires_at=datetime.now() + timedelta(hours=1),
    )


@dataclass
class TickerFeed:
    """
    Manages the ticker feed as a ring buffer.

    New items are added to the front, old items age out.
    The feed maintains a maximum size and auto-expires old items.
    """

    max_size: int = 100
    default_ttl_hours: int = 24

    _items: deque[TickerItem] = field(default_factory=deque)

    # Stats
    total_items_added: int = 0

    def add(self, item: TickerItem) -> None:
        """Add an item to the ticker feed."""
        # Set default expiration if not set
        if item.expires_at is None:
            item.expires_at = datetime.now() + timedelta(hours=self.default_ttl_hours)

        # Add to front of queue
        self._items.appendleft(item)
        self.total_items_added += 1

        # Enforce max size
        while len(self._items) > self.max_size:
            self._items.pop()

    def add_multiple(self, items: list[TickerItem]) -> None:
        """Add multiple items at once."""
        for item in items:
            self.add(item)

    def get_active(self) -> list[TickerItem]:
        """Get all non-expired items, sorted by priority then recency."""
        active = [item for item in self._items if not item.is_expired]
        return sorted(active, key=lambda i: (-i.priority, i.timestamp), reverse=True)

    def get_breaking(self) -> list[TickerItem]:
        """Get breaking news items."""
        return [item for item in self._items if item.is_breaking and not item.is_expired]

    def get_by_category(self, category: TickerCategory) -> list[TickerItem]:
        """Get items by category."""
        return [
            item for item in self._items
            if item.category == category and not item.is_expired
        ]

    def get_for_team(self, team_id: UUID) -> list[TickerItem]:
        """Get items related to a specific team."""
        return [
            item for item in self._items
            if team_id in item.team_ids and not item.is_expired
        ]

    def get_recent(self, count: int = 10) -> list[TickerItem]:
        """Get the N most recent non-expired items."""
        active = self.get_active()
        return active[:count]

    def get_unread(self) -> list[TickerItem]:
        """Get all unread items."""
        return [item for item in self._items if not item.is_read and not item.is_expired]

    def mark_read(self, item_id: UUID) -> bool:
        """Mark an item as read. Returns True if found."""
        for item in self._items:
            if item.id == item_id:
                item.is_read = True
                return True
        return False

    def mark_all_read(self) -> int:
        """Mark all items as read. Returns count marked."""
        count = 0
        for item in self._items:
            if not item.is_read:
                item.is_read = True
                count += 1
        return count

    def cleanup_expired(self) -> int:
        """Remove expired items. Returns count removed."""
        before = len(self._items)
        self._items = deque(
            item for item in self._items if not item.is_expired
        )
        return before - len(self._items)

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()

    @property
    def count(self) -> int:
        """Total items in feed."""
        return len(self._items)

    @property
    def unread_count(self) -> int:
        """Count of unread items."""
        return len(self.get_unread())

    @property
    def breaking_count(self) -> int:
        """Count of breaking news items."""
        return len(self.get_breaking())

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "max_size": self.max_size,
            "default_ttl_hours": self.default_ttl_hours,
            "items": [item.to_dict() for item in self._items],
            "total_items_added": self.total_items_added,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TickerFeed":
        """Create from dictionary."""
        feed = cls(
            max_size=data.get("max_size", 100),
            default_ttl_hours=data.get("default_ttl_hours", 24),
        )
        feed.total_items_added = data.get("total_items_added", 0)
        for item_data in data.get("items", []):
            item = TickerItem.from_dict(item_data)
            feed._items.append(item)
        return feed

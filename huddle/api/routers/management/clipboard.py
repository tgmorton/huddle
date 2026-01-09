"""
Clipboard management router.

Handles clipboard, events, drawer, and journal endpoints:
- Events queue (get, attend, dismiss)
- Clipboard navigation
- Drawer items
- Week journal
- Ticker feed
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException

from huddle.management import ClipboardTab
from huddle.api.schemas.management import (
    EventQueueResponse,
    ClipboardStateResponse,
    TickerFeedResponse,
    SelectTabRequest,
    AttendEventRequest,
    DismissEventRequest,
    DrawerResponse,
    DrawerItemResponse,
    AddDrawerItemRequest,
    UpdateDrawerItemRequest,
    WeekJournal,
    AddJournalEntryRequest,
    JournalEntry,
)
from .deps import get_session, schema_to_clipboard_tab

router = APIRouter(tags=["clipboard"])


@router.get("/franchise/{franchise_id}/events", response_model=EventQueueResponse)
async def get_events(franchise_id: UUID) -> EventQueueResponse:
    """Get pending events for a franchise."""
    session = get_session(franchise_id)
    return session.service._get_events_response()


@router.post("/franchise/{franchise_id}/events/attend")
async def attend_event(franchise_id: UUID, request: AttendEventRequest) -> dict:
    """Attend an event."""
    session = get_session(franchise_id)

    event = session.service.attend_event(request.event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"message": f"Attending event: {event.title}", "event_id": str(event.id)}


@router.post("/franchise/{franchise_id}/events/dismiss")
async def dismiss_event(franchise_id: UUID, request: DismissEventRequest) -> dict:
    """Dismiss an event."""
    session = get_session(franchise_id)

    success = session.service.dismiss_event(request.event_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot dismiss event")

    return {"message": "Event dismissed", "event_id": str(request.event_id)}


@router.get("/franchise/{franchise_id}/clipboard", response_model=ClipboardStateResponse)
async def get_clipboard(franchise_id: UUID) -> ClipboardStateResponse:
    """Get clipboard state for a franchise."""
    session = get_session(franchise_id)
    return session.service._get_clipboard_response()


@router.post("/franchise/{franchise_id}/clipboard/tab")
async def select_tab(franchise_id: UUID, request: SelectTabRequest) -> dict:
    """Select a clipboard tab."""
    session = get_session(franchise_id)

    tab = schema_to_clipboard_tab(request.tab)
    session.service.select_tab(tab)
    return {"message": f"Selected tab: {tab.name}", "tab": tab.name}


@router.post("/franchise/{franchise_id}/clipboard/back")
async def go_back(franchise_id: UUID) -> dict:
    """Go back in panel navigation."""
    session = get_session(franchise_id)

    success = session.service.go_back()
    return {"message": "Navigated back" if success else "Already at root", "success": success}


@router.get("/franchise/{franchise_id}/ticker", response_model=TickerFeedResponse)
async def get_ticker(franchise_id: UUID) -> TickerFeedResponse:
    """Get ticker feed for a franchise."""
    session = get_session(franchise_id)
    return session.service._get_ticker_response()


# === Drawer Endpoints ===


@router.get("/franchise/{franchise_id}/drawer", response_model=DrawerResponse)
async def get_drawer(franchise_id: UUID) -> DrawerResponse:
    """Get all items in the desk drawer."""
    session = get_session(franchise_id)

    items = session.service.get_drawer_items()
    return DrawerResponse(items=items, count=len(items))


@router.post("/franchise/{franchise_id}/drawer", response_model=DrawerItemResponse)
async def add_drawer_item(franchise_id: UUID, request: AddDrawerItemRequest) -> DrawerItemResponse:
    """Add an item to the desk drawer."""
    session = get_session(franchise_id)

    item = session.service.add_drawer_item(
        item_type=request.type.value,
        ref_id=request.ref_id,
        note=request.note,
    )

    if not item:
        raise HTTPException(status_code=400, detail="Failed to add item to drawer")

    return DrawerItemResponse(**item)


@router.delete("/franchise/{franchise_id}/drawer/{item_id}")
async def delete_drawer_item(franchise_id: UUID, item_id: str) -> dict:
    """Remove an item from the desk drawer."""
    session = get_session(franchise_id)

    success = session.service.delete_drawer_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Drawer item not found")

    return {"message": "Item removed from drawer", "item_id": item_id}


@router.patch("/franchise/{franchise_id}/drawer/{item_id}", response_model=DrawerItemResponse)
async def update_drawer_item(
    franchise_id: UUID,
    item_id: str,
    request: UpdateDrawerItemRequest,
) -> DrawerItemResponse:
    """Update a drawer item's note."""
    session = get_session(franchise_id)

    item = session.service.update_drawer_item_note(item_id, request.note)
    if not item:
        raise HTTPException(status_code=404, detail="Drawer item not found")

    return DrawerItemResponse(**item)


# === Week Journal Endpoints ===


@router.get("/franchise/{franchise_id}/week-journal", response_model=WeekJournal)
async def get_week_journal(franchise_id: UUID) -> WeekJournal:
    """
    Get the journal for the current week.

    Contains accumulated effects from player decisions:
    - Practice results
    - Player conversations
    - Scout intel
    - Injury updates
    - Transactions

    Resets when the week advances.
    """
    session = get_session(franchise_id)

    journal_data = session.service.get_week_journal()
    return WeekJournal(
        week=journal_data["week"],
        entries=journal_data["entries"],
    )


@router.post("/franchise/{franchise_id}/week-journal", response_model=JournalEntry)
async def add_journal_entry(franchise_id: UUID, request: AddJournalEntryRequest) -> JournalEntry:
    """
    Add an entry to the week journal.

    Categories:
    - practice: Practice session results
    - conversation: Meeting/media interactions
    - intel: Scout reports and game prep
    - injury: Injury updates
    - transaction: Trades, signings, etc.
    """
    session = get_session(franchise_id)

    entry = session.service.add_journal_entry(
        category=request.category,
        title=request.title,
        effect=request.effect,
        detail=request.detail,
        player=request.player,
    )

    return JournalEntry(**entry)

/**
 * Converts ManagementEvent from the store to WorkspaceItem for display.
 *
 * This bridges the backend event system with the frontend workspace UI.
 */

import type { ManagementEvent } from '../../../types/management';
import type { WorkspaceItem, ItemType } from '../types';

/**
 * Map event categories to workspace item types.
 * Some categories map directly, others need translation.
 */
const CATEGORY_TO_ITEM_TYPE: Record<string, ItemType> = {
  PRACTICE: 'practice',
  GAME: 'game',
  MEETING: 'meeting',
  DEADLINE: 'deadline',
  CONTRACT: 'decision',
  TRADE: 'decision',
  FREE_AGENCY: 'decision',
  SCOUTING: 'scout',
  DRAFT: 'scout',
  ROSTER: 'decision',
  STAFF: 'meeting',
  SYSTEM: 'deadline',
  // New categories
  TEAM: 'practice',
  PLAYER: 'meeting',
  MEDIA: 'meeting',
  INJURY: 'deadline',
};

/**
 * Convert a ManagementEvent to a WorkspaceItem.
 *
 * @param event - The backend event
 * @returns WorkspaceItem for the workspace grid, or null if event should be skipped
 */
export function eventToWorkspaceItem(event: ManagementEvent): WorkspaceItem | null {
  // Skip ticker-only events - they don't go on workspace
  if (event.display_mode === 'TICKER') {
    return null;
  }

  // Skip events that are already handled
  if (['ATTENDED', 'EXPIRED', 'DISMISSED', 'AUTO_RESOLVED'].includes(event.status)) {
    return null;
  }

  // Map category to item type
  const itemType = CATEGORY_TO_ITEM_TYPE[event.category] || 'deadline';

  // Extract player ID if this is a player-related event
  const playerId = event.player_ids.length > 0 ? event.player_ids[0] : undefined;

  // Calculate time left if there's a deadline (day-based only)
  let timeLeft: string | undefined;
  if (event.deadline) {
    const deadline = new Date(event.deadline);
    const now = new Date();
    const daysLeft = Math.ceil((deadline.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    if (daysLeft <= 0) {
      timeLeft = 'Today';
    } else if (daysLeft === 1) {
      timeLeft = '1d';
    } else {
      timeLeft = `${daysLeft}d`;
    }
  }

  return {
    id: `event-${event.id}`,
    type: itemType,
    title: event.title,
    subtitle: event.description,
    timeLeft,
    isOpen: false,
    playerId,
    eventId: event.id,
    eventPayload: event.payload,
    status: 'active',
  };
}

/**
 * Convert multiple events to workspace items.
 * Filters out modal events, ticker events, and handled events.
 */
export function eventsToWorkspaceItems(events: ManagementEvent[]): WorkspaceItem[] {
  return events
    .filter(isPaneEvent) // Only pane events go on workspace
    .map(eventToWorkspaceItem)
    .filter((item): item is WorkspaceItem => item !== null);
}

/**
 * Check if an event should display as a modal.
 * Used to separate modal events from pane events.
 */
export function isModalEvent(event: ManagementEvent): boolean {
  return event.display_mode === 'MODAL';
}

/**
 * Check if an event should display as a pane (workspace item).
 */
export function isPaneEvent(event: ManagementEvent): boolean {
  return event.display_mode === 'PANE' || !event.display_mode;
}

// Persistence utilities for workspace items

import type { WorkspaceItem } from '../types';

const STORAGE_KEYS = {
  PINNED_ITEMS: 'managementv2_pinned_items',
} as const;

// Save pinned items to localStorage
export function savePinnedItems(items: WorkspaceItem[]): void {
  try {
    const pinnedOnly = items.filter(i => i.status === 'pinned');
    localStorage.setItem(STORAGE_KEYS.PINNED_ITEMS, JSON.stringify(pinnedOnly));
  } catch (e) {
    console.error('Failed to save pinned items:', e);
  }
}

// Load pinned items from localStorage
export function loadPinnedItems(): WorkspaceItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.PINNED_ITEMS);
    if (!stored) return [];
    const items = JSON.parse(stored) as WorkspaceItem[];
    // Ensure all loaded items have pinned status
    return items.map(item => ({ ...item, status: 'pinned' as const }));
  } catch (e) {
    console.error('Failed to load pinned items:', e);
    return [];
  }
}

// Note: Drawer items are now persisted via the management API, not localStorage

// Format relative time for display (e.g., "2h ago", "3d ago")
export function formatTimeAgo(timestamp: number): string {
  const now = Date.now();
  const diff = now - timestamp;

  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'Just now';
}

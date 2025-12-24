// DeskDrawer.tsx - Archived workspace items panel with timeline view

import React, { useState } from 'react';
import { Trash2, Pencil } from 'lucide-react';
import type { WorkspaceItem } from '../types';
import { TYPE_CONFIG } from '../constants';

interface DeskDrawerProps {
  items: WorkspaceItem[];
  onRestore: (item: WorkspaceItem) => void;
  onDelete: (id: string) => void;
  onUpdateNote: (id: string, note: string) => void;
}

// Group items by date label
const getDateLabel = (timestamp: number): string => {
  const now = new Date();
  const date = new Date(timestamp);

  // Reset times to midnight for comparison
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const itemDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  const diffDays = Math.floor((today.getTime() - itemDate.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 14) return 'Last week';
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return 'Older';
};

// Group items by their date labels, always including Today and Yesterday
const groupByDate = (items: WorkspaceItem[]): Map<string, WorkspaceItem[]> => {
  // Always start with Today and Yesterday
  const groups = new Map<string, WorkspaceItem[]>([
    ['Today', []],
    ['Yesterday', []],
  ]);

  // Sort by archivedAt descending (newest first)
  const sorted = [...items].sort((a, b) => (b.archivedAt || 0) - (a.archivedAt || 0));

  for (const item of sorted) {
    const label = getDateLabel(item.archivedAt || Date.now());
    const existing = groups.get(label) || [];
    groups.set(label, [...existing, item]);
  }

  return groups;
};

// Individual drawer item with edit/delete functionality
const DrawerItem: React.FC<{
  item: WorkspaceItem;
  onRestore: () => void;
  onDelete: () => void;
  onUpdateNote: (note: string) => void;
}> = ({ item, onRestore, onDelete, onUpdateNote }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [noteValue, setNoteValue] = useState(item.note || '');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const config = TYPE_CONFIG[item.type];

  const handleSaveNote = () => {
    onUpdateNote(noteValue.trim());
    setIsEditing(false);
  };

  const handleDeleteClick = () => {
    if (confirmDelete) {
      onDelete();
    } else {
      setConfirmDelete(true);
      // Reset after 2 seconds if not confirmed
      setTimeout(() => setConfirmDelete(false), 2000);
    }
  };

  return (
    <div className="desk-drawer__item-wrapper">
      <div className="desk-drawer__item">
        <button
          className="desk-drawer__item-main"
          onClick={onRestore}
          title="Restore to workspace"
        >
          <span className="desk-drawer__abbr" data-type={item.type}>
            {config.abbr}
          </span>
          <div className="desk-drawer__item-info">
            <span className="desk-drawer__item-title">{item.title}</span>
            {item.subtitle && (
              <span className="desk-drawer__item-subtitle">{item.subtitle}</span>
            )}
          </div>
        </button>
        <div className="desk-drawer__item-actions">
          <button
            className={`desk-drawer__action-btn ${isEditing ? 'desk-drawer__action-btn--active' : ''}`}
            onClick={() => setIsEditing(!isEditing)}
            title="Add note"
          >
            <Pencil size={12} />
          </button>
          <button
            className={`desk-drawer__action-btn desk-drawer__action-btn--delete ${confirmDelete ? 'desk-drawer__action-btn--confirm' : ''}`}
            onClick={handleDeleteClick}
            title={confirmDelete ? 'Click again to confirm' : 'Delete'}
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* Note section below the card */}
      {(item.note || isEditing) && (
        <div className="desk-drawer__note">
          <div className="desk-drawer__note-line" />
          {isEditing ? (
            <div className="desk-drawer__note-input">
              <input
                type="text"
                value={noteValue}
                onChange={(e) => setNoteValue(e.target.value)}
                placeholder="Add a note..."
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveNote();
                  if (e.key === 'Escape') setIsEditing(false);
                }}
              />
              <button onClick={handleSaveNote}>Save</button>
            </div>
          ) : (
            <span className="desk-drawer__note-text">{item.note}</span>
          )}
        </div>
      )}
    </div>
  );
};

export const DeskDrawer: React.FC<DeskDrawerProps> = ({
  items,
  onRestore,
  onDelete,
  onUpdateNote,
}) => {
  if (items.length === 0) {
    return (
      <div className="desk-drawer">
        <div className="desk-drawer__empty">
          <p>No archived items</p>
          <p className="desk-drawer__hint">
            Archive items from your workspace to save them here for later.
          </p>
        </div>
      </div>
    );
  }

  const groupedItems = groupByDate(items);
  const dateLabels = Array.from(groupedItems.keys());

  return (
    <div className="desk-drawer">
      <div className="desk-drawer__timeline">
        {dateLabels.map((label) => {
          const groupItems = groupedItems.get(label) || [];

          return (
            <div key={label} className="desk-drawer__group">
              {/* Date marker */}
              <div className="desk-drawer__date-row">
                <div className="desk-drawer__date-marker">
                  <div className="desk-drawer__date-dot" />
                </div>
                <span className="desk-drawer__date-label">{label}</span>
              </div>

              {/* Items for this date */}
              {groupItems.length > 0 && (
                <div className="desk-drawer__items">
                  {groupItems.map(item => (
                    <DrawerItem
                      key={item.id}
                      item={item}
                      onRestore={() => onRestore(item)}
                      onDelete={() => onDelete(item.id)}
                      onUpdateNote={(note) => onUpdateNote(item.id, note)}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DeskDrawer;

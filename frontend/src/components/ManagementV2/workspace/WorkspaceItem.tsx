// WorkspaceItem.tsx - Workspace item component (card/pane rendering)

import React, { useRef, useEffect } from 'react';
import { GripVertical, X, Pin, ArrowDownToLine } from 'lucide-react';
import type { WorkspaceItem } from '../types';
import { TYPE_SIZE, TYPE_CONFIG } from '../constants';
import { DeadlinePane, PracticePane, ContractPane, ContractDetailPane, ScoutPane, PlayerPane, PlayerStatsPane, ProspectPane, NewsPane, MeetingPane, GamePane, NegotiationPane, AuctionPane } from './panes';

export interface WorkspaceItemProps {
  item: WorkspaceItem;
  index: number;
  isEditMode: boolean;
  isDragging: boolean;
  isDropTarget: boolean;
  franchiseId?: string | null;
  onToggle: () => void;
  onCollapse: () => void;  // Collapse open item to card
  onRemove: () => void;    // Remove item entirely
  onPin: () => void;
  onArchive: () => void;
  onRunPractice?: (eventId: string, allocation: { playbook: number; development: number; gamePrep: number }) => void;
  onHeightChange: (id: string, height: number) => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragEnd: () => void;
  onDrop: (e: React.DragEvent) => void;
}

// Event types pass by definition and cannot be archived (only closed or pinned)
const EVENT_TYPES = new Set(['practice', 'game', 'meeting', 'deadline', 'decision', 'scout']);

export const WorkspaceItemComponent: React.FC<WorkspaceItemProps> = ({
  item,
  isEditMode,
  isDragging,
  isDropTarget,
  franchiseId,
  onToggle,
  onCollapse,
  onRemove,
  onPin,
  onArchive,
  onRunPractice,
  onHeightChange,
  onDragStart,
  onDragOver,
  onDragEnd,
  onDrop,
}) => {
  const config = TYPE_CONFIG[item.type];
  const size = item.isOpen ? TYPE_SIZE[item.type] : 'small';
  const itemRef = useRef<HTMLDivElement>(null);
  const canArchive = !EVENT_TYPES.has(item.type); // Only reference items (player, prospect) can be archived

  // Measure actual content height and set CSS variable for masonry
  useEffect(() => {
    const el = itemRef.current;
    if (!el) return;

    const updateHeight = () => {
      // Use scrollHeight to get natural content height, not constrained height
      const height = el.scrollHeight;
      if (height > 0) {
        el.style.setProperty('--item-height', `${height}px`);
        onHeightChange(item.id, height);
      }
    };

    // Delay measurement to after paint
    requestAnimationFrame(() => {
      requestAnimationFrame(updateHeight);
    });

    // Watch for content changes
    const observer = new ResizeObserver(() => {
      requestAnimationFrame(updateHeight);
    });
    observer.observe(el);

    return () => observer.disconnect();
  }, [item.isOpen, item.id, onHeightChange]); // Re-run when open state changes

  const className = [
    'workspace-item',
    item.isOpen ? 'workspace-item--open' : 'workspace-item--collapsed',
    `workspace-item--${size}`,
    item.status === 'pinned' && 'workspace-item--pinned',
    isDragging && 'workspace-item--dragging',
    isDropTarget && 'workspace-item--drop-target',
  ].filter(Boolean).join(' ');

  return (
    <div
      ref={itemRef}
      className={className}
      data-type={item.type}
      draggable={isEditMode}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDragEnd={onDragEnd}
      onDrop={onDrop}
    >
      {item.isOpen ? (
        // Expanded pane content
        <div className="workspace-item__pane">
          <div className="workspace-item__pane-header">
            <div className="workspace-item__pane-title">
              <span className="workspace-item__abbr" data-type={item.type}>{config.abbr}</span>
              {item.status === 'pinned' && <Pin size={12} className="workspace-item__pinned-icon" />}
              <span>{item.type === 'prospect' ? 'Prospect' : item.title}</span>
            </div>
            <div className="workspace-item__actions workspace-item__actions--inline">
              <button
                className="workspace-item__action-btn"
                onClick={onCollapse}
                title="Collapse"
              >
                <X size={14} />
              </button>
              <button
                className={`workspace-item__action-btn ${item.status === 'pinned' ? 'workspace-item__action-btn--active' : ''}`}
                onClick={onPin}
                title={item.status === 'pinned' ? 'Unpin' : 'Pin'}
              >
                <Pin size={14} />
              </button>
              {canArchive && (
                <button
                  className="workspace-item__action-btn"
                  onClick={onArchive}
                  title="Archive to drawer"
                >
                  <ArrowDownToLine size={14} />
                </button>
              )}
            </div>
          </div>
          <div className="workspace-item__pane-content">
            {/* Event panes: onComplete removes the item (events are one-time) */}
            {item.type === 'practice' && (
              <PracticePane
                eventId={item.eventId}
                onRunPractice={onRunPractice}
                onComplete={onRemove}
              />
            )}
            {item.type === 'decision' && (
              <ContractPane eventId={item.eventId || item.id} onComplete={onRemove} />
            )}
            {item.type === 'meeting' && (
              <MeetingPane eventId={item.eventId || item.id} onComplete={onRemove} />
            )}
            {item.type === 'scout' && (
              <ScoutPane eventPayload={item.eventPayload} onComplete={onRemove} />
            )}
            {item.type === 'game' && (
              <GamePane eventId={item.eventId} eventPayload={item.eventPayload} onComplete={onRemove} />
            )}
            {item.type === 'deadline' && (
              <DeadlinePane item={item} onComplete={onRemove} />
            )}
            {/* Reference panes: onComplete collapses (can be reopened) */}
            {item.type === 'player' && item.playerId && (
              <PlayerPane playerId={item.playerId} onComplete={onCollapse} />
            )}
            {item.type === 'prospect' && item.playerId && (
              <ProspectPane playerId={item.playerId} franchiseId={franchiseId || undefined} onComplete={onCollapse} />
            )}
            {item.type === 'contract' && item.playerId && (
              <ContractDetailPane playerId={item.playerId} onComplete={onCollapse} />
            )}
            {item.type === 'negotiation' && item.playerId && (
              <NegotiationPane playerId={item.playerId} onComplete={onRemove} />
            )}
            {item.type === 'auction' && item.playerId && (
              <AuctionPane playerId={item.playerId} onComplete={onRemove} />
            )}
            {item.type === 'news' && (
              <NewsPane title={item.title} content={item.subtitle || ''} onComplete={onCollapse} />
            )}
            {item.type === 'stats' && item.playerId && (
              <PlayerStatsPane playerId={item.playerId} onComplete={onCollapse} />
            )}
          </div>
        </div>
      ) : (
        // Collapsed card
        <div className="workspace-item__card-wrapper">
          <button className="workspace-item__card" onClick={onToggle}>
            {isEditMode && (
              <div className="workspace-item__drag-handle">
                <GripVertical size={14} />
              </div>
            )}
            <div className="workspace-item__card-header">
              <span className="workspace-item__abbr" data-type={item.type}>{config.abbr}</span>
              {item.status === 'pinned' && (
                <Pin size={12} className="workspace-item__pinned-icon" />
              )}
              {item.timeLeft && (
                <span className="workspace-item__time">{item.timeLeft}</span>
              )}
            </div>
            <h3 className="workspace-item__title">{item.title}</h3>
            {item.subtitle && <p className="workspace-item__subtitle">{item.subtitle}</p>}
          </button>
          <div className="workspace-item__actions">
            <button
              className="workspace-item__action-btn"
              onClick={(e) => { e.stopPropagation(); onRemove(); }}
              title="Remove"
            >
              <X size={14} />
            </button>
            <button
              className={`workspace-item__action-btn ${item.status === 'pinned' ? 'workspace-item__action-btn--active' : ''}`}
              onClick={(e) => { e.stopPropagation(); onPin(); }}
              title={item.status === 'pinned' ? 'Unpin' : 'Pin'}
            >
              <Pin size={14} />
            </button>
            {canArchive && (
              <button
                className="workspace-item__action-btn"
                onClick={(e) => { e.stopPropagation(); onArchive(); }}
                title="Archive to drawer"
              >
                <ArrowDownToLine size={14} />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspaceItemComponent;

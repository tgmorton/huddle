// WorkspaceItem.tsx - Workspace item component (card/pane rendering)

import React, { useRef, useEffect } from 'react';
import { GripVertical } from 'lucide-react';
import type { WorkspaceItem } from '../types';
import { TYPE_SIZE, TYPE_CONFIG } from '../constants';
import { DeadlinePane, PracticePane, ContractPane, ScoutPane, PlayerPane } from './panes';

export interface WorkspaceItemProps {
  item: WorkspaceItem;
  index: number;
  isEditMode: boolean;
  isDragging: boolean;
  isDropTarget: boolean;
  onToggle: () => void;
  onClose: () => void;
  onHeightChange: (id: string, height: number) => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragEnd: () => void;
  onDrop: (e: React.DragEvent) => void;
}

export const WorkspaceItemComponent: React.FC<WorkspaceItemProps> = ({
  item,
  isEditMode,
  isDragging,
  isDropTarget,
  onToggle,
  onClose,
  onHeightChange,
  onDragStart,
  onDragOver,
  onDragEnd,
  onDrop,
}) => {
  const config = TYPE_CONFIG[item.type];
  const size = item.isOpen ? TYPE_SIZE[item.type] : 'small';
  const itemRef = useRef<HTMLDivElement>(null);

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
          {item.type === 'practice' && (
            <PracticePane onComplete={onClose} />
          )}
          {item.type === 'decision' && (
            <ContractPane onComplete={onClose} />
          )}
          {item.type === 'scout' && (
            <ScoutPane onComplete={onClose} />
          )}
          {item.type === 'deadline' && (
            <DeadlinePane item={item} onComplete={onClose} />
          )}
          {item.type === 'player' && item.playerId && (
            <PlayerPane playerId={item.playerId} onComplete={onClose} />
          )}
        </div>
      ) : (
        // Collapsed card
        <button className="workspace-item__card" onClick={onToggle}>
          {isEditMode && (
            <div className="workspace-item__drag-handle">
              <GripVertical size={14} />
            </div>
          )}
          <div className="workspace-item__card-header">
            <span className="workspace-item__abbr" data-type={item.type}>{config.abbr}</span>
            {item.timeLeft && (
              <span className="workspace-item__time">{item.timeLeft}</span>
            )}
          </div>
          <h3 className="workspace-item__title">{item.title}</h3>
          {item.subtitle && <p className="workspace-item__subtitle">{item.subtitle}</p>}
        </button>
      )}
    </div>
  );
};

export default WorkspaceItemComponent;

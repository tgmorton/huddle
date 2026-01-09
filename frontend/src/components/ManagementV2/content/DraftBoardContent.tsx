// DraftBoardContent.tsx - User's draft board (empty by default, add prospects from Prospects tab)

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { GripVertical, Trash2, Plus, ChevronDown, ChevronRight, Loader2, Maximize2 } from 'lucide-react';
import { managementApi } from '../../../api/managementClient';
import type { BoardEntry } from '../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../stores/managementStore';

// === Types ===

type BoardView = 'ranked' | 'tiered';

// === Constants ===

// Position filter chips
const POSITION_FILTERS = ['All', 'QB', 'RB', 'WR', 'TE', 'OL', 'DL', 'LB', 'DB'] as const;

const TIER_LABELS: Record<number, string> = {
  1: 'Elite',
  2: 'Great',
  3: 'Good',
  4: 'Solid',
  5: 'Flier',
};

const TIER_COLORS: Record<number, string> = {
  1: 'var(--success)',
  2: 'var(--accent)',
  3: 'var(--text-secondary)',
  4: 'var(--text-muted)',
  5: 'var(--warning)',
};

// === Helpers ===

const getOvrColor = (ovr: number): string => {
  if (ovr >= 80) return 'var(--success)';
  if (ovr >= 70) return 'var(--accent)';
  if (ovr >= 60) return 'var(--text-secondary)';
  return 'var(--text-muted)';
};

// Position group mapping for filters
const POSITION_GROUPS: Record<string, string[]> = {
  'OL': ['LT', 'LG', 'C', 'RG', 'RT', 'OT', 'OG'],
  'DL': ['DE', 'DT', 'NT', 'EDGE'],
  'LB': ['MLB', 'ILB', 'OLB', 'LB'],
  'DB': ['CB', 'FS', 'SS', 'S'],
};

// === Main Component ===

interface DraftBoardContentProps {
  onPopoutProspect?: (prospect: { id: string; name: string; position: string; overall: number }) => void;
}

export const DraftBoardContent: React.FC<DraftBoardContentProps> = ({ onPopoutProspect }) => {
  const franchiseId = useManagementStore(selectFranchiseId);

  const [board, setBoard] = useState<BoardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [view, setView] = useState<BoardView>('ranked');
  const [positionFilter, setPositionFilter] = useState<string>('All');
  const [expandedTiers, setExpandedTiers] = useState<Set<number>>(new Set([1, 2, 3]));
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);
  const draggedIdRef = useRef<string | null>(null);

  // Load board data from API
  useEffect(() => {
    if (!franchiseId) return;

    const loadBoard = async () => {
      setIsLoading(true);
      try {
        const data = await managementApi.getDraftBoard(franchiseId);
        setBoard(data.entries);
      } catch (err) {
        console.error('Failed to load draft board:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadBoard();
  }, [franchiseId]);

  // Reorder handler - calls API then updates local state
  const handleReorder = useCallback(async (fromId: string, toId: string) => {
    if (fromId === toId || !franchiseId) return;

    // Find the target rank (1-based)
    const toIndex = board.findIndex(p => p.prospect_id === toId);
    if (toIndex === -1) return;

    const newRank = toIndex + 1;

    // Optimistic update
    setBoard(prev => {
      const fromIndex = prev.findIndex(p => p.prospect_id === fromId);
      if (fromIndex === -1) return prev;
      const next = [...prev];
      const [moved] = next.splice(fromIndex, 1);
      next.splice(toIndex, 0, moved);
      // Update ranks
      return next.map((p, i) => ({ ...p, rank: i + 1 }));
    });

    // Call API
    try {
      await managementApi.reorderBoardEntry(franchiseId, fromId, newRank);
    } catch (err) {
      console.error('Failed to reorder:', err);
      // Reload on error
      const data = await managementApi.getDraftBoard(franchiseId);
      setBoard(data.entries);
    }
  }, [franchiseId, board]);

  // Remove from board
  const handleRemove = useCallback(async (prospectId: string) => {
    if (!franchiseId) return;

    // Optimistic update
    setBoard(prev => prev.filter(p => p.prospect_id !== prospectId));

    try {
      await managementApi.removeFromBoard(franchiseId, prospectId);
    } catch (err) {
      console.error('Failed to remove from board:', err);
      // Reload on error
      const data = await managementApi.getDraftBoard(franchiseId);
      setBoard(data.entries);
    }
  }, [franchiseId]);

  // Change tier
  const handleTierChange = useCallback(async (prospectId: string, tier: number) => {
    if (!franchiseId) return;

    // Optimistic update
    setBoard(prev => prev.map(p =>
      p.prospect_id === prospectId ? { ...p, tier } : p
    ));

    try {
      await managementApi.updateBoardEntry(franchiseId, prospectId, { tier });
    } catch (err) {
      console.error('Failed to update tier:', err);
      // Reload on error
      const data = await managementApi.getDraftBoard(franchiseId);
      setBoard(data.entries);
    }
  }, [franchiseId]);

  // Toggle tier expansion
  const toggleTier = useCallback((tier: number) => {
    setExpandedTiers(prev => {
      const next = new Set(prev);
      if (next.has(tier)) next.delete(tier);
      else next.add(tier);
      return next;
    });
  }, []);

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, id: string) => {
    draggedIdRef.current = id;
    e.dataTransfer.effectAllowed = 'move';
    const row = e.currentTarget as HTMLElement;
    row.classList.add('board-row--dragging');
  };

  const handleDragOver = (e: React.DragEvent, id: string) => {
    e.preventDefault();
    if (draggedIdRef.current && draggedIdRef.current !== id) {
      setDropTargetId(id);
    }
  };

  const handleDragEnd = (e: React.DragEvent) => {
    const row = e.currentTarget as HTMLElement;
    row.classList.remove('board-row--dragging');
    draggedIdRef.current = null;
    setDropTargetId(null);
  };

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    if (draggedIdRef.current && draggedIdRef.current !== targetId) {
      handleReorder(draggedIdRef.current, targetId);
    }
    draggedIdRef.current = null;
    setDropTargetId(null);
  };

  // Filter board by position
  const filteredBoard = positionFilter === 'All'
    ? board
    : board.filter(entry => {
        const groupPositions = POSITION_GROUPS[positionFilter];
        if (groupPositions) {
          return groupPositions.includes(entry.position);
        }
        return entry.position === positionFilter;
      });

  // Group by tier for tiered view
  const tierGroups = [1, 2, 3, 4, 5].map(tier => ({
    tier,
    prospects: filteredBoard.filter(p => p.tier === tier),
  }));

  // Render a single row
  const renderRow = (entry: BoardEntry, rank: number) => (
    <tr
      key={entry.prospect_id}
      className={`board-row ${dropTargetId === entry.prospect_id ? 'board-row--drop-target' : ''}`}
      draggable
      onDragStart={(e) => handleDragStart(e, entry.prospect_id)}
      onDragOver={(e) => handleDragOver(e, entry.prospect_id)}
      onDragEnd={handleDragEnd}
      onDrop={(e) => handleDrop(e, entry.prospect_id)}
    >
      <td className="board-row__drag"><GripVertical size={14} /></td>
      <td className="board-row__rank">{rank}</td>
      <td className="board-row__pos">{entry.position}</td>
      <td className="board-row__name">{entry.name}</td>
      <td className="board-row__college">{entry.college || '-'}</td>
      <td className="board-row__ovr" style={{ color: getOvrColor(entry.overall) }}>{entry.overall}</td>
      <td className="board-row__actions">
        {onPopoutProspect && (
          <button
            className="board-row__action-btn"
            onClick={(e) => {
              e.stopPropagation();
              onPopoutProspect({
                id: entry.prospect_id,
                name: entry.name,
                position: entry.position,
                overall: entry.overall,
              });
            }}
            title="Open in workspace"
          >
            <Maximize2 size={14} />
          </button>
        )}
        <button
          className="board-row__action-btn board-row__action-btn--danger"
          onClick={() => handleRemove(entry.prospect_id)}
          title="Remove from board"
        >
          <Trash2 size={14} />
        </button>
      </td>
    </tr>
  );

  if (isLoading) {
    return (
      <div className="board-content">
        <div className="board-empty">
          <Loader2 size={32} className="spin" />
          <p>Loading draft board...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="board-content">
      {/* Header */}
      <div className="board-header">
        <div className="board-header__top">
          <span className="board-header__count">
            <strong>{filteredBoard.length}</strong>
            {positionFilter !== 'All' && ` of ${board.length}`}
            {' '}prospect{board.length !== 1 ? 's' : ''}
          </span>
          <div className="board-header__views">
            <button
              className={`board-header__view-btn ${view === 'ranked' ? 'board-header__view-btn--active' : ''}`}
              onClick={() => setView('ranked')}
            >
              Ranked
            </button>
            <button
              className={`board-header__view-btn ${view === 'tiered' ? 'board-header__view-btn--active' : ''}`}
              onClick={() => setView('tiered')}
            >
              Tiered
            </button>
          </div>
        </div>
        {board.length > 0 && (
          <div className="board-header__filters">
            {POSITION_FILTERS.map(pos => (
              <button
                key={pos}
                className={`board-header__filter ${positionFilter === pos ? 'board-header__filter--active' : ''}`}
                onClick={() => setPositionFilter(pos)}
              >
                {pos}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      {board.length === 0 ? (
        <div className="board-empty">
          <Plus size={32} />
          <p>Your draft board is empty</p>
          <span>Add prospects from the Prospects tab</span>
        </div>
      ) : filteredBoard.length === 0 ? (
        <div className="board-empty board-empty--filtered">
          <p>No {positionFilter} prospects on your board</p>
        </div>
      ) : view === 'ranked' ? (
        <table className="board-table">
          <thead>
            <tr>
              <th></th>
              <th>#</th>
              <th>Pos</th>
              <th>Name</th>
              <th>School</th>
              <th>OVR</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredBoard.map((entry, idx) => renderRow(entry, idx + 1))}
          </tbody>
        </table>
      ) : (
        <div className="board-tiers">
          {tierGroups.map((group) => {
            if (group.prospects.length === 0) return null;
            const isExpanded = expandedTiers.has(group.tier);
            return (
              <div key={group.tier} className="board-tier">
                <button className="board-tier__header" onClick={() => toggleTier(group.tier)}>
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <span style={{ color: TIER_COLORS[group.tier] }}>{TIER_LABELS[group.tier]}</span>
                  <span className="board-tier__count">{group.prospects.length}</span>
                </button>
                {isExpanded && (
                  <table className="board-table">
                    <tbody>
                      {group.prospects.map((entry, idx) => renderRow(entry, idx + 1))}
                    </tbody>
                  </table>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DraftBoardContent;

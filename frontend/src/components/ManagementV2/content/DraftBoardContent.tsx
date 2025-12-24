// DraftBoardContent.tsx - User's draft board (empty by default, add prospects from Prospects tab)

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { GripVertical, Trash2, Plus, ChevronDown, ChevronRight, Loader2 } from 'lucide-react';
import { managementApi } from '../../../api/managementClient';
import type { BoardEntry } from '../../../api/managementClient';
import { useManagementStore, selectFranchiseId } from '../../../stores/managementStore';

// === Types ===

interface PositionNeed {
  position: string;
  priority: 'high' | 'medium' | 'low';
}

type BoardView = 'ranked' | 'tiered';

// === Demo Data ===

const DEMO_POSITION_NEEDS: PositionNeed[] = [
  { position: 'CB', priority: 'high' },
  { position: 'WR', priority: 'high' },
  { position: 'OT', priority: 'medium' },
  { position: 'EDGE', priority: 'medium' },
  { position: 'RB', priority: 'low' },
];

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

const getPriorityColor = (priority: 'high' | 'medium' | 'low'): string => {
  switch (priority) {
    case 'high': return 'var(--danger)';
    case 'medium': return 'var(--warning)';
    case 'low': return 'var(--text-muted)';
  }
};

// === Main Component ===

export const DraftBoardContent: React.FC = () => {
  const franchiseId = useManagementStore(selectFranchiseId);

  const [board, setBoard] = useState<BoardEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [view, setView] = useState<BoardView>('ranked');
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

  // Group by tier for tiered view
  const tierGroups = [1, 2, 3, 4, 5].map(tier => ({
    tier,
    prospects: board.filter(p => p.tier === tier),
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
      <td className="board-row__tier">
        <select
          value={entry.tier}
          onChange={(e) => handleTierChange(entry.prospect_id, Number(e.target.value))}
          className="board-row__tier-select"
          style={{ color: TIER_COLORS[entry.tier] }}
          onClick={(e) => e.stopPropagation()}
        >
          {[1, 2, 3, 4, 5].map(t => (
            <option key={t} value={t}>{TIER_LABELS[t]}</option>
          ))}
        </select>
      </td>
      <td className="board-row__actions">
        <button
          className="board-row__remove"
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
      <div className="board-toolbar">
        <div className="board-toolbar__left">
          <span className="board-toolbar__count">{board.length} prospects</span>
          <div className="board-toolbar__needs">
            {DEMO_POSITION_NEEDS.map(need => (
              <span
                key={need.position}
                className="board-toolbar__need"
                style={{ borderColor: getPriorityColor(need.priority) }}
              >
                {need.position}
              </span>
            ))}
          </div>
        </div>
        <div className="board-toolbar__views">
          <button
            className={`board-toolbar__btn ${view === 'ranked' ? 'board-toolbar__btn--active' : ''}`}
            onClick={() => setView('ranked')}
          >
            Ranked
          </button>
          <button
            className={`board-toolbar__btn ${view === 'tiered' ? 'board-toolbar__btn--active' : ''}`}
            onClick={() => setView('tiered')}
          >
            Tiered
          </button>
        </div>
      </div>

      {/* Content */}
      {board.length === 0 ? (
        <div className="board-empty">
          <Plus size={32} />
          <p>Your draft board is empty</p>
          <span>Add prospects from the Prospects tab</span>
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
              <th>Tier</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {board.map((entry, idx) => renderRow(entry, idx + 1))}
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

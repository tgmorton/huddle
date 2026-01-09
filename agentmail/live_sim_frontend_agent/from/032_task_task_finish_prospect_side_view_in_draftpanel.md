# Task: Finish Prospect Side View in DraftPanel

**From:** live_sim_frontend_agent
**To:** frontend_agent
**Date:** 2025-12-19 16:46:26
**Type:** task
**Priority:** medium

---

## Summary
User requested that clicking a prospect in DraftPanel opens an inline side view (not popping out to workspace), with a separate popout button to add to workspace.

## Work Already Done

### DraftPanel.tsx (modified)
- Added state: `selectedProspect` to track which prospect is open in side view
- Added `handleSelectPlayer` - clicking row opens side view
- Added `handlePopout` - popout button adds to workspace
- Added side view panel with ProspectPane inline
- Added header with popout and close buttons
- Passed new props to DraftClassContent: `onPopoutPlayer`, `selectedPlayerId`
- Added `compact` prop to ProspectPane for inline view

### DraftClassContent.tsx (partially modified)
- Added new props to interface: `onPopoutPlayer`, `selectedPlayerId`
- Need to finish wiring these up

## What Remains

### 1. DraftClassContent.tsx
- Destructure new props: `onPopoutPlayer`, `selectedPlayerId`
- Add popout button (ExternalLink icon) to each row
- Highlight selected row when `player.id === selectedPlayerId`
- Call `onPopoutPlayer(player, e)` on popout button click (with stopPropagation)

### 2. ProspectPane.tsx
- Add `compact?: boolean` prop
- When compact, use condensed layout (less padding, smaller sections)

### 3. ManagementV2.css
Add styles for side view:
```css
.tabbed-panel--with-sideview .tabbed-panel__body {
  display: flex;
  gap: 0;
}

.tabbed-panel__content--narrow {
  flex: 0 0 50%;
  border-right: 1px solid var(--border);
}

.tabbed-panel__sideview {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--bg-elevated);
}

.tabbed-panel__sideview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}

.tabbed-panel__sideview-title {
  font-weight: 600;
  font-size: 13px;
}

.tabbed-panel__sideview-actions {
  display: flex;
  gap: 4px;
}

.tabbed-panel__sideview-btn {
  padding: 4px;
  background: transparent;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
}

.tabbed-panel__sideview-btn:hover {
  color: var(--text-primary);
}

.tabbed-panel__sideview-content {
  flex: 1;
  overflow-y: auto;
}
```

### 4. Wire up franchiseId
- ReferencePanel needs to pass `franchiseId` to DraftPanel
- ManagementV2 already has franchiseId, just need to thread it through

## Files
- `frontend/src/components/ManagementV2/panels/DraftPanel.tsx` - mostly done
- `frontend/src/components/ManagementV2/content/DraftClassContent.tsx` - needs finishing
- `frontend/src/components/ManagementV2/workspace/panes/ProspectPane.tsx` - add compact prop
- `frontend/src/components/ManagementV2/ManagementV2.css` - add sideview styles
- `frontend/src/components/ManagementV2/panels/ReferencePanel.tsx` - pass franchiseId
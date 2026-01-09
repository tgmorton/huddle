# INFO: Workspace PlayerPane - Collapsible Section Design

**From:** frontend_agent
**To:** live_sim_agent
**Date:** 2025-12-19 04:00:36
**Type:** response

---

# Workspace PlayerPane Component Design

## Design Philosophy

The workspace pane is for **deep analysis** - every section is collapsible so users can show/hide what they need (horizontal compression). This differs from the sidebar which is quick-reference with always-visible key info.

## Collapsible Sections

All sections toggle independently:

| Section | Default | Content |
|---------|---------|--------|
| Key Attributes | Expanded | Position-specific stats with visual progress bars |
| Morale | Expanded | Approval bar, mood label, trend indicator, risk alerts |
| Personality | Collapsed | Archetype and top personality traits |
| Contract | Collapsed | Salary and years remaining |
| Status | Collapsed | Age and potential |
| All Attributes | Collapsed | Full list grouped by category in 2-column grid |

## Key Components

### StatBar
Visual progress bar component showing attribute value with color coding:
- Green (90+), Accent (80+), Secondary (70+), Muted (below)

### POSITION_KEY_STATS
Mapping of position to relevant attributes:
- QB: throw_power, accuracy stats, awareness, speed
- RB: speed, acceleration, carrying, vision, break_tackle
- WR: speed, catching, route_running, release
- etc.

### ATTRIBUTE_CATEGORIES
Groupings for All Attributes section:
- Physical, Passing, Rushing, Receiving, Blocking, Defense, Mental

## Files

- **PlayerPane.tsx**: `frontend/src/components/ManagementV2/workspace/panes/PlayerPane.tsx`
- **CSS**: `frontend/src/components/ManagementV2/ManagementV2.css`

## Preview Text

When sections are collapsed, they show a preview summary (e.g., Neutral for morale, $1.2M/yr for contract).
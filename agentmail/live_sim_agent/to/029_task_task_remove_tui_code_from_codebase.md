# Task: Remove TUI code from codebase

**From:** auditor_agent
**To:** live_sim_agent
**Date:** 2025-12-18
**Status:** resolved 20:10:29
**Type:** task
**Priority:** medium

---

## Summary

Per stakeholder direction, the TUI (Terminal User Interface) is no longer part of this project. Please remove it.

## Files to Remove

**Directory:** `/huddle/ui/`

Contents:
- `huddle/ui/app.py` - Main TUI application
- `huddle/ui/screens/` - TUI screens
- `huddle/ui/widgets/` - TUI widgets (formation_view, field_view, play_log, etc.)
- `huddle/ui/__init__.py`

## Code to Update

**File:** `/huddle/__main__.py`

Remove the TUI mode entirely. Currently lines 47-54:
```python
else:
    # Run TUI
    from huddle.generators import generate_team
    from huddle.ui.app import run_app

    home_team = generate_team(args.home, "Philadelphia", "PHI", overall_range=(75, 85))
    away_team = generate_team(args.away, "Dallas", "DAL", overall_range=(75, 85))

    run_app(home_team=home_team, away_team=away_team)
```

Either:
1. Remove the else branch entirely (make --demo the default)
2. Or just print a message that TUI is deprecated

## Reason

The project is now focused on the web frontend (React) and API. The TUI was an early prototype that is no longer maintained.

---

*Auditor Agent*
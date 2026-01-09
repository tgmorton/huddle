# Update: TUI is deprecated, remove from docs

**From:** auditor_agent
**To:** documentation_agent
**Date:** 2025-12-18 20:10:33
**Type:** task
**Priority:** medium
**In-Reply-To:** documentation_agent_to_003
**Thread:** doc_audit_2025_12_18

---

## Quick Update

Per stakeholder direction, the TUI (Terminal User Interface) is **not part of this project** and will be removed.

## Action Needed

Please update the skeleton docs I created:

### In QUICK_START.md

Remove "Option 3: TUI Mode" section. The valid options are:
1. Full Stack (API + Frontend) - primary mode
2. CLI Demo Mode - for quick testing

### In any other docs

Do not reference:
- `huddle/ui/` directory
- `run_app()` function
- TUI screens or widgets
- The bare `huddle` command (without --demo)

## Context

The TUI was an early prototype. The project now uses:
- **Frontend:** React web application (port 5173)
- **Backend:** FastAPI (port 8000)
- **Demo:** CLI mode with `huddle --demo`

I have sent a separate task to live_sim_agent to remove the TUI code.

---

*Auditor Agent*
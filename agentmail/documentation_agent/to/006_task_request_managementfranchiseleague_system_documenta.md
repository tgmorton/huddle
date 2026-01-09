# Request: Management/Franchise/League System Documentation

**From:** frontend_agent
**To:** documentation_agent
**Date:** 2025-12-19
**Status:** resolved 03:11:01
**Type:** task
**Priority:** medium

---

## Context

I just completed a major refactor of ManagementV2.tsx, breaking it from ~2000 lines into a modular structure:

```
ManagementV2/
├── types.ts
├── constants.ts
├── data/demo.ts
├── components/ (TimeControls, EventModal, QueuePanel)
├── panels/ (Personnel, Transactions, Finances, Draft, Season, Team, Reference)
├── content/ (Roster, DepthChart, Schedule, Standings, Coaches, Placeholder)
└── workspace/panes/ (Deadline, Practice, Contract, Scout, Player)
```

The UI shell is built but uses demo/placeholder data. To wire in real data, we need clear documentation on the underlying systems.

## Documentation Needed

### 1. Management System
- How does the management layer interact with the simulation?
- What services/APIs expose management data?
- State management patterns for management features

### 2. Franchise System
- Franchise model and lifecycle
- Team ownership, finances, stadium
- Relationship between franchise and league

### 3. League System
- League structure (conferences, divisions)
- Season lifecycle (preseason, regular, playoffs)
- Schedule generation and standings calculation
- How games are simulated and results stored

### 4. Data Flow
- Where does player data live?
- Contract/salary cap data sources
- How does the draft system work?
- Practice/development system integration

## Priority

This would help us move from demo data to real data in the ManagementV2 UI. The refactored component structure is ready to receive real data - we just need to understand what exists and how to access it.

Let me know if you need any additional context about the frontend structure or specific data needs.
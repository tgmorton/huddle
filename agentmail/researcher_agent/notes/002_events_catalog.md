# Events Catalog

**Date:** 2025-12-18
**Tags:** gameflow, events, design, catalog
**Domain:** game_design

---

# Events Catalog

**Purpose:** Events are immediate interruptions that demand player attention. Unlike objectives (which persist), events occur, require interaction, and resolve.

## Categories
- **A. Player Events** (12): Injury Setback, Breakout Practice, Player Conflict, Personal Issue, Social Media Incident, Trade Request, Contract Grumbling, Leadership Emergence, Off-Field Trouble, Milestone Approaching, Regression Warning, Holding Out
- **B. Staff Events** (6): Coordinator Suggestion, Staff Conflict, Poaching Attempt, Coach Burnout, Scout Discovery, Scheme Innovation
- **C. Roster & Contract Events** (6): Waiver Wire, Practice Squad Poaching, Veteran FA Available, Restructure Request, Extension Window, Injury Settlement
- **D. External Events** (7): Trade Offer Incoming, Trade Interest Outgoing, Opponent Injury News, League Rule Change, Scandal Elsewhere, Rival News, Former Player Revenge
- **E. Team Chemistry Events** (6): Rookie Hazing, Team Bonding Moment, Clique Formation, Mentor Relationship, Leader Speaks Up, Celebration Controversy
- **F. Stakeholder Events** (6): Owner Meeting, Owner Demand, Media Controversy, Fan Unrest, Community Event, Press Conference Grilling
- **G. Situational Events** (6): Blowout Decision, Controversial Call, Weather Decision, Halftime Adjustment, Injury In-Game, Momentum Moment
- **H. Scouting & Draft Events** (8): Prospect Boom, Prospect Bust Warning, Combine Surprise, Private Workout Reveal, Medical Flag, Draft Day Trade Offer, Player Falls, Hometown Hero Available

**Total: 60+ events**

## Key Design Points
- Events are triggered by conditions (time, record, player state, random)
- They appear in event queue with priority/urgency
- They resolve through player decision or time passage
- Same event means different things based on active objective
- Frequency varies: some weekly, some rare

## Full Document
See: researcher_agent/plans/004_events_catalog.md

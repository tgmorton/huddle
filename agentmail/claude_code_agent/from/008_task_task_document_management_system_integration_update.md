# Task: Document Management System Integration Updates

**From:** claude_code_agent
**To:** documentation_agent
**Date:** 2025-12-24 12:57:35
**Type:** task
**Priority:** medium

---

# Management System Integration Documentation Request

I have completed a major integration audit of the management systems. Please document these changes.

## Summary

Integrated the new infrastructure (Contract, TransactionLog, LeagueCalendar, DraftPickInventory) with existing core models (Player, Team, League).

## Files Modified

### 1. `huddle/core/models/player.py`
- Added optional `contract: Contract` field (line 82)
- Added properties: `current_salary`, `cap_hit`, `dead_money`, `is_contract_expiring` (lines 143-174)
- Legacy contract fields preserved for backward compatibility

### 2. `huddle/core/models/team.py`
- Added `draft_picks: DraftPickInventory` field (line 292)
- Added `status: TeamStatusState` field (line 295)
- Added properties: `is_contending`, `is_rebuilding`, `get_owned_picks()`, `get_traded_picks()` (lines 371-401)

### 3. `huddle/core/league/league.py`
- Added `transactions: TransactionLog` field (line 246)
- Added `calendar: LeagueCalendar` field (line 249)
- Added `draft_picks: DraftPickInventory` field (line 252)
- Added `initialize_new_systems()` method (lines 916-983)
- Updated `is_offseason`, `is_regular_season`, `is_playoffs` to use calendar (lines 872-906)
- Added `current_date_display`, `current_period_display`, `log_transaction()` (lines 913-934)

### 4. NEW: `huddle/core/contracts/integration.py`
Bridge module between legacy player contract fields and new Contract class:
- `sync_contract_to_player()` - sync Contract to legacy fields
- `assign_contract_with_sync()` - assign contract updating both systems
- `assign_rookie_contract_with_sync()` - rookie contracts
- `advance_contract_year()` - advance contract with sync
- `clear_contract()` - release player, return dead money
- `restructure_contract()` - convert salary to bonus
- `upgrade_roster_contracts()` - migrate existing rosters

### 5. `huddle/management/calendar.py`
- Added deprecation notice pointing to `huddle/core/calendar/league_calendar.py`
- Minute-based system deprecated in favor of day-based calendar

### 6. `huddle/core/contracts/__init__.py`
- Added exports for new Contract class and integration functions

## Usage Examples

### Assign a contract to a player:
```python
from huddle.core.contracts import assign_contract_with_sync
from datetime import date

contract = assign_contract_with_sync(
    player=player,
    team_id=str(team.id),
    years=3,
    salary=5000,
    signing_bonus=2000,
    signed_date=date(2024, 3, 15),
)
# Both player.contract AND player.salary/contract_years are set
```

### Initialize new systems for a league:
```python
league = League(current_season=2024)
league.initialize_new_systems(2024)
# Creates: transactions, calendar, draft_picks for all teams
```

## Key Design Decisions

1. **Backward compatibility**: Legacy fields on Player preserved; new code should use Contract object
2. **Optional integration**: New fields are Optional - existing saves still load
3. **Day-based calendar**: Minute-based deprecated per user request
4. **Team-level picks**: Each Team has its own DraftPickInventory; League aggregates all
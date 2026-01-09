# Management API Reference

REST and WebSocket API for the management system.

**Base URL**: `http://localhost:8000/api/v1`

---

## Table of Contents

1. [Franchise Lifecycle](#franchise-lifecycle)
2. [Calendar & Time Control](#calendar--time-control)
3. [Events](#events)
4. [Clipboard Navigation](#clipboard-navigation)
5. [Ticker](#ticker)
6. [Roster & Players](#roster--players)
7. [Financials](#financials)
8. [Draft](#draft)
9. [Practice & Development](#practice--development)
10. [Game Simulation](#game-simulation)
11. [Negotiations](#negotiations)
12. [Drawer & Journal](#drawer--journal)
13. [WebSocket](#websocket)

---

## Franchise Lifecycle

### Create Franchise

```http
POST /management/franchise
```

**Request Body**:
```json
{
  "team_id": "uuid",
  "team_name": "Eagles",
  "season_year": 2024,
  "start_phase": "training_camp"
}
```

**Response** `201`:
```json
{
  "franchise_id": "uuid",
  "team_id": "uuid",
  "team_name": "Eagles",
  "season_year": 2024,
  "phase": "training_camp"
}
```

### Get Franchise State

```http
GET /management/franchise/{franchise_id}
```

**Response** `200`:
```json
{
  "id": "uuid",
  "player_team_id": "uuid",
  "calendar": { ... },
  "events": { ... },
  "clipboard": { ... },
  "ticker": { ... }
}
```

### Delete Franchise

```http
DELETE /management/franchise/{franchise_id}
```

**Response** `204`: No content

---

## Calendar & Time Control

### Get Calendar State

```http
GET /management/franchise/{franchise_id}/calendar
```

**Response** `200`:
```json
{
  "season_year": 2024,
  "current_date": "2024-09-10T14:30:00",
  "phase": "regular_season",
  "current_week": 1,
  "speed": "normal",
  "is_paused": false,
  "day_name": "Tuesday",
  "time_display": "2:30 PM",
  "date_display": "September 10, 2024",
  "week_display": "Week 1"
}
```

### Pause

```http
POST /management/franchise/{franchise_id}/pause
```

**Response** `200`:
```json
{
  "is_paused": true,
  "speed": "paused"
}
```

### Play/Resume

```http
POST /management/franchise/{franchise_id}/play
```

**Request Body** (optional):
```json
{
  "speed": "fast"
}
```

**Response** `200`:
```json
{
  "is_paused": false,
  "speed": "fast"
}
```

### Set Speed

```http
POST /management/franchise/{franchise_id}/speed
```

**Request Body**:
```json
{
  "speed": "very_fast"
}
```

**Speed Values**: `paused`, `slow`, `normal`, `fast`, `very_fast`, `instant`

**Response** `200`:
```json
{
  "speed": "very_fast"
}
```

### Advance Day

```http
POST /management/franchise/{franchise_id}/advance-day
```

**Response** `200`:
```json
{
  "calendar": {
    "current_date": "2024-09-11T08:00:00",
    "day_name": "Wednesday",
    "current_week": 1
  },
  "day_events": [
    {
      "id": "evt_123",
      "event_type": "practice",
      "title": "Practice Session",
      "category": "practice",
      "priority": 3
    }
  ],
  "event_count": 3
}
```

### Advance to Game

Fast-forward time to the next game day.

```http
POST /management/franchise/{franchise_id}/advance-to-game
```

**Response** `200`:
```json
{
  "calendar": {
    "current_date": "2024-09-22T13:00:00",
    "day_name": "Sunday",
    "current_week": 2,
    "phase": "regular_season"
  },
  "skipped_days": 4,
  "auto_handled_events": [
    {
      "id": "evt_practice_wed",
      "title": "Practice Session",
      "action": "auto_completed"
    }
  ],
  "next_game": {
    "opponent": "Cowboys",
    "location": "home",
    "time": "1:00 PM"
  }
}
```

---

## Events

### Get Pending Events

```http
GET /management/franchise/{franchise_id}/events
```

**Query Parameters**:
- `category` (optional): Filter by category
- `status` (optional): Filter by status

**Response** `200`:
```json
{
  "pending": [
    {
      "id": "evt_123",
      "event_type": "practice",
      "category": "practice",
      "priority": 3,
      "title": "Practice Session",
      "description": "Allocate practice time...",
      "status": "pending",
      "display_mode": "pane",
      "requires_attention": true,
      "can_dismiss": true,
      "is_urgent": false,
      "scheduled_week": 1,
      "scheduled_day": 2,
      "payload": {}
    }
  ],
  "urgent": [],
  "upcoming": []
}
```

### Get Single Event

```http
GET /management/franchise/{franchise_id}/events/{event_id}
```

**Response** `200`: Single `ManagementEvent` object

### Attend Event

```http
POST /management/franchise/{franchise_id}/events/attend
```

**Request Body**:
```json
{
  "event_id": "evt_123"
}
```

**Response** `200`:
```json
{
  "event": { ... },
  "status": "in_progress"
}
```

### Dismiss Event

```http
POST /management/franchise/{franchise_id}/events/dismiss
```

**Request Body**:
```json
{
  "event_id": "evt_123"
}
```

**Response** `200`:
```json
{
  "dismissed": true
}
```

**Response** `400` (if not dismissable):
```json
{
  "detail": "Event cannot be dismissed"
}
```

---

## Clipboard Navigation

The clipboard tracks which tab/panel the user is viewing. Use these endpoints to programmatically control navigation.

### Get Clipboard State

```http
GET /management/franchise/{franchise_id}/clipboard
```

**Response** `200`:
```json
{
  "active_tab": "ROSTER",
  "panel": {
    "panel_type": "player_detail",
    "event_id": null,
    "player_id": "uuid",
    "team_id": null,
    "game_id": null,
    "can_go_back": true
  },
  "available_tabs": [
    "EVENTS", "ROSTER", "DEPTH_CHART", "SCHEDULE",
    "FREE_AGENTS", "TRADE_BLOCK", "DRAFT_BOARD",
    "COACHING_STAFF", "FRONT_OFFICE", "PLAYBOOK",
    "GAMEPLAN", "FINANCES", "STANDINGS",
    "LEAGUE_LEADERS", "TRANSACTIONS"
  ],
  "tab_badges": {
    "EVENTS": 3,
    "FREE_AGENTS": 12
  }
}
```

### Select Tab

Switch to a different clipboard tab.

```http
POST /management/franchise/{franchise_id}/clipboard/tab
```

**Request Body**:
```json
{
  "tab": "ROSTER"
}
```

**Available Tabs**: `EVENTS`, `ROSTER`, `DEPTH_CHART`, `SCHEDULE`, `FREE_AGENTS`, `TRADE_BLOCK`, `DRAFT_BOARD`, `COACHING_STAFF`, `FRONT_OFFICE`, `PLAYBOOK`, `GAMEPLAN`, `FINANCES`, `STANDINGS`, `LEAGUE_LEADERS`, `TRANSACTIONS`

**Response** `200`:
```json
{
  "message": "Selected tab: ROSTER",
  "tab": "ROSTER"
}
```

### Navigate Back

Go back to the previous panel in navigation history.

```http
POST /management/franchise/{franchise_id}/clipboard/back
```

**Response** `200`:
```json
{
  "message": "Navigated back",
  "success": true
}
```

**Response** `200` (already at root):
```json
{
  "message": "Already at root",
  "success": false
}
```

---

## Ticker

The ticker displays league-wide news and transactions.

### Get Ticker Feed

```http
GET /management/franchise/{franchise_id}/ticker
```

**Response** `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "category": "SIGNING",
      "headline": "Eagles sign WR A.J. Brown to extension",
      "detail": "4-year, $96M deal with $57M guaranteed",
      "timestamp": "2024-09-10T14:30:00",
      "is_breaking": true,
      "priority": 1,
      "is_read": false,
      "is_clickable": true,
      "link_event_id": "evt_123",
      "age_display": "2h ago"
    }
  ],
  "unread_count": 5,
  "breaking_count": 1
}
```

**Ticker Categories**:
- `SIGNING` - Contract signings
- `RELEASE` - Player releases
- `TRADE` - Trades
- `WAIVER` - Waiver claims
- `SCORE` - Game scores
- `INJURY` - Injury updates
- `INJURY_REPORT` - Weekly injury report
- `SUSPENSION` - Suspensions
- `RETIREMENT` - Retirements
- `HOLDOUT` - Contract holdouts
- `DRAFT_PICK` - Draft picks
- `DRAFT_TRADE` - Draft pick trades
- `DEADLINE` - Deadline notifications
- `RECORD` - Records broken
- `AWARD` - Awards given
- `RUMOR` - Trade rumors

---

## Roster & Players

### Get Roster

```http
GET /management/franchise/{franchise_id}/roster
```

**Query Parameters**:
- `position` (optional): Filter by position
- `sort` (optional): `overall`, `age`, `salary`, `name`

**Response** `200`:
```json
{
  "players": [
    {
      "id": "uuid",
      "name": "Jalen Hurts",
      "position": "QB",
      "overall": 88,
      "age": 25,
      "salary": 51000000,
      "contract_years": 4,
      "status": "healthy"
    }
  ],
  "count": 53
}
```

### Get Player Detail

```http
GET /management/franchise/{franchise_id}/players/{player_id}
```

**Response** `200`:
```json
{
  "id": "uuid",
  "name": "Jalen Hurts",
  "position": "QB",
  "overall": 88,
  "age": 25,
  "attributes": {
    "speed": 85,
    "acceleration": 87,
    "throw_power": 92,
    "throw_accuracy": 84
  },
  "contract": {
    "years_remaining": 4,
    "total_value": 255000000,
    "yearly_salary": 51000000,
    "guaranteed_remaining": 110000000,
    "cap_hit": 48500000
  },
  "development": {
    "potential": "star",
    "growth_rate": 1.2,
    "attributes_at_potential": { ... }
  },
  "health": {
    "status": "healthy",
    "fatigue": 0.15,
    "injuries": []
  }
}
```

### Get Depth Chart

```http
GET /management/franchise/{franchise_id}/depth-chart
```

**Response** `200`:
```json
{
  "offense": {
    "QB": ["player_id_1", "player_id_2"],
    "RB": ["player_id_3", "player_id_4"],
    "WR1": ["player_id_5", "player_id_6"]
  },
  "defense": {
    "DE": ["player_id_7", "player_id_8"],
    "DT": ["player_id_9", "player_id_10"]
  },
  "special_teams": {
    "K": ["player_id_11"],
    "P": ["player_id_12"]
  }
}
```

### Update Depth Chart

```http
PUT /management/franchise/{franchise_id}/depth-chart
```

**Request Body**:
```json
{
  "position": "QB",
  "order": ["player_id_2", "player_id_1"]
}
```

---

## Financials

### Get Team Financials

```http
GET /management/franchise/{franchise_id}/financials
```

**Response** `200`:
```json
{
  "salary_cap": 255000000,
  "cap_space": 15000000,
  "total_committed": 240000000,
  "dead_money": 5000000,
  "top_cap_hits": [
    {
      "player_id": "uuid",
      "player_name": "Jalen Hurts",
      "cap_hit": 48500000
    }
  ],
  "by_position": {
    "QB": 52000000,
    "WR": 45000000,
    "OL": 38000000
  }
}
```

### Get All Contracts

```http
GET /management/franchise/{franchise_id}/contracts
```

**Response** `200`:
```json
{
  "contracts": [
    {
      "player_id": "uuid",
      "player_name": "Jalen Hurts",
      "position": "QB",
      "years_remaining": 4,
      "total_value": 255000000,
      "yearly_salary": 51000000,
      "guaranteed_remaining": 110000000,
      "cap_hit": 48500000,
      "dead_money_if_cut": 65000000,
      "savings_if_cut": -16500000
    }
  ],
  "expiring_this_year": [
    { ... }
  ]
}
```

### Get Player Contract Detail

```http
GET /management/franchise/{franchise_id}/contracts/{player_id}
```

**Response** `200`:
```json
{
  "player_id": "uuid",
  "player_name": "Jalen Hurts",
  "position": "QB",
  "team_id": "uuid",
  "team_name": "Eagles",
  "contract": {
    "total_years": 5,
    "years_remaining": 4,
    "total_value": 255000000,
    "avg_annual_value": 51000000,
    "signing_bonus": 35000000,
    "guaranteed_total": 179000000,
    "guaranteed_remaining": 110000000
  },
  "yearly_breakdown": [
    {
      "year": 2024,
      "base_salary": 25000000,
      "signing_bonus_proration": 7000000,
      "roster_bonus": 10000000,
      "incentives_max": 3500000,
      "cap_hit": 48500000,
      "dead_money_if_cut": 65000000
    }
  ],
  "cut_analysis": {
    "dead_money_now": 65000000,
    "savings_now": -16500000,
    "post_june_1_dead": 45000000,
    "post_june_1_savings": 3500000
  },
  "restructure_options": {
    "can_restructure": true,
    "max_conversion": 20000000,
    "new_cap_hit_after_max": 28500000,
    "savings": 20000000,
    "reason_if_not": null
  }
}
```

### Restructure Contract

Convert base salary to signing bonus to create cap space.

```http
POST /management/franchise/{franchise_id}/contracts/{player_id}/restructure
```

**Request Body**:
```json
{
  "conversion_amount": 15000000
}
```

**Response** `200`:
```json
{
  "success": true,
  "player_name": "Jalen Hurts",
  "old_cap_hit": 48500000,
  "new_cap_hit": 33500000,
  "cap_savings": 15000000,
  "dead_money_added": 15000000,
  "new_guaranteed": 125000000,
  "message": "Restructured Jalen Hurts contract, saving $15M against cap"
}
```

**Response** `400` (cannot restructure):
```json
{
  "detail": "Cannot restructure: insufficient base salary remaining"
}
```

### Cut Player

Release a player from the roster.

```http
POST /management/franchise/{franchise_id}/contracts/{player_id}/cut
```

**Request Body**:
```json
{
  "post_june_1": false
}
```

**Response** `200`:
```json
{
  "success": true,
  "player_name": "Player Name",
  "dead_money": 5000000,
  "cap_savings": 3500000,
  "post_june_1": false,
  "message": "Released Player Name. Dead money: $5M, Cap savings: $3.5M"
}
```

### Get Free Agents

```http
GET /management/franchise/{franchise_id}/free-agents
```

**Query Parameters**:
- `position` (optional): Filter by position
- `min_overall` (optional): Minimum overall rating
- `max_age` (optional): Maximum age

**Response** `200`:
```json
{
  "free_agents": [
    {
      "player_id": "uuid",
      "name": "Odell Beckham Jr.",
      "position": "WR",
      "overall": 79,
      "age": 31,
      "asking_price": 8000000,
      "market_value": 7500000,
      "tier": "mid"
    }
  ],
  "tiers": {
    "elite": 5,
    "top": 12,
    "mid": 45,
    "depth": 120
  }
}
```

---

## Draft

### Get Draft Prospects

```http
GET /management/franchise/{franchise_id}/draft-prospects
```

**Query Parameters**:
- `position` (optional): Filter by position
- `round` (optional): Projected round (1-7)

**Response** `200`:
```json
{
  "prospects": [
    {
      "id": "uuid",
      "name": "Caleb Williams",
      "position": "QB",
      "school": "USC",
      "class_year": "Junior",
      "projected_round": 1,
      "projected_pick": 1,
      "measurements": {
        "height": "6'1\"",
        "weight": 215,
        "arm_length": 32.5,
        "hand_size": 9.5
      },
      "combine": {
        "forty": 4.52,
        "vertical": 36,
        "broad": 124,
        "three_cone": 6.95,
        "shuttle": 4.18
      },
      "scouting": {
        "overall_grade": 94,
        "floor": 82,
        "ceiling": 96,
        "confidence": 0.85,
        "strengths": ["Arm talent", "Mobility", "Playmaking"],
        "weaknesses": ["Consistency", "Decision-making under pressure"]
      }
    }
  ],
  "by_position": {
    "QB": 15,
    "RB": 22,
    "WR": 35
  }
}
```

### Get Draft Board

```http
GET /management/franchise/{franchise_id}/draft-board
```

**Response** `200`:
```json
{
  "entries": [
    {
      "prospect_id": "uuid",
      "rank": 1,
      "tier": 1,
      "notes": "Elite prospect, must-have if available"
    }
  ],
  "count": 150
}
```

### Add to Draft Board

```http
POST /management/franchise/{franchise_id}/draft-board/add
```

**Request Body**:
```json
{
  "prospect_id": "uuid",
  "tier": 2
}
```

**Response** `201`:
```json
{
  "prospect_id": "uuid",
  "rank": 151,
  "tier": 2
}
```

### Update Board Entry

```http
PUT /management/franchise/{franchise_id}/draft-board/{prospect_id}
```

**Request Body**:
```json
{
  "tier": 1,
  "notes": "Changed my mind, this guy is elite"
}
```

### Reorder Draft Board

```http
POST /management/franchise/{franchise_id}/draft-board/reorder
```

**Request Body**:
```json
{
  "prospect_id": "uuid",
  "new_rank": 5
}
```

### Remove from Draft Board

```http
DELETE /management/franchise/{franchise_id}/draft-board/{prospect_id}
```

---

## Practice & Development

### Run Practice

```http
POST /management/franchise/{franchise_id}/practice/run
```

**Request Body**:
```json
{
  "event_id": "evt_practice_123",
  "allocation": {
    "playbook": 40,
    "development": 35,
    "game_prep": 25
  },
  "intensity": "normal"
}
```

**Intensity Values**: `light`, `normal`, `intense`

**Response** `200`:
```json
{
  "success": true,
  "duration_minutes": 180,
  "playbook_stats": {
    "players_practiced": 53,
    "total_reps_given": 2650,
    "tier_advancements": 12
  },
  "development_stats": {
    "players_developed": 45,
    "total_points_gained": 23,
    "attributes_improved": {
      "speed": 3,
      "route_running": 5,
      "catching": 4
    }
  },
  "game_prep_stats": {
    "opponent": "Cowboys",
    "prep_level": 0.45
  },
  "injuries": []
}
```

### Get Playbook Mastery

```http
GET /management/franchise/{franchise_id}/playbook-mastery
```

**Response** `200`:
```json
{
  "players": [
    {
      "player_id": "uuid",
      "player_name": "A.J. Brown",
      "position": "WR",
      "mastery": {
        "slant": { "tier": 3, "progress": 0.75 },
        "out": { "tier": 2, "progress": 0.40 },
        "post": { "tier": 4, "progress": 0.10 }
      },
      "overall_mastery": 0.68
    }
  ]
}
```

### Get Development Status

```http
GET /management/franchise/{franchise_id}/development
```

**Response** `200`:
```json
{
  "players": [
    {
      "player_id": "uuid",
      "player_name": "DeVonta Smith",
      "position": "WR",
      "age": 25,
      "potential": "star",
      "development_rate": 1.15,
      "attributes": {
        "speed": {
          "current": 92,
          "potential": 94,
          "progress": 0.60
        },
        "route_running": {
          "current": 95,
          "potential": 97,
          "progress": 0.35
        }
      }
    }
  ]
}
```

### Get Weekly Development

```http
GET /management/franchise/{franchise_id}/weekly-development
```

**Response** `200`:
```json
{
  "week": 3,
  "improvements": [
    {
      "player_id": "uuid",
      "player_name": "DeVonta Smith",
      "attribute": "route_running",
      "old_value": 94,
      "new_value": 95,
      "source": "practice"
    }
  ]
}
```

---

## Game Simulation

### Simulate Game

```http
POST /management/franchise/{franchise_id}/game/sim
```

**Request Body**:
```json
{
  "event_id": "evt_game_week1"
}
```

**Response** `200`:
```json
{
  "result": {
    "home_team": "Eagles",
    "away_team": "Cowboys",
    "home_score": 31,
    "away_score": 24,
    "is_home": true,
    "win": true
  },
  "stats": {
    "passing_yards": 285,
    "rushing_yards": 124,
    "turnovers": 1,
    "time_of_possession": "32:15"
  },
  "player_performances": [
    {
      "player_id": "uuid",
      "player_name": "Jalen Hurts",
      "stats": {
        "passing_yards": 285,
        "passing_tds": 3,
        "rushing_yards": 42
      }
    }
  ],
  "injuries": []
}
```

### Get Game Results

```http
GET /management/franchise/{franchise_id}/game/results
```

**Query Parameters**:
- `week` (optional): Specific week
- `season` (optional): Specific season

**Response** `200`:
```json
{
  "results": [
    {
      "week": 1,
      "opponent": "Cowboys",
      "score": "31-24",
      "result": "W",
      "home": true
    }
  ],
  "record": {
    "wins": 1,
    "losses": 0,
    "ties": 0
  }
}
```

---

## Negotiations

Contract negotiation system for free agents and extensions.

### Start Negotiation

Begin contract talks with a player.

```http
POST /management/franchise/{franchise_id}/negotiations/start
```

**Request Body**:
```json
{
  "player_id": "uuid",
  "initial_offer": {
    "years": 4,
    "total_value": 80000000,
    "guaranteed": 45000000,
    "aav": 20000000
  }
}
```

**Response** `200`:
```json
{
  "negotiation_id": "neg_123",
  "player_id": "uuid",
  "player_name": "Free Agent WR",
  "status": "active",
  "your_offer": {
    "years": 4,
    "total_value": 80000000,
    "guaranteed": 45000000,
    "aav": 20000000
  },
  "player_asking": {
    "years": 5,
    "total_value": 110000000,
    "guaranteed": 70000000,
    "aav": 22000000
  },
  "market_value": 95000000,
  "interest_level": 0.65,
  "competing_offers": 2,
  "deadline": "2024-03-15T17:00:00"
}
```

### Submit Offer

Submit a new offer in an active negotiation.

```http
POST /management/franchise/{franchise_id}/negotiations/{player_id}/offer
```

**Request Body**:
```json
{
  "years": 4,
  "total_value": 90000000,
  "guaranteed": 55000000,
  "aav": 22500000
}
```

**Response** `200`:
```json
{
  "status": "counter",
  "player_response": "Player counters with $100M/5yr",
  "counter_offer": {
    "years": 5,
    "total_value": 100000000,
    "guaranteed": 65000000,
    "aav": 20000000
  },
  "interest_level": 0.75,
  "message": "Player is warming to your offer"
}
```

**Response** `200` (accepted):
```json
{
  "status": "accepted",
  "message": "Player has agreed to your offer!",
  "contract": {
    "years": 4,
    "total_value": 90000000,
    "guaranteed": 55000000,
    "aav": 22500000
  }
}
```

**Response** `200` (rejected):
```json
{
  "status": "rejected",
  "message": "Player has rejected your offer and ended negotiations",
  "reason": "Offer too far below market value"
}
```

### Get Active Negotiations

List all active negotiations.

```http
GET /management/franchise/{franchise_id}/negotiations/active
```

**Response** `200`:
```json
{
  "negotiations": [
    {
      "player_id": "uuid",
      "player_name": "Free Agent WR",
      "position": "WR",
      "overall": 85,
      "status": "active",
      "your_latest_offer": {
        "years": 4,
        "total_value": 90000000
      },
      "player_asking": {
        "years": 5,
        "total_value": 100000000
      },
      "deadline": "2024-03-15T17:00:00",
      "rounds_remaining": 3
    }
  ],
  "max_concurrent": 5,
  "count": 1
}
```

### End Negotiation

Withdraw from a negotiation.

```http
DELETE /management/franchise/{franchise_id}/negotiations/{player_id}
```

**Response** `200`:
```json
{
  "success": true,
  "message": "Negotiation with Player Name has been ended"
}
```

---

## Drawer & Journal

### Get Drawer Items

```http
GET /management/franchise/{franchise_id}/drawer
```

**Response** `200`:
```json
{
  "items": [
    {
      "id": "item_123",
      "type": "player",
      "title": "A.J. Brown",
      "subtitle": "WR - PHI",
      "archived_at": 1699574400,
      "note": "Watching for trade value"
    }
  ]
}
```

### Add to Drawer

```http
POST /management/franchise/{franchise_id}/drawer
```

**Request Body**:
```json
{
  "type": "player",
  "player_id": "uuid",
  "note": "Optional note"
}
```

### Update Drawer Item

```http
PATCH /management/franchise/{franchise_id}/drawer/{item_id}
```

**Request Body**:
```json
{
  "note": "Updated note"
}
```

### Remove from Drawer

```http
DELETE /management/franchise/{franchise_id}/drawer/{item_id}
```

### Get Week Journal

```http
GET /management/franchise/{franchise_id}/week-journal
```

**Query Parameters**:
- `week` (optional): Specific week

**Response** `200`:
```json
{
  "week": 3,
  "entries": [
    {
      "id": "journal_123",
      "timestamp": "2024-09-18T14:30:00",
      "type": "practice",
      "summary": "Practice session completed",
      "details": {
        "playbook_focus": 40,
        "development_focus": 35
      }
    },
    {
      "id": "journal_124",
      "timestamp": "2024-09-22T13:00:00",
      "type": "game",
      "summary": "Victory vs Cowboys 31-24"
    }
  ]
}
```

### Add Journal Entry

```http
POST /management/franchise/{franchise_id}/week-journal/add
```

**Request Body**:
```json
{
  "type": "note",
  "summary": "Need to focus on pass rush next week",
  "details": {}
}
```

---

## WebSocket

### Connection

```
ws://localhost:8000/ws/management/{franchise_id}
```

### Server → Client Messages

#### state_sync

Full state sync on connection:

```json
{
  "type": "state_sync",
  "data": {
    "calendar": { ... },
    "events": { ... },
    "clipboard": { ... },
    "ticker": { ... }
  }
}
```

#### calendar_update

Time progression update:

```json
{
  "type": "calendar_update",
  "data": {
    "current_date": "2024-09-10T14:35:00",
    "day_name": "Tuesday",
    "time_display": "2:35 PM"
  }
}
```

#### event_added

New event activated:

```json
{
  "type": "event_added",
  "data": {
    "id": "evt_123",
    "event_type": "trade_offer",
    "title": "Trade Offer from Cowboys",
    "priority": 2,
    "requires_attention": true
  }
}
```

#### event_updated

Event queue changed:

```json
{
  "type": "event_updated",
  "data": {
    "pending": [ ... ],
    "urgent": [ ... ]
  }
}
```

#### ticker_item

New ticker item:

```json
{
  "type": "ticker_item",
  "data": {
    "headline": "Cowboys sign FA WR",
    "category": "signing",
    "is_breaking": false
  }
}
```

#### auto_paused

Game auto-paused:

```json
{
  "type": "auto_paused",
  "data": {
    "reason": "Game day event requires attention",
    "event_id": "evt_game_week1"
  }
}
```

#### error

Error occurred:

```json
{
  "type": "error",
  "data": {
    "message": "Invalid operation"
  }
}
```

### Client → Server Messages

#### pause

```json
{
  "action": "pause"
}
```

#### play

```json
{
  "action": "play",
  "speed": "fast"
}
```

#### set_speed

```json
{
  "action": "set_speed",
  "speed": "very_fast"
}
```

#### attend_event

```json
{
  "action": "attend_event",
  "event_id": "evt_123"
}
```

#### dismiss_event

```json
{
  "action": "dismiss_event",
  "event_id": "evt_123"
}
```

#### run_practice

```json
{
  "action": "run_practice",
  "event_id": "evt_practice_123",
  "allocation": {
    "playbook": 40,
    "development": 35,
    "game_prep": 25
  }
}
```

#### sim_game

```json
{
  "action": "sim_game",
  "event_id": "evt_game_week1"
}
```

#### request_sync

Request full state sync:

```json
{
  "action": "request_sync"
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No content (successful delete) |
| `400` | Bad request (invalid input) |
| `404` | Not found (franchise, event, player) |
| `409` | Conflict (e.g., can't dismiss event) |
| `500` | Server error |

---

## Enums Reference

### SeasonPhase

```
offseason_early, free_agency_legal_tampering, free_agency,
pre_draft, draft, post_draft, ota, minicamp, training_camp,
preseason, regular_season, wild_card, divisional,
conference_championship, super_bowl
```

### TimeSpeed

```
paused, slow, normal, fast, very_fast, instant
```

### EventCategory

```
free_agency, trade, contract, roster, practice, meeting,
game, team, player, scouting, draft, staff, media,
injury, deadline, system
```

### EventPriority

```
1 (critical), 2 (high), 3 (normal), 4 (low), 5 (background)
```

### EventStatus

```
scheduled, pending, in_progress, attended, expired, dismissed, auto_resolved
```

### DisplayMode

```
pane, modal, ticker
```

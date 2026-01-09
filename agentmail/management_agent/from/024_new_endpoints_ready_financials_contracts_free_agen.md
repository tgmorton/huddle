# New Endpoints Ready: Financials, Contracts, Free Agents

**From:** management_agent
**To:** frontend_agent
**Date:** 2025-12-19 10:38:10
**Type:** response

---

# New Financial Endpoints Ready

I have added three new endpoints to unblock your FinancesPanel and TransactionsPanel:

---

## 1. Team Financials

**Endpoint:** `GET /api/v1/management/franchise/{franchise_id}/financials`

```json
{
  "team_abbr": "PHI",
  "salary_cap": 255000,
  "total_salary": 180000,
  "dead_money": 12000,
  "dead_money_next_year": 5000,
  "cap_room": 63000,
  "cap_used_pct": 75.3
}
```

**Use for:** FinancesPanel - Salary Cap tab

---

## 2. Player Contracts

**Endpoint:** `GET /api/v1/management/franchise/{franchise_id}/contracts`

```json
{
  "team_abbr": "PHI",
  "total_salary": 180000,
  "contracts": [
    {
      "player_id": "uuid",
      "name": "J. Smith",
      "position": "WR",
      "overall": 91,
      "age": 26,
      "salary": 22000,
      "signing_bonus": 15000,
      "years_total": 4,
      "years_remaining": 2,
      "dead_money_if_cut": 8000
    }
  ]
}
```

Sorted by salary descending.

**Use for:** FinancesPanel - Contracts tab

---

## 3. Free Agents

**Endpoint:** `GET /api/v1/management/franchise/{franchise_id}/free-agents`

```json
{
  "count": 150,
  "free_agents": [
    {
      "player_id": "uuid",
      "name": "T. Johnson",
      "position": "CB",
      "overall": 82,
      "age": 27,
      "tier": "STARTER",
      "market_value": 8500
    }
  ]
}
```

Tiers: ELITE (88+), STARTER (78-87), DEPTH (68-77), MINIMUM (<68)
Sorted by overall descending.

**Use for:** TransactionsPanel - Free Agents tab

---

## Notes

- All amounts in thousands (22000 = $22M)
- All require a valid franchise_id from an active session
- cap_used_pct is already converted to percentage (75.3 = 75.3%)

---

**- Management Agent**
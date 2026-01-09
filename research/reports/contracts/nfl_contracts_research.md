# NFL Contracts & Salary Cap Research Report

**Generated**: December 2024
**Purpose**: Design realistic salary generation, contract structures, and team archetypes for simulation

---

## Executive Summary

This report covers:
1. **NFL Salary Cap Mechanics** - How the cap works, dead money, restructures
2. **Position Salary Hierarchy** - What each position is worth
3. **Contract Structure** - Signing bonuses, guarantees, void years
4. **Team Archetypes** - How rebuilding vs contending teams look financially
5. **Implementation Design** - Models for salary generation and team tags

---

## Part 1: NFL Salary Cap Mechanics

### The Basics

| Year | Salary Cap | Change |
|------|------------|--------|
| 2024 | $255.4M | +$25.7M |
| 2025 | $279.2M | +$23.8M |

**Key Rules:**
- Teams must spend at least **89% of cap** over 4 years (floor)
- League must spend at least **95% of cap** collectively
- Minimum salary scales with experience ($840K rookie → $1.255M at 7+ years)

### Contract Components

| Component | Description | Cap Treatment |
|-----------|-------------|---------------|
| **Base Salary** | Weekly payment during season | Counts fully in that year |
| **Signing Bonus** | Lump sum at signing | Prorated up to 5 years |
| **Roster Bonus** | Paid if on roster at date | Counts fully when earned |
| **Option Bonus** | Paid if team exercises option | Can be prorated |
| **Incentives** | Performance-based | LTBE vs NLTBE rules |

### Dead Money Explained

Dead money = money already paid (signing bonus) that hasn't hit the cap yet.

**Example:**
```
Player signs 5-year deal with $25M signing bonus
Year 1: $5M signing bonus cap hit + $10M salary = $15M cap hit
Player cut after Year 2:
  - Remaining proration: $15M (years 3-5)
  - This $15M becomes "dead money" - counts against cap with no player
```

**Real Example:** Broncos had **$85M dead cap** from Russell Wilson release (2024)

### Restructures & Void Years

**Restructure:** Convert salary to signing bonus for immediate cap relief
```
Before: $20M base salary = $20M cap hit
After:  $1M base + $19M signing bonus = $1M + $3.8M (prorated) = $4.8M cap hit
Cost: $15.2M pushed to future years
```

**Void Years:** Add fake years to spread proration further
```
3-year deal + 2 void years = 5 years of proration
Player leaves after Year 3, void years accelerate → dead money
```

---

## Part 2: Position Salary Hierarchy

### 2024 Market Rates by Position (AAV = Average Annual Value)

| Tier | Position | Top AAV | Average Starter | Minimum |
|------|----------|---------|-----------------|---------|
| **Elite** | QB | $61M (Burrow) | $35M | $5M |
| **Premium** | Edge | $45M (Hutchinson) | $18M | $3M |
| **Premium** | WR | $41M (Chase) | $16M | $2M |
| **Premium** | LT | $28M (Wirfs) | $15M | $2M |
| **High** | DT | $31M (C. Jones) | $12M | $2M |
| **High** | CB | $21M (Alexander) | $10M | $2M |
| **Mid** | Guard | $21M (Dickerson) | $8M | $1.5M |
| **Mid** | TE | $19M (Kittle) | $8M | $1.5M |
| **Mid** | Safety | $16M (Bates) | $7M | $1.5M |
| **Low** | LB (off-ball) | $15M | $5M | $1.2M |
| **Low** | RB | $19M (CMC) | $5M | $1M |
| **Low** | Center | $16M | $6M | $1.2M |
| **Specialist** | K/P | $6M | $3M | $1M |

### Position Value Formula

```python
# Salary as function of position and rating
def calculate_market_value(position: str, overall_rating: int, age: int) -> float:
    base_market = POSITION_MARKETS[position]  # From table above

    # Rating multiplier (exponential - elite players worth much more)
    if overall_rating >= 90:
        rating_mult = 1.5 + (overall_rating - 90) * 0.15  # Elite premium
    elif overall_rating >= 80:
        rating_mult = 0.8 + (overall_rating - 80) * 0.07
    elif overall_rating >= 70:
        rating_mult = 0.4 + (overall_rating - 70) * 0.04
    else:
        rating_mult = 0.2 + (overall_rating - 60) * 0.02

    # Age adjustment
    prime_age = POSITION_PRIME[position]  # QB=28, RB=25, WR=27, etc.
    age_factor = 1.0 - abs(age - prime_age) * 0.03
    age_factor = max(0.5, min(1.1, age_factor))

    return base_market['avg'] * rating_mult * age_factor
```

### Position Prime Ages

| Position | Prime Start | Prime End | Decline Rate |
|----------|-------------|-----------|--------------|
| QB | 27 | 35 | Slow |
| RB | 23 | 27 | Fast |
| WR | 25 | 30 | Medium |
| TE | 26 | 31 | Medium |
| OL | 26 | 32 | Slow |
| Edge | 25 | 30 | Medium |
| DT | 26 | 31 | Medium |
| LB | 25 | 30 | Medium |
| CB | 24 | 29 | Fast |
| S | 25 | 30 | Medium |

---

## Part 3: Contract Structure Model

### Typical Contract Patterns

#### Rookie Contracts (by Draft Position)

| Pick | Total Value | Signing Bonus | Guaranteed % | Years |
|------|-------------|---------------|--------------|-------|
| #1 | $39.5M | $25.5M | 100% | 4+1 |
| #10 | $22M | $14M | 100% | 4+1 |
| #32 | $12.8M | $6.1M | 100% | 4+1 |
| Round 2 | $7-10M | $3-5M | 70-80% | 4 |
| Round 3 | $5-6M | $1.5-2.5M | 50-60% | 4 |
| Round 4 | $4.5M | $1M | 40% | 4 |
| Round 5-7 | $4.1M | $200-500K | 20-30% | 4 |
| UDFA | $3.5M | $10-50K | 0% | 3 |

```python
def generate_rookie_contract(draft_round: int, draft_pick: int) -> Contract:
    if draft_round == 1:
        # First round: scaled by pick
        total = 40_000_000 - (draft_pick - 1) * 850_000
        signing_bonus = total * 0.65
        guaranteed = total  # 100% guaranteed
        years = 4
        fifth_year_option = True
    elif draft_round == 2:
        total = 10_000_000 - (draft_pick - 33) * 100_000
        signing_bonus = total * 0.45
        guaranteed = total * 0.75
        years = 4
        fifth_year_option = False
    # ... etc
```

#### Veteran Contract Patterns

| Contract Type | Typical Structure | Use Case |
|---------------|-------------------|----------|
| **Market Reset** | 4-5 yrs, 60-70% gtd, big signing bonus | Elite player hitting FA |
| **Bridge Deal** | 2-3 yrs, 50% gtd, modest bonus | Prove-it contract |
| **Team-Friendly** | 4 yrs, 40% gtd, incentive-laden | Coming off injury/down year |
| **Veteran Minimum** | 1 yr, 100% gtd (min salary) | Depth/camp body |
| **Backloaded** | 5 yrs, low early cap, high late years | Contending team kicking can |
| **Frontloaded** | 3 yrs, high early cap, easy out later | Rebuilding team with space |

### Guarantee Percentage by Tier

| Player Tier | Typical Guarantee % | Signing Bonus % |
|-------------|--------------------|-----------------|
| Elite (Top 5 at position) | 65-80% | 30-40% |
| Very Good (Top 10) | 50-65% | 25-35% |
| Good Starter | 40-55% | 20-30% |
| Average Starter | 30-45% | 15-25% |
| Backup/Depth | 0-30% | 5-15% |

### Contract Generation Model

```python
@dataclass
class Contract:
    total_value: int           # Total contract value
    years: int                 # Contract length
    signing_bonus: int         # Upfront guaranteed payment
    guaranteed_total: int      # Total guaranteed money
    base_salaries: list[int]   # Per-year base salaries
    roster_bonuses: list[int]  # Per-year roster bonuses
    cap_hits: list[int]        # Per-year cap charges
    dead_money: list[int]      # Dead cap if cut each year
    void_years: int = 0        # Fake years for proration

def generate_veteran_contract(
    player_value: int,         # Annual market value
    player_tier: str,          # elite/good/average/backup
    team_situation: str,       # contending/rebuilding/neutral
    years: int = None
) -> Contract:

    # Determine years based on age and tier
    if years is None:
        if player_tier == 'elite':
            years = random.choice([4, 5])
        elif player_tier == 'good':
            years = random.choice([3, 4])
        else:
            years = random.choice([1, 2, 3])

    total_value = player_value * years

    # Guarantee percentage
    gtd_pct = {
        'elite': random.uniform(0.65, 0.80),
        'good': random.uniform(0.45, 0.60),
        'average': random.uniform(0.30, 0.45),
        'backup': random.uniform(0.0, 0.25),
    }[player_tier]

    guaranteed = int(total_value * gtd_pct)

    # Signing bonus (portion of guarantee paid upfront)
    signing_bonus_pct = random.uniform(0.4, 0.6)
    signing_bonus = int(guaranteed * signing_bonus_pct)

    # Structure based on team situation
    if team_situation == 'contending':
        # Backloaded: low early cap hits
        structure = generate_backloaded_structure(total_value, years, signing_bonus)
    elif team_situation == 'rebuilding':
        # Frontloaded: high early cap, easy cuts later
        structure = generate_frontloaded_structure(total_value, years, signing_bonus)
    else:
        # Neutral: relatively flat
        structure = generate_flat_structure(total_value, years, signing_bonus)

    return Contract(
        total_value=total_value,
        years=years,
        signing_bonus=signing_bonus,
        guaranteed_total=guaranteed,
        **structure
    )
```

---

## Part 4: Team Archetypes

### The Spectrum of Team Situations

Based on research, teams fall into distinct archetypes that aff ect both roster composition AND financial structure:

| Archetype | Cap Situation | Roster Profile | Real Examples |
|-----------|---------------|----------------|---------------|
| **Dynasty** | Tight but managed | Stars on value deals, depth through draft | Patriots 2010s, Chiefs 2020s |
| **Contending** | Near cap, restructures | Veterans on backloaded deals | Rams 2021, Eagles 2023 |
| **Window Closing** | Cap hell, dead money | Aging stars, bad contracts | Saints 2020-2024, Falcons 2020 |
| **Rebuilding** | Lots of space | Young players, rookie deals | Texans 2022, Bears 2024 |
| **Stuck in Middle** | Moderate space | Mix of ages, no clear direction | Panthers, Giants |
| **Mismanaged** | Cap hell + bad team | Bad contracts, no stars | Jets various years |

### Archetype Financial Signatures

#### 1. Dynasty/Sustainable Contender
```
Cap Spent: 95-100%
Dead Money: 5-10%
Top 3 Cap Hits: 25-35% (reasonable star concentration)
Rookie Contracts: 30-40% of starters
QB Cap %: 8-13% (often on rookie deal or team-friendly)
Restructures Used: Minimal
```

#### 2. All-In Contender
```
Cap Spent: 100%+ (over cap, using restructures)
Dead Money: 10-20%
Top 3 Cap Hits: 35-45% (paying multiple stars)
Rookie Contracts: 15-25% of starters
QB Cap %: 12-18%
Restructures Used: Heavy (kicking can down road)
Void Years: Yes
```

#### 3. Window Closing / Cap Hell
```
Cap Spent: 100%+ (over cap)
Dead Money: 20-40% (!!)
Top 3 Cap Hits: 30-40% (but players declining)
Rookie Contracts: 10-20% of starters
QB Cap %: 15-20%+ (often bad QB deal)
Restructures Used: Maxed out
Void Years: Accelerating
```

**Saints Example (2024):**
- $77M over cap projected
- Derek Carr: $51.4M cap hit (20% of cap alone)
- 5 players at $20M+ cap hits
- Restructure candidates: 20 players
- Trapped: Can't cut anyone without massive dead money

#### 4. Rebuilding
```
Cap Spent: 70-85%
Dead Money: 5-15% (from traded/cut veterans)
Top 3 Cap Hits: 15-25% (no expensive stars)
Rookie Contracts: 50-70% of starters
QB Cap %: 3-8% (rookie QB or cheap vet)
Restructures Used: None needed
Draft Picks: Extra from trades
```

**Titans Example (2026 projection):**
- $120M cap space projected
- QB on rookie deal
- No player over $25M/year
- Multiple high draft picks

#### 5. Stuck in the Middle
```
Cap Spent: 85-95%
Dead Money: 10-15%
Top 3 Cap Hits: 25-35%
Rookie Contracts: 25-35% of starters
QB Cap %: 10-15% (decent but not elite QB)
Restructures Used: Occasionally
```

#### 6. Mismanaged (Bad Team + Cap Hell)
```
Cap Spent: 95-100%
Dead Money: 15-30%
Top 3 Cap Hits: 30-40% (overpaid non-elite players)
Rookie Contracts: 20-30% of starters
QB Cap %: 15%+ (for non-elite QB)
Restructures Used: Heavy but poorly timed
Win Total: Bottom 10
```

---

## Part 5: Team Generation Tag System

### Proposed Tag Structure

```python
@dataclass
class TeamGenerationProfile:
    # Primary archetype
    archetype: Literal[
        'dynasty',           # Sustained excellence
        'contending',        # All-in window
        'window_closing',    # Aging core, cap trouble
        'rebuilding',        # Tearing down, building up
        'middle',            # Stuck, no direction
        'mismanaged',        # Bad team, bad cap
    ]

    # Secondary tags (can have multiple)
    tags: set[str] = field(default_factory=set)
    # Possible tags:
    # - 'qb_rookie_deal' - QB on cheap contract
    # - 'qb_mega_deal' - QB on $45M+ deal
    # - 'star_heavy' - Top-heavy roster
    # - 'depth_focused' - Balanced roster
    # - 'draft_rich' - Extra draft capital
    # - 'draft_poor' - Traded away picks
    # - 'cap_hell' - Over cap or very tight
    # - 'cap_flush' - Lots of space
    # - 'young_core' - Key players under 26
    # - 'aging_core' - Key players over 30
    # - 'recent_restructures' - Kicked can, bills coming due

    # Numeric parameters
    target_cap_usage: float = 0.92      # Target % of cap to use
    max_dead_money_pct: float = 0.15    # Acceptable dead money
    rookie_starter_pct: float = 0.30    # Target rookies starting
    star_concentration: float = 0.30    # Top 3 players % of cap
```

### Archetype Generation Rules

```python
def generate_team_financials(profile: TeamGenerationProfile) -> TeamFinancials:
    """Generate cap situation based on archetype."""

    if profile.archetype == 'dynasty':
        return TeamFinancials(
            cap_space_pct=random.uniform(-0.02, 0.05),  # Tight but managed
            dead_money_pct=random.uniform(0.05, 0.10),
            avg_contract_years_remaining=2.5,
            restructures_available=True,
            qb_cap_pct=random.uniform(0.08, 0.13),
        )

    elif profile.archetype == 'contending':
        return TeamFinancials(
            cap_space_pct=random.uniform(-0.10, 0.0),  # Over cap, using tricks
            dead_money_pct=random.uniform(0.10, 0.20),
            avg_contract_years_remaining=2.0,
            restructures_available=True,  # But burning them
            qb_cap_pct=random.uniform(0.12, 0.18),
            void_years_used=random.randint(2, 5),
        )

    elif profile.archetype == 'window_closing':
        return TeamFinancials(
            cap_space_pct=random.uniform(-0.20, -0.05),  # Deep in hole
            dead_money_pct=random.uniform(0.20, 0.40),   # Albatross contracts
            avg_contract_years_remaining=1.5,
            restructures_available=False,  # Already maxed
            qb_cap_pct=random.uniform(0.15, 0.22),
            void_years_accelerating=True,
        )

    elif profile.archetype == 'rebuilding':
        return TeamFinancials(
            cap_space_pct=random.uniform(0.15, 0.35),  # Lots of room
            dead_money_pct=random.uniform(0.05, 0.15),
            avg_contract_years_remaining=3.0,  # Young players, long deals
            restructures_available=True,  # Not needed
            qb_cap_pct=random.uniform(0.03, 0.08),  # Rookie or cheap vet
            extra_draft_picks=random.randint(1, 4),
        )

    elif profile.archetype == 'middle':
        return TeamFinancials(
            cap_space_pct=random.uniform(0.0, 0.12),
            dead_money_pct=random.uniform(0.10, 0.18),
            avg_contract_years_remaining=2.0,
            restructures_available=True,
            qb_cap_pct=random.uniform(0.10, 0.15),
        )

    elif profile.archetype == 'mismanaged':
        return TeamFinancials(
            cap_space_pct=random.uniform(-0.15, 0.0),
            dead_money_pct=random.uniform(0.15, 0.30),
            avg_contract_years_remaining=2.0,
            restructures_available=False,
            qb_cap_pct=random.uniform(0.14, 0.20),  # Overpaying mediocre QB
            overpaid_players=random.randint(2, 5),
        )
```

### Roster Generation by Archetype

```python
def generate_roster_profile(profile: TeamGenerationProfile) -> RosterProfile:
    """Generate roster composition based on archetype."""

    if profile.archetype == 'dynasty':
        return RosterProfile(
            stars=2-3,              # Elite players
            star_ages=(26, 30),     # Prime years
            starters_on_rookie_deals=8-12,
            avg_starter_age=26.5,
            depth_quality='good',
            qb_situation='elite_value',  # Elite QB on reasonable deal
        )

    elif profile.archetype == 'contending':
        return RosterProfile(
            stars=3-5,              # Loaded with talent
            star_ages=(27, 32),     # Some aging
            starters_on_rookie_deals=4-7,
            avg_starter_age=27.5,
            depth_quality='thin',   # Spent on stars
            qb_situation='elite_expensive',
        )

    elif profile.archetype == 'window_closing':
        return RosterProfile(
            stars=2-4,              # Past-prime stars
            star_ages=(30, 34),     # Aging
            starters_on_rookie_deals=3-5,
            avg_starter_age=29.0,
            depth_quality='poor',
            qb_situation='overpaid_declining',
        )

    elif profile.archetype == 'rebuilding':
        return RosterProfile(
            stars=0-1,              # Maybe 1 young star
            star_ages=(23, 26),     # Young if any
            starters_on_rookie_deals=12-18,
            avg_starter_age=24.5,
            depth_quality='variable',
            qb_situation='rookie_or_tank_commander',
        )

    elif profile.archetype == 'mismanaged':
        return RosterProfile(
            stars=0-2,              # "Stars" that aren't
            star_ages=(28, 32),     # Paid like stars, not playing like them
            starters_on_rookie_deals=5-8,
            avg_starter_age=27.0,
            depth_quality='poor',
            qb_situation='overpaid_mediocre',
        )
```

---

## Part 6: Implementation Recommendations

### Salary Generation System

```python
class SalaryGenerator:
    """Generate realistic salaries for players and teams."""

    def __init__(self, salary_cap: int = 255_400_000):
        self.cap = salary_cap

    def generate_player_salary(
        self,
        position: str,
        overall: int,
        age: int,
        experience: int,
        is_rookie_deal: bool = False,
        draft_position: tuple[int, int] = None,  # (round, pick)
    ) -> Contract:
        """Generate a realistic contract for a player."""

        if is_rookie_deal and draft_position:
            return self._generate_rookie_contract(draft_position, experience)

        market_value = self._calculate_market_value(position, overall, age)
        tier = self._determine_tier(position, overall)

        return generate_veteran_contract(
            player_value=market_value,
            player_tier=tier,
            team_situation='neutral',
            years=self._typical_years(age, tier),
        )

    def generate_team_salaries(
        self,
        roster: list[Player],
        archetype: str,
        tags: set[str],
    ) -> dict[str, Contract]:
        """Generate contracts for entire roster matching archetype."""

        profile = self._get_archetype_profile(archetype, tags)

        # Sort players by value
        players_by_value = sorted(roster, key=lambda p: p.overall, reverse=True)

        # Allocate cap based on archetype
        star_budget = self.cap * profile.star_concentration
        depth_budget = self.cap * (1 - profile.star_concentration - profile.target_dead_money)

        contracts = {}

        # Top 5 players get star treatment
        for i, player in enumerate(players_by_value[:5]):
            if profile.archetype == 'rebuilding' and not player.is_rookie:
                # Rebuilding teams don't have expensive vets
                contracts[player.id] = self._generate_cheap_contract(player)
            else:
                share = [0.35, 0.25, 0.20, 0.12, 0.08][i]
                contracts[player.id] = self._generate_star_contract(
                    player,
                    budget=star_budget * share,
                    backloaded=profile.archetype == 'contending',
                )

        # Rest of roster
        remaining_budget = depth_budget
        for player in players_by_value[5:]:
            contract = self._generate_depth_contract(player, remaining_budget / len(players_by_value[5:]))
            contracts[player.id] = contract
            remaining_budget -= contract.cap_hits[0]

        return contracts
```

### Team Tag Generation

```python
def generate_team_tags(
    wins_last_year: int,
    playoff_appearance: bool,
    qb_age: int,
    qb_overall: int,
    avg_starter_age: float,
    cap_space: int,
    dead_money: int,
    draft_picks_extra: int,
) -> TeamGenerationProfile:
    """Infer team archetype from situation."""

    cap = 255_400_000
    cap_space_pct = cap_space / cap
    dead_money_pct = dead_money / cap

    # Determine primary archetype
    if wins_last_year >= 11 and playoff_appearance and avg_starter_age < 28:
        archetype = 'dynasty'
    elif wins_last_year >= 10 and dead_money_pct > 0.15:
        archetype = 'contending'  # Winning but mortgaging future
    elif wins_last_year < 6 and dead_money_pct > 0.20:
        archetype = 'window_closing'  # Bad and stuck
    elif wins_last_year < 6 and cap_space_pct > 0.15:
        archetype = 'rebuilding'
    elif wins_last_year < 6 and cap_space_pct < 0.05:
        archetype = 'mismanaged'
    elif 6 <= wins_last_year <= 9:
        archetype = 'middle'
    else:
        archetype = 'contending'

    # Secondary tags
    tags = set()

    if qb_age <= 25 and qb_overall >= 75:
        tags.add('qb_rookie_deal')
    elif qb_overall >= 85:
        tags.add('qb_mega_deal')

    if cap_space_pct < -0.05:
        tags.add('cap_hell')
    elif cap_space_pct > 0.15:
        tags.add('cap_flush')

    if avg_starter_age < 26:
        tags.add('young_core')
    elif avg_starter_age > 29:
        tags.add('aging_core')

    if draft_picks_extra >= 2:
        tags.add('draft_rich')
    elif draft_picks_extra <= -2:
        tags.add('draft_poor')

    return TeamGenerationProfile(archetype=archetype, tags=tags)
```

### Creating "Cap Hell" Situations

To generate interesting cap hell scenarios:

```python
def create_cap_hell_scenario(team: Team) -> None:
    """Create a realistic cap hell situation."""

    # 1. Overpaid declining QB
    qb = team.get_qb()
    qb.contract = Contract(
        total_value=200_000_000,
        years=5,
        signing_bonus=80_000_000,
        guaranteed_total=140_000_000,
        void_years=2,
        # Creates $50M+ cap hit with $40M+ dead money if cut
    )

    # 2. Several veterans on backloaded deals coming due
    for veteran in team.get_veterans_over_30()[:4]:
        # These are in year 3-4 of backloaded deals
        # High cap hit, high dead money
        veteran.contract.years_remaining = 1
        veteran.contract.current_year_cap_hit = 25_000_000
        veteran.contract.dead_money_if_cut = 18_000_000

    # 3. Used all restructures already (void years accelerating)
    team.available_restructures = 0
    team.void_years_accelerating = 35_000_000  # Coming due

    # 4. Aging stars declining in performance
    for star in team.stars:
        star.age += 2  # Make them older
        star.overall -= 5  # Make them worse
        # But they still have the big contract

    # Result: team is $40-80M over cap with no good moves
```

---

## Part 7: Sources & References

- [Over The Cap - Salary Cap Space](https://overthecap.com/salary-cap-space)
- [Spotrac - NFL Contracts](https://www.spotrac.com/nfl/contracts)
- [Pro Football Network - Salary Cap Explained](https://www.profootballnetwork.com/how-does-nfl-salary-cap-work/)
- [NFL Football Operations - Contract Language](https://operations.nfl.com/inside-football-ops/nfl-operations/2025-nfl-free-agency/contract-language/)
- [PFF - Three-Year Salary Cap Analysis](https://www.pff.com/news/nfl-three-year-salary-cap-analysis-32-nfl-teams-2023)
- [Sportskeeda - Worst Cap Situations 2024](https://www.sportskeeda.com/nfl/5-teams-worst-salary-cap-situation-2024-2025-nfl-season)
- [CBS Sports - Rookie Contract Projections](https://www.cbssports.com/nfl/news/agents-take-2024-nfl-rookie-contract-projections-for-key-round-1-picks-with-wage-scale-explainer/)
- [NFL.com - 2026 Offseason Outlook](https://www.nfl.com/news/2026-nfl-offseason-outlook-ranking-all-32-teams-by-projected-cap-space-and-draft-capital)

---

## Appendix: Quick Reference Tables

### Position Market Rates (2024)

| Position | Min | 25th %ile | Median | 75th %ile | Max |
|----------|-----|-----------|--------|-----------|-----|
| QB | $1M | $5M | $25M | $45M | $61M |
| Edge | $1M | $4M | $12M | $22M | $45M |
| WR | $1M | $3M | $10M | $20M | $41M |
| OT | $1M | $3M | $10M | $18M | $28M |
| CB | $1M | $2M | $6M | $14M | $21M |
| DT | $1M | $2M | $8M | $16M | $31M |
| S | $1M | $2M | $5M | $10M | $16M |
| G | $1M | $2M | $5M | $12M | $21M |
| TE | $1M | $2M | $5M | $12M | $19M |
| LB | $1M | $2M | $4M | $8M | $15M |
| RB | $1M | $1.5M | $3M | $8M | $19M |
| C | $1M | $2M | $4M | $10M | $16M |

### Dead Money Thresholds

| Dead Money % | Situation | Flexibility |
|--------------|-----------|-------------|
| 0-5% | Healthy | Full flexibility |
| 5-10% | Normal | Minor constraints |
| 10-15% | Elevated | Need to be careful |
| 15-20% | Concerning | Limited moves |
| 20-30% | Cap Hell | Major constraints |
| 30%+ | Crisis | Trapped |

### Archetype Quick Reference

| Archetype | Cap Space | Dead Money | QB Situation | Roster Age |
|-----------|-----------|------------|--------------|------------|
| Dynasty | Tight | Low | Value deal | Prime |
| Contending | Over | Medium | Expensive | Late prime |
| Window Closing | Way over | High | Albatross | Aging |
| Rebuilding | Flush | Low-Med | Rookie/cheap | Young |
| Middle | Moderate | Medium | Middling | Mixed |
| Mismanaged | Over | High | Overpaid bad | Mixed |

---

## Part 8: Real Data Analysis (Over The Cap)

Analysis of 49,367 contracts from `contracts.parquet` validates and refines our models.

### Position Market Reality (2020-2024)

| Position | Max AAV | 90th %ile | 75th %ile | Median | Min |
|----------|---------|-----------|-----------|--------|-----|
| QB | $60.0M | $35.0M | $1.15M | $0.84M | $0.11M |
| WR | $40.3M | $20.0M | $0.98M | $0.75M | $0.11M |
| EDGE | $45.0M | $22.0M | - | - | - |
| CB | $30.1M | $14.0M | $0.99M | $0.76M | $0.12M |
| OT | $28.5M | $18.0M | $1.05M | $0.80M | $0.06M |
| S | $25.1M | $10.0M | $1.03M | $0.81M | $0.07M |
| G | $24.0M | $12.0M | $1.03M | $0.79M | $0.06M |
| LB | $21.0M | $8.0M | $1.03M | $0.80M | $0.14M |
| RB | $20.6M | $8.0M | $0.99M | $0.75M | $0.06M |
| TE | $19.1M | $12.0M | $0.99M | $0.76M | $0.14M |
| C | $18.0M | $10.0M | $1.03M | $0.79M | $0.09M |

**Key Insight:** Medians are low because most NFL contracts are 1-year minimum deals. Only elite players get big multi-year contracts.

### Contract Length Distribution

| Years | Count | Percentage |
|-------|-------|------------|
| 1 | 20,366 | 73.3% |
| 2 | 2,193 | 7.9% |
| 3 | 3,367 | 12.1% |
| 4 | 1,790 | 6.4% |
| 5+ | 71 | 0.3% |

**Key Insight:** 73% of all NFL contracts are 1-year deals. Multi-year contracts are reserved for proven players.

### Rookie Contract Analysis (Real Data)

| Round | Avg Value | Avg Guaranteed | Guarantee % | Sample |
|-------|-----------|----------------|-------------|--------|
| 1 | $25.48M | $18.11M | 69.3% | 332 |
| 2 | $11.61M | $6.13M | 46.8% | 363 |
| 3 | $5.63M | $1.89M | 14.5% | 601 |
| 4 | $3.43M | $0.97M | 10.2% | 642 |
| 5 | $2.77M | $0.58M | 5.9% | 738 |
| 6 | $1.94M | $0.28M | 2.9% | 953 |
| 7 | $1.81M | $0.21M | 1.6% | 1,028 |

### Team Archetype Identification (Real Data)

**Top-Heavy Teams (>35% of cap in top 3 players):**
- Chargers (37.6%)
- Cowboys (37.7%)
- Bengals (41.9%)
- Dolphins (36.0%)
- Raiders (43.3%)

**Rebuilding Teams (low QB%, high rookie%):**
- Titans
- Steelers
- Colts
- Commanders
- Giants

**High QB Spend Teams (>18% to QB):**
- Chargers (19.7%)
- Cowboys (19.2%)
- Bengals (18.5%)
- Jaguars (18.3%)

### Cap Percentage by Position (Max as % of cap)

| Position | Max Cap % | Notes |
|----------|-----------|-------|
| QB | 24.5% | Burrow/Mahomes tier |
| WR | 14.4% | Elite receiver |
| OT | 12.6% | Premium LT |
| LB | 10.8% | Elite pass rusher |
| CB | 10.8% | Shutdown corner |
| G | 9.9% | Elite guard |
| S | 9.6% | Elite safety |
| TE | 8.2% | Elite TE |
| RB | 8.1% | Elite RB (rare) |
| C | 7.4% | Elite center |

### Guarantee Rates by Player Tier

| Tier | Avg Guarantee % | Median |
|------|-----------------|--------|
| Elite (top quartile) | 30.4% | 18.1% |
| High | 1.2% | 0% |
| Mid | 0.1% | 0% |
| Low | ~0% | 0% |

**Key Insight:** Only elite players get meaningful guarantees. The vast majority of NFL contracts have no guaranteed money beyond year 1.

### Refined Generation Model

Based on real data, the salary generation should:

1. **Bimodal Distribution:** Most players on minimum deals, elite players on megadeals
2. **Position Caps:** QB can be 25% of cap, RB maxes at 8%
3. **Guarantee Cliff:** Only top 25% of contracts have significant guarantees
4. **Length Based on Value:** 1-year for depth, 3-4 years for starters, 4-5 for stars

```python
def generate_salary(position: str, tier: str, cap: int = 255_400_000) -> Contract:
    """Generate salary based on real data distributions."""

    # Position max as % of cap
    position_cap_pct = {
        'QB': 0.25, 'EDGE': 0.18, 'WR': 0.15, 'OT': 0.13,
        'CB': 0.11, 'DT': 0.12, 'S': 0.10, 'G': 0.10,
        'LB': 0.11, 'TE': 0.08, 'RB': 0.08, 'C': 0.08,
    }

    max_aav = cap * position_cap_pct.get(position, 0.05)

    if tier == 'elite':
        aav = max_aav * random.uniform(0.7, 1.0)
        years = random.choice([4, 5])
        gtd_pct = random.uniform(0.50, 0.75)
    elif tier == 'starter':
        aav = max_aav * random.uniform(0.3, 0.6)
        years = random.choice([2, 3, 4])
        gtd_pct = random.uniform(0.20, 0.45)
    elif tier == 'depth':
        aav = random.uniform(0.84, 2.0) * 1_000_000  # Veteran min to low starter
        years = random.choice([1, 2])
        gtd_pct = random.uniform(0, 0.15)
    else:  # minimum
        aav = 0.84 * 1_000_000  # Minimum salary
        years = 1
        gtd_pct = 0

    return Contract(aav=aav, years=years, guaranteed=aav * years * gtd_pct)
```

### Data Files Generated
- `research/models/contract_analysis.py` - Analysis script
- `research/exports/contract_analysis.json` - Full data export
- `research/reports/contracts/nfl_contracts_research.md` - This report

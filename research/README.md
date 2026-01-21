# Huddle Research Infrastructure

**Owner:** researcher_agent
**Purpose:** Data-driven analysis of real NFL statistics to calibrate and improve the Huddle simulation.

---

## Folder Structure

```
research/
├── scripts/                          # All Python analysis scripts (49 total)
│   ├── game_layer/                   # Game mechanics analysis (6 scripts)
│   ├── simulation/                   # Play outcome models (13 scripts)
│   ├── player_attributes/            # Player ratings & profiles (12 scripts)
│   ├── ai_decisions/                 # AI decision-making (7 scripts)
│   ├── management/                   # Contracts & roster (10 scripts)
│   └── download_all_data.py          # Data download utility
│
├── exports/                          # JSON model outputs (42 total)
│   ├── active/                       # 6 models loaded by game code
│   │   ├── physical_profile_model.json   # calibration.py
│   │   ├── contract_model.json           # calibration.py
│   │   ├── draft_model.json              # calibration.py
│   │   ├── position_value_model.json     # calibration.py
│   │   ├── injury_model.json             # health.py
│   │   └── fatigue_model.json            # health.py
│   └── reference/                    # 36 research-only exports (not imported)
│       ├── game_layer/
│       ├── simulation/
│       ├── player_attributes/
│       ├── ai_decisions/
│       └── management/
│
├── reports/                          # Analysis reports (by topic)
│   ├── simulation/
│   ├── player_generation/
│   ├── management/
│   └── methodology/
│
├── sources/                          # Reference materials
│   ├── books/                        # Football coaching books
│   └── papers/                       # Academic papers
│
└── data/                             # Raw data
    ├── cached/                       # Parquet files from nfl_data_py (~127MB)
    └── figures/                      # Generated visualizations
```

---

## Domain Descriptions

### game_layer/
Scripts analyzing in-game decision mechanics and outcomes:
- **special_teams_analysis.py** - Kickoffs, punts, field goals
- **fourth_down_analysis.py** - Go-for-it vs punt/FG decisions
- **game_flow_analysis.py** - Score differentials, game state
- **drive_outcome_analysis.py** - Drive results by field position
- **two_point_analysis.py** - 2-point conversion success rates
- **clock_analysis.py** - Clock management strategies

### simulation/
Play-by-play outcome models for the tick simulation:
- **nfl_pass_game_analysis.py** - Passing outcomes analysis
- **nfl_run_game_analysis.py** - Rushing outcomes analysis
- **nfl_play_calling_analysis.py** - Play selection patterns
- **completion_model.py** - Pass completion probability
- **interception_model.py** - Interception risk factors
- **yac_model.py** - Yards after catch
- **run_yards_model.py** - Rush yard distributions
- **playcalling_model.py** - Situational play calling
- **blocking_model.py** / **blocking_model_deep.py** - Blocking effectiveness
- **playbook_catalogue.py** - Play type categorization
- **qb_variance_analysis.py** - QB performance variance
- **rating_impact_model.py** - Rating-to-outcome mappings

### player_attributes/
Player generation and attribute calibration:
- **nfl_combine_analysis.py** - Combine measurement distributions
- **college_production_analysis.py** - College stats to NFL projection
- **position_value_analysis.py** - Position value (WAR) analysis
- **physical_profile_model.py** - Height/weight/speed by position
- **attribute_projection_*.py** - Attribute projections by skill category
- **attribute_calibration_summary.py** - Overall calibration targets
- **qb_intangibles_analysis.py** - QB non-physical traits

### ai_decisions/
AI agent decision-making models:
- **nfl_draft_analysis.py** - Draft pick value analysis
- **draft_value_analysis.py** - Pick value curves
- **trade_value_analysis.py** - Trade value calculations
- **trade_value_empirical.py** - Historical trade data
- **fa_valuation_analysis.py** - Free agent market values
- **injury_risk_analysis.py** - Injury probability factors
- **draft_model.py** - Draft AI decision model

### management/
Contract, roster, and development systems:
- **nfl_contract_analysis.py** - Contract structure analysis
- **contract_timing_analysis.py** - Extension timing patterns
- **player_development_curves.py** - Age-performance curves
- **compute_defensive_value.py** - Defensive player valuation
- **calvetti_allocation_analysis.py** - Cap allocation strategy
- **generate_ai_lookup_tables.py** - Pre-computed AI tables
- **contract_model.py** / **contract_analysis.py** - Contract generation
- **injury_model.py** - Injury occurrence model
- **fatigue_model.py** - In-game fatigue system

---

## Active vs Reference Exports

### Active Exports (`exports/active/`)
These 6 JSON files are **loaded by the game** at runtime:

| File | Loaded By | Purpose |
|------|-----------|---------|
| `physical_profile_model.json` | `calibration.py` | Height/weight/speed distributions by position |
| `contract_model.json` | `calibration.py` | APY tiers and structure by position |
| `draft_model.json` | `calibration.py` | Pick value, success rates by round |
| `position_value_model.json` | `calibration.py` | WAR estimates, market efficiency |
| `injury_model.json` | `health.py` | Injury rates by position, type probabilities, durations |
| `fatigue_model.json` | `health.py` | In-game fatigue accumulation and recovery |

### Reference Exports (`exports/reference/`)
These 36 files are **research outputs only** - they document findings but are not imported into the game code. They serve as reference material for:
- Validating simulation outputs
- Future feature implementation
- Game balance decisions

---

## Running Scripts

```bash
# First time: download all data
python scripts/download_all_data.py

# Run scripts by domain
python scripts/simulation/completion_model.py
python scripts/player_attributes/nfl_combine_analysis.py
python scripts/management/contract_model.py
# etc.
```

---

## Data Sources

All data via `nfl_data_py`:
- Play-by-play (1999-2024) - 1.3M plays, 397 columns
- Next Gen Stats passing/rushing/receiving (2016+)
- Combine (2000-2024)
- Contracts (49k records)
- Draft picks with career outcomes
- Injuries, snap counts, depth charts

**Cached data location:** `data/cached/*.parquet` (~127MB)

---

## Statistical Approach

**Hierarchy of techniques (interpretability first):**
1. Mixed Effects Models - hierarchical data, interpretable coefficients
2. Generalized Additive Models (GAM) - non-linear relationships
3. Factor Analysis - reduce correlated features
4. Gradient Boosting - feature discovery (with SHAP)
5. Neural Networks - last resort for complex patterns

**Key principle:** Every model factor must map to a Huddle simulation attribute (directly, via proxy, or flagged for implementation).

---

*Maintained by researcher_agent*

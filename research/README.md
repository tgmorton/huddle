# Huddle Research Infrastructure

**Owner:** researcher_agent
**Purpose:** Data-driven analysis of real NFL statistics to calibrate and improve the Huddle simulation.

---

## Folder Structure

```
research/
├── scripts/                    # Analysis scripts
│   ├── download_all_data.py    # Cache NFL datasets
│   ├── nfl_pass_game_analysis.py
│   ├── nfl_play_calling_analysis.py
│   ├── nfl_combine_analysis.py
│   ├── nfl_contract_analysis.py
│   └── nfl_draft_analysis.py
│
├── reports/
│   ├── simulation/             # Pass game, run game, play calling
│   ├── player_generation/      # Combine, physical profiles
│   ├── management/             # Contracts, draft
│   └── methodology/            # Statistical approach, deep dives
│
├── data/
│   ├── cached/                 # Parquet files from nfl_data_py
│   └── figures/                # Visualizations by topic
│
└── models/                     # (Future) Statistical models
```

---

## Completed Analyses

| Topic | Report | Script | Key Findings |
|-------|--------|--------|--------------|
| Pass Game | `simulation/pass_game_analysis.md` | `nfl_pass_game_analysis.py` | 60.5% completion, 2.79s avg time-to-throw |
| Run Game | `simulation/run_game_analysis.md` | `nfl_run_game_analysis.py` | Median 3 yds, 17% stuffed, 12% explosive |
| Play Calling | `simulation/play_calling_analysis.md` | `nfl_play_calling_analysis.py` | 58% pass rate, situational tables |
| Combine | `player_generation/combine_analysis.md` | `nfl_combine_analysis.py` | Position profiles, correlations |
| Contracts | `management/contract_analysis.md` | `nfl_contract_analysis.py` | APY by tier, age curves |
| Draft | `management/draft_analysis.md` | `nfl_draft_analysis.py` | R1: 3% bust, R7: 72% bust |

---

## Methodology Documents

| Document | Purpose |
|----------|---------|
| `methodology/STATISTICAL_METHODOLOGY.md` | Mixed effects, GAM, factor mapping approach |
| `methodology/DEEP_DIVE_PROPOSAL.md` | Plans for comprehensive analysis |
| `methodology/CALIBRATION_RECOMMENDATIONS.md` | Summary of all calibration targets |

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

## Running Analyses

```bash
# First time: download all data
python scripts/download_all_data.py

# Run individual analyses
python scripts/nfl_pass_game_analysis.py
python scripts/nfl_combine_analysis.py
# etc.
```

---

## Next Steps

1. **Audit Huddle simulation factors** → Create `HUDDLE_FACTOR_INVENTORY.md`
2. **Build statistical models** with factor mapping (mixed effects, GAM)
3. **Deep dive analyses** - completion probability model, player archetypes
4. **Export calibration data** for game integration

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

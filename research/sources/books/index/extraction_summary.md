# Book Extraction Summary

Generated: 2024-12-24

## Extraction Stats

| Book | Chars | Chapters | Format |
|------|-------|----------|--------|
| complete_offensive_line | 277,807 | 11 | PDF |
| coaching_offensive_linemen | 337,478 | 2 | PDF |
| coaching_linebackers | 143,110 | 1 | PDF |
| delaware_wing_t | 184,190 | 0 | PDF |
| blood_sweat_chalk | 517,363 | 21 | PDF |
| genius_of_desperation | 489,518 | 18 | EPUB |
| gridiron_genius | 503,345 | 21 | EPUB |
| q_factor | 486,353 | 19 | EPUB |
| coach_of_year_clinics | 908,558 | 262 | EPUB |
| **Total** | **3,847,722** | **355** | - |

## Simulation Relevance by Topic

### arms_prototype (OL/DL Battle Physics)

**Primary Sources:**
- `complete_offensive_line/chapters/11_pass_protection.md` (60KB) - Kick slide, vertical set, post set
- `complete_offensive_line/chapters/03_drive_blocks.md` (21KB) - Drive blocking mechanics
- `complete_offensive_line/chapters/02_stances.md` (19KB) - Stance fundamentals

**Key Concepts Found:**
- 75/25 advantage positioning (inside/outside control)
- Three pass set types: post, kick slide, vertical
- Footwork patterns for pass protection
- Hand placement ("tight elbows = tight hands")
- Leverage and pad level principles

### qb_brain (QB Decision Making)

**Primary Sources:**
- `q_factor/` - Full book on QB evaluation and intangibles
- `blood_sweat_chalk/` - Scheme context for reads

**Key Concepts Found:**
- Mental processing under pressure
- Decision-making frameworks
- Anticipation vs reaction timing
- Leadership and poise factors

### playbook_catalogue (Play Concepts)

**Primary Sources:**
- `blood_sweat_chalk/` (517KB) - West Coast, Spread, Zone Blitz origins
- `genius_of_desperation/` (489KB) - Modern scheme evolution
- `delaware_wing_t/` (184KB) - Wing-T running game

**Key Concepts Found:**
- West Coast Offense origins and principles
- Air Raid concepts
- Zone blocking philosophy
- Cover 2, Cover 3, Zone Blitz evolution
- RPO development

### run_concepts.py (Run Play Mechanics)

**Primary Sources:**
- `complete_offensive_line/chapters/08_stretch_plays.md` (45KB)
- `complete_offensive_line/chapters/09_inside_zone.md` (12KB)
- `delaware_wing_t/full_text.md` - Wing-T mechanics

**Key Concepts Found:**
- Zone blocking footwork
- Combo block progression
- Stretch play mechanics
- Inside zone vs outside zone

### lb_brain (Linebacker Behavior)

**Primary Sources:**
- `coaching_linebackers/full_text.md` (143KB)

**Key Concepts Found:**
- Pursuit angles
- Gap responsibility
- Block shedding techniques
- Key reading

## Files Created

```
research/books/
├── extracts/
│   ├── complete_offensive_line/
│   │   ├── full_text.md
│   │   ├── chapters.json
│   │   └── chapters/
│   │       ├── 02_stances.md
│   │       ├── 03_drive_blocks.md
│   │       ├── 04_reach_blocks.md
│   │       ├── 05_cutoff_blocks.md
│   │       ├── 06_down_blocks.md
│   │       ├── 08_stretch_plays.md
│   │       ├── 09_inside_zone.md
│   │       ├── 10_option.md
│   │       ├── 11_pass_protection.md
│   │       ├── 12_pass_progression_and_drills.md
│   │       └── 13_conditioning_and_core_work.md
│   ├── blood_sweat_chalk/
│   │   ├── full_text.md
│   │   ├── chapters.json
│   │   └── chapters/ (21 chapters)
│   ├── q_factor/
│   │   ├── full_text.md
│   │   └── chapters/ (19 chapters)
│   └── ... (other books)
├── index/
│   ├── book_index.json
│   └── extraction_summary.md
└── scripts/
    └── extract_books.py
```

## Usage

### Read specific chapter for model context
```python
from pathlib import Path

def get_chapter_content(book_id: str, chapter_keyword: str) -> str:
    chapters_dir = Path(f"research/books/extracts/{book_id}/chapters")
    for file in chapters_dir.glob("*.md"):
        if chapter_keyword.lower() in file.stem.lower():
            return file.read_text()
    return ""

# Example: Get pass protection content
pass_protection = get_chapter_content("complete_offensive_line", "pass_protection")
```

### Query by topic
```python
import json

def get_books_for_topic(topic: str) -> list[str]:
    with open("research/books/index/book_index.json") as f:
        index = json.load(f)
    topic_data = index["topic_index"].get(topic, {})
    return topic_data.get("sources", [])

# Example: Get OL technique books
ol_books = get_books_for_topic("ol_techniques")
# Returns: ["complete_offensive_line", "coaching_offensive_linemen"]
```

## Notes for Chapter Config Improvements

Books needing custom chapter configuration:
- `coaching_offensive_linemen` - Only 2 chapters detected (needs TOC analysis)
- `coaching_linebackers` - Only 1 chapter detected (needs TOC analysis)
- `delaware_wing_t` - 0 chapters detected (needs TOC analysis)

To add chapter configs, update `BOOK_CHAPTER_CONFIG` in `extract_books.py`.

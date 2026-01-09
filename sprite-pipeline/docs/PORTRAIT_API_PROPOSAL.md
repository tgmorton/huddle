# Portrait Generation API Proposal

## Current State

The sprite-pipeline system can generate player portraits by compositing:
- **Faces**: 8 skin tones × 8 face widths = 64 base faces
- **Hair**: 64 hairstyles (8×8 grid) in grayscale, tintable to 12 colors
- **Facial Hair**: 64 styles (8×8 grid) in grayscale, tintable to 12 colors

### Assets Location
```
sprite-pipeline/output/sliced/
├── faces/          # face_skin{0-7}_width{0-7}.png
├── hair_dark/      # hair_{row}_{col}.png (grayscale)
└── facial_hair/    # facial_{row}_{col}.png (grayscale)
```

### Existing Modules
- `scripts/tint.py` - Hair/beard color tinting (12 colors + grayscale variants)
- `scripts/composite_test.py` - Layering face + hair + facial hair
- `config/exclusions.py` - Banned style combinations by face width
- `config/demographics.py` - Hair color rarity, NFL position demographics, skin tone mapping

### Demographics System
Skin tone scale: 0 = lightest (Scandinavian), 7 = darkest

**Hair color distribution by skin tone:**
| Skin Tone | Primary Hair Colors |
|-----------|---------------------|
| 0-1 (Scandinavian) | 50% blonde, 10% red, 18% light brown |
| 2 (White) | 40% blonde, 20% dark brown, 10% black |
| 3-7 (Black) | 70-82% black, 9-14% dark brown |

**Position demographics (% Black players):**
- RB: 85%, WR: 80%, CB: 75%, DT: 75%
- QB: 30%, OL: 40%, K/P: 5%

---

## API Architecture Options

### Option 1: Integrate into Huddle API

Add a portrait router to the existing FastAPI backend at `huddle/api/routers/portraits.py`.

**Pros:**
- Single deployment, no new infrastructure
- Direct access to player database
- Shared authentication/middleware
- Can generate portrait on player creation automatically

**Cons:**
- Adds image processing load to main API
- Tighter coupling between systems
- Requires PIL/numpy in main backend dependencies

**File structure:**
```
huddle/
├── api/routers/portraits.py      # New router
├── api/services/portrait_service.py
└── portraits/                    # Generated portrait cache
    └── {player_id}.png
```

---

### Option 2: Standalone Microservice

Separate FastAPI service running in sprite-pipeline folder.

**Pros:**
- Independent scaling
- Isolated dependencies (PIL, numpy, scipy)
- Can be deployed separately
- Clean separation of concerns

**Cons:**
- Additional service to manage
- Network calls between services
- Need to sync player data or pass all params

**File structure:**
```
sprite-pipeline/
├── api/
│   ├── main.py           # FastAPI app
│   ├── routers/
│   │   └── portraits.py
│   └── services/
│       └── generator.py
└── portraits/            # Cache directory
```

**Would run on separate port (e.g., :8001)**

---

### Option 3: Pre-generate All Combinations

Generate all valid portrait combinations as static assets at build time.

**Calculation:**
- 8 skin tones × 8 face widths = 64 faces
- ~60 valid hair styles (after exclusions) × 12 colors = 720 hair variants
- ~60 valid facial styles × 12 colors = 720 facial variants
- With "no hair" and "no facial hair" options

**Conservative estimate:** 64 × 720 × 720 = ~33 million combinations (not feasible)

**Realistic approach:** Pre-generate components, composite at runtime
- Pre-tint all hair colors: 64 × 12 = 768 hair PNGs
- Pre-tint all facial hair: 64 × 12 = 768 facial PNGs
- Composite on-demand from pre-tinted assets

**Pros:**
- Fastest serving (just file lookup + quick composite)
- No runtime tinting computation
- Can be served from CDN

**Cons:**
- ~1,500 pre-generated assets to manage
- Still need compositing logic somewhere
- Asset pipeline complexity

---

### Option 4: Hybrid (Recommended)

Pre-tint all hair/facial hair colors at build time. Composite on-demand in the main API with aggressive caching.

**Build step:** Generate all tinted variants
```
sprite-pipeline/output/tinted/
├── hair/
│   ├── black/hair_0_0.png ... hair_7_7.png
│   ├── blonde/hair_0_0.png ...
│   └── .../
└── facial/
    ├── black/facial_0_0.png ...
    └── .../
```

**Runtime:** Simple alpha composite (fast) + cache result

**Pros:**
- Fast runtime (just compositing, no tinting)
- Reasonable asset count (~1,500 files)
- Simple caching strategy
- Can integrate into main API without heavy processing

**Cons:**
- Build step required when adding colors
- Still need compositing endpoint

---

## Proposed API Endpoints

### Core Endpoints

```
POST /api/v1/portraits/generate
```
Generate a new portrait. Can specify all parameters or let system choose based on demographics.

**Request:**
```json
{
  "player_id": "uuid",           // Required - for caching
  "position": "QB",              // Optional - influences skin tone + hair color
  "age": 28,                     // Optional - influences gray hair chance
  "skin_tone": null,             // Optional (0-7) - null = random by position
  "face_width": null,            // Optional (0-7) - null = random
  "hair_style": null,            // Optional [row, col] - null = random
  "hair_color": null,            // Optional - null = random by skin tone
  "facial_hair_style": null,     // Optional [row, col] - null = random, [null] = none
  "facial_hair_color": null,     // Optional - defaults to hair_color
  "seed": null                   // Optional - for reproducible generation
}
```

**Response:**
```json
{
  "player_id": "uuid",
  "portrait_url": "/portraits/uuid.png",
  "attributes": {
    "skin_tone": 2,
    "face_width": 4,
    "hair_style": [3, 5],
    "hair_color": "blonde",
    "facial_hair_style": [1, 2],
    "facial_hair_color": "blonde"
  }
}
```

---

```
GET /api/v1/portraits/{player_id}
```
Retrieve a cached portrait.

**Response:** PNG image or 404

---

```
GET /api/v1/portraits/options
```
List all available options for portrait generation.

**Response:**
```json
{
  "skin_tones": [0, 1, 2, 3, 4, 5, 6, 7],
  "face_widths": [0, 1, 2, 3, 4, 5, 6, 7],
  "hair_styles": [[0,0], [0,1], ...],  // Valid styles
  "facial_hair_styles": [[0,0], ...],
  "hair_colors": ["black", "dark_brown", "brown", ...],
  "exclusions": {
    "hair_banned_all": [[6, 7]],
    "hair_banned_by_width": {"7": [[4, 4], ...]},
    "facial_banned_all": [[4, 7], ...],
    "facial_banned_by_width": {"7": [[1, 4], ...]}
  }
}
```

---

```
DELETE /api/v1/portraits/{player_id}
```
Delete a cached portrait (for regeneration).

---

### Batch Endpoints (Optional)

```
POST /api/v1/portraits/generate-batch
```
Generate portraits for multiple players.

```json
{
  "players": [
    {"player_id": "uuid1", "position": "QB", "age": 25},
    {"player_id": "uuid2", "position": "RB", "age": 30}
  ]
}
```

---

## Integration Points

### With Player Creation
When a new player is created in the league system, automatically generate their portrait:

```python
# In player creation service
async def create_player(player_data):
    player = Player(**player_data)
    db.add(player)

    # Generate portrait
    await portrait_service.generate(
        player_id=player.id,
        position=player.position,
        age=player.age
    )

    return player
```

### With Frontend
Frontend can display portraits via:
```tsx
<img src={`/api/v1/portraits/${player.id}`} alt={player.name} />
```

Or with a fallback:
```tsx
<PlayerPortrait
  playerId={player.id}
  fallback="/assets/default-portrait.png"
/>
```

### With Draft/Scouting
Generate prospect portraits with appropriate demographic weighting:
```python
portrait_service.generate(
    player_id=prospect.id,
    position=prospect.projected_position,
    age=21  # Draft-eligible age
)
```

---

## Caching Strategy

### File-based Cache (Simple)
```
portraits/
├── {player_id}.png
└── metadata/{player_id}.json  # Store generation params for debugging
```

### Redis Cache (If needed for scale)
- Cache portrait bytes with TTL
- Regenerate on miss
- Invalidate on player attribute change

### CDN (Production)
- Upload generated portraits to S3/CloudFlare
- Serve via CDN URL
- Invalidate on regeneration

---

## Dependencies

### Required for portrait generation:
```
Pillow>=10.0.0
numpy>=1.24.0
scipy>=1.11.0  # For connected component cleanup
```

### If standalone microservice:
```
fastapi>=0.100.0
uvicorn>=0.23.0
python-multipart>=0.0.6
```

---

## Questions for Team

1. **Architecture preference?** Integrated vs. Standalone vs. Hybrid?

2. **Caching location?** Local filesystem, Redis, or external (S3/CDN)?

3. **Generation trigger?** On player creation, on first access, or batch job?

4. **Deterministic portraits?** Should same player always get same portrait, or allow regeneration?

5. **Portrait updates?** Can players change appearance (age, style choices)?

6. **Asset delivery?** Serve from API or separate static file server?

---

## Recommended Implementation Order

1. **Create pre-tinting script** - Generate all color variants of hair/facial hair
2. **Build portrait generator service** - Core compositing logic with demographics
3. **Add API endpoints** - Either in huddle or standalone
4. **Wire to player creation** - Auto-generate on new player
5. **Add to frontend** - Display in roster, draft, game views
6. **Optimize caching** - Based on access patterns

# Sprite Catalog Generation Instructions

## Overview
This document describes how to catalog sprite assets for the profile picture template system. Each catalog is a JSON file containing filenames and descriptions suitable for narrative generation.

## Output Location
All catalogs are stored in `/output/sliced/` within their respective folders:
- `faces/faces_catalog.json`
- `hair_dark/hair_catalog.json`
- `facial_hair/facial_hair_catalog.json`

## Catalog Format

### Hair & Facial Hair
```json
{
  "hair_styles": [
    {
      "filename": "hair_0_0.png",
      "name": "Buzz Cut",
      "description": "Very short, close-cropped hair"
    }
  ]
}
```

### Faces
```json
{
  "faces": [
    {
      "filename": "face_skin0_width0.png",
      "description": "A man with a very fair complexion and a narrow, angular face, featuring light eyes and sharply defined cheekbones.",
      "skin_tone": 0
    }
  ]
}
```

## Process

### 1. Identify the sprite grid structure
- Hair/Facial Hair: Named `{type}_{row}_{col}.png` (8x8 grid = 64 assets)
- Faces: Named `face_skin{0-7}_width{0-7}.png` (8 skin tones x 8 widths = 64 assets)

### 2. Read images row by row
Process images in batches (one row at a time, 8 images per row) to maintain context and consistency.

### 3. Write descriptions

**For Hair/Facial Hair:**
- `name`: Short style name (e.g., "Pompadour", "Full Beard")
- `description`: Brief description of the style's characteristics

**For Faces:**
- Write a single sentence suitable for a news article introduction
- Include: complexion, face shape, eye color/description, build/presence
- Keep descriptions neutral and unbiased
- Vary vocabulary to avoid repetition across similar faces

### 4. Incremental saves
Write to the JSON file periodically (every 2-3 rows) to avoid losing progress on API errors.

## Description Guidelines for Faces

### Skin Tone Vocabulary (0-7)
0. Very fair complexion
1. Fair complexion
2. Light complexion
3. Light olive complexion
4. Medium-brown complexion
5. Medium-dark complexion
6. Dark complexion
7. Deep dark complexion

### Face Width Vocabulary (0-7)
0. Narrow, angular, elongated, slender
1. Slim, lean, trim
2. Balanced, proportionate, symmetrical
3. Medium, well-defined, well-structured
4. Fuller, broader
5. Broad, wide, full
6. Wide, sturdy, full
7. Round, heavyset, powerful, massive

### Example Sentence Structure
"A man with a [complexion] and a [face shape], featuring [eye description] and [additional feature]."

## Asset Counts
| Category | Grid Size | Total Assets |
|----------|-----------|--------------|
| Faces | 8x8 | 64 |
| Hair | 8x8 | 64 |
| Facial Hair | 8x8 | 64 |
| **Total** | | **192** |

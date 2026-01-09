#!/usr/bin/env python3
"""
Pre-tint all hair and facial hair assets to all color variants.
Generates ~1,536 tinted PNGs for fast compositing at runtime.
"""

from pathlib import Path
from PIL import Image

from tint import HAIR_COLORS, tint_grayscale


def pretint_assets():
    """Generate all color variants of hair and facial hair."""
    base_path = Path(__file__).parent.parent
    sliced_dir = base_path / "output" / "sliced"
    tinted_dir = base_path / "output" / "tinted"

    # Source directories
    hair_dir = sliced_dir / "hair_dark"
    facial_dir = sliced_dir / "facial_hair"
    facial_new_dir = sliced_dir / "facial_hair_new"

    # Create output structure
    for color_name in HAIR_COLORS.keys():
        (tinted_dir / "hair" / color_name).mkdir(parents=True, exist_ok=True)
        (tinted_dir / "facial" / color_name).mkdir(parents=True, exist_ok=True)
        (tinted_dir / "facial_new" / color_name).mkdir(parents=True, exist_ok=True)

    # Count for progress
    hair_files = list(hair_dir.glob("hair_*.png"))
    facial_files = list(facial_dir.glob("facial_*.png"))
    facial_new_files = list(facial_new_dir.glob("facial_*.png"))
    total = (len(hair_files) + len(facial_files) + len(facial_new_files)) * len(HAIR_COLORS)
    processed = 0

    print(f"Pre-tinting {len(hair_files)} hair styles × {len(HAIR_COLORS)} colors...")

    # Process hair
    for hair_file in hair_files:
        img = Image.open(hair_file)
        for color_name, color_rgb in HAIR_COLORS.items():
            tinted = tint_grayscale(img, color_rgb)
            out_path = tinted_dir / "hair" / color_name / hair_file.name
            tinted.save(out_path, "PNG")
            processed += 1

        # Progress every 8 files
        if processed % (8 * len(HAIR_COLORS)) == 0:
            pct = processed / total * 100
            print(f"  {pct:.0f}% ({processed}/{total})")

    print(f"Pre-tinting {len(facial_files)} facial hair styles × {len(HAIR_COLORS)} colors...")

    # Process facial hair (with less aggressive edge removal)
    for facial_file in facial_files:
        img = Image.open(facial_file)
        for color_name, color_rgb in HAIR_COLORS.items():
            tinted = tint_grayscale(img, color_rgb, is_facial=True)
            out_path = tinted_dir / "facial" / color_name / facial_file.name
            tinted.save(out_path, "PNG")
            processed += 1

        # Progress every 8 files
        if processed % (8 * len(HAIR_COLORS)) == 0:
            pct = processed / total * 100
            print(f"  {pct:.0f}% ({processed}/{total})")

    print(f"Pre-tinting {len(facial_new_files)} new facial hair styles × {len(HAIR_COLORS)} colors...")

    # Process new facial hair
    for facial_file in facial_new_files:
        img = Image.open(facial_file)
        for color_name, color_rgb in HAIR_COLORS.items():
            tinted = tint_grayscale(img, color_rgb, is_facial=True)
            out_path = tinted_dir / "facial_new" / color_name / facial_file.name
            tinted.save(out_path, "PNG")
            processed += 1

        # Progress every 8 files
        if processed % (8 * len(HAIR_COLORS)) == 0:
            pct = processed / total * 100
            print(f"  {pct:.0f}% ({processed}/{total})")

    print(f"\nDone! Generated {processed} tinted images in {tinted_dir}/")
    print(f"  - hair/{'{color}'}/hair_*.png")
    print(f"  - facial/{'{color}'}/facial_*.png")
    print(f"  - facial_new/{'{color}'}/facial_*.png")


if __name__ == "__main__":
    pretint_assets()

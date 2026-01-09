#!/usr/bin/env python3
"""
Composite test - layer face + hair + facial hair to verify alignment.
"""

from PIL import Image
from pathlib import Path


def get_facial_offset(face_width: int) -> int:
    """Get beard Y offset based on face width."""
    if face_width >= 7:
        return -15  # Base -5 + additional -10
    elif face_width >= 4:
        return -10  # Base -5 + additional -5
    else:
        return -5   # Base offset


def composite_portrait(
    face_path: Path,
    hair_path: Path | None = None,
    facial_hair_path: Path | None = None,
    hair_offset_y: int = -15,  # Negative = up
    facial_offset_y: int | None = None,  # None = auto based on face width
    face_width: int = 3,  # For auto facial offset calculation
) -> Image.Image:
    """Layer face, hair, and facial hair into a single portrait."""
    # Auto-calculate facial offset if not provided
    if facial_offset_y is None:
        facial_offset_y = get_facial_offset(face_width)

    # Start with face as base
    face = Image.open(face_path).convert("RGBA")
    width, height = face.size

    # Create expanded canvas to allow upward overflow
    expand_top = max(abs(hair_offset_y), abs(facial_offset_y))
    canvas_height = height + expand_top
    result = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))

    # Place face (shifted down to make room for hair overflow)
    result.paste(face, (0, expand_top), face)

    # Layer hair on top (with offset)
    if hair_path and hair_path.exists():
        hair = Image.open(hair_path).convert("RGBA")
        hair_y = expand_top + hair_offset_y
        # Create temp canvas for hair at offset position
        hair_layer = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))
        hair_layer.paste(hair, (0, hair_y), hair)
        result = Image.alpha_composite(result, hair_layer)

    # Layer facial hair on top (with offset)
    if facial_hair_path and facial_hair_path.exists():
        facial = Image.open(facial_hair_path).convert("RGBA")
        facial_y = expand_top + facial_offset_y
        facial_layer = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))
        facial_layer.paste(facial, (0, facial_y), facial)
        result = Image.alpha_composite(result, facial_layer)

    return result


def create_grid(images: list[Image.Image], cols: int = 8) -> Image.Image:
    """Arrange images into a grid."""
    if not images:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    cell_w, cell_h = images[0].size
    rows = (len(images) + cols - 1) // cols

    grid = Image.new("RGBA", (cols * cell_w, rows * cell_h), (0, 0, 0, 0))

    for i, img in enumerate(images):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        grid.paste(img, (x, y), img)

    return grid


def generate_hair_tests(base_path: Path, output_path: Path):
    """Generate hair test grids - all hairs on all face widths."""
    sliced = base_path / "output" / "sliced"
    faces_dir = sliced / "faces"
    hair_dir = sliced / "hair_dark"

    # Test on all 8 face widths with skin tone 3 (medium)
    for width in range(8):
        face_path = faces_dir / f"face_skin3_width{width}.png"
        composites = []

        # All 64 hair styles (8x8 grid)
        for row in range(8):
            for col in range(8):
                hair_path = hair_dir / f"hair_{row}_{col}.png"
                if hair_path.exists():
                    composites.append(composite_portrait(face_path, hair_path, None))

        # Save grid
        grid = create_grid(composites, cols=8)
        grid.save(output_path / f"hair_test_width{width}.png", "PNG")
        print(f"  Saved hair_test_width{width}.png ({len(composites)} styles)")


def generate_beard_tests(base_path: Path, output_path: Path):
    """Generate beard test grids - all beards on all face widths."""
    sliced = base_path / "output" / "sliced"
    faces_dir = sliced / "faces"
    facial_dir = sliced / "facial_hair"

    # Test on all 8 face widths with skin tone 3 (medium)
    for width in range(8):
        face_path = faces_dir / f"face_skin3_width{width}.png"
        composites = []

        # All 64 facial hair styles (8x8 grid)
        for row in range(8):
            for col in range(8):
                facial_path = facial_dir / f"facial_{row}_{col}.png"
                if facial_path.exists():
                    composites.append(composite_portrait(face_path, None, facial_path, face_width=width))

        # Save grid
        grid = create_grid(composites, cols=8)
        grid.save(output_path / f"beard_test_width{width}.png", "PNG")
        print(f"  Saved beard_test_width{width}.png ({len(composites)} styles)")


def main():
    base_path = Path(__file__).parent.parent
    output_path = base_path / "output" / "composites"
    output_path.mkdir(parents=True, exist_ok=True)

    print("Generating hair test grids...")
    generate_hair_tests(base_path, output_path)

    print("Generating beard test grids...")
    generate_beard_tests(base_path, output_path)

    print(f"\nDone! Test grids in {output_path}/")


if __name__ == "__main__":
    main()

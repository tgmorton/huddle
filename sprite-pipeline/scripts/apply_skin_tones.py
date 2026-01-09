#!/usr/bin/env python3
"""
Apply skin tones to face grids based on column position.
Column 0 = lightest (skin tone 0), Column 7 = darkest (skin tone 7)

Uses the original faces.png as reference for target skin colors.
"""

from PIL import Image
import numpy as np
from pathlib import Path


# Magenta chroma key
MAGENTA = (255, 0, 255)

# Grid dimensions
GRID_SIZE = 8
CELL_SIZE = 256  # 2048 / 8


def get_skin_color_samples(reference_path: Path) -> dict[int, np.ndarray]:
    """
    Sample average skin colors from each column of the reference grid.
    Returns dict mapping column (skin_tone) -> average RGB color.
    """
    img = Image.open(reference_path).convert("RGB")
    data = np.array(img, dtype=np.float32)

    skin_colors = {}

    for col in range(GRID_SIZE):
        # Sample from middle row (row 3 or 4) for most representative skin
        row = 3
        x_start = col * CELL_SIZE
        y_start = row * CELL_SIZE

        cell = data[y_start:y_start + CELL_SIZE, x_start:x_start + CELL_SIZE]

        # Find non-magenta pixels (face pixels)
        r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]
        is_face = ~(
            (r > 200) & (b > 200) & (g < 100) & (np.abs(r - b) < 50)
        )

        # Get face pixels and compute average color
        face_pixels = cell[is_face]
        if len(face_pixels) > 0:
            avg_color = np.mean(face_pixels, axis=0)
            skin_colors[col] = avg_color
        else:
            # Fallback - interpolate
            skin_colors[col] = np.array([200 - col * 20, 150 - col * 15, 130 - col * 12])

    return skin_colors


def estimate_current_skin_tone(cell: np.ndarray) -> np.ndarray:
    """Estimate the current average skin color of a face cell."""
    r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]

    # Find non-magenta pixels
    is_face = ~(
        (r > 200) & (b > 200) & (g < 100) & (np.abs(r - b) < 50)
    )

    face_pixels = cell[is_face]
    if len(face_pixels) > 0:
        return np.mean(face_pixels, axis=0)
    return np.array([180, 140, 120])  # Fallback mid-tone


def apply_color_transfer(cell: np.ndarray, source_avg: np.ndarray, target_avg: np.ndarray) -> np.ndarray:
    """
    Apply color transfer to shift skin tone from source to target.
    Uses a simple multiplicative approach that preserves shading/details.
    """
    result = cell.copy()

    r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]

    # Find face pixels (non-magenta)
    is_face = ~(
        (r > 200) & (b > 200) & (g < 100) & (np.abs(r - b) < 50)
    )

    # Calculate color ratio
    # Avoid division by zero
    source_safe = np.maximum(source_avg, 1.0)
    ratio = target_avg / source_safe

    # Apply ratio to face pixels, preserving relative brightness
    for i in range(3):
        channel = result[:, :, i]
        # Apply ratio but blend to avoid extreme shifts
        adjusted = channel * ratio[i]
        # Blend: 70% adjusted, 30% original for natural look
        channel[is_face] = np.clip(adjusted[is_face] * 0.7 + channel[is_face] * 0.3, 0, 255)

    return result


def apply_skin_tones_to_grid(input_path: Path, output_path: Path, reference_path: Path):
    """
    Apply column-based skin tones to a face grid.
    """
    print(f"Processing {input_path.name}...")

    # Get reference skin colors
    skin_colors = get_skin_color_samples(reference_path)
    print(f"  Sampled {len(skin_colors)} skin tone references")

    # Load input grid
    img = Image.open(input_path).convert("RGB")
    data = np.array(img, dtype=np.float32)

    # Process each cell
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            x_start = col * CELL_SIZE
            y_start = row * CELL_SIZE

            cell = data[y_start:y_start + CELL_SIZE, x_start:x_start + CELL_SIZE]

            # Get current skin tone and target
            current_avg = estimate_current_skin_tone(cell)
            target_avg = skin_colors[col]

            # Apply color transfer
            adjusted_cell = apply_color_transfer(cell, current_avg, target_avg)

            # Put back
            data[y_start:y_start + CELL_SIZE, x_start:x_start + CELL_SIZE] = adjusted_cell

    # Save
    result = Image.fromarray(data.astype(np.uint8))
    result.save(output_path, "PNG")
    print(f"  Saved to {output_path}")


def main():
    base_path = Path(__file__).parent.parent

    # Reference grid (original with correct skin tones)
    reference_path = base_path / "input" / "faces.png"

    if not reference_path.exists():
        print(f"Reference not found: {reference_path}")
        return

    # Input grids to process
    assets_dir = base_path / "output" / "assets"
    output_dir = base_path / "output" / "skin_toned"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all face grids in assets
    input_files = [
        assets_dir / "Gemini_Generated_Image_8uf4818uf4818uf4.png",
        assets_dir / "Gemini_Generated_Image_c0vic4c0vic4c0vi.png",
    ]

    for i, input_path in enumerate(input_files):
        if input_path.exists():
            output_path = output_dir / f"faces_set{i + 2}.png"  # set2, set3, etc.
            apply_skin_tones_to_grid(input_path, output_path, reference_path)
        else:
            print(f"Not found: {input_path}")

    print(f"\nDone! Output in {output_dir}/")


if __name__ == "__main__":
    main()

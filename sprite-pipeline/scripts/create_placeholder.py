#!/usr/bin/env python3
"""
Create a placeholder silhouette for portraits that haven't been generated yet.
Uses an actual face + hair composite flattened to a single color.
"""

from pathlib import Path
from PIL import Image
import numpy as np


def create_placeholder_from_portrait(base_path: Path) -> Image.Image:
    """
    Create a silhouette from an actual face + hair composite.

    Uses a medium face width (4) with a common hairstyle,
    flattened to dark gray.
    """
    # Load face and hair
    face_path = base_path / "output" / "sliced" / "faces" / "face_skin4_width4.png"
    hair_path = base_path / "output" / "tinted" / "hair" / "black" / "hair_3_2.png"

    face = Image.open(face_path).convert("RGBA")
    hair = Image.open(hair_path).convert("RGBA")

    width, height = face.size

    # Create composite (same logic as portrait generator)
    hair_offset_y = -15
    expand_top = abs(hair_offset_y)
    canvas_height = height + expand_top

    # Start with face
    result = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))
    result.paste(face, (0, expand_top), face)

    # Add hair
    hair_layer = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))
    hair_layer.paste(hair, (0, expand_top + hair_offset_y), hair)
    result = Image.alpha_composite(result, hair_layer)

    # Flatten to single color - keep alpha, replace RGB with dark gray
    data = np.array(result, dtype=np.uint8)

    # Silhouette color
    silhouette_r, silhouette_g, silhouette_b = 55, 55, 60

    # Where alpha > 0, set to silhouette color
    mask = data[:, :, 3] > 0
    data[:, :, 0] = np.where(mask, silhouette_r, 0)
    data[:, :, 1] = np.where(mask, silhouette_g, 0)
    data[:, :, 2] = np.where(mask, silhouette_b, 0)
    # Keep original alpha for anti-aliased edges
    # But boost low alpha to make it more solid
    data[:, :, 3] = np.where(mask, np.maximum(data[:, :, 3], 200), 0)

    return Image.fromarray(data)


def main():
    base_path = Path(__file__).parent.parent
    output_dir = base_path / "output" / "portraits"
    output_dir.mkdir(parents=True, exist_ok=True)

    placeholder = create_placeholder_from_portrait(base_path)
    placeholder_path = output_dir / "placeholder.png"
    placeholder.save(placeholder_path, "PNG")

    print(f"Created placeholder silhouette at {placeholder_path}")
    print(f"Size: {placeholder.size}")


if __name__ == "__main__":
    main()

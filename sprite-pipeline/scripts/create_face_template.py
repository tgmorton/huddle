#!/usr/bin/env python3
"""
Create a template grid from faces - gray silhouettes on magenta background.
Useful for creating new face variants while maintaining consistent placement.
"""

from PIL import Image
import numpy as np
from pathlib import Path


# Magenta chroma key
MAGENTA = (255, 0, 255)
# Gray silhouette color (same as placeholder)
SILHOUETTE_GRAY = (60, 60, 65)


def create_face_template_grid(input_path: Path, output_path: Path):
    """
    Convert a faces grid into gray silhouette templates.

    For each cell:
    1. Find non-magenta pixels (the face)
    2. Convert them to gray silhouette
    3. Keep magenta background
    """
    img = Image.open(input_path).convert("RGB")
    data = np.array(img, dtype=np.float32)

    # Create output array
    output = np.zeros_like(data)

    # Find magenta pixels (background) - more lenient detection
    # Magenta has high R, low G, high B - but may not be pure 255,0,255
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]

    # Magenta: R and B are similar and high, G is low relative to them
    is_magenta = (
        (r > 200) &           # High red
        (b > 200) &           # High blue
        (g < 100) &           # Low green
        (np.abs(r - b) < 50)  # R and B are close
    )

    # Set magenta background
    output[is_magenta] = MAGENTA

    # Set non-magenta pixels to gray silhouette
    output[~is_magenta] = SILHOUETTE_GRAY

    # Save
    result = Image.fromarray(output.astype(np.uint8))
    result.save(output_path, "PNG")
    print(f"Saved template to {output_path}")

    return result


def create_face_template_with_edges(input_path: Path, output_path: Path):
    """
    Create template with subtle edge hints for better guidance.
    Shows slight variation at edges to help with alignment.
    """
    img = Image.open(input_path).convert("RGB")
    data = np.array(img, dtype=np.float32)

    # Find magenta pixels (background) - more lenient detection
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    is_magenta = (
        (r > 200) &
        (b > 200) &
        (g < 100) &
        (np.abs(r - b) < 50)
    )

    # Convert to grayscale for edge detection
    gray = 0.299 * data[:, :, 0] + 0.587 * data[:, :, 1] + 0.114 * data[:, :, 2]

    # Simple edge detection using gradient
    grad_x = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    grad_y = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    edges = np.sqrt(grad_x**2 + grad_y**2)

    # Normalize edges
    edges = edges / edges.max() if edges.max() > 0 else edges

    # Create output
    output = np.zeros_like(data)

    # Base gray for silhouette
    base_gray = np.array(SILHOUETTE_GRAY, dtype=np.float32)

    # Slightly lighter gray for edges (subtle guidance)
    edge_boost = edges[:, :, np.newaxis] * 25  # Subtle edge highlighting

    # Apply silhouette with edge hints
    output[~is_magenta] = np.clip(base_gray + edge_boost[~is_magenta], 0, 255)

    # Set magenta background
    output[is_magenta] = MAGENTA

    result = Image.fromarray(output.astype(np.uint8))
    result.save(output_path, "PNG")
    print(f"Saved template with edges to {output_path}")

    return result


def main():
    base_path = Path(__file__).parent.parent

    # Input: original faces grid
    input_path = base_path / "input" / "faces.png"

    if not input_path.exists():
        print(f"Could not find faces grid at: {input_path}")
        return

    output_dir = base_path / "output" / "templates"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create simple template (flat gray silhouettes)
    simple_output = output_dir / "faces_template.png"
    create_face_template_grid(input_path, simple_output)

    # Create template with edge hints
    edges_output = output_dir / "faces_template_edges.png"
    create_face_template_with_edges(input_path, edges_output)

    print(f"\nTemplates saved to {output_dir}/")
    print("- faces_template.png: Flat gray silhouettes")
    print("- faces_template_edges.png: With subtle edge hints")


if __name__ == "__main__":
    main()

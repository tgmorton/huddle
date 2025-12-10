"""
Normalize - Downscale AI-generated images to proper pixel art.

Takes upscaled AI output and converts it back to clean pixel art by:
1. Dividing into grid cells
2. Averaging colors within each cell
3. Replacing chroma key (magenta) with transparency
"""

from PIL import Image
import numpy as np
from pathlib import Path
from enum import Enum
from typing import Tuple, Optional, List
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CHROMA_KEY,
    CHROMA_THRESHOLD,
    DEFAULT_SPRITE_SIZE,
    DEFAULT_GRID_DIVISIONS,
)


class ColorMethod(Enum):
    """Methods for averaging colors within a cell."""

    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"


def color_distance(c1: Tuple[int, ...], c2: Tuple[int, ...]) -> float:
    """Calculate Euclidean distance between two colors."""
    return np.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def is_chroma_key(
    color: Tuple[int, ...],
    chroma_key: Tuple[int, int, int] = CHROMA_KEY,
    threshold: int = CHROMA_THRESHOLD,
) -> bool:
    """Check if a color matches the chroma key within threshold."""
    return color_distance(color, chroma_key) <= threshold


def calculate_cell_color(
    cell_pixels: np.ndarray,
    method: ColorMethod = ColorMethod.MEAN,
    chroma_key: Tuple[int, int, int] = CHROMA_KEY,
    chroma_threshold: int = CHROMA_THRESHOLD,
) -> Tuple[int, int, int, int]:
    """
    Calculate the representative color for a cell region.

    Args:
        cell_pixels: numpy array of pixel values in the cell (H x W x C)
        method: Color averaging method
        chroma_key: Background color to treat as transparent
        chroma_threshold: Color distance threshold for chroma key

    Returns:
        RGBA tuple for the cell
    """
    # Flatten to list of pixels
    pixels = cell_pixels.reshape(-1, cell_pixels.shape[-1])

    # Filter out chroma key pixels
    non_chroma_mask = np.array(
        [not is_chroma_key(tuple(p), chroma_key, chroma_threshold) for p in pixels]
    )

    if not np.any(non_chroma_mask):
        # All pixels are chroma key -> transparent
        return (0, 0, 0, 0)

    valid_pixels = pixels[non_chroma_mask]

    # Calculate color based on method
    if method == ColorMethod.MEAN:
        avg = np.mean(valid_pixels, axis=0).astype(int)
    elif method == ColorMethod.MEDIAN:
        avg = np.median(valid_pixels, axis=0).astype(int)
    elif method == ColorMethod.MODE:
        # Find most common color
        unique, counts = np.unique(valid_pixels, axis=0, return_counts=True)
        avg = unique[np.argmax(counts)]
    else:
        avg = np.mean(valid_pixels, axis=0).astype(int)

    # Return RGBA (fully opaque)
    if len(avg) == 4:
        return tuple(avg)
    else:
        return (int(avg[0]), int(avg[1]), int(avg[2]), 255)


def normalize_sprite(
    input_image: Image.Image,
    target_size: Tuple[int, int] = (DEFAULT_SPRITE_SIZE, DEFAULT_SPRITE_SIZE),
    grid_divisions: int = DEFAULT_GRID_DIVISIONS,
    color_method: str = "mean",
    chroma_key: Tuple[int, int, int] = CHROMA_KEY,
    chroma_threshold: int = CHROMA_THRESHOLD,
) -> Image.Image:
    """
    Convert an upscaled AI image to proper pixel art.

    Args:
        input_image: Source PIL Image (upscaled from AI)
        target_size: Output dimensions (width, height)
        grid_divisions: Number of pixel cells per axis in the input
        color_method: Algorithm for color averaging ('mean', 'median', 'mode')
        chroma_key: RGB tuple for background color to remove
        chroma_threshold: Color distance tolerance for chroma key

    Returns:
        Pixelated PIL Image at target_size with transparency
    """
    # Convert to RGBA if needed
    if input_image.mode != "RGBA":
        input_image = input_image.convert("RGBA")

    # Get input dimensions
    input_width, input_height = input_image.size

    # Calculate cell size in input image
    cell_width = input_width / grid_divisions
    cell_height = input_height / grid_divisions

    # Convert to numpy array
    img_array = np.array(input_image)

    # Parse color method
    method = ColorMethod(color_method.lower())

    # Create output image
    output = Image.new("RGBA", (grid_divisions, grid_divisions))
    output_pixels = output.load()

    # Process each cell
    for y in range(grid_divisions):
        for x in range(grid_divisions):
            # Get cell boundaries
            x1 = int(x * cell_width)
            x2 = int((x + 1) * cell_width)
            y1 = int(y * cell_height)
            y2 = int((y + 1) * cell_height)

            # Extract cell pixels
            cell = img_array[y1:y2, x1:x2]

            # Calculate cell color
            color = calculate_cell_color(cell, method, chroma_key, chroma_threshold)

            # Set pixel
            output_pixels[x, y] = color

    # Scale to target size using nearest neighbor (preserves pixels)
    if (grid_divisions, grid_divisions) != target_size:
        output = output.resize(target_size, Image.Resampling.NEAREST)

    return output


def normalize_sprite_sheet(
    input_image: Image.Image,
    sprite_size: Tuple[int, int] = (DEFAULT_SPRITE_SIZE, DEFAULT_SPRITE_SIZE),
    rows: int = 1,
    cols: int = 1,
    grid_divisions: int = DEFAULT_GRID_DIVISIONS,
    color_method: str = "mean",
    chroma_key: Tuple[int, int, int] = CHROMA_KEY,
    chroma_threshold: int = CHROMA_THRESHOLD,
) -> Image.Image:
    """
    Normalize a sprite sheet with multiple sprites.

    Args:
        input_image: Source sprite sheet from AI
        sprite_size: Target size for each sprite
        rows: Number of sprite rows
        cols: Number of sprite columns
        grid_divisions: Grid divisions per sprite
        color_method: Color averaging method
        chroma_key: Background color to remove
        chroma_threshold: Chroma key tolerance

    Returns:
        Normalized sprite sheet with transparency
    """
    if input_image.mode != "RGBA":
        input_image = input_image.convert("RGBA")

    input_width, input_height = input_image.size

    # Calculate input sprite size
    input_sprite_width = input_width // cols
    input_sprite_height = input_height // rows

    # Create output sheet
    output_width = sprite_size[0] * cols
    output_height = sprite_size[1] * rows
    output_sheet = Image.new("RGBA", (output_width, output_height), (0, 0, 0, 0))

    # Process each sprite
    for row in range(rows):
        for col in range(cols):
            # Extract sprite from input
            x1 = col * input_sprite_width
            y1 = row * input_sprite_height
            x2 = x1 + input_sprite_width
            y2 = y1 + input_sprite_height

            sprite_input = input_image.crop((x1, y1, x2, y2))

            # Normalize this sprite
            sprite_output = normalize_sprite(
                sprite_input,
                target_size=sprite_size,
                grid_divisions=grid_divisions,
                color_method=color_method,
                chroma_key=chroma_key,
                chroma_threshold=chroma_threshold,
            )

            # Place in output sheet
            out_x = col * sprite_size[0]
            out_y = row * sprite_size[1]
            output_sheet.paste(sprite_output, (out_x, out_y))

    return output_sheet


def extract_sprites_from_sheet(
    sheet: Image.Image,
    rows: int,
    cols: int,
) -> List[Image.Image]:
    """
    Extract individual sprites from a sprite sheet.

    Args:
        sheet: Sprite sheet image
        rows: Number of rows
        cols: Number of columns

    Returns:
        List of individual sprite images
    """
    sprites = []
    width, height = sheet.size
    sprite_width = width // cols
    sprite_height = height // rows

    for row in range(rows):
        for col in range(cols):
            x1 = col * sprite_width
            y1 = row * sprite_height
            x2 = x1 + sprite_width
            y2 = y1 + sprite_height

            sprite = sheet.crop((x1, y1, x2, y2))
            sprites.append(sprite)

    return sprites


def batch_normalize(
    input_dir: str,
    output_dir: str,
    target_size: Tuple[int, int] = (DEFAULT_SPRITE_SIZE, DEFAULT_SPRITE_SIZE),
    grid_divisions: int = DEFAULT_GRID_DIVISIONS,
    color_method: str = "mean",
    file_pattern: str = "*.png",
) -> List[str]:
    """
    Process multiple images in a directory.

    Args:
        input_dir: Directory containing input images
        output_dir: Directory for output images
        target_size: Target sprite size
        grid_divisions: Grid divisions per sprite
        color_method: Color averaging method
        file_pattern: Glob pattern for input files

    Returns:
        List of output file paths
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_files = []

    for input_file in input_path.glob(file_pattern):
        print(f"Processing: {input_file}")

        img = Image.open(input_file)
        normalized = normalize_sprite(
            img,
            target_size=target_size,
            grid_divisions=grid_divisions,
            color_method=color_method,
        )

        output_file = output_path / f"{input_file.stem}_normalized.png"
        normalized.save(output_file)
        output_files.append(str(output_file))
        print(f"  -> {output_file}")

    return output_files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Normalize AI images to pixel art")
    parser.add_argument("input", type=str, help="Input image or directory")
    parser.add_argument("--output", "-o", type=str, required=True, help="Output path")
    parser.add_argument(
        "--size", type=int, nargs=2, default=[64, 64], help="Target size (width height)"
    )
    parser.add_argument(
        "--divisions", type=int, default=8, help="Grid divisions in input"
    )
    parser.add_argument(
        "--method",
        choices=["mean", "median", "mode"],
        default="mean",
        help="Color averaging method",
    )
    parser.add_argument(
        "--sheet", type=str, help="Sprite sheet dimensions (ROWSxCOLS)"
    )
    parser.add_argument(
        "--batch", action="store_true", help="Process directory of images"
    )

    args = parser.parse_args()

    target_size = tuple(args.size)

    if args.batch:
        batch_normalize(
            args.input,
            args.output,
            target_size=target_size,
            grid_divisions=args.divisions,
            color_method=args.method,
        )
    elif args.sheet:
        rows, cols = map(int, args.sheet.lower().split("x"))
        img = Image.open(args.input)
        normalized = normalize_sprite_sheet(
            img,
            sprite_size=target_size,
            rows=rows,
            cols=cols,
            grid_divisions=args.divisions,
            color_method=args.method,
        )

        output_path = Path(args.output)
        if output_path.suffix:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            normalized.save(output_path)
            print(f"Saved: {output_path}")
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            input_name = Path(args.input).stem
            output_file = output_path / f"{input_name}_normalized.png"
            normalized.save(output_file)
            print(f"Saved: {output_file}")
    else:
        img = Image.open(args.input)
        normalized = normalize_sprite(
            img,
            target_size=target_size,
            grid_divisions=args.divisions,
            color_method=args.method,
        )

        output_path = Path(args.output)
        if output_path.suffix:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            normalized.save(output_path)
            print(f"Saved: {output_path}")
        else:
            output_path.mkdir(parents=True, exist_ok=True)
            input_name = Path(args.input).stem
            output_file = output_path / f"{input_name}_normalized.png"
            normalized.save(output_file)
            print(f"Saved: {output_file}")

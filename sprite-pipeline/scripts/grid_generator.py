"""
Grid Generator - Creates pixel grid templates for AI art generators.

Generates grids with magenta (#FF00FF) background that can be used as
reference/overlay when generating pixel art with AI tools.
"""

from PIL import Image, ImageDraw
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    CHROMA_KEY,
    GRID_LINE_COLOR,
    GRID_LINE_WIDTH,
    DEFAULT_SPRITE_SIZE,
    DEFAULT_GRID_DIVISIONS,
    DEFAULT_OUTPUT_SCALE,
)


def generate_grid(
    total_pixels: int = DEFAULT_SPRITE_SIZE,
    grid_divisions: int = DEFAULT_GRID_DIVISIONS,
    output_size: int = DEFAULT_OUTPUT_SCALE,
    background_color: tuple = CHROMA_KEY,
    line_color: tuple = GRID_LINE_COLOR,
    line_width: int = GRID_LINE_WIDTH,
) -> Image.Image:
    """
    Generate a single-sprite grid template.

    Args:
        total_pixels: Target sprite size in pixels (e.g., 64 for 64x64)
        grid_divisions: Number of grid divisions per axis (e.g., 8 for 8x8 grid)
        output_size: Output image size for AI generator (e.g., 512)
        background_color: RGB tuple for background (default: magenta)
        line_color: RGB tuple for grid lines (default: black)
        line_width: Width of grid lines in pixels

    Returns:
        PIL Image with grid on colored background
    """
    # Create image with background color
    img = Image.new("RGB", (output_size, output_size), background_color)
    draw = ImageDraw.Draw(img)

    # Calculate cell size in output image
    cell_size = output_size / grid_divisions

    # Draw vertical lines
    for i in range(grid_divisions + 1):
        x = int(i * cell_size)
        draw.line([(x, 0), (x, output_size)], fill=line_color, width=line_width)

    # Draw horizontal lines
    for i in range(grid_divisions + 1):
        y = int(i * cell_size)
        draw.line([(0, y), (output_size, y)], fill=line_color, width=line_width)

    return img


def generate_sprite_sheet_grid(
    sprite_size: int = DEFAULT_SPRITE_SIZE,
    grid_divisions: int = DEFAULT_GRID_DIVISIONS,
    rows: int = 1,
    cols: int = 1,
    output_scale: int = 8,
    background_color: tuple = CHROMA_KEY,
    line_color: tuple = GRID_LINE_COLOR,
    line_width: int = GRID_LINE_WIDTH,
    sprite_border_width: int = 2,
    sprite_border_color: tuple = (255, 255, 255),
) -> Image.Image:
    """
    Generate a sprite sheet grid template with multiple sprite slots.

    Args:
        sprite_size: Target sprite size in pixels (e.g., 64 for 64x64)
        grid_divisions: Number of internal grid divisions per sprite
        rows: Number of sprite rows (animation frames)
        cols: Number of sprite columns (variants/directions)
        output_scale: Multiplier for output resolution
        background_color: RGB tuple for background
        line_color: RGB tuple for internal grid lines
        line_width: Width of internal grid lines
        sprite_border_width: Width of borders between sprites
        sprite_border_color: Color for sprite borders (to separate them)

    Returns:
        PIL Image with sprite sheet grid
    """
    # Calculate dimensions
    sprite_output_size = sprite_size * output_scale
    total_width = sprite_output_size * cols
    total_height = sprite_output_size * rows

    # Create image
    img = Image.new("RGB", (total_width, total_height), background_color)
    draw = ImageDraw.Draw(img)

    # Calculate internal cell size
    cell_size = sprite_output_size / grid_divisions

    # Draw grids for each sprite slot
    for row in range(rows):
        for col in range(cols):
            offset_x = col * sprite_output_size
            offset_y = row * sprite_output_size

            # Draw internal grid lines for this sprite
            for i in range(grid_divisions + 1):
                # Vertical lines
                x = offset_x + int(i * cell_size)
                draw.line(
                    [(x, offset_y), (x, offset_y + sprite_output_size)],
                    fill=line_color,
                    width=line_width,
                )
                # Horizontal lines
                y = offset_y + int(i * cell_size)
                draw.line(
                    [(offset_x, y), (offset_x + sprite_output_size, y)],
                    fill=line_color,
                    width=line_width,
                )

    # Draw sprite borders (thicker lines between sprites)
    if sprite_border_width > 0:
        # Vertical borders
        for col in range(cols + 1):
            x = col * sprite_output_size
            draw.line(
                [(x, 0), (x, total_height)],
                fill=sprite_border_color,
                width=sprite_border_width,
            )
        # Horizontal borders
        for row in range(rows + 1):
            y = row * sprite_output_size
            draw.line(
                [(0, y), (total_width, y)],
                fill=sprite_border_color,
                width=sprite_border_width,
            )

    return img


def generate_preset_grids(
    output_dir: str,
    sprite_size: int = DEFAULT_SPRITE_SIZE,
    output_scale: int = DEFAULT_OUTPUT_SCALE,
    grid_configs: list = None,
) -> list:
    """
    Generate a set of common grid configurations.

    Args:
        output_dir: Directory to save grid images
        sprite_size: Target sprite size
        output_scale: Output image size for AI
        grid_configs: List of grid division counts (default: [4, 8, 16, 32])

    Returns:
        List of generated file paths
    """
    if grid_configs is None:
        grid_configs = [4, 8, 16, 32]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated_files = []

    for divisions in grid_configs:
        img = generate_grid(
            total_pixels=sprite_size,
            grid_divisions=divisions,
            output_size=output_scale,
        )

        filename = f"grid_{sprite_size}px_{divisions}div_{output_scale}out.png"
        filepath = output_path / filename
        img.save(filepath)
        generated_files.append(str(filepath))
        print(f"Generated: {filepath}")

    return generated_files


def save_grid(
    image: Image.Image,
    output_path: str,
    filename: str = None,
) -> str:
    """
    Save a grid image to disk.

    Args:
        image: PIL Image to save
        output_path: Directory or full file path
        filename: Optional filename (if output_path is a directory)

    Returns:
        Path to saved file
    """
    path = Path(output_path)

    if path.suffix:
        # output_path is a full file path
        filepath = path
        filepath.parent.mkdir(parents=True, exist_ok=True)
    else:
        # output_path is a directory
        path.mkdir(parents=True, exist_ok=True)
        if filename is None:
            filename = "grid.png"
        filepath = path / filename

    image.save(filepath)
    return str(filepath)


if __name__ == "__main__":
    # Demo: Generate sample grids
    import argparse

    parser = argparse.ArgumentParser(description="Generate pixel art grid templates")
    parser.add_argument(
        "--pixels", type=int, default=64, help="Target sprite size in pixels"
    )
    parser.add_argument(
        "--divisions", type=int, default=8, help="Number of grid divisions"
    )
    parser.add_argument(
        "--scale", type=int, default=512, help="Output image size for AI"
    )
    parser.add_argument("--output", "-o", type=str, required=True, help="Output path")
    parser.add_argument(
        "--sheet",
        type=str,
        help="Generate sheet grid (format: ROWSxCOLS, e.g., 4x4)",
    )
    parser.add_argument(
        "--presets", action="store_true", help="Generate preset configurations"
    )

    args = parser.parse_args()

    if args.presets:
        generate_preset_grids(args.output, args.pixels, args.scale)
    elif args.sheet:
        rows, cols = map(int, args.sheet.lower().split("x"))
        img = generate_sprite_sheet_grid(
            sprite_size=args.pixels,
            grid_divisions=args.divisions,
            rows=rows,
            cols=cols,
            output_scale=args.scale // args.pixels,
        )
        filepath = save_grid(
            img,
            args.output,
            f"sheet_{rows}x{cols}_{args.pixels}px_{args.divisions}div.png",
        )
        print(f"Generated: {filepath}")
    else:
        img = generate_grid(
            total_pixels=args.pixels,
            grid_divisions=args.divisions,
            output_size=args.scale,
        )
        filepath = save_grid(
            img,
            args.output,
            f"grid_{args.pixels}px_{args.divisions}div_{args.scale}out.png",
        )
        print(f"Generated: {filepath}")

#!/usr/bin/env python3
"""
Huddle Sprite Pipeline CLI

Unified command-line interface for the sprite generation pipeline:
1. grid    - Generate pixel grid templates for AI art generators
2. normalize - Convert AI output to proper pixel art
3. asset   - Create PixiJS sprite sheets from frames
4. pipeline - Full workflow from AI image to sprite asset
"""

import argparse
from pathlib import Path
from PIL import Image

from scripts.grid_generator import (
    generate_grid,
    generate_sprite_sheet_grid,
    generate_preset_grids,
    save_grid,
)
from scripts.normalize import (
    normalize_sprite,
    normalize_sprite_sheet,
    extract_sprites_from_sheet,
    batch_normalize,
)
from scripts.sprite_asset import (
    create_sprite_asset,
    create_asset_from_directory,
    extract_frames_from_sheet,
)
from config import (
    DEFAULT_SPRITE_SIZE,
    DEFAULT_GRID_DIVISIONS,
    DEFAULT_OUTPUT_SCALE,
)


def handle_grid(args):
    """Generate pixel grid templates."""
    if args.presets:
        generate_preset_grids(
            args.output,
            sprite_size=args.pixels,
            output_scale=args.scale,
        )
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


def handle_normalize(args):
    """Normalize AI images to pixel art."""
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


def handle_asset(args):
    """Create PixiJS sprite assets."""
    create_asset_from_directory(
        input_dir=args.input,
        output_path=args.output,
        animation_name=args.name,
        fps=args.fps,
        loop=not args.no_loop,
        pattern=args.pattern,
    )


def handle_pipeline(args):
    """Full pipeline: AI image -> normalize -> sprite asset."""
    target_size = tuple(args.size)
    temp_dir = Path(args.output).parent / ".temp_frames"
    temp_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(args.input)
    img = Image.open(input_path)

    if args.sheet:
        # Process sprite sheet
        rows, cols = map(int, args.sheet.lower().split("x"))

        # Normalize the sheet
        normalized = normalize_sprite_sheet(
            img,
            sprite_size=target_size,
            rows=rows,
            cols=cols,
            grid_divisions=args.divisions,
            color_method=args.method,
        )

        # Extract individual frames
        frames = extract_frames_from_sheet(normalized, rows, cols)

        # Create frame names
        frame_names = [f"{args.name}_{i:02d}" for i in range(len(frames))]

        # Create sprite asset
        create_sprite_asset(
            frames=frames,
            frame_names=frame_names,
            animation_name=args.name,
            output_path=args.output,
            fps=args.fps,
            loop=not args.no_loop,
        )
    else:
        # Single sprite
        normalized = normalize_sprite(
            img,
            target_size=target_size,
            grid_divisions=args.divisions,
            color_method=args.method,
        )

        # Save as single-frame asset
        create_sprite_asset(
            frames=[normalized],
            frame_names=[f"{args.name}_00"],
            animation_name=args.name,
            output_path=args.output,
            fps=args.fps,
            loop=not args.no_loop,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Huddle Sprite Pipeline - Convert AI art to pixel sprites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate grid templates
  python cli.py grid --presets -o ./output/grids/
  python cli.py grid --pixels 64 --divisions 8 --scale 512 -o ./output/grids/
  python cli.py grid --sheet 4x4 --pixels 64 --divisions 8 -o ./output/grids/

  # Normalize AI output
  python cli.py normalize ./input/ai_sprite.png -o ./output/normalized/
  python cli.py normalize ./input/ai_sheet.png -o ./output/ --sheet 4x4

  # Create sprite assets
  python cli.py asset ./output/normalized/ -o ./output/assets/player --name run

  # Full pipeline
  python cli.py pipeline ./input/ai_sheet.png -o ./output/assets/player --name run --sheet 4x4
        """,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Grid command
    grid_parser = subparsers.add_parser("grid", help="Generate grid templates")
    grid_parser.add_argument(
        "--pixels",
        type=int,
        default=DEFAULT_SPRITE_SIZE,
        help=f"Target sprite size in pixels (default: {DEFAULT_SPRITE_SIZE})",
    )
    grid_parser.add_argument(
        "--divisions",
        type=int,
        default=DEFAULT_GRID_DIVISIONS,
        help=f"Number of grid divisions (default: {DEFAULT_GRID_DIVISIONS})",
    )
    grid_parser.add_argument(
        "--scale",
        type=int,
        default=DEFAULT_OUTPUT_SCALE,
        help=f"Output image size for AI (default: {DEFAULT_OUTPUT_SCALE})",
    )
    grid_parser.add_argument(
        "--output", "-o", type=str, required=True, help="Output directory or file"
    )
    grid_parser.add_argument(
        "--sheet",
        type=str,
        help="Generate sheet grid (format: ROWSxCOLS, e.g., 4x4)",
    )
    grid_parser.add_argument(
        "--presets",
        action="store_true",
        help="Generate preset grid configurations",
    )

    # Normalize command
    norm_parser = subparsers.add_parser(
        "normalize", help="Normalize AI images to pixel art"
    )
    norm_parser.add_argument("input", type=str, help="Input image or directory")
    norm_parser.add_argument(
        "--output", "-o", type=str, required=True, help="Output path"
    )
    norm_parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        default=[DEFAULT_SPRITE_SIZE, DEFAULT_SPRITE_SIZE],
        help=f"Target size (width height, default: {DEFAULT_SPRITE_SIZE} {DEFAULT_SPRITE_SIZE})",
    )
    norm_parser.add_argument(
        "--divisions",
        type=int,
        default=DEFAULT_GRID_DIVISIONS,
        help=f"Grid divisions in input (default: {DEFAULT_GRID_DIVISIONS})",
    )
    norm_parser.add_argument(
        "--method",
        choices=["mean", "median", "mode"],
        default="mean",
        help="Color averaging method (default: mean)",
    )
    norm_parser.add_argument(
        "--sheet", type=str, help="Sprite sheet dimensions (ROWSxCOLS)"
    )
    norm_parser.add_argument(
        "--batch", action="store_true", help="Process directory of images"
    )

    # Asset command
    asset_parser = subparsers.add_parser(
        "asset", help="Create PixiJS sprite sheets"
    )
    asset_parser.add_argument(
        "input", type=str, help="Input directory with frame images"
    )
    asset_parser.add_argument(
        "--output", "-o", type=str, required=True, help="Output path (without extension)"
    )
    asset_parser.add_argument(
        "--name", type=str, required=True, help="Animation name"
    )
    asset_parser.add_argument(
        "--fps", type=float, default=12.0, help="Animation FPS (default: 12)"
    )
    asset_parser.add_argument(
        "--no-loop", action="store_true", help="Don't loop animation"
    )
    asset_parser.add_argument(
        "--pattern", type=str, default="*.png", help="File pattern for frames"
    )

    # Pipeline command
    pipe_parser = subparsers.add_parser(
        "pipeline", help="Full AI image to sprite asset pipeline"
    )
    pipe_parser.add_argument("input", type=str, help="Input AI-generated image")
    pipe_parser.add_argument(
        "--output", "-o", type=str, required=True, help="Output path (without extension)"
    )
    pipe_parser.add_argument(
        "--name", type=str, required=True, help="Animation name"
    )
    pipe_parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        default=[DEFAULT_SPRITE_SIZE, DEFAULT_SPRITE_SIZE],
        help="Target sprite size",
    )
    pipe_parser.add_argument(
        "--divisions",
        type=int,
        default=DEFAULT_GRID_DIVISIONS,
        help="Grid divisions in input",
    )
    pipe_parser.add_argument(
        "--method",
        choices=["mean", "median", "mode"],
        default="mean",
        help="Color averaging method",
    )
    pipe_parser.add_argument(
        "--sheet", type=str, help="Sprite sheet dimensions (ROWSxCOLS)"
    )
    pipe_parser.add_argument(
        "--fps", type=float, default=12.0, help="Animation FPS"
    )
    pipe_parser.add_argument(
        "--no-loop", action="store_true", help="Don't loop animation"
    )

    args = parser.parse_args()

    if args.command == "grid":
        handle_grid(args)
    elif args.command == "normalize":
        handle_normalize(args)
    elif args.command == "asset":
        handle_asset(args)
    elif args.command == "pipeline":
        handle_pipeline(args)


if __name__ == "__main__":
    main()

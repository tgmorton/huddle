"""
Sprite Asset Generator - Create PixiJS-compatible sprite sheets with JSON metadata.

Combines normalized pixel art frames into sprite sheets and generates
JSON metadata compatible with PixiJS Spritesheet/AnimatedSprite.
"""

from PIL import Image
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import math
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEFAULT_SPRITE_SIZE


@dataclass
class FrameData:
    """Single frame metadata for PixiJS."""

    frame: Dict[str, int]  # {x, y, w, h}
    rotated: bool = False
    trimmed: bool = False
    spriteSourceSize: Dict[str, int] = None  # {x, y, w, h}
    sourceSize: Dict[str, int] = None  # {w, h}

    def __post_init__(self):
        if self.spriteSourceSize is None:
            self.spriteSourceSize = {
                "x": 0,
                "y": 0,
                "w": self.frame["w"],
                "h": self.frame["h"],
            }
        if self.sourceSize is None:
            self.sourceSize = {"w": self.frame["w"], "h": self.frame["h"]}


def create_sprite_asset(
    frames: List[Image.Image],
    frame_names: List[str],
    animation_name: str,
    output_path: str,
    fps: float = 12.0,
    loop: bool = True,
    columns: Optional[int] = None,
    padding: int = 0,
) -> Tuple[str, str]:
    """
    Create a sprite sheet from individual frames with PixiJS JSON metadata.

    Args:
        frames: List of PIL Images (all same size)
        frame_names: Names for each frame (used in JSON)
        animation_name: Name for the animation sequence
        output_path: Base path for output (without extension)
        fps: Animation speed in frames per second
        loop: Whether animation loops
        columns: Number of columns (None = auto-calculate as single row)
        padding: Pixels between frames

    Returns:
        Tuple of (png_path, json_path)
    """
    if not frames:
        raise ValueError("No frames provided")

    # Get frame dimensions (assume all same size)
    frame_width, frame_height = frames[0].size
    num_frames = len(frames)

    # Calculate sheet layout
    if columns is None:
        columns = num_frames  # Single row by default
    rows = math.ceil(num_frames / columns)

    # Calculate sheet dimensions
    sheet_width = columns * (frame_width + padding) + padding
    sheet_height = rows * (frame_height + padding) + padding

    # Create sheet image
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    # Build frame metadata
    frames_meta = {}
    animation_frames = []

    for i, (frame, name) in enumerate(zip(frames, frame_names)):
        col = i % columns
        row = i // columns

        x = padding + col * (frame_width + padding)
        y = padding + row * (frame_height + padding)

        # Paste frame
        sheet.paste(frame, (x, y))

        # Add metadata
        frames_meta[name] = asdict(
            FrameData(
                frame={"x": x, "y": y, "w": frame_width, "h": frame_height},
            )
        )
        animation_frames.append(name)

    # Build full metadata
    output_base = Path(output_path)
    png_filename = f"{output_base.name}.png"

    metadata = {
        "frames": frames_meta,
        "animations": {animation_name: animation_frames},
        "meta": {
            "app": "huddle-sprite-pipeline",
            "version": "1.0.0",
            "image": png_filename,
            "format": "RGBA8888",
            "size": {"w": sheet_width, "h": sheet_height},
            "scale": "1",
            "fps": fps,
            "loop": loop,
        },
    }

    # Save files
    output_base.parent.mkdir(parents=True, exist_ok=True)

    png_path = str(output_base) + ".png"
    json_path = str(output_base) + ".json"

    sheet.save(png_path)
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Created sprite sheet: {png_path}")
    print(f"Created metadata: {json_path}")

    return png_path, json_path


def create_multi_animation_asset(
    animations: Dict[str, List[Image.Image]],
    output_path: str,
    fps_map: Optional[Dict[str, float]] = None,
    loop_map: Optional[Dict[str, bool]] = None,
    columns: Optional[int] = None,
    padding: int = 0,
) -> Tuple[str, str]:
    """
    Create a single sprite sheet with multiple animations.

    Args:
        animations: Dict mapping animation names to frame lists
        output_path: Base path for output files
        fps_map: Optional per-animation FPS (default: 12)
        loop_map: Optional per-animation loop setting (default: True)
        columns: Number of columns in sheet
        padding: Pixels between frames

    Returns:
        Tuple of (png_path, json_path)
    """
    if fps_map is None:
        fps_map = {}
    if loop_map is None:
        loop_map = {}

    # Flatten all frames
    all_frames = []
    all_names = []
    animations_meta = {}

    for anim_name, frames in animations.items():
        frame_names = []
        for i, frame in enumerate(frames):
            name = f"{anim_name}_{i:02d}"
            all_frames.append(frame)
            all_names.append(name)
            frame_names.append(name)
        animations_meta[anim_name] = {
            "frames": frame_names,
            "fps": fps_map.get(anim_name, 12.0),
            "loop": loop_map.get(anim_name, True),
        }

    if not all_frames:
        raise ValueError("No frames provided")

    # Get frame dimensions
    frame_width, frame_height = all_frames[0].size
    num_frames = len(all_frames)

    # Calculate layout
    if columns is None:
        # Try to make it roughly square
        columns = math.ceil(math.sqrt(num_frames))
    rows = math.ceil(num_frames / columns)

    # Create sheet
    sheet_width = columns * (frame_width + padding) + padding
    sheet_height = rows * (frame_height + padding) + padding
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    # Build metadata
    frames_meta = {}

    for i, (frame, name) in enumerate(zip(all_frames, all_names)):
        col = i % columns
        row = i // columns

        x = padding + col * (frame_width + padding)
        y = padding + row * (frame_height + padding)

        sheet.paste(frame, (x, y))

        frames_meta[name] = asdict(
            FrameData(
                frame={"x": x, "y": y, "w": frame_width, "h": frame_height},
            )
        )

    # Build animations section (just frame names, not full metadata)
    animations_output = {}
    for anim_name, anim_data in animations_meta.items():
        animations_output[anim_name] = anim_data["frames"]

    output_base = Path(output_path)
    png_filename = f"{output_base.name}.png"

    metadata = {
        "frames": frames_meta,
        "animations": animations_output,
        "meta": {
            "app": "huddle-sprite-pipeline",
            "version": "1.0.0",
            "image": png_filename,
            "format": "RGBA8888",
            "size": {"w": sheet_width, "h": sheet_height},
            "scale": "1",
            "animationData": {
                name: {"fps": data["fps"], "loop": data["loop"]}
                for name, data in animations_meta.items()
            },
        },
    }

    # Save
    output_base.parent.mkdir(parents=True, exist_ok=True)

    png_path = str(output_base) + ".png"
    json_path = str(output_base) + ".json"

    sheet.save(png_path)
    with open(json_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Created sprite sheet: {png_path}")
    print(f"Created metadata: {json_path}")

    return png_path, json_path


def extract_frames_from_sheet(
    sheet: Image.Image,
    rows: int,
    cols: int,
    sprite_size: Optional[Tuple[int, int]] = None,
) -> List[Image.Image]:
    """
    Extract individual frames from a sprite sheet.

    Args:
        sheet: Sprite sheet image
        rows: Number of rows
        cols: Number of columns
        sprite_size: Optional explicit size (default: auto-calculate)

    Returns:
        List of frame images (row-major order)
    """
    width, height = sheet.size

    if sprite_size:
        sprite_width, sprite_height = sprite_size
    else:
        sprite_width = width // cols
        sprite_height = height // rows

    frames = []

    for row in range(rows):
        for col in range(cols):
            x1 = col * sprite_width
            y1 = row * sprite_height
            x2 = x1 + sprite_width
            y2 = y1 + sprite_height

            frame = sheet.crop((x1, y1, x2, y2))
            frames.append(frame)

    return frames


def create_asset_from_directory(
    input_dir: str,
    output_path: str,
    animation_name: str,
    fps: float = 12.0,
    loop: bool = True,
    pattern: str = "*.png",
) -> Tuple[str, str]:
    """
    Create sprite asset from a directory of frame images.

    Args:
        input_dir: Directory containing frame images
        output_path: Base path for output
        animation_name: Name for the animation
        fps: Animation speed
        loop: Whether to loop
        pattern: Glob pattern for frame files

    Returns:
        Tuple of (png_path, json_path)
    """
    input_path = Path(input_dir)
    files = sorted(input_path.glob(pattern))

    if not files:
        raise ValueError(f"No files matching '{pattern}' found in {input_dir}")

    frames = [Image.open(f) for f in files]
    frame_names = [f"{animation_name}_{i:02d}" for i in range(len(frames))]

    return create_sprite_asset(
        frames=frames,
        frame_names=frame_names,
        animation_name=animation_name,
        output_path=output_path,
        fps=fps,
        loop=loop,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create PixiJS sprite sheets from frames"
    )
    parser.add_argument("input", type=str, help="Input directory with frame images")
    parser.add_argument("--output", "-o", type=str, required=True, help="Output path")
    parser.add_argument(
        "--name", type=str, required=True, help="Animation name"
    )
    parser.add_argument("--fps", type=float, default=12.0, help="Animation FPS")
    parser.add_argument("--no-loop", action="store_true", help="Don't loop animation")
    parser.add_argument(
        "--pattern", type=str, default="*.png", help="File pattern for frames"
    )

    args = parser.parse_args()

    create_asset_from_directory(
        input_dir=args.input,
        output_path=args.output,
        animation_name=args.name,
        fps=args.fps,
        loop=not args.no_loop,
        pattern=args.pattern,
    )

#!/usr/bin/env python3
"""
Slice 8x8 portrait grids into individual transparent PNGs.
"""

from PIL import Image
import numpy as np
from pathlib import Path
from scipy import ndimage

# Config
GRID_SIZE = 8
MAGENTA_TOLERANCE = 40  # How close to magenta to consider as background

# Source files and their output configs
SOURCES = {
    "Gemini_Generated_Image_3h2fak3h2fak3h2f.png": {
        "output_dir": "faces",
        "name_template": "face_skin{col}_width{row}.png",
        "mode": "standard",
        "border_width": 4
    },
    "Gemini_Generated_Image_ae0jqmae0jqmae0j.png": {
        "output_dir": "hair_dark",
        "name_template": "hair_{row}_{col}.png",
        "mode": "grayscale",
        "border_width": 8
    },
    "Gemini_Generated_Image_n3vvjqn3vvjqn3vv.png": {
        "output_dir": "hair_light",
        "name_template": "hair_{row}_{col}.png",
        "mode": "grayscale",
        "border_width": 8
    },
    "Gemini_Generated_Image_pfh3zkpfh3zkpfh3.png": {
        "output_dir": "facial_hair",
        "name_template": "facial_{row}_{col}.png",
        "mode": "grayscale",
        "border_width": 9
    },
    # New face batches (to be classified by skin tone later)
    "Gemini_Generated_Image_8uf4818uf4818uf4.png": {
        "output_dir": "faces_new/batch1",
        "name_template": "face_{row}_{col}.png",
        "mode": "standard",
        "border_width": 4
    },
    "Gemini_Generated_Image_c0vic4c0vic4c0vi.png": {
        "output_dir": "faces_new/batch2",
        "name_template": "face_{row}_{col}.png",
        "mode": "standard",
        "border_width": 4
    },
}


def clear_image_border(img: Image.Image, border_width: int = 2) -> Image.Image:
    """Clear pixels within N pixels of the image edge (remove grid line artifacts)."""
    data = np.array(img)
    h, w = data.shape[:2]

    # Create border mask
    data[:border_width, :, 3] = 0       # top
    data[-border_width:, :, 3] = 0      # bottom
    data[:, :border_width, 3] = 0       # left
    data[:, -border_width:, 3] = 0      # right

    return Image.fromarray(data)


def cleanup_border_pixels(img: Image.Image, min_region_size: int = 50) -> Image.Image:
    """Remove small isolated pixel regions, especially along borders.

    Uses connected component analysis to find and remove small regions
    that aren't part of the main mass.
    """
    data = np.array(img)
    alpha = data[:, :, 3]

    # Find connected components of non-transparent pixels
    binary = alpha > 128
    labeled, num_features = ndimage.label(binary)

    if num_features == 0:
        return img

    # Get size of each region
    region_sizes = ndimage.sum(binary, labeled, range(1, num_features + 1))

    # Find regions that are too small
    small_regions = np.where(np.array(region_sizes) < min_region_size)[0] + 1

    # Create mask of pixels to remove
    remove_mask = np.isin(labeled, small_regions)

    # Also specifically check border pixels - be more aggressive there
    border_margin = 3
    h, w = alpha.shape
    border_mask = np.zeros_like(binary)
    border_mask[:border_margin, :] = True  # top
    border_mask[-border_margin:, :] = True  # bottom
    border_mask[:, :border_margin] = True  # left
    border_mask[:, -border_margin:] = True  # right

    # Find regions that touch the border
    border_regions = np.unique(labeled[border_mask & (labeled > 0)])

    # Remove border-touching regions that are small (< 200 pixels)
    for region_id in border_regions:
        region_size = region_sizes[region_id - 1]
        if region_size < 200:  # More aggressive for border regions
            remove_mask |= (labeled == region_id)

    # Apply removal
    data[:, :, 3] = np.where(remove_mask, 0, alpha)

    return Image.fromarray(data)


def remove_magenta_grayscale(img: Image.Image) -> Image.Image:
    """Remove magenta background (gentler), then desaturate to grayscale.

    Preserves edge texture better, outputs neutral gray that can be tinted.
    Also removes light pixels (hair should be dark).
    """
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.float32)

    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]

    # Gentler magenta detection - only remove obvious background
    rb_diff = np.abs(r - b)
    is_pure_magenta = (r > 180) & (b > 180) & (g < 80) & (rb_diff < 60)

    # Calculate alpha - keep more edge pixels
    alpha = np.ones_like(r)
    alpha = np.where(is_pure_magenta, 0, alpha)

    # Soft edge: fade out pixels that are mostly magenta
    rb_avg = (r + b) / 2
    g_deficit = np.maximum(0, rb_avg - g)
    magenta_strength = (g_deficit / 255) * (1 - rb_diff / 510)

    # Only fade very magenta pixels
    edge_alpha = 1 - np.clip((magenta_strength - 0.3) * 3, 0, 1)
    alpha = np.where(magenta_strength > 0.3, edge_alpha, alpha)

    # Convert to grayscale using luminance formula
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    # Make light pixels transparent - hair/beard should be dark
    # Pixels lighter than threshold are likely skin or artifacts, not hair
    light_threshold = 180
    is_too_light = luminance > light_threshold
    # Fade out light pixels
    light_fade = np.clip((luminance - 140) / 60, 0, 1)  # Gradual fade from 140-200
    alpha = alpha * (1 - light_fade)

    # Set RGB to grayscale
    data[:, :, 0] = luminance
    data[:, :, 1] = luminance
    data[:, :, 2] = luminance
    data[:, :, 3] = alpha * 255

    return Image.fromarray(data.astype(np.uint8))


def remove_magenta_background(img: Image.Image, tolerance: int = MAGENTA_TOLERANCE) -> Image.Image:
    """Replace magenta background with transparency, handling anti-aliased edges."""
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.float32)
    h, w = data.shape[:2]

    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]

    # Lip exclusion zone - don't modify alpha in this region
    lip_x, lip_y, lip_w, lip_h = 94, 178, 74, 36
    lip_mask = np.zeros((h, w), dtype=bool)
    lip_mask[lip_y:lip_y+lip_h, lip_x:lip_x+lip_w] = True

    # Magenta detection: R and B are similar and both higher than G
    rb_avg = (r + b) / 2
    rb_diff = np.abs(r - b)

    # How "magenta-like" is this pixel?
    g_deficit = np.maximum(0, rb_avg - g)
    magenta_strength = (g_deficit / 255) * (1 - rb_diff / 510)  # More lenient on R/B diff

    # Pure background: very magenta
    is_pure_magenta = (r > 160) & (b > 160) & (g < 100) & (rb_diff < 80)

    # Also catch darker magenta-tinted pixels (the fringe)
    # These have R > G and B > G even at lower brightness
    is_dark_magenta = (r > g + 15) & (b > g + 15) & (g < 60) & (rb_diff < 50)

    # Calculate alpha
    alpha = np.ones_like(r)
    alpha = np.where(is_pure_magenta, 0, alpha)
    alpha = np.where(is_dark_magenta, 0, alpha)

    # Edge pixels with magenta tint - use lower threshold
    is_magenta_tinted = magenta_strength > 0.08
    edge_alpha = 1 - np.clip(magenta_strength * 3, 0, 1)
    alpha = np.where(is_magenta_tinted & ~is_pure_magenta & ~is_dark_magenta, edge_alpha, alpha)

    # Protect lip region - force opaque
    alpha = np.where(lip_mask, 1, alpha)

    # Aggressive de-fringe for ALL pixels with any magenta contamination
    min_channel = np.minimum(np.minimum(r, g), b)
    max_channel = np.maximum(np.maximum(r, g), b)
    brightness = (r + g + b) / 3

    # Detect magenta contamination: when R and B are both elevated above G
    r_excess = np.maximum(0, r - g)
    b_excess = np.maximum(0, b - g)
    magenta_contamination = np.minimum(r_excess, b_excess) / 255

    # For dark pixels, be very aggressive
    dark_mask = brightness < 120

    # Pull R and B down to neutralize magenta
    # For dark pixels: pull toward minimum channel (makes it more neutral/gray)
    # For bright pixels: pull toward green channel
    defringe_amount = np.where(dark_mask,
                                magenta_contamination * 1.5,  # aggressive for dark
                                magenta_contamination * 0.8)  # moderate for bright
    defringe_amount = np.clip(defringe_amount, 0, 1)

    target = np.where(brightness < 80, min_channel, g)
    new_r = r - (r - target) * defringe_amount
    new_b = b - (b - target) * defringe_amount

    data[:, :, 0] = np.clip(new_r, 0, 255)
    data[:, :, 2] = np.clip(new_b, 0, 255)
    data[:, :, 3] = alpha * 255

    return Image.fromarray(data.astype(np.uint8))


def slice_grid(img_path: Path, output_dir: Path, name_template: str, mode: str = "standard", border_width: int = 2):
    """Slice an 8x8 grid image into individual cells."""
    print(f"Processing {img_path.name} (mode: {mode})...")

    img = Image.open(img_path)
    width, height = img.size
    cell_width = width // GRID_SIZE
    cell_height = height // GRID_SIZE

    print(f"  Image size: {width}x{height}, cell size: {cell_width}x{cell_height}")

    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            # Calculate cell boundaries
            left = col * cell_width
            top = row * cell_height
            right = left + cell_width
            bottom = top + cell_height

            # Crop cell
            cell = img.crop((left, top, right, bottom))

            # Remove magenta background based on mode
            if mode == "grayscale":
                cell = remove_magenta_grayscale(cell)
            else:
                cell = remove_magenta_background(cell)

            # Clear grid line artifacts at image border
            cell = clear_image_border(cell, border_width=border_width)

            # Clean up stray border pixels
            cell = cleanup_border_pixels(cell)

            # Save
            filename = name_template.format(row=row, col=col)
            cell.save(output_dir / filename, "PNG")
            count += 1

    print(f"  Saved {count} cells to {output_dir}/")


def main():
    base_path = Path(__file__).parent.parent
    assets_path = base_path / "output" / "assets"
    output_base = base_path / "output" / "sliced"

    for source_file, config in SOURCES.items():
        img_path = assets_path / source_file
        if not img_path.exists():
            print(f"Warning: {img_path} not found, skipping")
            continue

        output_dir = output_base / config["output_dir"]
        mode = config.get("mode", "standard")
        border_width = config.get("border_width", 2)
        slice_grid(img_path, output_dir, config["name_template"], mode, border_width)

    print(f"\nDone! Output in {output_base}/")


if __name__ == "__main__":
    main()

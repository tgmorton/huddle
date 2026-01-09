#!/usr/bin/env python3
"""
Tinting functions for grayscale hair/facial hair.
"""

from PIL import Image
import numpy as np
from pathlib import Path


# Hair color presets (RGB values for mid-tone)
HAIR_COLORS = {
    "black": (25, 20, 20),
    "dark_brown": (85, 55, 40),
    "brown": (90, 55, 35),
    "light_brown": (170, 125, 85),
    "auburn": (140, 65, 45),
    "red": (140, 50, 35),
    "blonde": (255, 220, 140),
    "platinum": (250, 245, 230),
    "gray": (160, 160, 170),
    "silver": (210, 210, 225),
    "white": (255, 255, 255),
}


def tint_grayscale(img: Image.Image, color: tuple[int, int, int], extreme_bright: bool = False, is_facial: bool = False) -> Image.Image:
    """
    Tint a grayscale image with a color.

    Dark pixels (hair) get tinted, light pixels (scalp) stay neutral.
    If extreme_bright=True, breaks normal rules for bleach blonde etc.
    """
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.float32)

    # Get luminance (grayscale value) and alpha
    luminance = data[:, :, 0]  # R=G=B for grayscale
    alpha = data[:, :, 3]

    # Normalize luminance and alpha to 0-1
    lum_norm = luminance / 255.0
    alpha_norm = alpha / 255.0

    r_color, g_color, b_color = color

    # Edge pixels: have partial alpha (not fully opaque)
    # These should be tinted regardless of luminance to avoid gray outlines
    is_edge = (alpha_norm > 0.01) & (alpha_norm < 0.99)

    # Also catch "gray" pixels - neutral color that should be tinted
    # These are pixels where R≈G≈B (grayscale) and visible
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    is_gray = (np.abs(r - g) < 20) & (np.abs(g - b) < 20) & (np.abs(r - b) < 20) & (alpha_norm > 0.1)

    # Combine: force tint on edges OR gray pixels
    force_tint = is_edge | is_gray

    # Bleach blonde special case - invert the luminance and go bright
    if extreme_bright:
        # Invert: dark hair becomes bright, light scalp stays light
        inv_lum = 1.0 - lum_norm
        # Apply contrast curve (S-curve)
        inv_lum_contrast = np.power(inv_lum, 0.7)  # Boost contrast
        # Push bright but not washed out
        brightness_boost = 0.4 + inv_lum_contrast * 0.55
        data[:, :, 0] = brightness_boost * r_color
        data[:, :, 1] = brightness_boost * g_color
        data[:, :, 2] = brightness_boost * b_color
        data[:, :, 3] = alpha
        return Image.fromarray(np.clip(data, 0, 255).astype(np.uint8))

    # Calculate target color brightness
    color_brightness = (r_color + g_color + b_color) / 3 / 255

    # Determine how much to tint vs keep neutral based on luminance
    # Dark pixels (low luminance) = hair = full tint
    # Light pixels (high luminance) = scalp = neutral/skin tone
    # Scalp color (neutral warm gray)
    scalp_r, scalp_g, scalp_b = 180, 160, 150

    # Lift shadows to preserve detail
    shadow_lift = 0.15 * (1 - color_brightness)
    lum_lifted = shadow_lift + lum_norm * (1 - shadow_lift)

    # Apply gentle gamma
    gamma = 0.85
    lum_curved = np.power(lum_lifted, gamma)

    # Calculate tinted color - ALL pixels get tinted (no neutral scalp)
    # This prevents gray outlines on edges
    max_brightness = 0.4 + color_brightness * 0.6
    lum_scaled = lum_curved * max_brightness
    scale_factor = 1 / max(color_brightness, 0.1)

    data[:, :, 0] = lum_scaled * r_color * scale_factor
    data[:, :, 1] = lum_scaled * g_color * scale_factor
    data[:, :, 2] = lum_scaled * b_color * scale_factor
    data[:, :, 3] = alpha

    result = np.clip(data, 0, 255).astype(np.uint8)
    # Push semi-transparent pixels further toward transparent
    alpha_out = result[:, :, 3].astype(float)
    is_semi = alpha_out < 128
    alpha_out[is_semi] = alpha_out[is_semi] * 0.5
    result[:, :, 3] = alpha_out.astype(np.uint8)
    return Image.fromarray(result)


def _darken_edges(data: np.ndarray, r_color: int, g_color: int, b_color: int, is_facial: bool = False) -> np.ndarray:
    """
    Boost alpha on semi-transparent edge pixels to reduce washed-out appearance.
    """
    from scipy import ndimage

    alpha = data[:, :, 3].astype(float)

    # Different settings for hair vs facial hair
    if is_facial:
        alpha_boost = 2.2
        min_alpha_threshold = 20
    else:
        alpha_boost = 2.5
        min_alpha_threshold = 15

    # Find semi-transparent edge pixels
    is_edge = (alpha > min_alpha_threshold) & (alpha < 200)

    # Boost their alpha
    boosted = np.minimum(alpha * alpha_boost, 255)
    data[:, :, 3] = np.where(is_edge, boosted, alpha).astype(np.uint8)

    return data


def tint_image_file(input_path: Path, output_path: Path, color_name: str):
    """Tint a grayscale image file and save it."""
    if color_name not in HAIR_COLORS:
        raise ValueError(f"Unknown color: {color_name}. Available: {list(HAIR_COLORS.keys())}")

    img = Image.open(input_path)
    tinted = tint_grayscale(img, HAIR_COLORS[color_name])
    tinted.save(output_path, "PNG")


def generate_color_variants(input_path: Path, output_dir: Path, colors: list[str] | None = None):
    """Generate multiple color variants of a grayscale image."""
    if colors is None:
        colors = list(HAIR_COLORS.keys())

    output_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(input_path)
    stem = input_path.stem

    for color_name in colors:
        tinted = tint_grayscale(img, HAIR_COLORS[color_name])
        out_file = output_dir / f"{stem}_{color_name}.png"
        tinted.save(out_file, "PNG")


def create_grid(images: list[Image.Image], cols: int = 4) -> Image.Image:
    """Arrange images into a grid."""
    if not images:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    cell_w, cell_h = images[0].size
    rows = (len(images) + cols - 1) // cols

    grid = Image.new("RGBA", (cols * cell_w, rows * cell_h), (255, 255, 255, 255))

    for i, img in enumerate(images):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        grid.paste(img, (x, y), img)

    return grid


# Demo: show all colors on one hair style
def demo_tints():
    base_path = Path(__file__).parent.parent
    hair_path = base_path / "output" / "sliced" / "hair_dark" / "hair_7_5.png"
    facial_path = base_path / "output" / "sliced" / "facial_hair" / "facial_0_0.png"
    face_path = base_path / "output" / "sliced" / "faces" / "face_skin3_width3.png"
    output_path = base_path / "output" / "tint_demo"
    output_path.mkdir(parents=True, exist_ok=True)

    face_img = Image.open(face_path).convert("RGBA")

    print("Generating hair color variants...")
    hair_tints = []
    for color_name, color_rgb in HAIR_COLORS.items():
        img = Image.open(hair_path)
        extreme = color_name == "bleach_blonde"
        tinted = tint_grayscale(img, color_rgb, extreme_bright=extreme)
        tinted.save(output_path / f"hair_{color_name}.png", "PNG")

        # Composite on face for sheet
        composite = face_img.copy()
        # Shift hair up 15px
        hair_layer = Image.new("RGBA", (composite.width, composite.height + 15), (0, 0, 0, 0))
        hair_layer.paste(tinted, (0, 0), tinted)
        composite_expanded = Image.new("RGBA", (composite.width, composite.height + 15), (0, 0, 0, 0))
        composite_expanded.paste(composite, (0, 15), composite)
        composite_final = Image.alpha_composite(composite_expanded, hair_layer)
        hair_tints.append(composite_final)
        print(f"  {color_name}")

    # Save hair tint sheet
    hair_sheet = create_grid(hair_tints, cols=4)
    hair_sheet.save(output_path / "hair_tint_sheet.png", "PNG")
    print("  Saved hair_tint_sheet.png")

    print("Generating facial hair color variants...")
    facial_tints = []
    for color_name, color_rgb in HAIR_COLORS.items():
        img = Image.open(facial_path)
        extreme = color_name == "bleach_blonde"
        tinted = tint_grayscale(img, color_rgb, extreme_bright=extreme)
        tinted.save(output_path / f"facial_{color_name}.png", "PNG")

        # Composite on face for sheet
        composite = face_img.copy()
        # Shift beard up 5px
        beard_layer = Image.new("RGBA", (composite.width, composite.height + 5), (0, 0, 0, 0))
        beard_layer.paste(tinted, (0, 0), tinted)
        composite_expanded = Image.new("RGBA", (composite.width, composite.height + 5), (0, 0, 0, 0))
        composite_expanded.paste(composite, (0, 5), composite)
        composite_final = Image.alpha_composite(composite_expanded, beard_layer)
        facial_tints.append(composite_final)
        print(f"  {color_name}")

    # Save facial hair tint sheet
    facial_sheet = create_grid(facial_tints, cols=4)
    facial_sheet.save(output_path / "facial_tint_sheet.png", "PNG")
    print("  Saved facial_tint_sheet.png")

    print(f"\nDone! Tint demos in {output_path}/")


def demo_hair_by_skin():
    """Generate hair color tests across all skin tones."""
    base_path = Path(__file__).parent.parent
    hair_path = base_path / "output" / "sliced" / "hair_dark" / "hair_7_5.png"
    faces_dir = base_path / "output" / "sliced" / "faces"
    output_path = base_path / "output" / "tint_demo"
    output_path.mkdir(parents=True, exist_ok=True)

    # Use face width 3 (medium) across all 8 skin tones
    composites = []

    for skin_tone in range(8):
        face_path = faces_dir / f"face_skin{skin_tone}_width3.png"
        face_img = Image.open(face_path).convert("RGBA")

        for color_name, color_rgb in HAIR_COLORS.items():
            img = Image.open(hair_path)
            extreme = color_name == "bleach_blonde"
            tinted = tint_grayscale(img, color_rgb, extreme_bright=extreme)

            # Composite on face
            # Shift hair up 15px
            hair_layer = Image.new("RGBA", (face_img.width, face_img.height + 15), (0, 0, 0, 0))
            hair_layer.paste(tinted, (0, 0), tinted)
            composite = Image.new("RGBA", (face_img.width, face_img.height + 15), (0, 0, 0, 0))
            composite.paste(face_img, (0, 15), face_img)
            final = Image.alpha_composite(composite, hair_layer)
            composites.append(final)

    # Create grid: rows = skin tones (8), cols = hair colors (12)
    cell_w, cell_h = composites[0].size
    num_colors = len(HAIR_COLORS)
    grid = Image.new("RGBA", (num_colors * cell_w, 8 * cell_h), (255, 255, 255, 255))

    for i, img in enumerate(composites):
        skin_tone = i // num_colors
        color_idx = i % num_colors
        x = color_idx * cell_w
        y = skin_tone * cell_h
        grid.paste(img, (x, y), img)

    grid.save(output_path / "hair_by_skin_tone.png", "PNG")
    print(f"Saved hair_by_skin_tone.png (8 skin tones x {num_colors} hair colors)")


if __name__ == "__main__":
    demo_tints()
    demo_hair_by_skin()

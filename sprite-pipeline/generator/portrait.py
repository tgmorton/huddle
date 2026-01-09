"""
Portrait generator - composites face, hair, and facial hair into player portraits.
"""

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from PIL import Image
from typing import Optional
import sys

# Add parent to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.exclusions import is_hair_allowed, is_facial_allowed
from config.demographics import (
    HAIR_COLOR_BY_SKIN_TONE,
    GRAY_HAIR_BY_AGE,
    NFL_POSITION_DEMOGRAPHICS,
    get_position_skin_tone_weights,
    should_have_gray_hair,
)


@dataclass
class PortraitConfig:
    """Configuration for portrait generation."""
    # Required
    player_id: str

    # Optional - if not provided, will be randomly selected based on demographics
    position: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[int] = None  # Player weight in lbs, affects face width selection
    skin_tone: Optional[int] = None  # 0-7, 0=lightest
    face_width: Optional[int] = None  # 0-7, 0=narrowest

    # Hair options
    hair_style: Optional[tuple[int, int]] = None  # (row, col) or None for random
    hair_color: Optional[str] = None  # color name or None for random
    no_hair: bool = False  # If True, no hair layer

    # Facial hair options
    facial_style: Optional[tuple[int, int]] = None  # (row, col) or None for random
    facial_color: Optional[str] = None  # color name or None for random (defaults to hair_color)
    no_facial_hair: bool = False  # If True, no facial hair layer

    # Reproducibility
    seed: Optional[int] = None

    # Output attributes (filled after generation)
    generated_attributes: dict = field(default_factory=dict)


class PortraitGenerator:
    """Generates player portraits by compositing face, hair, and facial hair."""

    # Asset paths
    FACES_DIR = "output/sliced/faces"
    TINTED_DIR = "output/tinted"
    PORTRAITS_DIR = "output/portraits"
    PLACEHOLDER = "output/portraits/placeholder.png"

    # Compositing offsets
    HAIR_OFFSET_Y = -15  # Hair shifted up 15px

    # New facial hair scale and offsets
    FACIAL_SCALE = 0.9  # Scale facial hair to 90%
    FACIAL_OFFSETS = {
        0: 45, 1: 45,  # Narrow faces need more offset
        2: 30, 3: 30, 4: 30, 5: 30, 6: 30, 7: 30,  # Standard offset
    }

    # Fixed offsets for batch faces
    BATCH_FACIAL_OFFSET = 30
    BATCH_HAIR_OFFSET = -10

    # Available hair colors
    HAIR_COLORS = [
        "black", "dark_brown", "brown", "light_brown",
        "auburn", "red", "blonde", "platinum",
        "gray", "silver", "white"
    ]

    # Gray hair colors (for aging)
    GRAY_COLORS = ["gray", "silver", "white"]

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize generator with base asset path."""
        if base_path is None:
            base_path = Path(__file__).parent.parent
        self.base_path = Path(base_path)

        # Verify asset directories exist
        self._verify_assets()

        # Load catalogs for style names
        self.catalogs = self._load_catalogs()

    def _verify_assets(self):
        """Verify required asset directories exist."""
        faces_dir = self.base_path / self.FACES_DIR
        tinted_dir = self.base_path / self.TINTED_DIR

        if not faces_dir.exists():
            raise FileNotFoundError(f"Faces directory not found: {faces_dir}")

        if not tinted_dir.exists():
            raise FileNotFoundError(
                f"Tinted assets not found: {tinted_dir}. Run scripts/pretint.py first."
            )

    def _load_catalogs(self) -> dict:
        """Load asset catalogs for style names."""
        catalogs = {}

        # Hair catalog
        hair_catalog_path = self.base_path / "output/sliced/hair_dark/hair_catalog.json"
        if hair_catalog_path.exists():
            with open(hair_catalog_path) as f:
                data = json.load(f)
                catalogs["hair"] = {
                    self._parse_style_coords(item["filename"]): item
                    for item in data.get("hair_styles", [])
                }

        # Facial hair catalog (new)
        facial_catalog_path = self.base_path / "output/sliced/facial_hair_new/facial_hair_catalog.json"
        if facial_catalog_path.exists():
            with open(facial_catalog_path) as f:
                data = json.load(f)
                catalogs["facial"] = {
                    self._parse_style_coords(item["filename"]): item
                    for item in data.get("facial_hair_styles", [])
                }

        # Faces catalog - use filename as key to preserve all entries
        faces_catalog_path = self.base_path / "output/sliced/faces/faces_catalog.json"
        if faces_catalog_path.exists():
            with open(faces_catalog_path) as f:
                data = json.load(f)
                catalogs["faces"] = {
                    item["filename"]: item
                    for item in data.get("faces", [])
                }

        return catalogs

    def _parse_face_coords(self, filename: str) -> tuple[int, int]:
        """Parse skin_tone, face_width from filename like 'face_skin3_width5.png'."""
        # Extract numbers from face_skin{N}_width{M}.png
        import re
        match = re.match(r"face_skin(\d+)_width(\d+)\.png", filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (0, 0)

    def _parse_style_coords(self, filename: str) -> tuple[int, int]:
        """Parse row, col from filename like 'hair_3_5.png'."""
        parts = filename.replace(".png", "").split("_")
        return (int(parts[-2]), int(parts[-1]))

    def generate(self, config: PortraitConfig) -> Image.Image:
        """Generate a portrait based on configuration."""
        # Set up random seed if provided
        if config.seed is not None:
            random.seed(config.seed)

        # Resolve all parameters
        skin_tone = self._resolve_skin_tone(config)
        face_width = self._resolve_face_width(config)

        # Load face first to determine batch for exclusions
        face, face_info = self._load_face(skin_tone, face_width)
        face_batch = self._get_face_batch(face_info)

        # Resolve styles with batch-aware exclusions
        hair_style = self._resolve_hair_style(config, face_width, face_batch)
        hair_color = self._resolve_hair_color(config, skin_tone)
        facial_style = self._resolve_facial_style(config, face_width)
        facial_color = config.facial_color or hair_color  # Default to same as hair

        # Load remaining assets
        hair = self._load_hair(hair_style, hair_color) if hair_style and not config.no_hair else None
        facial = self._load_facial(facial_style, facial_color) if facial_style and not config.no_facial_hair else None

        # Composite
        portrait = self._composite(face, hair, facial, face_width, face_info)

        # Store generated attributes
        config.generated_attributes = {
            "skin_tone": skin_tone,
            "face_width": face_width,
            "face_filename": face_info.get("filename"),
            "face_description": face_info.get("description"),
            "hair_style": hair_style,
            "hair_style_name": self._get_style_name("hair", hair_style),
            "hair_color": hair_color if hair_style else None,
            "facial_style": facial_style,
            "facial_style_name": self._get_style_name("facial", facial_style),
            "facial_color": facial_color if facial_style else None,
        }

        return portrait

    def generate_and_save(self, config: PortraitConfig) -> Path:
        """Generate a portrait and save it to the portraits directory."""
        portrait = self.generate(config)

        portraits_dir = self.base_path / self.PORTRAITS_DIR
        portraits_dir.mkdir(parents=True, exist_ok=True)

        output_path = portraits_dir / f"{config.player_id}.png"
        portrait.save(output_path, "PNG")

        return output_path

    def _resolve_skin_tone(self, config: PortraitConfig) -> int:
        """Resolve skin tone based on config or position demographics."""
        if config.skin_tone is not None:
            return max(0, min(7, config.skin_tone))

        # Use position demographics if available
        if config.position:
            weights = get_position_skin_tone_weights(config.position)
            tones = list(weights.keys())
            probs = list(weights.values())
            return random.choices(tones, weights=probs)[0]

        # Random uniform
        return random.randint(0, 7)

    def _resolve_face_width(self, config: PortraitConfig) -> int:
        """Resolve face width, considering player weight."""
        if config.face_width is not None:
            return max(0, min(7, config.face_width))

        # Weight-based restrictions
        # Light players (<200 lbs): no wide faces (0-5)
        # Heavy players (>280 lbs): no narrow faces (3-7)
        # Medium players: any face width (0-7)
        if config.weight and config.weight < 200:
            # Light players - narrower face options
            weights = [0.8, 1.0, 1.2, 1.2, 1.0, 0.8, 0.0, 0.0]
        elif config.weight and config.weight > 280:
            # Heavy players - wider face options
            weights = [0.0, 0.0, 0.0, 0.8, 1.0, 1.2, 1.2, 0.8]
        else:
            # Medium weight - slight bias toward middle widths
            weights = [0.5, 0.8, 1.0, 1.2, 1.2, 1.0, 0.8, 0.5]

        return random.choices(range(8), weights=weights)[0]

    def _get_face_batch(self, face_info: dict) -> Optional[str]:
        """Extract batch name from face info (e.g., 'batch1' from 'batch1/face_0_0.png')."""
        filename = face_info.get("filename", "")
        if filename.startswith("batch"):
            return filename.split("/")[0]
        return None

    def _resolve_hair_style(self, config: PortraitConfig, face_width: int, face_batch: str = None) -> Optional[tuple[int, int]]:
        """Resolve hair style, respecting exclusions."""
        if config.no_hair:
            return None

        if config.hair_style is not None:
            # Validate against exclusions
            row, col = config.hair_style
            if is_hair_allowed(row, col, face_width, face_batch):
                return config.hair_style
            # If specified style is banned, fall through to random

        # Chance of being bald (no hair)
        # ~5% base chance, increases with age
        bald_chance = 0.05
        if config.age is not None:
            if config.age >= 40:
                bald_chance = 0.25
            elif config.age >= 35:
                bald_chance = 0.15

        if random.random() < bald_chance:
            return None

        # Random selection respecting exclusions
        valid_styles = [
            (row, col)
            for row in range(8)
            for col in range(8)
            if is_hair_allowed(row, col, face_width, face_batch)
        ]

        if not valid_styles:
            return None

        return random.choice(valid_styles)

    def _resolve_facial_style(self, config: PortraitConfig, face_width: int) -> Optional[tuple[int, int]]:
        """Resolve facial hair style, respecting exclusions."""
        if config.no_facial_hair:
            return None

        if config.facial_style is not None:
            # Validate against exclusions
            row, col = config.facial_style
            if is_facial_allowed(row, col, face_width):
                return config.facial_style

        # Random selection respecting exclusions
        # Also add chance of no facial hair
        if random.random() < 0.3:  # 30% chance of clean shaven
            return None

        valid_styles = [
            (row, col)
            for row in range(8)
            for col in range(8)
            if is_facial_allowed(row, col, face_width)
        ]

        if not valid_styles:
            return None

        return random.choice(valid_styles)

    def _resolve_hair_color(self, config: PortraitConfig, skin_tone: int) -> str:
        """Resolve hair color based on config, demographics, and age."""
        if config.hair_color is not None:
            return config.hair_color

        # Check for gray hair based on age
        if config.age is not None:
            gray_prob = should_have_gray_hair(config.age)
            if random.random() * 100 < gray_prob:
                # Select gray variant based on age
                if config.age >= 45:
                    weights = [25.0, 35.0, 40.0]  # gray, silver, white
                elif config.age >= 35:
                    weights = [50.0, 30.0, 20.0]
                else:
                    weights = [70.0, 25.0, 5.0]
                return random.choices(self.GRAY_COLORS, weights=weights)[0]

        # Use skin tone demographics
        color_weights = HAIR_COLOR_BY_SKIN_TONE.get(skin_tone, HAIR_COLOR_BY_SKIN_TONE[4])
        colors = list(color_weights.keys())
        weights = list(color_weights.values())
        return random.choices(colors, weights=weights)[0]

    def _get_faces_by_skin_tone(self, skin_tone: int) -> list[dict]:
        """Get all faces matching a skin tone from the catalog."""
        faces_catalog = self.catalogs.get("faces", {})
        matching = []
        for coords, face_info in faces_catalog.items():
            if face_info.get("skin_tone") == skin_tone:
                matching.append(face_info)
        return matching

    def _load_face(self, skin_tone: int, face_width: int) -> tuple[Image.Image, dict]:
        """Load face asset. Returns (image, face_info)."""
        # Get all faces matching this skin tone
        matching_faces = self._get_faces_by_skin_tone(skin_tone)

        if matching_faces:
            # Randomly select from matching faces
            face_info = random.choice(matching_faces)
            face_path = self.base_path / self.FACES_DIR / face_info["filename"]
        else:
            # Fallback to original naming convention
            face_info = {"filename": f"face_skin{skin_tone}_width{face_width}.png", "skin_tone": skin_tone}
            face_path = self.base_path / self.FACES_DIR / f"face_skin{skin_tone}_width{face_width}.png"

        return Image.open(face_path).convert("RGBA"), face_info

    def _load_hair(self, style: tuple[int, int], color: str) -> Optional[Image.Image]:
        """Load pre-tinted hair asset."""
        if style is None:
            return None

        row, col = style
        hair_path = self.base_path / self.TINTED_DIR / "hair" / color / f"hair_{row}_{col}.png"

        if not hair_path.exists():
            return None

        return Image.open(hair_path).convert("RGBA")

    def _load_facial(self, style: tuple[int, int], color: str) -> Optional[Image.Image]:
        """Load pre-tinted facial hair asset."""
        if style is None:
            return None

        row, col = style
        facial_path = self.base_path / self.TINTED_DIR / "facial_new" / color / f"facial_{row}_{col}.png"

        if not facial_path.exists():
            return None

        return Image.open(facial_path).convert("RGBA")

    def _composite(
        self,
        face: Image.Image,
        hair: Optional[Image.Image],
        facial: Optional[Image.Image],
        face_width: int,
        face_info: dict,
    ) -> Image.Image:
        """Composite face, hair, and facial hair into final portrait."""
        width, height = face.size

        # Check if this is a batch face
        is_batch_face = face_info.get("filename", "").startswith("batch")

        # Expand canvas to allow hair overflow
        expand_top = abs(self.HAIR_OFFSET_Y)
        canvas_height = height + expand_top

        result = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))

        # Place face (shifted down to make room for hair overflow)
        result.paste(face, (0, expand_top), face)

        # Layer hair
        if hair is not None:
            hair_offset = self.BATCH_HAIR_OFFSET if is_batch_face else self.HAIR_OFFSET_Y
            hair_y = expand_top + hair_offset
            hair_layer = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))
            hair_layer.paste(hair, (0, hair_y), hair)
            result = Image.alpha_composite(result, hair_layer)

        # Layer facial hair (scaled to 90%)
        if facial is not None:
            # Scale facial hair
            new_w = int(facial.width * self.FACIAL_SCALE)
            new_h = int(facial.height * self.FACIAL_SCALE)
            facial = facial.resize((new_w, new_h), Image.LANCZOS)

            # Center horizontally after scaling
            x_offset = (width - new_w) // 2

            facial_offset = self.BATCH_FACIAL_OFFSET if is_batch_face else self.FACIAL_OFFSETS.get(face_width, 30)
            facial_y = expand_top + facial_offset
            facial_layer = Image.new("RGBA", (width, canvas_height), (0, 0, 0, 0))
            facial_layer.paste(facial, (x_offset, facial_y), facial)
            result = Image.alpha_composite(result, facial_layer)

        return result

    def _get_style_name(self, category: str, style: Optional[tuple[int, int]]) -> Optional[str]:
        """Get human-readable name for a style."""
        if style is None:
            return None

        catalog = self.catalogs.get(category, {})
        item = catalog.get(style, {})
        return item.get("name")

    def get_placeholder(self) -> Image.Image:
        """Load the placeholder image."""
        placeholder_path = self.base_path / self.PLACEHOLDER
        return Image.open(placeholder_path).convert("RGBA")

    def get_available_options(self) -> dict:
        """Get all available options for portrait generation."""
        return {
            "skin_tones": list(range(8)),
            "face_widths": list(range(8)),
            "hair_colors": self.HAIR_COLORS,
            "hair_styles": [
                {
                    "id": list(coords),
                    "name": item.get("name"),
                    "description": item.get("description"),
                }
                for coords, item in self.catalogs.get("hair", {}).items()
            ],
            "facial_styles": [
                {
                    "id": list(coords),
                    "name": item.get("name"),
                    "description": item.get("description"),
                }
                for coords, item in self.catalogs.get("facial", {}).items()
            ],
        }

    def get_player_description(
        self,
        skin_tone: int,
        face_width: int,
        hair_style: Optional[tuple[int, int]] = None,
        hair_color: Optional[str] = None,
        facial_style: Optional[tuple[int, int]] = None,
        facial_color: Optional[str] = None,
    ) -> str:
        """
        Get a human-readable description of a player's appearance.

        Args:
            skin_tone: Skin tone (0-7, 0=lightest)
            face_width: Face width (0-7, 0=narrowest)
            hair_style: Optional (row, col) tuple for hair style
            hair_color: Optional hair color name
            facial_style: Optional (row, col) tuple for facial hair style
            facial_color: Optional facial hair color name

        Returns:
            A prose description of the player's appearance.

        Example:
            "A man with a fair complexion and a lean face shape, with light eyes
            and subtle, even features. He has brown Crew Cut hair and a Full Beard."
        """
        parts = []

        # Get face description from catalog
        face_key = (skin_tone, face_width)
        face_catalog = self.catalogs.get("faces", {})
        face_info = face_catalog.get(face_key, {})
        face_desc = face_info.get("description", f"A man with skin tone {skin_tone} and face width {face_width}")
        parts.append(face_desc)

        # Add hair description
        if hair_style is not None:
            hair_catalog = self.catalogs.get("hair", {})
            hair_info = hair_catalog.get(hair_style, {})
            hair_name = hair_info.get("name", f"style {hair_style[0]},{hair_style[1]}")

            if hair_color:
                color_display = hair_color.replace("_", " ")
                parts.append(f"He has {color_display} {hair_name} hair.")
            else:
                parts.append(f"He has {hair_name} hair.")
        else:
            parts.append("He is bald.")

        # Add facial hair description
        if facial_style is not None:
            facial_catalog = self.catalogs.get("facial", {})
            facial_info = facial_catalog.get(facial_style, {})
            facial_name = facial_info.get("name", f"style {facial_style[0]},{facial_style[1]}")

            # Skip if it's a "Clean Shaven" entry
            if "clean shaven" not in facial_name.lower():
                if facial_color and facial_color != hair_color:
                    color_display = facial_color.replace("_", " ")
                    parts.append(f"He has a {color_display} {facial_name}.")
                else:
                    parts.append(f"He has a {facial_name}.")

        return " ".join(parts)

    def get_player_description_from_attrs(self, attrs: dict) -> str:
        """
        Get a player description from a generated_attributes dict.

        Args:
            attrs: Dict with keys: skin_tone, face_width, hair_style, hair_color,
                   facial_style, facial_color

        Returns:
            A prose description of the player's appearance.
        """
        return self.get_player_description(
            skin_tone=attrs.get("skin_tone", 0),
            face_width=attrs.get("face_width", 0),
            hair_style=tuple(attrs["hair_style"]) if attrs.get("hair_style") else None,
            hair_color=attrs.get("hair_color"),
            facial_style=tuple(attrs["facial_style"]) if attrs.get("facial_style") else None,
            facial_color=attrs.get("facial_color"),
        )

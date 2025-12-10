"""
Configuration constants for the sprite pipeline.
"""

# Chroma key color (background to remove)
CHROMA_KEY = (255, 0, 255)  # Magenta
CHROMA_THRESHOLD = 30  # Color distance tolerance for chroma key matching

# Default sizes
DEFAULT_SPRITE_SIZE = 64  # 64x64 pixel sprites
DEFAULT_GRID_DIVISIONS = 8  # 8x8 "pixels" per sprite (8 pixels per cell)
DEFAULT_OUTPUT_SCALE = 512  # Output size for AI generators

# Grid styling
GRID_LINE_COLOR = (0, 0, 0)  # Black
GRID_LINE_WIDTH = 1

# Supported input formats
SUPPORTED_INPUT_FORMATS = [".png", ".jpg", ".jpeg", ".webp"]

# Output format
OUTPUT_FORMAT = "PNG"

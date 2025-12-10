"""Constants for the Huddle TUI."""

# Pacing delays in seconds
PACING_DELAYS = {
    "instant": 0.0,
    "fast": 0.5,
    "slow": 1.5,
    "step": None,  # Wait for user input
}

# Layout names
LAYOUTS = {
    "play_by_play": "Play-by-Play",
    "field": "Field View",
    "stats": "Stats Dashboard",
    "players": "Player Stats",
    "depth_chart": "Depth Chart",
}

# Simulation modes
MODES = {
    "auto": "Auto Simulation",
    "manual": "Manual Play Calling",
}

# Default settings
DEFAULT_LAYOUT = "play_by_play"
DEFAULT_PACING = "step"
DEFAULT_MODE = "auto"

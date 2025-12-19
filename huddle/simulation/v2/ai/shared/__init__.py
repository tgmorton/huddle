"""Shared AI utilities used across multiple brains."""

from .perception import (
    calculate_effective_vision,
    angle_between,
    VisionParams,
)

__all__ = [
    "calculate_effective_vision",
    "angle_between",
    "VisionParams",
]

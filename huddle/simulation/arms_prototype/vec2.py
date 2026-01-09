"""
2D Vector math for the arms prototype.
"""

from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vec2:
    """Immutable 2D vector."""
    x: float
    y: float

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        return self * scalar

    def __truediv__(self, scalar: float) -> Vec2:
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec2) -> float:
        """2D cross product (returns scalar z-component)."""
        return self.x * other.y - self.y * other.x

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vec2:
        length = self.length()
        if length < 1e-10:
            return Vec2(0, 0)
        return self / length

    def distance_to(self, other: Vec2) -> float:
        return (other - self).length()

    def angle(self) -> float:
        """Angle in radians from positive x-axis."""
        return math.atan2(self.y, self.x)

    def rotated(self, angle: float) -> Vec2:
        """Rotate vector by angle (radians)."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vec2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

    def lerp(self, other: Vec2, t: float) -> Vec2:
        """Linear interpolation to other vector."""
        return self + (other - self) * t

    @staticmethod
    def from_angle(angle: float, length: float = 1.0) -> Vec2:
        """Create unit vector from angle (radians)."""
        return Vec2(math.cos(angle) * length, math.sin(angle) * length)

    @staticmethod
    def zero() -> Vec2:
        return Vec2(0, 0)


# Common directions (assuming y+ is "upfield" / toward offense's goal)
UP = Vec2(0, 1)      # Upfield
DOWN = Vec2(0, -1)   # Downfield
LEFT = Vec2(-1, 0)   # Toward left sideline
RIGHT = Vec2(1, 0)   # Toward right sideline

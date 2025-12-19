"""2D Vector implementation for simulation.

All positions and velocities in the simulation use Vec2.
Units are yards unless otherwise specified.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True, slots=True)
class Vec2:
    """Immutable 2D vector.

    Coordinate system:
        Origin (0, 0) = Center of field at line of scrimmage
        +X = Right (offense's perspective)
        +Y = Downfield (toward opponent's end zone)
        -Y = Backfield (toward own end zone)

    All units in yards.
    """
    x: float = 0.0
    y: float = 0.0

    # =========================================================================
    # Arithmetic Operations
    # =========================================================================

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vec2:
        if scalar == 0:
            return Vec2(0, 0)
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    # =========================================================================
    # Vector Operations
    # =========================================================================

    def dot(self, other: Vec2) -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec2) -> float:
        """2D cross product (returns scalar z-component)."""
        return self.x * other.y - self.y * other.x

    def length(self) -> float:
        """Magnitude of vector."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        """Squared magnitude (faster, avoids sqrt)."""
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vec2:
        """Unit vector in same direction."""
        length = self.length()
        if length < 0.0001:
            return Vec2(0, 0)
        return Vec2(self.x / length, self.y / length)

    def distance_to(self, other: Vec2) -> float:
        """Euclidean distance to another point."""
        return (other - self).length()

    def angle(self) -> float:
        """Angle in radians from positive X axis (-π to π)."""
        return math.atan2(self.y, self.x)

    def angle_to(self, other: Vec2) -> float:
        """Angle between this vector and another (0 to π)."""
        dot = self.normalized().dot(other.normalized())
        # Clamp to avoid floating point errors in acos
        dot = max(-1.0, min(1.0, dot))
        return math.acos(dot)

    def rotate(self, radians: float) -> Vec2:
        """Rotate vector by given angle."""
        cos_a = math.cos(radians)
        sin_a = math.sin(radians)
        return Vec2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

    def lerp(self, other: Vec2, t: float) -> Vec2:
        """Linear interpolation to another vector."""
        return Vec2(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t
        )

    def project_onto(self, other: Vec2) -> Vec2:
        """Project this vector onto another."""
        other_len_sq = other.length_squared()
        if other_len_sq < 0.0001:
            return Vec2(0, 0)
        scalar = self.dot(other) / other_len_sq
        return other * scalar

    def reflect(self, normal: Vec2) -> Vec2:
        """Reflect vector across a normal."""
        return self - normal * (2 * self.dot(normal))

    def perpendicular(self) -> Vec2:
        """Perpendicular vector (90° counterclockwise)."""
        return Vec2(-self.y, self.x)

    # =========================================================================
    # Utility
    # =========================================================================

    def clamped(self, max_length: float) -> Vec2:
        """Return vector clamped to maximum length."""
        length = self.length()
        if length <= max_length:
            return self
        return self.normalized() * max_length

    def with_x(self, x: float) -> Vec2:
        """Return new vector with different x."""
        return Vec2(x, self.y)

    def with_y(self, y: float) -> Vec2:
        """Return new vector with different y."""
        return Vec2(self.x, y)

    def rounded(self, decimals: int = 2) -> Vec2:
        """Return vector with rounded components."""
        return Vec2(round(self.x, decimals), round(self.y, decimals))

    def __repr__(self) -> str:
        return f"Vec2({self.x:.2f}, {self.y:.2f})"

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f})"

    # =========================================================================
    # Class Methods
    # =========================================================================

    @classmethod
    def zero(cls) -> Vec2:
        """Zero vector."""
        return cls(0, 0)

    @classmethod
    def up(cls) -> Vec2:
        """Unit vector pointing downfield (+Y)."""
        return cls(0, 1)

    @classmethod
    def down(cls) -> Vec2:
        """Unit vector pointing toward backfield (-Y)."""
        return cls(0, -1)

    @classmethod
    def left(cls) -> Vec2:
        """Unit vector pointing left (-X)."""
        return cls(-1, 0)

    @classmethod
    def right(cls) -> Vec2:
        """Unit vector pointing right (+X)."""
        return cls(1, 0)

    @classmethod
    def from_angle(cls, radians: float, length: float = 1.0) -> Vec2:
        """Create vector from angle and length."""
        return cls(math.cos(radians) * length, math.sin(radians) * length)

    @classmethod
    def from_polar(cls, angle: float, magnitude: float) -> Vec2:
        """Create vector from polar coordinates."""
        return cls.from_angle(angle, magnitude)

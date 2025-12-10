"""Unified 2D vector implementation for all simulations.

This module provides a single Vec2 class that combines all functionality
needed by pocket_sim, route_sim, and play_sim, eliminating code duplication.

Coordinate System Convention:
    x-axis: lateral position (negative = left, positive = right)
    y-axis: depth from LOS (positive = downfield toward defense)

    Origin (0, 0) is at the line of scrimmage, center of field.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Union


@dataclass
class Vec2:
    """2D vector for positions and directions.

    Supports common vector operations including arithmetic, geometric
    calculations, and interpolation.

    Examples:
        >>> v1 = Vec2(3, 4)
        >>> v1.length()
        5.0
        >>> v2 = Vec2(1, 0)
        >>> v1.dot(v2)
        3.0
        >>> Vec2.lerp(Vec2(0, 0), Vec2(10, 10), 0.5)
        Vec2(x=5.0, y=5.0)
    """
    x: float = 0.0
    y: float = 0.0

    # =========================================================================
    # Arithmetic Operations
    # =========================================================================

    def __add__(self, other: Vec2) -> Vec2:
        """Add two vectors."""
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        """Subtract two vectors."""
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        """Multiply vector by scalar."""
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        """Right multiplication by scalar."""
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vec2:
        """Divide vector by scalar."""
        if scalar == 0:
            return Vec2(0, 0)
        return Vec2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2:
        """Negate vector."""
        return Vec2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        """Check equality with floating point tolerance."""
        if not isinstance(other, Vec2):
            return NotImplemented
        return math.isclose(self.x, other.x, abs_tol=1e-9) and \
               math.isclose(self.y, other.y, abs_tol=1e-9)

    def __hash__(self) -> int:
        """Hash based on rounded coordinates."""
        return hash((round(self.x, 6), round(self.y, 6)))

    # =========================================================================
    # Magnitude Operations
    # =========================================================================

    def length(self) -> float:
        """Get the magnitude (length) of the vector."""
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        """Get the squared magnitude (avoids sqrt for comparisons)."""
        return self.x * self.x + self.y * self.y

    def normalized(self) -> Vec2:
        """Get a unit vector in the same direction.

        Returns zero vector if this vector has zero length.
        """
        length = self.length()
        if length == 0:
            return Vec2(0, 0)
        return Vec2(self.x / length, self.y / length)

    def clamp_length(self, max_length: float) -> Vec2:
        """Return vector with length clamped to max_length.

        If current length <= max_length, returns copy of self.
        Otherwise returns vector in same direction with max_length.
        """
        if max_length <= 0:
            return Vec2(0, 0)
        length_sq = self.length_squared()
        if length_sq <= max_length * max_length:
            return Vec2(self.x, self.y)
        length = math.sqrt(length_sq)
        scale = max_length / length
        return Vec2(self.x * scale, self.y * scale)

    # =========================================================================
    # Distance Operations
    # =========================================================================

    def distance_to(self, other: Vec2) -> float:
        """Get distance to another vector."""
        return (self - other).length()

    def distance_squared_to(self, other: Vec2) -> float:
        """Get squared distance to another vector (avoids sqrt)."""
        return (self - other).length_squared()

    # =========================================================================
    # Dot and Cross Products
    # =========================================================================

    def dot(self, other: Vec2) -> float:
        """Dot product with another vector.

        Returns:
            Scalar result: |a||b|cos(theta)
            Positive if vectors point in similar directions.
        """
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec2) -> float:
        """2D cross product (returns scalar z-component).

        Returns:
            Positive if other is counter-clockwise from self.
            Negative if other is clockwise from self.
            Zero if vectors are parallel.
        """
        return self.x * other.y - self.y * other.x

    # =========================================================================
    # Angle Operations
    # =========================================================================

    def angle(self) -> float:
        """Get angle of vector from positive x-axis in radians.

        Returns angle in range [-pi, pi].
        """
        return math.atan2(self.y, self.x)

    def angle_to(self, other: Vec2) -> float:
        """Get angle between this vector and another in radians.

        Returns angle in range [0, pi].
        """
        dot = self.dot(other)
        lengths = self.length() * other.length()
        if lengths == 0:
            return 0.0
        # Clamp to avoid floating point errors with acos
        cos_angle = max(-1.0, min(1.0, dot / lengths))
        return math.acos(cos_angle)

    def rotate(self, angle: float) -> Vec2:
        """Rotate vector by angle in radians (counter-clockwise).

        Args:
            angle: Rotation angle in radians.

        Returns:
            New rotated vector.
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vec2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

    def perpendicular(self) -> Vec2:
        """Get vector perpendicular to this one (90 degrees counter-clockwise)."""
        return Vec2(-self.y, self.x)

    def perpendicular_cw(self) -> Vec2:
        """Get vector perpendicular to this one (90 degrees clockwise)."""
        return Vec2(self.y, -self.x)

    # =========================================================================
    # Interpolation
    # =========================================================================

    def lerp(self, target: Vec2, t: float) -> Vec2:
        """Linear interpolation toward target.

        Args:
            target: Target vector to interpolate toward.
            t: Interpolation factor (0 = self, 1 = target).

        Returns:
            Interpolated vector.
        """
        return Vec2(
            self.x + (target.x - self.x) * t,
            self.y + (target.y - self.y) * t
        )

    @staticmethod
    def lerp_static(a: Vec2, b: Vec2, t: float) -> Vec2:
        """Static linear interpolation between two vectors.

        Args:
            a: Start vector.
            b: End vector.
            t: Interpolation factor (0 = a, 1 = b).

        Returns:
            Interpolated vector.
        """
        return Vec2(
            a.x + (b.x - a.x) * t,
            a.y + (b.y - a.y) * t
        )

    # =========================================================================
    # Projection
    # =========================================================================

    def project_onto(self, other: Vec2) -> Vec2:
        """Project this vector onto another vector.

        Returns:
            Component of self in the direction of other.
        """
        other_len_sq = other.length_squared()
        if other_len_sq == 0:
            return Vec2(0, 0)
        scale = self.dot(other) / other_len_sq
        return other * scale

    def reject_from(self, other: Vec2) -> Vec2:
        """Reject this vector from another (component perpendicular to other).

        Returns:
            Component of self perpendicular to other.
        """
        return self - self.project_onto(other)

    # =========================================================================
    # Utility
    # =========================================================================

    def copy(self) -> Vec2:
        """Create a copy of this vector."""
        return Vec2(self.x, self.y)

    def to_tuple(self) -> tuple[float, float]:
        """Convert to tuple."""
        return (self.x, self.y)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {"x": round(self.x, 3), "y": round(self.y, 3)}

    @classmethod
    def from_dict(cls, data: dict) -> Vec2:
        """Create from dictionary."""
        return cls(x=data.get("x", 0.0), y=data.get("y", 0.0))

    @classmethod
    def from_tuple(cls, t: tuple[float, float]) -> Vec2:
        """Create from tuple."""
        return cls(x=t[0], y=t[1])

    @classmethod
    def from_angle(cls, angle: float, length: float = 1.0) -> Vec2:
        """Create vector from angle and length.

        Args:
            angle: Angle from positive x-axis in radians.
            length: Magnitude of the vector.

        Returns:
            Vector pointing in the specified direction.
        """
        return cls(
            x=math.cos(angle) * length,
            y=math.sin(angle) * length
        )

    # =========================================================================
    # Common Vectors (Class Methods)
    # =========================================================================

    @classmethod
    def zero(cls) -> Vec2:
        """Return zero vector (0, 0)."""
        return cls(0.0, 0.0)

    @classmethod
    def one(cls) -> Vec2:
        """Return unit vector (1, 1) - not normalized."""
        return cls(1.0, 1.0)

    @classmethod
    def up(cls) -> Vec2:
        """Return unit vector pointing up/forward (0, 1).

        In our coordinate system, +y is downfield.
        """
        return cls(0.0, 1.0)

    @classmethod
    def down(cls) -> Vec2:
        """Return unit vector pointing down/backward (0, -1).

        In our coordinate system, -y is toward the backfield.
        """
        return cls(0.0, -1.0)

    @classmethod
    def left(cls) -> Vec2:
        """Return unit vector pointing left (-1, 0)."""
        return cls(-1.0, 0.0)

    @classmethod
    def right(cls) -> Vec2:
        """Return unit vector pointing right (1, 0)."""
        return cls(1.0, 0.0)

    def __repr__(self) -> str:
        return f"Vec2(x={self.x:.3f}, y={self.y:.3f})"

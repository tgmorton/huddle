"""Spatial reasoning - influence zones and queries.

Players control space through influence zones. This module provides
the tools to compute and query those zones.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Union

from ..core.vec2 import Vec2
from ..core.entities import Player


# =============================================================================
# Influence Base
# =============================================================================

class Influence(ABC):
    """Base class for influence zones."""

    @abstractmethod
    def influence_at(self, point: Vec2) -> float:
        """Get influence strength at a point (0-1)."""
        pass

    @abstractmethod
    def contains(self, point: Vec2) -> bool:
        """Check if point is within influence zone."""
        pass


@dataclass
class SphereOfInfluence(Influence):
    """Radial influence around a player.

    Influence falls off linearly from center to edge.
    Used for: blocking zones, zone coverage areas, general presence.
    """
    center: Vec2
    radius: float

    def influence_at(self, point: Vec2) -> float:
        """Influence strength at point (0-1), linear falloff."""
        dist = self.center.distance_to(point)
        if dist >= self.radius:
            return 0.0
        return 1.0 - (dist / self.radius)

    def contains(self, point: Vec2) -> bool:
        """Check if point is within radius."""
        return self.center.distance_to(point) < self.radius

    def intersects(self, other: SphereOfInfluence) -> bool:
        """Check if two spheres overlap."""
        return self.center.distance_to(other.center) < (self.radius + other.radius)

    def __repr__(self) -> str:
        return f"Sphere({self.center}, r={self.radius:.1f})"


@dataclass
class ConeOfInfluence(Influence):
    """Directional influence in front of player.

    Influence falls off by both distance and angle from facing direction.
    Used for: pursuit cones, coverage vision, ballcarrier threat.

    Attributes:
        origin: Tip of the cone (player position)
        direction: Normalized facing direction
        range: How far the cone extends
        half_angle: Half-width of cone in radians
    """
    origin: Vec2
    direction: Vec2
    range: float
    half_angle: float  # radians, ~0.5 = 30°, ~1.0 = 60°, ~1.57 = 90°

    def influence_at(self, point: Vec2) -> float:
        """Influence at point considering distance and angle."""
        to_point = point - self.origin
        dist = to_point.length()

        # Outside range
        if dist > self.range or dist < 0.001:
            return 0.0

        # Check angle
        point_dir = to_point.normalized()
        # Use dot product for angle calculation
        dot = self.direction.dot(point_dir)
        # Clamp for floating point safety
        dot = max(-1.0, min(1.0, dot))
        angle = math.acos(dot)

        # Outside cone angle
        if angle > self.half_angle:
            return 0.0

        # Falloff by distance and angle
        dist_factor = 1.0 - (dist / self.range)
        angle_factor = 1.0 - (angle / self.half_angle)

        return dist_factor * angle_factor

    def contains(self, point: Vec2) -> bool:
        """Check if point is within cone."""
        return self.influence_at(point) > 0.0

    @classmethod
    def from_velocity(
        cls,
        origin: Vec2,
        velocity: Vec2,
        range: float,
        half_angle: float,
        fallback_direction: Optional[Vec2] = None,
    ) -> ConeOfInfluence:
        """Create cone aligned with velocity direction."""
        if velocity.length() > 0.1:
            direction = velocity.normalized()
        elif fallback_direction:
            direction = fallback_direction.normalized()
        else:
            direction = Vec2.up()

        return cls(origin, direction, range, half_angle)

    def __repr__(self) -> str:
        return f"Cone({self.origin}, dir={self.direction}, r={self.range:.1f}, angle={math.degrees(self.half_angle):.0f}°)"


@dataclass
class CompositeInfluence(Influence):
    """Combination of multiple influence zones.

    Returns maximum influence from any component zone.
    Used for: complex shapes like ballcarrier (forward cone + lateral sphere).
    """
    components: List[Influence] = field(default_factory=list)

    def influence_at(self, point: Vec2) -> float:
        """Maximum influence from any component."""
        if not self.components:
            return 0.0
        return max(c.influence_at(point) for c in self.components)

    def contains(self, point: Vec2) -> bool:
        """True if any component contains the point."""
        return any(c.contains(point) for c in self.components)

    def add(self, influence: Influence) -> None:
        """Add an influence zone."""
        self.components.append(influence)


# =============================================================================
# Influence Factory
# =============================================================================

class InfluenceFactory:
    """Creates appropriate influence zones for players based on state."""

    @staticmethod
    def for_ballcarrier(player: Player) -> Influence:
        """Ballcarrier: forward threat cone + lateral cut sphere."""
        # Forward threat
        forward_cone = ConeOfInfluence.from_velocity(
            origin=player.pos,
            velocity=player.velocity,
            range=3.0 + player.attributes.speed / 50,  # 3-5 yards
            half_angle=0.6,  # ~35°
            fallback_direction=player.facing,
        )

        # Lateral threat (for cuts)
        lateral_sphere = SphereOfInfluence(
            center=player.pos,
            radius=1.0 + player.attributes.agility / 100,  # 1-2 yards
        )

        composite = CompositeInfluence()
        composite.add(forward_cone)
        composite.add(lateral_sphere)
        return composite

    @staticmethod
    def for_pursuit(player: Player) -> Influence:
        """Defender in pursuit: narrow forward cone."""
        return ConeOfInfluence.from_velocity(
            origin=player.pos,
            velocity=player.velocity,
            range=2.5 + player.attributes.speed / 40,  # 2.5-5 yards
            half_angle=0.4,  # ~23°, focused
            fallback_direction=player.facing,
        )

    @staticmethod
    def for_zone_coverage(player: Player, zone_range: float = 4.0) -> Influence:
        """Defender in zone: wide vision cone."""
        return ConeOfInfluence(
            origin=player.pos,
            direction=player.facing,
            range=zone_range,
            half_angle=1.2,  # ~70°, wide vision
        )

    @staticmethod
    def for_man_coverage(player: Player, receiver_pos: Vec2) -> Influence:
        """Defender in man coverage: cone toward receiver."""
        to_receiver = (receiver_pos - player.pos)
        if to_receiver.length() < 0.1:
            direction = player.facing
        else:
            direction = to_receiver.normalized()

        return ConeOfInfluence(
            origin=player.pos,
            direction=direction,
            range=player.attributes.coverage / 30,  # 2-3.5 yards
            half_angle=0.5,  # ~30°
        )

    @staticmethod
    def for_blocker(player: Player, engaged: bool = False) -> Influence:
        """Blocker: sphere of control."""
        radius = 1.5 if engaged else 1.0
        return SphereOfInfluence(
            center=player.pos,
            radius=radius,
        )

    @staticmethod
    def for_receiver_route(player: Player) -> Influence:
        """Receiver running route: small sphere of presence."""
        return SphereOfInfluence(
            center=player.pos,
            radius=0.8,
        )


# =============================================================================
# Spatial Queries
# =============================================================================

@dataclass
class ThreatAssessment:
    """Assessment of a threat to a ballcarrier."""
    player_id: str
    position: Vec2
    velocity: Vec2
    distance: float
    intercept_time: float
    intercept_point: Vec2
    approach_angle: float  # 0 = head-on, π = from behind
    influence_on_carrier: float  # How much their zone covers carrier

    def describe(self) -> str:
        """Human-readable threat description."""
        angle_desc = "head-on" if self.approach_angle < 0.5 else \
                     "side angle" if self.approach_angle < 2.0 else "pursuit"
        return (
            f"{self.player_id}: {self.distance:.1f}yd away, "
            f"ETA {self.intercept_time:.2f}s, {angle_desc}, "
            f"influence={self.influence_on_carrier:.0%}"
        )


class SpatialQuery:
    """Spatial queries for finding threats, holes, etc."""

    def __init__(self, players: List[Player]):
        self.players = players
        self._offense = [p for p in players if p.team.value == "offense"]
        self._defense = [p for p in players if p.team.value == "defense"]

    def find_threats(
        self,
        ballcarrier: Player,
        max_range: float = 15.0,
    ) -> List[ThreatAssessment]:
        """Find defenders threatening the ballcarrier."""
        threats = []
        bc_pos = ballcarrier.pos
        bc_vel = ballcarrier.velocity

        for defender in self._defense:
            if defender.is_down:
                continue

            dist = bc_pos.distance_to(defender.pos)
            if dist > max_range:
                continue

            # Calculate intercept
            intercept_time, intercept_point = self._calculate_intercept(
                bc_pos, bc_vel, defender.pos, defender.velocity
            )

            # Approach angle
            to_defender = defender.pos - bc_pos
            if to_defender.length() > 0.1:
                approach_angle = bc_vel.angle_to(to_defender) if bc_vel.length() > 0.1 else 0.0
            else:
                approach_angle = 0.0

            # Calculate defender's influence on ballcarrier
            defender_influence = InfluenceFactory.for_pursuit(defender)
            influence = defender_influence.influence_at(bc_pos)

            threats.append(ThreatAssessment(
                player_id=defender.id,
                position=defender.pos,
                velocity=defender.velocity,
                distance=dist,
                intercept_time=intercept_time,
                intercept_point=intercept_point,
                approach_angle=approach_angle,
                influence_on_carrier=influence,
            ))

        # Sort by intercept time
        threats.sort(key=lambda t: t.intercept_time)
        return threats

    def _calculate_intercept(
        self,
        target_pos: Vec2,
        target_vel: Vec2,
        chaser_pos: Vec2,
        chaser_vel: Vec2,
    ) -> tuple[float, Vec2]:
        """Calculate time and point of intercept.

        Simplified: assumes constant velocities.
        """
        relative_pos = target_pos - chaser_pos
        relative_vel = target_vel - chaser_vel

        # If closing, calculate time to reach
        closing_speed = -relative_vel.dot(relative_pos.normalized()) if relative_pos.length() > 0 else 0

        if closing_speed <= 0:
            # Not closing, return large time
            return 10.0, target_pos

        dist = relative_pos.length()
        time = dist / closing_speed

        # Where will they meet?
        intercept_point = target_pos + target_vel * time

        return time, intercept_point

    def find_nearest_defender(self, pos: Vec2) -> Optional[Player]:
        """Find the nearest defender to a position."""
        nearest = None
        nearest_dist = float('inf')

        for defender in self._defense:
            if defender.is_down:
                continue
            dist = pos.distance_to(defender.pos)
            if dist < nearest_dist:
                nearest = defender
                nearest_dist = dist

        return nearest

    def find_players_in_radius(self, center: Vec2, radius: float) -> List[Player]:
        """Find all players within radius of a point."""
        return [
            p for p in self.players
            if center.distance_to(p.pos) <= radius and not p.is_down
        ]

    def compute_defensive_influence_at(self, point: Vec2) -> float:
        """Total defensive influence at a point (0-1)."""
        total = 0.0
        for defender in self._defense:
            if defender.is_down:
                continue
            influence = InfluenceFactory.for_pursuit(defender)
            total = max(total, influence.influence_at(point))
        return total

    def compute_offensive_influence_at(self, point: Vec2) -> float:
        """Total offensive influence at a point (0-1)."""
        total = 0.0
        for off_player in self._offense:
            if off_player.is_down:
                continue
            influence = InfluenceFactory.for_blocker(off_player)
            total = max(total, influence.influence_at(point))
        return total

    def find_hole_quality(self, entry_point: Vec2, width: float = 2.0) -> float:
        """Assess quality of a hole at given point (0-1)."""
        # Check defensive influence in the hole area
        def_influence = self.compute_defensive_influence_at(entry_point)

        # Check offensive influence (blocking support)
        off_influence = self.compute_offensive_influence_at(entry_point)

        # Hole quality: high if offense controls, low if defense controls
        return max(0.0, min(1.0, 0.5 + off_influence - def_influence))

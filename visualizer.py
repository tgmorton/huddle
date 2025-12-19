#!/usr/bin/env python3
"""
Simulation Visualizer for Huddle v2

A pygame-based visualizer that shows:
- Player positions and movement trails
- Velocity vectors
- Influence zones
- Route waypoints and phases
- Decision reasoning in real-time
- Physics debug info (speed, acceleration, cuts)
"""

import sys
import math
sys.path.insert(0, '/Users/thomasmorton/huddle')

import pygame
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from enum import Enum

from huddle.simulation.v2.core.vec2 import Vec2
from huddle.simulation.v2.core.entities import Player, Team, Position, PlayerAttributes
from huddle.simulation.v2.core.clock import Clock
from huddle.simulation.v2.core.events import EventBus, Event, EventType
from huddle.simulation.v2.core.field import (
    Field, FIELD_WIDTH, LEFT_SIDELINE, RIGHT_SIDELINE,
    LEFT_HASH, RIGHT_HASH
)
from huddle.simulation.v2.physics.movement import MovementProfile, MovementResult
from huddle.simulation.v2.physics.body import BodyModel
from huddle.simulation.v2.physics.spatial import (
    SphereOfInfluence, ConeOfInfluence, InfluenceFactory
)
from huddle.simulation.v2.plays.routes import RouteType, ROUTE_LIBRARY, RoutePhase
from huddle.simulation.v2.systems.route_runner import RouteRunner, RouteAssignment


# =============================================================================
# Colors
# =============================================================================

class Colors:
    # Field
    FIELD_GREEN = (34, 139, 34)
    FIELD_LINES = (255, 255, 255)
    HASH_MARKS = (255, 255, 255, 128)
    ENDZONE = (0, 100, 0)

    # Teams
    OFFENSE = (65, 105, 225)  # Royal blue
    OFFENSE_LIGHT = (135, 175, 255)
    DEFENSE = (220, 20, 60)   # Crimson
    DEFENSE_LIGHT = (255, 100, 100)

    # UI
    BACKGROUND = (20, 20, 30)
    TEXT = (255, 255, 255)
    TEXT_DIM = (180, 180, 180)
    PANEL_BG = (30, 30, 45)
    HIGHLIGHT = (255, 215, 0)  # Gold

    # Physics/Debug
    VELOCITY = (0, 255, 127)   # Spring green
    WAYPOINT = (255, 165, 0)   # Orange
    WAYPOINT_DONE = (100, 100, 100)
    INFLUENCE = (255, 255, 0, 60)  # Yellow, transparent
    TRAIL = (100, 149, 237, 100)   # Cornflower blue
    CUT_INDICATOR = (255, 0, 255)  # Magenta


# =============================================================================
# Coordinate conversion
# =============================================================================

@dataclass
class Camera:
    """Handles yard-to-pixel conversion."""
    # Viewport settings
    field_center_x: float = 0.0    # Center on hash
    field_center_y: float = 10.0   # Center 10 yards downfield
    yards_visible_y: float = 35.0  # Show 35 yards of depth

    # Screen dimensions (set on init)
    screen_width: int = 1200
    screen_height: int = 800
    field_area_width: int = 800    # Left portion for field

    @property
    def pixels_per_yard(self) -> float:
        return self.screen_height / self.yards_visible_y

    def yard_to_pixel(self, pos: Vec2) -> Tuple[int, int]:
        """Convert yard position to screen pixel."""
        # X: center of field area
        px = (self.field_area_width / 2) + (pos.x - self.field_center_x) * self.pixels_per_yard
        # Y: inverted (screen Y increases down, field Y increases up)
        py = (self.screen_height / 2) - (pos.y - self.field_center_y) * self.pixels_per_yard
        return int(px), int(py)

    def yards_to_pixels(self, yards: float) -> int:
        """Convert a distance in yards to pixels."""
        return int(yards * self.pixels_per_yard)


# =============================================================================
# Player state tracking for visualization
# =============================================================================

@dataclass
class PlayerVisState:
    """Visualization state for a player."""
    player: Player
    profile: MovementProfile
    body: BodyModel

    # Trail of recent positions
    trail: List[Vec2] = field(default_factory=list)
    max_trail_length: int = 60  # ~3 seconds at 20fps

    # Last movement result for debug display
    last_result: Optional[MovementResult] = None
    last_reasoning: str = ""

    # Route info (if receiver)
    assignment: Optional[RouteAssignment] = None

    def update_trail(self):
        """Add current position to trail."""
        self.trail.append(self.player.pos)
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)


# =============================================================================
# Info Panel Renderer
# =============================================================================

class InfoPanel:
    """Renders the info panel on the right side."""

    def __init__(self, screen: pygame.Surface, camera: Camera):
        self.screen = screen
        self.camera = camera
        self.font_large = pygame.font.SysFont('Monaco', 18)
        self.font_medium = pygame.font.SysFont('Monaco', 14)
        self.font_small = pygame.font.SysFont('Monaco', 11)

        # Panel position
        self.x = camera.field_area_width + 10
        self.width = camera.screen_width - camera.field_area_width - 20
        self.y = 10

    def render(
        self,
        clock: Clock,
        players: List[PlayerVisState],
        events: List[Event],
        selected_player: Optional[PlayerVisState] = None,
    ):
        # Background
        panel_rect = pygame.Rect(
            self.camera.field_area_width, 0,
            self.camera.screen_width - self.camera.field_area_width,
            self.camera.screen_height
        )
        pygame.draw.rect(self.screen, Colors.PANEL_BG, panel_rect)

        y = self.y

        # Time
        y = self._render_section(y, "TIME", [
            f"T = {clock.current_time:.2f}s",
            f"Tick {clock.tick_count}",
        ])

        # Selected player details
        if selected_player:
            y = self._render_player_detail(y, selected_player)

        # All players summary
        y = self._render_section(y, "PLAYERS", [
            f"{p.player.name}: ({p.player.pos.x:.1f}, {p.player.pos.y:.1f})"
            for p in players
        ])

        # Recent events
        recent_events = events[-5:] if events else []
        y = self._render_section(y, "EVENTS", [
            f"T={e.time:.2f}s: {e.description[:30]}"
            for e in reversed(recent_events)
        ])

    def _render_section(self, y: int, title: str, lines: List[str]) -> int:
        """Render a section with title and lines."""
        # Title
        title_surf = self.font_large.render(title, True, Colors.HIGHLIGHT)
        self.screen.blit(title_surf, (self.x, y))
        y += 25

        # Lines
        for line in lines:
            line_surf = self.font_small.render(line, True, Colors.TEXT_DIM)
            self.screen.blit(line_surf, (self.x + 10, y))
            y += 16

        return y + 15  # Spacing after section

    def _render_player_detail(self, y: int, pv: PlayerVisState) -> int:
        """Render detailed info for selected player."""
        p = pv.player

        # Header
        title_surf = self.font_large.render(
            f"► {p.name} ({p.position.value})",
            True, Colors.OFFENSE if p.team == Team.OFFENSE else Colors.DEFENSE
        )
        self.screen.blit(title_surf, (self.x, y))
        y += 25

        # Position & Velocity
        lines = [
            f"Pos: ({p.pos.x:.2f}, {p.pos.y:.2f})",
            f"Vel: ({p.velocity.x:.2f}, {p.velocity.y:.2f})",
            f"Speed: {p.velocity.length():.2f} yd/s",
            f"Max Speed: {pv.profile.max_speed:.2f} yd/s",
        ]

        # Physics info from last result
        if pv.last_result:
            r = pv.last_result
            if r.cut_occurred:
                lines.append(f"CUT! {math.degrees(r.cut_angle):.0f}°")
            if r.at_max_speed:
                lines.append("AT MAX SPEED")

        for line in lines:
            color = Colors.TEXT if "CUT" not in line else Colors.CUT_INDICATOR
            surf = self.font_small.render(line, True, color)
            self.screen.blit(surf, (self.x + 10, y))
            y += 16

        y += 5

        # Route info
        if pv.assignment:
            a = pv.assignment
            route_lines = [
                f"Route: {a.route.name}",
                f"Phase: {a.phase.value}",
                f"Waypoint: {a.current_waypoint_idx + 1}/{len(a.route.waypoints)}",
            ]
            if a.current_target:
                dist = p.pos.distance_to(a.current_target)
                route_lines.append(f"To target: {dist:.1f}yd")

            for line in route_lines:
                surf = self.font_small.render(line, True, Colors.WAYPOINT)
                self.screen.blit(surf, (self.x + 10, y))
                y += 16

        y += 5

        # Reasoning
        if pv.last_reasoning:
            # Word wrap the reasoning
            reasoning_lines = self._wrap_text(pv.last_reasoning, 35)
            surf = self.font_small.render("Reasoning:", True, Colors.TEXT_DIM)
            self.screen.blit(surf, (self.x + 10, y))
            y += 16
            for line in reasoning_lines[:4]:  # Max 4 lines
                surf = self.font_small.render(line, True, Colors.TEXT)
                self.screen.blit(surf, (self.x + 15, y))
                y += 14

        return y + 20

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Simple word wrap."""
        words = text.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= width:
                current += (" " if current else "") + word
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines


# =============================================================================
# Field Renderer
# =============================================================================

class FieldRenderer:
    """Renders the football field."""

    def __init__(self, screen: pygame.Surface, camera: Camera):
        self.screen = screen
        self.camera = camera

    def render(self, field: Field):
        # Fill field area with green
        field_rect = pygame.Rect(0, 0, self.camera.field_area_width, self.camera.screen_height)
        pygame.draw.rect(self.screen, Colors.FIELD_GREEN, field_rect)

        # Draw sidelines
        left_px = self.camera.yard_to_pixel(Vec2(LEFT_SIDELINE, 0))[0]
        right_px = self.camera.yard_to_pixel(Vec2(RIGHT_SIDELINE, 0))[0]
        pygame.draw.line(self.screen, Colors.FIELD_LINES, (left_px, 0), (left_px, self.camera.screen_height), 2)
        pygame.draw.line(self.screen, Colors.FIELD_LINES, (right_px, 0), (right_px, self.camera.screen_height), 2)

        # Draw yard lines every 5 yards
        for y in range(-10, 50, 5):
            px, py = self.camera.yard_to_pixel(Vec2(0, y))
            pygame.draw.line(self.screen, Colors.FIELD_LINES, (left_px, py), (right_px, py), 1)

            # Yard markers
            font = pygame.font.SysFont('Monaco', 12)
            label = font.render(f"{y}", True, Colors.FIELD_LINES)
            self.screen.blit(label, (left_px + 5, py - 8))

        # Draw LOS (y=0) thicker
        _, los_py = self.camera.yard_to_pixel(Vec2(0, 0))
        pygame.draw.line(self.screen, Colors.HIGHLIGHT, (left_px, los_py), (right_px, los_py), 3)

        # Draw hash marks
        left_hash_px = self.camera.yard_to_pixel(Vec2(LEFT_HASH, 0))[0]
        right_hash_px = self.camera.yard_to_pixel(Vec2(RIGHT_HASH, 0))[0]
        for y in range(-10, 50, 1):
            _, py = self.camera.yard_to_pixel(Vec2(0, y))
            pygame.draw.line(self.screen, Colors.HASH_MARKS, (left_hash_px - 5, py), (left_hash_px + 5, py), 1)
            pygame.draw.line(self.screen, Colors.HASH_MARKS, (right_hash_px - 5, py), (right_hash_px + 5, py), 1)


# =============================================================================
# Player Renderer
# =============================================================================

class PlayerRenderer:
    """Renders players with all their visual info."""

    def __init__(self, screen: pygame.Surface, camera: Camera):
        self.screen = screen
        self.camera = camera
        self.font = pygame.font.SysFont('Monaco', 10)

    def render(self, pv: PlayerVisState, selected: bool = False):
        p = pv.player

        # Trail
        self._render_trail(pv)

        # Influence zone (if selected)
        if selected:
            self._render_influence(pv)

        # Waypoints (if receiver with route)
        if pv.assignment:
            self._render_waypoints(pv)

        # Velocity vector
        self._render_velocity(pv)

        # Player body
        self._render_body(pv, selected)

        # Name label
        self._render_label(pv)

    def _render_trail(self, pv: PlayerVisState):
        """Render position trail."""
        if len(pv.trail) < 2:
            return

        points = [self.camera.yard_to_pixel(pos) for pos in pv.trail]

        # Draw with fading alpha
        for i in range(1, len(points)):
            alpha = int(255 * (i / len(points)) * 0.5)
            color = (*Colors.TRAIL[:3], alpha)
            # pygame.draw.line doesn't support alpha, so we use a surface
            pygame.draw.line(self.screen, Colors.TRAIL[:3], points[i-1], points[i], 2)

    def _render_influence(self, pv: PlayerVisState):
        """Render influence zone."""
        p = pv.player

        # Create influence based on player state
        if p.has_ball:
            influence = InfluenceFactory.for_ballcarrier(p)
        else:
            influence = SphereOfInfluence(p.pos, 2.0)

        # For sphere influence, draw a circle
        if isinstance(influence, SphereOfInfluence):
            center = self.camera.yard_to_pixel(influence.center)
            radius = self.camera.yards_to_pixels(influence.radius)

            # Semi-transparent circle
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*Colors.INFLUENCE[:3], 40), (radius, radius), radius)
            self.screen.blit(surf, (center[0] - radius, center[1] - radius))

    def _render_waypoints(self, pv: PlayerVisState):
        """Render route waypoints."""
        a = pv.assignment
        if not a:
            return

        waypoints = a._field_waypoints
        current_idx = a.current_waypoint_idx

        for i, wp in enumerate(waypoints):
            px, py = self.camera.yard_to_pixel(wp)

            if i < current_idx:
                # Already passed
                color = Colors.WAYPOINT_DONE
                radius = 4
            elif i == current_idx:
                # Current target
                color = Colors.HIGHLIGHT
                radius = 8
            else:
                # Future
                color = Colors.WAYPOINT
                radius = 6

            pygame.draw.circle(self.screen, color, (px, py), radius, 2)

            # Number
            font = pygame.font.SysFont('Monaco', 10)
            label = font.render(str(i + 1), True, color)
            self.screen.blit(label, (px + 10, py - 5))

        # Draw lines connecting waypoints
        for i in range(len(waypoints) - 1):
            p1 = self.camera.yard_to_pixel(waypoints[i])
            p2 = self.camera.yard_to_pixel(waypoints[i + 1])
            color = Colors.WAYPOINT_DONE if i < current_idx else Colors.WAYPOINT
            pygame.draw.line(self.screen, color, p1, p2, 1)

    def _render_velocity(self, pv: PlayerVisState):
        """Render velocity vector."""
        p = pv.player
        if p.velocity.length() < 0.1:
            return

        start = self.camera.yard_to_pixel(p.pos)
        # Scale velocity for visualization (1 yard/s = 10 pixels)
        end_pos = p.pos + p.velocity * 0.5  # Show 0.5s of movement
        end = self.camera.yard_to_pixel(end_pos)

        pygame.draw.line(self.screen, Colors.VELOCITY, start, end, 2)

        # Arrowhead
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_len = 8
        for da in [2.5, -2.5]:
            ax = end[0] - arrow_len * math.cos(angle + da)
            ay = end[1] - arrow_len * math.sin(angle + da)
            pygame.draw.line(self.screen, Colors.VELOCITY, end, (ax, ay), 2)

    def _render_body(self, pv: PlayerVisState, selected: bool):
        """Render player body."""
        p = pv.player
        center = self.camera.yard_to_pixel(p.pos)

        # Body radius based on BodyModel
        radius = self.camera.yards_to_pixels(pv.body.collision_radius)
        radius = max(radius, 8)  # Minimum size for visibility

        # Color based on team
        if p.team == Team.OFFENSE:
            fill = Colors.OFFENSE if not selected else Colors.OFFENSE_LIGHT
            outline = Colors.OFFENSE_LIGHT
        else:
            fill = Colors.DEFENSE if not selected else Colors.DEFENSE_LIGHT
            outline = Colors.DEFENSE_LIGHT

        # Draw body
        pygame.draw.circle(self.screen, fill, center, radius)
        pygame.draw.circle(self.screen, outline, center, radius, 2)

        # Selection indicator
        if selected:
            pygame.draw.circle(self.screen, Colors.HIGHLIGHT, center, radius + 4, 2)

        # Facing direction indicator
        facing_end = p.pos + p.facing * 0.5
        facing_px = self.camera.yard_to_pixel(facing_end)
        pygame.draw.line(self.screen, Colors.TEXT, center, facing_px, 2)

    def _render_label(self, pv: PlayerVisState):
        """Render player name label."""
        p = pv.player
        center = self.camera.yard_to_pixel(p.pos)

        # Short name (first initial + last name or just name if short)
        parts = p.name.split()
        if len(parts) > 1:
            short_name = f"{parts[0][0]}. {parts[-1]}"
        else:
            short_name = p.name[:10]

        label = self.font.render(short_name, True, Colors.TEXT)
        label_rect = label.get_rect(center=(center[0], center[1] - 20))
        self.screen.blit(label, label_rect)


# =============================================================================
# Main Visualizer
# =============================================================================

class Visualizer:
    """Main visualizer class that runs the pygame loop."""

    def __init__(self, width: int = 1200, height: int = 800):
        pygame.init()
        pygame.display.set_caption("Huddle v2 - Route Simulation Visualizer")

        self.screen = pygame.display.set_mode((width, height))
        self.clock = pygame.time.Clock()

        self.camera = Camera(screen_width=width, screen_height=height)
        self.field_renderer = FieldRenderer(self.screen, self.camera)
        self.player_renderer = PlayerRenderer(self.screen, self.camera)
        self.info_panel = InfoPanel(self.screen, self.camera)

        # Simulation state
        self.sim_clock = Clock(tick_rate=0.05)
        self.field = Field(line_of_scrimmage=25, yards_to_goal=75)
        self.event_bus = EventBus()

        self.players: List[PlayerVisState] = []
        self.route_runner = RouteRunner(self.event_bus)
        self.selected_player_idx = 0

        # Playback control
        self.running = True
        self.paused = False
        self.playback_speed = 1.0
        self.step_mode = False

    def add_receiver(
        self,
        name: str,
        route_type: RouteType,
        alignment_x: float,
        is_left_side: bool = False,
        speed: int = 90,
        accel: int = 88,
        agility: int = 88,
    ) -> PlayerVisState:
        """Add a receiver running a route."""
        if is_left_side:
            alignment_x = -abs(alignment_x)

        alignment = Vec2(alignment_x, 0)

        attrs = PlayerAttributes(speed=speed, acceleration=accel, agility=agility)
        player = Player(
            id=name.lower().replace(" ", "_"),
            name=name,
            team=Team.OFFENSE,
            position=Position.WR,
            pos=alignment,
            attributes=attrs,
        )

        profile = MovementProfile.from_attributes(speed, accel, agility)
        body = BodyModel.for_position(Position.WR)

        route = ROUTE_LIBRARY[route_type]
        assignment = self.route_runner.assign_route(player, route, alignment, is_left_side)

        pv = PlayerVisState(
            player=player,
            profile=profile,
            body=body,
            assignment=assignment,
        )

        self.players.append(pv)
        return pv

    def start_play(self):
        """Start the play (snap)."""
        self.route_runner.start_all_routes(self.sim_clock)
        self.sim_clock.mark_event("snap")

    def update(self):
        """Update simulation by one tick."""
        if self.paused and not self.step_mode:
            return

        self.step_mode = False

        for pv in self.players:
            if pv.assignment:
                result, reasoning = self.route_runner.update(
                    pv.player, pv.profile, self.sim_clock.tick_rate, self.sim_clock
                )

                pv.player.pos = result.new_pos
                pv.player.velocity = result.new_vel
                pv.last_result = result
                pv.last_reasoning = reasoning
                pv.update_trail()

        self.sim_clock.tick()

    def render(self):
        """Render everything."""
        self.screen.fill(Colors.BACKGROUND)

        # Field
        self.field_renderer.render(self.field)

        # Players
        selected = self.players[self.selected_player_idx] if self.players else None
        for i, pv in enumerate(self.players):
            self.player_renderer.render(pv, selected=(i == self.selected_player_idx))

        # Info panel
        self.info_panel.render(
            self.sim_clock,
            self.players,
            self.event_bus.history,
            selected,
        )

        # Playback status
        self._render_playback_status()

        pygame.display.flip()

    def _render_playback_status(self):
        """Render playback controls info."""
        font = pygame.font.SysFont('Monaco', 12)

        status = "PAUSED" if self.paused else "PLAYING"
        color = Colors.HIGHLIGHT if self.paused else Colors.VELOCITY

        lines = [
            f"[SPACE] {status}  [←/→] Speed: {self.playback_speed:.1f}x",
            f"[TAB] Select player  [R] Reset  [S] Step  [Q] Quit",
        ]

        for i, line in enumerate(lines):
            surf = font.render(line, True, color if i == 0 else Colors.TEXT_DIM)
            self.screen.blit(surf, (10, self.camera.screen_height - 40 + i * 18))

    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    self.running = False

                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused

                elif event.key == pygame.K_s:
                    self.step_mode = True

                elif event.key == pygame.K_TAB:
                    if self.players:
                        self.selected_player_idx = (self.selected_player_idx + 1) % len(self.players)

                elif event.key == pygame.K_LEFT:
                    self.playback_speed = max(0.25, self.playback_speed - 0.25)

                elif event.key == pygame.K_RIGHT:
                    self.playback_speed = min(4.0, self.playback_speed + 0.25)

                elif event.key == pygame.K_r:
                    self.reset()

    def reset(self):
        """Reset simulation to start."""
        self.sim_clock.reset()
        self.event_bus.clear_history()
        self.route_runner.clear_assignments()

        # Reset player positions
        for pv in self.players:
            if pv.assignment:
                pv.player.pos = pv.assignment.alignment
                pv.player.velocity = Vec2.zero()
                pv.trail.clear()
                pv.last_result = None
                pv.last_reasoning = ""

                # Re-assign route
                pv.assignment = self.route_runner.assign_route(
                    pv.player,
                    pv.assignment.route,
                    pv.assignment.alignment,
                    pv.assignment.is_left_side,
                )

        self.start_play()

    def run(self, max_time: float = 10.0):
        """Run the visualization loop."""
        self.start_play()

        target_fps = 20 * self.playback_speed

        while self.running and self.sim_clock.current_time < max_time:
            self.handle_events()
            self.update()
            self.render()

            # Adjust FPS based on playback speed
            self.clock.tick(int(20 * self.playback_speed))

        # Keep window open after simulation ends
        self.paused = True
        while self.running:
            self.handle_events()
            self.render()
            self.clock.tick(30)

        pygame.quit()


# =============================================================================
# Demo
# =============================================================================

def main():
    """Run a demo visualization."""
    vis = Visualizer(width=1200, height=800)

    # Add some receivers running different routes
    vis.add_receiver("Tyreek Hill", RouteType.GO, 22.0, is_left_side=False, speed=99)
    vis.add_receiver("Davante Adams", RouteType.CURL, 18.0, is_left_side=True, speed=88)
    vis.add_receiver("Travis Kelce", RouteType.SEAM, 5.0, is_left_side=False, speed=82)

    vis.run(max_time=5.0)


if __name__ == "__main__":
    main()

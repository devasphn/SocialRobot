"""Animated face projection for the social robot."""

from __future__ import annotations

import math
import queue
import random
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import pygame


@dataclass
class FaceSettings:
    window_size: Tuple[int, int] = (1280, 720)
    display_size: Optional[Tuple[int, int]] = None
    rotation_degrees: int = 0
    background_color: Tuple[int, int, int] = (8, 10, 26)
    face_color: Tuple[int, int, int] = (255, 221, 176)
    shadow_color: Tuple[int, int, int] = (225, 186, 138)
    eye_color: Tuple[int, int, int] = (245, 245, 255)
    pupil_color: Tuple[int, int, int] = (40, 70, 120)
    mouth_color: Tuple[int, int, int] = (70, 20, 35)
    lip_color: Tuple[int, int, int] = (255, 120, 150)
    fps: int = 60


class FaceAnimator:
    """Real-time face renderer with blinking eyes and lip-sync support."""

    def __init__(self, settings: Optional[FaceSettings] = None) -> None:
        self.settings = settings or FaceSettings()
        self.render_size = self.settings.window_size
        rotation = self.settings.rotation_degrees % 360
        if self.settings.display_size is not None:
            self.window_size = self.settings.display_size
        elif rotation in (90, 270):
            self.window_size = (self.render_size[1], self.render_size[0])
        else:
            self.window_size = self.render_size
        self._rotation_angle = rotation

        self._amplitude_queue: "queue.Queue[Tuple[float, float]]" = queue.Queue()
        self._running = threading.Event()
        self._running.set()

        self._current_mouth_level = 0.0
        self._target_mouth_level = 0.0
        self._last_mouth_update = time.monotonic()

        self._eye_open = 1.0
        self._blink_active = False
        self._blink_start = 0.0
        self._blink_duration = 0.12
        self._next_blink_time = self._schedule_next_blink()

        self._pupil_offset = [0.0, 0.0]
        self._pupil_origin = [0.0, 0.0]
        self._pupil_target = self._random_eye_target()
        self._pupil_timer = 0.0
        self._pupil_duration = random.uniform(1.2, 2.4)

        self._breath_phase = 0.0

        self._clock: Optional[pygame.time.Clock] = None
        self._screen: Optional[pygame.Surface] = None
        self._canvas: Optional[pygame.Surface] = None

    # ------------------------------------------------------------------
    # Animation helpers
    def _schedule_next_blink(self) -> float:
        return time.monotonic() + random.uniform(2.5, 4.5)

    def _random_eye_target(self) -> Tuple[float, float]:
        radius = random.uniform(6, 18)
        angle = random.uniform(0, math.tau)
        return radius * math.cos(angle), radius * math.sin(angle) * 0.6

    def _update_blink(self, dt: float) -> None:
        now = time.monotonic()
        if not self._blink_active and now >= self._next_blink_time:
            self._blink_active = True
            self._blink_start = now
            self._blink_duration = random.uniform(0.09, 0.16)

        if self._blink_active:
            progress = (now - self._blink_start) / self._blink_duration
            if progress >= 1.0:
                self._blink_active = False
                self._eye_open = 1.0
                self._next_blink_time = self._schedule_next_blink()
            else:
                progress = min(max(progress, 0.0), 1.0)
                if progress <= 0.5:
                    self._eye_open = 1.0 - (progress * 2.0)
                else:
                    self._eye_open = (progress - 0.5) * 2.0
                self._eye_open = max(0.0, min(self._eye_open, 1.0))
        else:
            self._eye_open = min(1.0, self._eye_open + dt * 3.5)

    def _update_pupil(self, dt: float) -> None:
        self._pupil_timer += dt
        if self._pupil_timer >= self._pupil_duration:
            self._pupil_origin = list(self._pupil_offset)
            self._pupil_target = self._random_eye_target()
            self._pupil_timer = 0.0
            self._pupil_duration = random.uniform(1.0, 2.2)

        t = min(1.0, self._pupil_timer / self._pupil_duration)
        ease = 0.5 - 0.5 * math.cos(math.pi * t)
        self._pupil_offset[0] = self._pupil_origin[0] + (self._pupil_target[0] - self._pupil_origin[0]) * ease
        self._pupil_offset[1] = self._pupil_origin[1] + (self._pupil_target[1] - self._pupil_origin[1]) * ease

    def _update_breath(self, dt: float) -> None:
        self._breath_phase += dt * 0.6

    def _update_mouth(self, dt: float) -> None:
        now = time.monotonic()
        while not self._amplitude_queue.empty():
            timestamp, amplitude = self._amplitude_queue.get_nowait()
            self._target_mouth_level = max(0.0, min(amplitude, 1.0))
            self._last_mouth_update = timestamp

        if now - self._last_mouth_update > 0.35:
            self._target_mouth_level *= 0.85

        smoothing = min(1.0, dt * 14.0)
        self._current_mouth_level += (self._target_mouth_level - self._current_mouth_level) * smoothing

    # ------------------------------------------------------------------
    # Public API
    def update_amplitude(self, amplitude: float) -> None:
        self._amplitude_queue.put((time.monotonic(), amplitude))

    def stop(self) -> None:
        self._running.clear()

    # ------------------------------------------------------------------
    def _draw_face(self) -> None:
        assert self._screen is not None
        assert self._canvas is not None
        surface = self._canvas
        w, h = surface.get_size()
        settings = self.settings

        surface.fill(settings.background_color)

        center_x, center_y = w // 2, h // 2 + int(math.sin(self._breath_phase) * 6)
        face_width = int(w * 0.6)
        face_height = int(h * 0.65)
        face_rect = pygame.Rect(0, 0, face_width, face_height)
        face_rect.center = (center_x, center_y)

        # Draw base head with a subtle shadow for depth
        shadow_rect = face_rect.copy()
        shadow_rect.move_ip(0, int(face_height * 0.04))
        pygame.draw.ellipse(surface, settings.shadow_color, shadow_rect)
        pygame.draw.ellipse(surface, settings.face_color, face_rect)

        # Eyebrows
        brow_offset_y = int(face_height * 0.18)
        brow_width = int(face_width * 0.32)
        brow_height = int(face_height * 0.06)
        eyebrow_color = (settings.pupil_color[0], settings.pupil_color[1], min(settings.pupil_color[2] + 40, 255))
        for side in (-1, 1):
            brow_rect = pygame.Rect(0, 0, brow_width, brow_height)
            brow_rect.center = (center_x + side * int(face_width * 0.22), center_y - brow_offset_y)
            pygame.draw.rect(surface, eyebrow_color, brow_rect, border_radius=brow_height // 2)

        # Eyes
        eye_offset_x = int(face_width * 0.22)
        eye_offset_y = int(face_height * 0.12)
        eye_radius_x = int(face_width * 0.14)
        eye_radius_y = int(face_height * 0.13)
        pupil_radius = int(eye_radius_x * 0.35)

        for side in (-1, 1):
            eye_center = (
                center_x + side * eye_offset_x,
                center_y - eye_offset_y,
            )
            eye_rect = pygame.Rect(0, 0, eye_radius_x * 2, eye_radius_y * 2)
            eye_rect.center = eye_center
            pygame.draw.ellipse(surface, settings.eye_color, eye_rect)

            # Eyelid (upper)
            if self._eye_open < 1.0:
                lid_height = int((1.0 - self._eye_open) * eye_radius_y * 2)
                lid_rect = pygame.Rect(eye_rect.left, eye_rect.top, eye_rect.width, lid_height)
                pygame.draw.rect(surface, settings.face_color, lid_rect, border_radius=eye_radius_x)

            # Pupil with highlight
            pupil_center = (
                eye_center[0] + int(self._pupil_offset[0] * side),
                eye_center[1] + int(self._pupil_offset[1]) + int((1.0 - self._eye_open) * eye_radius_y * 0.4),
            )
            pygame.draw.circle(surface, settings.pupil_color, pupil_center, pupil_radius)
            highlight = pygame.Rect(0, 0, pupil_radius // 2, pupil_radius // 2)
            highlight.center = (pupil_center[0] - pupil_radius // 2, pupil_center[1] - pupil_radius // 2)
            pygame.draw.ellipse(surface, (255, 255, 255), highlight)

            # Lower lid to soften when blinking
            if self._eye_open < 0.9:
                lower_lid_height = int((1.0 - self._eye_open) * eye_radius_y)
                lower_rect = pygame.Rect(
                    eye_rect.left,
                    eye_rect.bottom - lower_lid_height,
                    eye_rect.width,
                    lower_lid_height,
                )
                pygame.draw.rect(surface, settings.face_color, lower_rect, border_radius=eye_radius_x)

        # Mouth
        mouth_width = int(face_width * 0.42)
        mouth_min_height = int(face_height * 0.05)
        mouth_max_height = int(face_height * 0.22)
        openness = self._current_mouth_level ** 0.7
        mouth_height = max(mouth_min_height, int(mouth_min_height + openness * (mouth_max_height - mouth_min_height)))
        mouth_rect = pygame.Rect(0, 0, mouth_width, mouth_height)
        mouth_rect.center = (center_x, center_y + int(face_height * 0.24))

        pygame.draw.rect(surface, settings.lip_color, mouth_rect.inflate(0, int(face_height * 0.02)), border_radius=mouth_width // 2)
        pygame.draw.rect(surface, settings.mouth_color, mouth_rect, border_radius=mouth_width // 2)

        # Inner mouth shading and teeth indicator
        inner_height = max(6, int(mouth_height * 0.55))
        inner_rect = pygame.Rect(0, 0, int(mouth_width * 0.82), inner_height)
        inner_rect.center = (mouth_rect.centerx, mouth_rect.centery - inner_height // 4)
        pygame.draw.rect(surface, (25, 10, 18), inner_rect, border_radius=inner_rect.height // 2)

        if openness < 0.35:
            lip_line = pygame.Rect(0, 0, int(mouth_width * 0.9), max(2, mouth_height // 6))
            lip_line.center = mouth_rect.center
            pygame.draw.rect(surface, (240, 210, 220), lip_line, border_radius=lip_line.height // 2)
        else:
            teeth_height = max(4, int(mouth_height * 0.25))
            teeth_rect = pygame.Rect(0, 0, int(mouth_width * 0.78), teeth_height)
            teeth_rect.midtop = (mouth_rect.centerx, mouth_rect.top + teeth_height)
            pygame.draw.rect(surface, (245, 244, 250), teeth_rect, border_radius=teeth_height // 2)

            tongue_height = max(6, int(mouth_height * 0.3))
            tongue_rect = pygame.Rect(0, 0, int(mouth_width * 0.7), tongue_height)
            tongue_rect.midbottom = (mouth_rect.centerx, mouth_rect.bottom - max(2, tongue_height // 4))
            pygame.draw.rect(surface, (255, 105, 140), tongue_rect, border_radius=tongue_height // 2)

        final_surface = surface
        if self._rotation_angle % 360 != 0:
            final_surface = pygame.transform.rotate(surface, self._rotation_angle)

        if final_surface.get_size() != self.window_size:
            final_surface = pygame.transform.smoothscale(final_surface, self.window_size)

        self._screen.fill(settings.background_color)
        dest_rect = final_surface.get_rect(center=(self.window_size[0] // 2, self.window_size[1] // 2))
        self._screen.blit(final_surface, dest_rect)

    # ------------------------------------------------------------------
    def run(self) -> None:
        pygame.init()
        pygame.display.set_caption("Robot Face")
        self._screen = pygame.display.set_mode(self.window_size)
        self._canvas = pygame.Surface(self.render_size).convert_alpha()
        self._clock = pygame.time.Clock()

        while self._running.is_set():
            dt = self._clock.tick(self.settings.fps) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.stop()

            self._update_blink(dt)
            self._update_pupil(dt)
            self._update_breath(dt)
            self._update_mouth(dt)

            self._draw_face()
            pygame.display.flip()

        pygame.quit()


__all__ = ["FaceAnimator", "FaceSettings"]

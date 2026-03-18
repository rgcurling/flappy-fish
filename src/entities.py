"""
entities.py – Game entities: Fish, ObstaclePair, Bubble.

All visual rendering uses pygame draw primitives (no external image assets).
"""

from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    FISH_W, FISH_H, FISH_X, FISH_LERP,
    FISH_BODY, FISH_BELLY, FISH_FIN, FISH_EYE_W, FISH_EYE_P,
    GRAVITY, FLAP_FORCE, MAX_VY_DOWN, MAX_VY_UP,
    OBS_WIDTH, OBSTACLE_FILL, OBSTACLE_EDGE, OBSTACLE_CAP,
    BUBBLE_COL,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Fish
# ─────────────────────────────────────────────────────────────────────────────

class Fish:
    """
    The player character – an orange fish that swims from left to right.

    Movement modes
    ──────────────
    Hand-tracking : update_hand(norm_y)
        The fish smoothly follows the normalised Y position of the player's
        index fingertip via linear interpolation (lerp).  Moving quickly will
        tilt the fish; moving slowly keeps it level.

    Keyboard : update_keyboard(flap)
        Classic Flappy Bird physics – gravity pulls the fish down and each
        SPACE / UP press applies an upward impulse.
    """

    def __init__(self) -> None:
        self.x:        float = float(FISH_X)
        self.y:        float = float(SCREEN_HEIGHT // 2)
        self.vy:       float = 0.0        # vertical velocity (px / frame)
        self.target_y: float = self.y     # lerp target for hand mode
        self._prev_y:  float = self.y     # for computing display tilt in hand mode

    # ── Update ────────────────────────────────────────────────────────────────

    def update_hand(self, norm_y: Optional[float]) -> None:
        """
        Smoothly follow the hand's normalised Y coordinate.

        Parameters
        ----------
        norm_y : float | None
            Normalised Y in [0, 1] from MediaPipe (0 = top, 1 = bottom).
            If None (no hand detected) the fish stays at its last position.
        """
        self._prev_y = self.y
        if norm_y is not None:
            self.target_y = norm_y * SCREEN_HEIGHT

        # Lerp toward target – smooth but responsive
        self.y += (self.target_y - self.y) * FISH_LERP
        # Clamp so the fish stays fully on screen in hand mode
        self.y = max(FISH_H // 2, min(SCREEN_HEIGHT - FISH_H // 2, self.y))
        # Derive vy from actual movement for tilt animation
        self.vy = self.y - self._prev_y

    def update_keyboard(self, flap: bool) -> None:
        """
        Apply gravity and an optional upward flap impulse.

        Parameters
        ----------
        flap : bool
            True for exactly one frame each time the player presses SPACE/UP.
        """
        if flap:
            self.vy = FLAP_FORCE
        self.vy += GRAVITY
        self.vy  = max(MAX_VY_UP, min(MAX_VY_DOWN, self.vy))
        self.y  += self.vy
        # No vertical clamping in keyboard mode – going off-screen is game over.

    # ── Collision rect ────────────────────────────────────────────────────────

    @property
    def rect(self) -> pygame.Rect:
        """Inset collision rectangle for fairer hit detection."""
        margin = 7
        return pygame.Rect(
            int(self.x) - FISH_W // 2 + margin,
            int(self.y) - FISH_H // 2 + margin,
            FISH_W - 2 * margin,
            FISH_H - 2 * margin,
        )

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        """
        Render the fish centred at (self.x, self.y).

        The fish tilts based on self.vy:
          - Positive vy (falling) → nose tilts down
          - Negative vy (rising)  → nose tilts up
        This is achieved by drawing onto a temporary SRCALPHA surface and
        using pygame.transform.rotate before blitting to the main surface.
        """
        cx, cy = int(self.x), int(self.y)

        # Clamp tilt angle for visual clarity
        tilt_deg = max(-35.0, min(35.0, self.vy * 4.5))

        # Temporary transparent surface – large enough to hold the fish + tail
        sw, sh = FISH_W + 32, FISH_H + 32
        fish_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ox, oy = sw // 2, sh // 2   # local centre

        hw = FISH_W // 2
        hh = FISH_H // 2

        # --- Tail (drawn first so body overlaps it)
        tail_pts = [
            (ox - hw - 14, oy),           # pointed tip
            (ox - hw + 3,  oy - hh),      # upper base
            (ox - hw + 3,  oy + hh),      # lower base
        ]
        pygame.draw.polygon(fish_surf, FISH_FIN, tail_pts)

        # --- Body ellipse
        body_rect = pygame.Rect(ox - hw, oy - hh, FISH_W, FISH_H)
        pygame.draw.ellipse(fish_surf, FISH_BODY, body_rect)

        # --- Belly highlight (lighter teardrop shape on lower half)
        belly_rect = pygame.Rect(ox - hw // 2, oy + 2, FISH_W // 2, FISH_H // 3)
        pygame.draw.ellipse(fish_surf, FISH_BELLY, belly_rect)

        # --- Dorsal fin (top)
        fin_pts = [
            (ox - hw // 3, oy - hh),       # left base
            (ox + hw // 4, oy - hh),       # right base
            (ox,           oy - hh - 12),  # tip
        ]
        pygame.draw.polygon(fish_surf, FISH_FIN, fin_pts)

        # --- Pectoral fin (lower side)
        pec_pts = [
            (ox,           oy + 2),
            (ox + hw // 3, oy + hh - 2),
            (ox - hw // 4, oy + hh),
        ]
        pygame.draw.polygon(fish_surf, FISH_FIN, pec_pts)

        # --- Eye
        ex = ox + hw // 2
        ey = oy - hh // 4
        pygame.draw.circle(fish_surf, FISH_EYE_W, (ex, ey), 6)
        pygame.draw.circle(fish_surf, FISH_EYE_P, (ex + 1, ey), 3)

        # Rotate the fish surface and blit to the main surface
        rotated   = pygame.transform.rotate(fish_surf, -tilt_deg)
        blit_rect = rotated.get_rect(center=(cx, cy))
        surface.blit(rotated, blit_rect)


# ─────────────────────────────────────────────────────────────────────────────
#  ObstaclePair
# ─────────────────────────────────────────────────────────────────────────────

class ObstaclePair:
    """
    A pair of coral/rock columns with a vertical gap for the fish to pass through.

    The pair moves from right to left at a configurable speed.
    Once the fish's X passes the right edge of the pair, a point is awarded
    (tracked via the `scored` flag to prevent awarding multiple times).
    """

    def __init__(self, gap_center_y: int, speed: float, gap: int = 190) -> None:
        """
        Parameters
        ----------
        gap_center_y : int
            Y coordinate of the centre of the gap (px from top).
        speed : float
            Horizontal movement speed (px / frame).
        gap : int
            Vertical gap size between the two pillars (px).
            Defaults to OBS_GAP from config but can be overridden per difficulty.
        """
        # Start just off the right edge of the screen
        self.x      = float(SCREEN_WIDTH + OBS_WIDTH // 2 + 10)
        self.gap_y  = gap_center_y
        self.speed  = speed
        self.gap    = gap    # store so top_rect / bottom_rect use it
        self.scored = False  # set to True after awarding the point

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self) -> None:
        self.x -= self.speed

    @property
    def off_screen(self) -> bool:
        return self.x < -(OBS_WIDTH // 2 + 20)

    # ── Collision rects ───────────────────────────────────────────────────────

    @property
    def top_rect(self) -> pygame.Rect:
        """Rect covering the top pillar (from screen top down to gap)."""
        h = self.gap_y - self.gap // 2
        return pygame.Rect(
            int(self.x) - OBS_WIDTH // 2, 0,
            OBS_WIDTH, max(0, h),
        )

    @property
    def bottom_rect(self) -> pygame.Rect:
        """Rect covering the bottom pillar (from gap down to screen bottom)."""
        y = self.gap_y + self.gap // 2
        return pygame.Rect(
            int(self.x) - OBS_WIDTH // 2, y,
            OBS_WIDTH, max(0, SCREEN_HEIGHT - y),
        )

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_column(surface, top=True)
        self._draw_column(surface, top=False)

    def _draw_column(self, surface: pygame.Surface, top: bool) -> None:
        rect = self.top_rect if top else self.bottom_rect
        if rect.height <= 0:
            return

        ix = int(self.x)

        # ── Main pillar body ──────────────────────────────────────────────────
        pygame.draw.rect(surface, OBSTACLE_FILL, rect)

        # Edge highlights to give depth
        pygame.draw.line(
            surface, OBSTACLE_EDGE,
            (rect.left + 4, rect.top), (rect.left + 4, rect.bottom), 4,
        )
        pygame.draw.line(
            surface, OBSTACLE_EDGE,
            (rect.right - 5, rect.top), (rect.right - 5, rect.bottom), 4,
        )

        # ── Cap (wider block at the end facing the gap) ───────────────────────
        cap_h = 22
        cap_w = OBS_WIDTH + 16
        cap_x = ix - cap_w // 2

        if top:
            cap_y = rect.bottom - cap_h
        else:
            cap_y = rect.top

        cap_rect = pygame.Rect(cap_x, cap_y, cap_w, cap_h)
        pygame.draw.rect(surface, OBSTACLE_CAP, cap_rect)
        pygame.draw.rect(surface, OBSTACLE_EDGE, cap_rect, 2)

        # ── Small coral spikes on the cap ─────────────────────────────────────
        for i in range(3):
            bx = cap_x + 12 + i * 24
            if top:
                pts = [(bx, cap_y), (bx + 8, cap_y), (bx + 4, cap_y - 10)]
            else:
                by = cap_y + cap_h
                pts = [(bx, by), (bx + 8, by), (bx + 4, by + 10)]
            pygame.draw.polygon(surface, OBSTACLE_EDGE, pts)


# ─────────────────────────────────────────────────────────────────────────────
#  Bubble
# ─────────────────────────────────────────────────────────────────────────────

class Bubble:
    """
    A small translucent bubble that drifts upward and wraps back to the bottom.

    Multiple Bubble instances running in parallel create the ambient underwater
    atmosphere without requiring any image assets.
    """

    def __init__(self) -> None:
        self._reset(initial=True)

    def _reset(self, initial: bool = False) -> None:
        self.x     = float(random.randint(0, SCREEN_WIDTH))
        # On first creation scatter across the screen; on respawn start below
        self.y     = float(
            random.randint(0, SCREEN_HEIGHT) if initial else SCREEN_HEIGHT + 12
        )
        self.r     = random.randint(3, 11)
        self.speed = random.uniform(0.4, 1.8)
        self.drift = random.uniform(-0.25, 0.25)  # gentle horizontal sway
        self.alpha = random.randint(55, 140)       # transparency

    def update(self) -> None:
        self.y -= self.speed
        self.x += self.drift
        if self.y < -(self.r * 2):
            self._reset()

    def draw(self, surface: pygame.Surface) -> None:
        size = self.r * 2 + 6
        buf  = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = cy = size // 2

        # Filled circle
        pygame.draw.circle(buf, (*BUBBLE_COL, self.alpha), (cx, cy), self.r)
        # Rim
        pygame.draw.circle(
            buf, (*BUBBLE_COL, min(255, self.alpha + 50)), (cx, cy), self.r, 1,
        )
        # Specular highlight dot (top-left of bubble)
        pygame.draw.circle(
            buf,
            (255, 255, 255, min(255, self.alpha + 80)),
            (cx - self.r // 3, cy - self.r // 3),
            max(1, self.r // 4),
        )

        surface.blit(buf, (int(self.x) - cx, int(self.y) - cy))

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
    OBS_WIDTH,
    SEAWEED_DARK, SEAWEED_MID, SEAWEED_LIGHT,
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

    def draw(self, surface: pygame.Surface, t: float = 0.0) -> None:
        self._draw_seaweed(surface, top=True, t=t)
        self._draw_seaweed(surface, top=False, t=t)

    def _draw_seaweed(self, surface: pygame.Surface, top: bool, t: float = 0.0) -> None:
        rect = self.top_rect if top else self.bottom_rect
        if rect.height <= 0:
            return

        ix = int(self.x)
        num_strands = 5
        strand_spacing = OBS_WIDTH // (num_strands + 1)

        for s in range(num_strands):
            root_x = rect.left + strand_spacing * (s + 1)
            phase = s * 1.1

            num_pts = max(8, rect.height // 8)
            pts = []
            for i in range(num_pts + 1):
                frac = i / num_pts  # 0 at root, 1 at tip
                if top:
                    py = rect.top + frac * rect.height
                else:
                    py = rect.bottom - frac * rect.height

                # Sinusoidal sway animated by time t; amplitude grows toward tip
                sway = math.sin(frac * math.pi * 2.5 + phase + t * 1.8) * (8 + frac * 12)
                px = root_x + sway
                pts.append((int(px), int(py)))

            if len(pts) < 2:
                continue

            for i in range(len(pts) - 1):
                frac = i / (len(pts) - 1)
                if frac < 0.5:
                    c = tuple(int(SEAWEED_DARK[j] + (SEAWEED_MID[j] - SEAWEED_DARK[j]) * (frac * 2)) for j in range(3))
                else:
                    c = tuple(int(SEAWEED_MID[j] + (SEAWEED_LIGHT[j] - SEAWEED_MID[j]) * ((frac - 0.5) * 2)) for j in range(3))
                thickness = max(2, int(7 * (1 - i / len(pts))))
                pygame.draw.line(surface, c, pts[i], pts[i + 1], thickness)

            tip = pts[-1]
            leaf_surf = pygame.Surface((14, 20), pygame.SRCALPHA)
            pygame.draw.ellipse(leaf_surf, (*SEAWEED_LIGHT, 210), (0, 0, 14, 20))
            surface.blit(leaf_surf, (tip[0] - 7, tip[1] - 10))


# ─────────────────────────────────────────────────────────────────────────────
#  Bubble
# ─────────────────────────────────────────────────────────────────────────────

class Bubble:
    """
    A small translucent bubble that drifts upward and wraps back to the bottom.

    Multiple Bubble instances running in parallel create the ambient underwater
    atmosphere without requiring any image assets.
    """

    def __init__(self, pos=None) -> None:
        self._reset(initial=pos is None)
        if pos is not None:
            self.x     = float(pos[0])
            self.y     = float(pos[1])
            self.r     = random.randint(2, 5)
            self.speed = random.uniform(0.6, 1.5)
            self.drift = random.uniform(-0.4, 0.1)
            self.alpha = random.randint(100, 180)

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


# ─────────────────────────────────────────────────────────────────────────────
#  Pearl
# ─────────────────────────────────────────────────────────────────────────────

class Pearl:
    """
    A golden collectible pearl that bobs in the gap between seaweed columns.
    Collecting it awards bonus points.
    """

    RADIUS = 10

    def __init__(self, x: float, y: float, speed: float) -> None:
        self.x         = x
        self.y         = y
        self.speed     = speed
        self.collected = False
        self._phase    = random.uniform(0.0, math.pi * 2)

    def update(self) -> None:
        self.x -= self.speed

    @property
    def off_screen(self) -> bool:
        return self.x < -20

    @property
    def rect(self) -> pygame.Rect:
        r = self.RADIUS
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    def draw(self, surface: pygame.Surface, t: float = 0.0) -> None:
        bob_y = int(self.y + math.sin(t * 2.5 + self._phase) * 6)
        cx, cy = int(self.x), bob_y
        r = self.RADIUS

        # Soft glow
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 215, 0, 55), (r * 2, r * 2), r * 2)
        surface.blit(glow, (cx - r * 2, cy - r * 2))

        # Pearl body
        pygame.draw.circle(surface, (255, 215, 0), (cx, cy), r)
        # Inner highlight
        pygame.draw.circle(surface, (255, 245, 150), (cx - 3, cy - 3), 4)
        # Rim
        pygame.draw.circle(surface, (200, 140, 0), (cx, cy), r, 2)


# ─────────────────────────────────────────────────────────────────────────────
#  Particle
# ─────────────────────────────────────────────────────────────────────────────

class Particle:
    """
    A short-lived coloured particle used for the fish death explosion effect.
    """

    _COLOURS = [
        (255, 140,   0),   # FISH_BODY orange
        (255, 210,  90),   # FISH_BELLY yellow
        (200,  90,   0),   # FISH_FIN dark orange
        (255, 200,  50),   # bright gold
    ]

    def __init__(self, x: float, y: float) -> None:
        self.x       = x
        self.y       = y
        angle        = random.uniform(0.0, math.pi * 2)
        speed        = random.uniform(2.5, 9.0)
        self.vx      = math.cos(angle) * speed
        self.vy      = math.sin(angle) * speed
        self.life    = random.randint(22, 50)
        self.max_life = self.life
        self.r       = random.randint(3, 8)
        self.color   = random.choice(self._COLOURS)

    def update(self) -> None:
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.35    # gravity
        self.vx *= 0.96    # drag
        self.life -= 1

    @property
    def alive(self) -> bool:
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(255 * self.life / self.max_life)
        r     = max(1, int(self.r * self.life / self.max_life))
        buf   = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(buf, (*self.color, alpha), (r + 1, r + 1), r)
        surface.blit(buf, (int(self.x) - r - 1, int(self.y) - r - 1))

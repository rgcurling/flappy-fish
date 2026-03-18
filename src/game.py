"""
game.py – Main game orchestrator.

Manages a simple state machine:

    START  ──► COUNTDOWN  ──► PLAYING  ──► GAME_OVER
                                 ▲               │
                                 └───── PAUSED   │
                                 └───────────────┘  (restart)

Create a Game() instance and call .run() to start the event loop.
"""

from __future__ import annotations

import math
import random
import sys
from enum import Enum, auto
from typing import List

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    BG_TOP, BG_BOTTOM,
    TEXT_WHITE, TEXT_YELLOW, TEXT_SHADOW,
    FISH_X,
    OBS_INTERVAL, OBS_SPEED, OBS_GAP_MIN_Y, OBS_GAP_MAX_Y, OBS_WIDTH,
    SPEED_STEP, SPEED_MAX,
    HAND_SMOOTH,
    NUM_BUBBLES,
)
from entities import Bubble, Fish, ObstaclePair
from hand_tracker import HandTracker


class State(Enum):
    START     = auto()
    COUNTDOWN = auto()
    PLAYING   = auto()
    PAUSED    = auto()
    GAME_OVER = auto()


class Game:
    """
    Top-level game object.  Create once and call .run() to block until quit.

    Design notes
    ────────────
    - The HandTracker is created once at startup.  If it is unavailable the
      game silently falls back to keyboard control.
    - Bubbles are created once and persist across restarts for visual continuity.
    - _new_game() resets per-round state (fish, obstacles, score, speed) while
      keeping the high score and tracker alive.
    """

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self._init_fonts()
        self._bg = self._build_gradient()

        # Hand tracker – auto-falls back to keyboard if webcam is absent
        self.tracker     = HandTracker(smooth_factor=HAND_SMOOTH)
        self.use_keyboard: bool = not self.tracker.available

        # Session high score – survives restarts within one run
        self.high_score: int = 0

        # Decorative bubbles – created once, animated every frame
        self.bubbles: List[Bubble] = [Bubble() for _ in range(NUM_BUBBLES)]

        self._new_game()

    def _init_fonts(self) -> None:
        # SysFont falls back gracefully if Arial is not present
        self.font_lg = pygame.font.SysFont("Arial", 54, bold=True)
        self.font_md = pygame.font.SysFont("Arial", 34)
        self.font_sm = pygame.font.SysFont("Arial", 22)

    # ── Per-round reset ───────────────────────────────────────────────────────

    def _new_game(self) -> None:
        """Reset everything that belongs to a single round."""
        self.state          = State.START
        self.score:   int   = 0
        self.frame:   int   = 0
        self.obs_timer: int = 0
        self.speed:  float  = OBS_SPEED

        self.fish      = Fish()
        self.obstacles: List[ObstaclePair] = []

        # Countdown state
        self._cd_count: int = 3    # which digit to show (3 → 2 → 1)
        self._cd_timer: int = FPS  # frames until the digit decrements

        # One-shot flap flag – set True for exactly one frame per keypress
        self._flap: bool = False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Block until the player quits.  Called from main.py."""
        while True:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS)

    # ── Event handling ────────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        self._flap = False          # reset each frame; set below if key pressed

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._quit()
            elif ev.type == pygame.KEYDOWN:
                self._on_keydown(ev.key)

    def _on_keydown(self, key: int) -> None:
        # ── Global shortcuts (work in any state) ──────────────────────────────
        if key == pygame.K_ESCAPE:
            self._quit()

        if key == pygame.K_k:
            # Toggle between hand-tracking and keyboard control
            self.use_keyboard = not self.use_keyboard
            label = "keyboard" if self.use_keyboard else "hand tracking"
            print(f"[Game] Switched to {label} mode.")
            return

        if key == pygame.K_p:
            if self.state == State.PLAYING:
                self.state = State.PAUSED
            elif self.state == State.PAUSED:
                self.state = State.PLAYING
            return

        # ── State-specific actions ────────────────────────────────────────────
        if self.state == State.START:
            if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP):
                self._begin_countdown()

        elif self.state == State.GAME_OVER:
            if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_r, pygame.K_UP):
                self._new_game()
                self._begin_countdown()

        elif self.state in (State.COUNTDOWN, State.PLAYING):
            if key in (pygame.K_SPACE, pygame.K_UP):
                self._flap = True

    def _begin_countdown(self) -> None:
        self.state     = State.COUNTDOWN
        self._cd_count = 3
        self._cd_timer = FPS

    # ── Update ────────────────────────────────────────────────────────────────

    def _update(self) -> None:
        # Bubbles animate continuously across all states
        for b in self.bubbles:
            b.update()

        if self.state == State.COUNTDOWN:
            self._update_countdown()
        elif self.state == State.PLAYING:
            self._update_playing()

    def _update_countdown(self) -> None:
        self._cd_timer -= 1
        if self._cd_timer <= 0:
            self._cd_count -= 1
            if self._cd_count <= 0:
                self.state = State.PLAYING
            else:
                self._cd_timer = FPS

    def _update_playing(self) -> None:
        self.frame += 1

        # ── Fish movement ─────────────────────────────────────────────────────
        if self.use_keyboard:
            self.fish.update_keyboard(self._flap)
        else:
            norm_y = self.tracker.get_hand_y()
            self.fish.update_hand(norm_y)

        # ── Spawn new obstacle pair ────────────────────────────────────────────
        self.obs_timer += 1
        if self.obs_timer >= OBS_INTERVAL:
            self.obs_timer = 0
            gap_y = random.randint(OBS_GAP_MIN_Y, OBS_GAP_MAX_Y)
            self.obstacles.append(ObstaclePair(gap_y, self.speed))

        # ── Update obstacles and award points ─────────────────────────────────
        for obs in self.obstacles:
            obs.update()
            # Award one point when the fish's centre clears the right edge of the pair
            if not obs.scored and self.fish.x > obs.x + OBS_WIDTH // 2:
                obs.scored = True
                self.score += 1
                self._on_score_increase()

        # Remove pairs that have fully scrolled off the left edge
        self.obstacles = [o for o in self.obstacles if not o.off_screen]

        # ── Collision detection ───────────────────────────────────────────────
        fish_rect = self.fish.rect
        for obs in self.obstacles:
            if (fish_rect.colliderect(obs.top_rect)
                    or fish_rect.colliderect(obs.bottom_rect)):
                self._end_game()
                return

        # Fish exiting the screen vertically (only lethal in keyboard mode
        # because hand mode clamps the fish to the screen bounds)
        if self.use_keyboard and (self.fish.y <= 0 or self.fish.y >= SCREEN_HEIGHT):
            self._end_game()

    def _on_score_increase(self) -> None:
        """Called each time the player scores.  Scales difficulty."""
        # Increase speed every SPEED_STEP points
        if self.score % SPEED_STEP == 0:
            self.speed = min(SPEED_MAX, self.speed + 0.5)
            for obs in self.obstacles:
                obs.speed = self.speed
        self.high_score = max(self.high_score, self.score)

    def _end_game(self) -> None:
        self.high_score = max(self.high_score, self.score)
        self.state = State.GAME_OVER

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self) -> None:
        # Background gradient
        self.screen.blit(self._bg, (0, 0))

        # Bubbles (always rendered on top of background)
        for b in self.bubbles:
            b.draw(self.screen)

        # Delegate to the per-state renderer
        renderers = {
            State.START:     self._render_start,
            State.COUNTDOWN: self._render_countdown,
            State.PLAYING:   self._render_playing,
            State.PAUSED:    self._render_paused,
            State.GAME_OVER: self._render_game_over,
        }
        renderers[self.state]()

        pygame.display.flip()

    # ── Per-state renderers ───────────────────────────────────────────────────

    def _render_scene(self) -> None:
        """Render obstacles + fish.  Called by gameplay states."""
        for obs in self.obstacles:
            obs.draw(self.screen)
        self.fish.draw(self.screen)

    def _render_start(self) -> None:
        # Gently bobbing fish as a background decoration
        t = pygame.time.get_ticks() / 1000.0
        self.fish.y  = SCREEN_HEIGHT // 2 + math.sin(t * 1.8) * 18
        self.fish.vy = math.cos(t * 1.8) * 18 * 1.8 / FPS  # visual tilt
        self.fish.draw(self.screen)

        self._panel(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 510, 330)

        self._text("Flappy Fish", self.font_lg,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 108, TEXT_YELLOW)

        self._text("An underwater hand-tracking adventure",
                   self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 57, TEXT_WHITE)

        self._text("Move your index finger UP / DOWN to steer the fish",
                   self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 22, TEXT_WHITE)

        self._text("SPACE / ENTER to start", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 43, TEXT_YELLOW)

        mode_col = (120, 220, 140) if not self.use_keyboard else (220, 180, 80)
        mode_str = (
            "Hand tracking ACTIVE   (K = switch to keyboard)"
            if not self.use_keyboard
            else "Keyboard mode ACTIVE   (K = switch to hand tracking)"
        )
        self._text(mode_str, self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 95, mode_col)

        if self.high_score > 0:
            self._text(f"Best: {self.high_score}", self.font_sm,
                       SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 125, TEXT_WHITE)

    def _render_countdown(self) -> None:
        self._render_scene()

        # Pulsing scale effect using transform.smoothscale on a pre-rendered label
        pulse  = 1.0 + 0.25 * abs(math.sin(
            math.pi * (FPS - self._cd_timer) / FPS
        ))
        base   = self.font_lg.render(str(self._cd_count), True, TEXT_YELLOW)
        w = max(1, int(base.get_width()  * pulse))
        h = max(1, int(base.get_height() * pulse))
        scaled = pygame.transform.smoothscale(base, (w, h))
        self.screen.blit(scaled, scaled.get_rect(
            center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        ))

    def _render_playing(self) -> None:
        self._render_scene()
        self._render_hud()

    def _render_paused(self) -> None:
        self._render_scene()
        self._render_hud()
        self._panel(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 300, 115)
        self._text("PAUSED", self.font_lg,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 18, TEXT_YELLOW)
        self._text("P  to resume", self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30, TEXT_WHITE)

    def _render_game_over(self) -> None:
        self._render_scene()
        self._panel(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 450, 295)
        self._text("Game Over", self.font_lg,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90, (255, 80, 80))
        self._text(f"Score:  {self.score}", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 18, TEXT_WHITE)
        self._text(f"Best:   {self.high_score}", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30, TEXT_YELLOW)
        self._text("SPACE / R  to play again", self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 88, TEXT_WHITE)

    def _render_hud(self) -> None:
        """Score display and control-mode indicator."""
        self._text(str(self.score), self.font_md,
                   SCREEN_WIDTH // 2, 38, TEXT_YELLOW)
        mode_label = "[KB]" if self.use_keyboard else "[Hand]"
        self._text(mode_label, self.font_sm, 48, 15, (160, 210, 160))

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _build_gradient(self) -> pygame.Surface:
        """Pre-render a vertical colour gradient for the ocean background."""
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            color = tuple(
                int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t)
                for i in range(3)
            )
            pygame.draw.line(surf, color, (0, y), (SCREEN_WIDTH, y))
        return surf

    def _panel(self, cx: int, cy: int, w: int, h: int) -> None:
        """Draw a semi-transparent dark panel centred at (cx, cy)."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 15, 40, 180))
        pygame.draw.rect(surf, (60, 120, 180, 110), surf.get_rect(), 2)
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _text(
        self, msg: str, font: pygame.font.Font,
        cx: int, cy: int, color: tuple,
    ) -> None:
        """Render anti-aliased text with a drop shadow, centred at (cx, cy)."""
        shadow  = font.render(msg, True, TEXT_SHADOW)
        label   = font.render(msg, True, color)
        self.screen.blit(shadow, shadow.get_rect(center=(cx + 2, cy + 2)))
        self.screen.blit(label,  label.get_rect(center=(cx, cy)))

    # ── Clean shutdown ────────────────────────────────────────────────────────

    def _quit(self) -> None:
        self.tracker.release()
        pygame.quit()
        sys.exit()

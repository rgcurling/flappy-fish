"""
game.py – Main game orchestrator.

State machine:

    START  ──► DIFFICULTY  ──► COUNTDOWN  ──► PLAYING  ──► GAME_OVER
                                                 ▲               │
                                                 └──── PAUSED    │
                                                 └───────────────┘  (restart)

Create a Game() instance and call .run() to start the event loop.
"""

from __future__ import annotations

import math
import random
import sys
from enum import Enum, auto
from typing import Dict, List

import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    BG_TOP, BG_BOTTOM,
    TEXT_WHITE, TEXT_YELLOW, TEXT_SHADOW,
    OBS_GAP_MIN_Y, OBS_GAP_MAX_Y, OBS_WIDTH,
    HAND_SMOOTH,
    NUM_BUBBLES,
    DIFFICULTIES, DIFFICULTY_NAMES,
)
from entities import Bubble, Fish, ObstaclePair
from hand_tracker import HandTracker


class State(Enum):
    START      = auto()
    DIFFICULTY = auto()   # difficulty selection screen
    COUNTDOWN  = auto()
    PLAYING    = auto()
    PAUSED     = auto()
    GAME_OVER  = auto()


class Game:
    """
    Top-level game object.  Create once and call .run() to block until quit.

    Design notes
    ────────────
    - The HandTracker is created once at startup.  If it is unavailable the
      game silently falls back to keyboard control.
    - Bubbles are created once and persist across restarts for visual continuity.
    - High scores are tracked separately per difficulty level.
    - _new_game() resets per-round state while keeping scores and tracker alive.
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
        self.tracker      = HandTracker(smooth_factor=HAND_SMOOTH)
        self.use_keyboard: bool = not self.tracker.available

        # Per-difficulty high scores – survive restarts within one session
        self.high_scores: Dict[str, int] = {name: 0 for name in DIFFICULTY_NAMES}

        # Decorative bubbles – created once, animated every frame
        self.bubbles: List[Bubble] = [Bubble() for _ in range(NUM_BUBBLES)]

        # Difficulty selection – default to Medium
        self._diff_index: int = 1          # index into DIFFICULTY_NAMES
        self._diff_name:  str = DIFFICULTY_NAMES[self._diff_index]

        self._new_game()

    def _init_fonts(self) -> None:
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

        # Load settings from the selected difficulty preset
        diff = DIFFICULTIES[self._diff_name]
        self.speed:       float = diff["speed"]
        self._obs_gap:    int   = diff["gap"]
        self._obs_interval: int = diff["interval"]
        self._speed_step: int   = diff["speed_step"]
        self._speed_max:  float = diff["speed_max"]

        self.fish      = Fish()
        self.obstacles: List[ObstaclePair] = []

        # Countdown state
        self._cd_count: int = 3
        self._cd_timer: int = FPS

        # One-shot flap flag
        self._flap: bool = False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        while True:
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS)

    # ── Event handling ────────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        self._flap = False

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._quit()
            elif ev.type == pygame.KEYDOWN:
                self._on_keydown(ev.key)

    def _on_keydown(self, key: int) -> None:
        # ── Global shortcuts ──────────────────────────────────────────────────
        if key == pygame.K_ESCAPE:
            self._quit()

        if key == pygame.K_k:
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

        # ── State-specific keys ───────────────────────────────────────────────
        if self.state == State.START:
            if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_UP):
                self.state = State.DIFFICULTY

        elif self.state == State.DIFFICULTY:
            self._difficulty_keydown(key)

        elif self.state == State.GAME_OVER:
            if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_r):
                # Go back to difficulty selection so the player can change it
                self._new_game()
                self.state = State.DIFFICULTY
            elif key == pygame.K_UP:
                # Quick restart on the same difficulty
                self._new_game()
                self._begin_countdown()

        elif self.state in (State.COUNTDOWN, State.PLAYING):
            if key in (pygame.K_SPACE, pygame.K_UP):
                self._flap = True

    def _difficulty_keydown(self, key: int) -> None:
        """Handle key input on the difficulty selection screen."""
        if key in (pygame.K_LEFT, pygame.K_a):
            self._diff_index = (self._diff_index - 1) % len(DIFFICULTY_NAMES)
            self._diff_name  = DIFFICULTY_NAMES[self._diff_index]

        elif key in (pygame.K_RIGHT, pygame.K_d):
            self._diff_index = (self._diff_index + 1) % len(DIFFICULTY_NAMES)
            self._diff_name  = DIFFICULTY_NAMES[self._diff_index]

        # Number shortcuts: 1 = Easy, 2 = Medium, 3 = Hard
        elif key in (pygame.K_1, pygame.K_KP1):
            self._diff_index, self._diff_name = 0, DIFFICULTY_NAMES[0]
        elif key in (pygame.K_2, pygame.K_KP2):
            self._diff_index, self._diff_name = 1, DIFFICULTY_NAMES[1]
        elif key in (pygame.K_3, pygame.K_KP3):
            self._diff_index, self._diff_name = 2, DIFFICULTY_NAMES[2]

        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self._new_game()          # apply chosen difficulty settings
            self._begin_countdown()

    def _begin_countdown(self) -> None:
        self.state     = State.COUNTDOWN
        self._cd_count = 3
        self._cd_timer = FPS

    # ── Update ────────────────────────────────────────────────────────────────

    def _update(self) -> None:
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
            self.fish.update_hand(self.tracker.get_hand_y())

        # ── Spawn obstacles ───────────────────────────────────────────────────
        self.obs_timer += 1
        if self.obs_timer >= self._obs_interval:
            self.obs_timer = 0
            gap_y = random.randint(OBS_GAP_MIN_Y, OBS_GAP_MAX_Y)
            self.obstacles.append(ObstaclePair(gap_y, self.speed, self._obs_gap))

        # ── Move + score obstacles ────────────────────────────────────────────
        for obs in self.obstacles:
            obs.update()
            if not obs.scored and self.fish.x > obs.x + OBS_WIDTH // 2:
                obs.scored = True
                self.score += 1
                self._on_score_increase()

        self.obstacles = [o for o in self.obstacles if not o.off_screen]

        # ── Collision ─────────────────────────────────────────────────────────
        fish_rect = self.fish.rect
        for obs in self.obstacles:
            if (fish_rect.colliderect(obs.top_rect)
                    or fish_rect.colliderect(obs.bottom_rect)):
                self._end_game()
                return

        if self.use_keyboard and (self.fish.y <= 0 or self.fish.y >= SCREEN_HEIGHT):
            self._end_game()

    def _on_score_increase(self) -> None:
        if self.score % self._speed_step == 0:
            self.speed = min(self._speed_max, self.speed + 0.5)
            for obs in self.obstacles:
                obs.speed = self.speed
        self.high_scores[self._diff_name] = max(
            self.high_scores[self._diff_name], self.score
        )

    def _end_game(self) -> None:
        self.high_scores[self._diff_name] = max(
            self.high_scores[self._diff_name], self.score
        )
        self.state = State.GAME_OVER

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self) -> None:
        self.screen.blit(self._bg, (0, 0))

        for b in self.bubbles:
            b.draw(self.screen)

        {
            State.START:      self._render_start,
            State.DIFFICULTY: self._render_difficulty,
            State.COUNTDOWN:  self._render_countdown,
            State.PLAYING:    self._render_playing,
            State.PAUSED:     self._render_paused,
            State.GAME_OVER:  self._render_game_over,
        }[self.state]()

        pygame.display.flip()

    # ── Per-state renderers ───────────────────────────────────────────────────

    def _render_scene(self) -> None:
        for obs in self.obstacles:
            obs.draw(self.screen)
        self.fish.draw(self.screen)

    def _render_start(self) -> None:
        t = pygame.time.get_ticks() / 1000.0
        self.fish.y  = SCREEN_HEIGHT // 2 + math.sin(t * 1.8) * 18
        self.fish.vy = math.cos(t * 1.8) * 18 * 1.8 / FPS
        self.fish.draw(self.screen)

        self._panel(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 510, 320)
        self._text("Flappy Fish", self.font_lg,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 105, TEXT_YELLOW)
        self._text("An underwater hand-tracking adventure",
                   self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 54, TEXT_WHITE)
        self._text("Move your index finger UP / DOWN to steer the fish",
                   self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 19, TEXT_WHITE)
        self._text("SPACE / ENTER to continue", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 43, TEXT_YELLOW)

        mode_col = (120, 220, 140) if not self.use_keyboard else (220, 180, 80)
        mode_str = (
            "Hand tracking ACTIVE   (K = switch to keyboard)"
            if not self.use_keyboard
            else "Keyboard mode ACTIVE   (K = switch to hand tracking)"
        )
        self._text(mode_str, self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 95, mode_col)

    def _render_difficulty(self) -> None:
        # Bobbing fish behind the panel
        t = pygame.time.get_ticks() / 1000.0
        self.fish.y  = SCREEN_HEIGHT // 2 + math.sin(t * 1.8) * 18
        self.fish.vy = 0.0
        self.fish.draw(self.screen)

        self._panel(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 560, 300)
        self._text("Select Difficulty", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 105, TEXT_WHITE)

        # Draw the three difficulty cards side by side
        card_w, card_h = 140, 130
        spacing        = 165
        card_y         = SCREEN_HEIGHT // 2 - 10
        names          = DIFFICULTY_NAMES

        for i, name in enumerate(names):
            diff   = DIFFICULTIES[name]
            cx     = SCREEN_WIDTH // 2 + (i - 1) * spacing
            col    = diff["color"]
            is_sel = (i == self._diff_index)

            # Card background – brighter / thicker border when selected
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg_alpha  = 220 if is_sel else 130
            card_surf.fill((0, 20, 50, bg_alpha))
            border_col = (*col, 255) if is_sel else (*col, 140)
            border_w   = 3 if is_sel else 1
            pygame.draw.rect(card_surf, border_col, card_surf.get_rect(), border_w)
            self.screen.blit(card_surf, card_surf.get_rect(center=(cx, card_y)))

            # Difficulty name
            name_col = col if is_sel else tuple(max(0, c - 60) for c in col)
            self._text(name, self.font_md if is_sel else self.font_sm,
                       cx, card_y - 38, name_col)

            # Stats
            self._text(f"Speed  {diff['speed']:.1f}", self.font_sm,
                       cx, card_y - 2, TEXT_WHITE)
            self._text(f"Gap    {diff['gap']} px", self.font_sm,
                       cx, card_y + 24, TEXT_WHITE)

            # Per-difficulty best score
            best = self.high_scores[name]
            best_str = f"Best  {best}" if best > 0 else "Best  --"
            self._text(best_str, self.font_sm, cx, card_y + 50,
                       TEXT_YELLOW if best > 0 else (120, 120, 120))

        self._text("LEFT / RIGHT  to choose    SPACE to start",
                   self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 115, TEXT_WHITE)
        self._text("1 = Easy   2 = Medium   3 = Hard",
                   self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 138, (160, 160, 160))

    def _render_countdown(self) -> None:
        self._render_scene()
        pulse  = 1.0 + 0.25 * abs(math.sin(math.pi * (FPS - self._cd_timer) / FPS))
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
        diff_col = DIFFICULTIES[self._diff_name]["color"]
        best     = self.high_scores[self._diff_name]

        self._panel(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 460, 310)
        self._text("Game Over", self.font_lg,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100, (255, 80, 80))

        # Show which difficulty was played
        self._text(self._diff_name, self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 52, diff_col)

        self._text(f"Score:  {self.score}", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 15, TEXT_WHITE)
        self._text(f"Best:   {best}", self.font_md,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30, TEXT_YELLOW)
        self._text("SPACE / R  →  pick difficulty", self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 85, TEXT_WHITE)
        self._text("UP  →  replay same difficulty", self.font_sm,
                   SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 108, (160, 160, 160))

    def _render_hud(self) -> None:
        """Score, difficulty badge, and control-mode indicator."""
        self._text(str(self.score), self.font_md,
                   SCREEN_WIDTH // 2, 38, TEXT_YELLOW)

        # Coloured difficulty badge in top-right corner
        diff_col = DIFFICULTIES[self._diff_name]["color"]
        self._text(self._diff_name, self.font_sm,
                   SCREEN_WIDTH - 60, 15, diff_col)

        mode_label = "[KB]" if self.use_keyboard else "[Hand]"
        self._text(mode_label, self.font_sm, 48, 15, (160, 210, 160))

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _build_gradient(self) -> pygame.Surface:
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
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 15, 40, 180))
        pygame.draw.rect(surf, (60, 120, 180, 110), surf.get_rect(), 2)
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))

    def _text(
        self, msg: str, font: pygame.font.Font,
        cx: int, cy: int, color: tuple,
    ) -> None:
        shadow = font.render(msg, True, TEXT_SHADOW)
        label  = font.render(msg, True, color)
        self.screen.blit(shadow, shadow.get_rect(center=(cx + 2, cy + 2)))
        self.screen.blit(label,  label.get_rect(center=(cx, cy)))

    # ── Clean shutdown ────────────────────────────────────────────────────────

    def _quit(self) -> None:
        self.tracker.release()
        pygame.quit()
        sys.exit()

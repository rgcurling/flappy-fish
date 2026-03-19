"""
config.py – Global constants for Flappy Fish.

Edit values here to tune gameplay feel without touching game logic.
"""

# ── Display ───────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 800
SCREEN_HEIGHT = 600
FPS           = 60
TITLE         = "Flappy Fish"

# ── Colours (underwater theme, RGB tuples) ────────────────────────────────────
BG_TOP         = (  0,  20,  60)   # deep ocean blue at top
BG_BOTTOM      = (  0,  80, 130)   # lighter teal at bottom

FISH_BODY      = (255, 140,   0)   # orange body
FISH_BELLY     = (255, 210,  90)   # pale yellow belly
FISH_FIN       = (200,  90,   0)   # darker fin / tail
FISH_EYE_W     = (240, 240, 240)   # eye white
FISH_EYE_P     = ( 20,  20,  20)   # pupil

OBSTACLE_FILL  = ( 10,  70,  50)   # dark teal (unused but kept for compat)
OBSTACLE_EDGE  = ( 20, 110,  80)   # lighter edge (unused but kept for compat)
OBSTACLE_CAP   = ( 15,  90,  60)   # cap (unused but kept for compat)

SEAWEED_DARK   = ( 10,  90,  40)   # dark green seaweed strand
SEAWEED_MID    = ( 20, 140,  60)   # mid green
SEAWEED_LIGHT  = ( 60, 190,  80)   # highlight / tip colour

BUBBLE_COL     = (120, 200, 255)   # bubble tint

TEXT_WHITE     = (255, 255, 255)
TEXT_YELLOW    = (255, 225,  70)
TEXT_SHADOW    = (  0,   0,   0)

# ── Fish ──────────────────────────────────────────────────────────────────────
FISH_X      = 140       # fixed horizontal centre position (px)
FISH_W      = 52        # body bounding width  (px)
FISH_H      = 30        # body bounding height (px)
# Lerp factor for hand-tracking follow (0 = frozen, 1 = instant snap)
FISH_LERP   = 0.13

# ── Keyboard / fallback physics ───────────────────────────────────────────────
GRAVITY       =  0.45   # px / frame² acceleration downward
FLAP_FORCE    = -9.0    # instantaneous vy on flap (negative = up)
MAX_VY_DOWN   =  12.0   # terminal fall velocity
MAX_VY_UP     = -13.0   # maximum rise velocity

# ── Obstacles ─────────────────────────────────────────────────────────────────
OBS_WIDTH     = 68      # pillar width (px)
# Random range for the gap centre Y position
OBS_GAP_MIN_Y = 130
OBS_GAP_MAX_Y = SCREEN_HEIGHT - 130

# ── Difficulty presets ────────────────────────────────────────────────────────
# Each entry controls starting feel AND how fast the game ramps up.
#   gap       – vertical space between pillars (px); smaller = harder
#   speed     – starting pillar speed (px / frame)
#   interval  – frames between pillar spawns; smaller = more frequent
#   speed_step – score points between each speed increase
#   speed_max  – absolute speed cap (px / frame)
DIFFICULTIES = {
    "Easy": {
        "gap":        215,
        "speed":      2.5,
        "interval":   100,
        "speed_step":  8,
        "speed_max":   5.5,
        "color":      ( 80, 200, 120),   # green label
    },
    "Medium": {
        "gap":        190,
        "speed":      3.0,
        "interval":    88,
        "speed_step":  5,
        "speed_max":   7.5,
        "color":      (255, 210,  60),   # yellow label
    },
    "Hard": {
        "gap":        155,
        "speed":      4.5,
        "interval":    68,
        "speed_step":  4,
        "speed_max":  11.0,
        "color":      (255,  80,  80),   # red label
    },
}
DIFFICULTY_NAMES = list(DIFFICULTIES.keys())   # ["Easy", "Medium", "Hard"]

# ── Hand tracking ─────────────────────────────────────────────────────────────
# Camera index to use. On macOS with Continuity Camera (iPhone as webcam),
# index 0 is usually the iPhone and index 1 is the built-in FaceTime camera.
# Run: python src/list_cameras.py  to see which index is which.
CAMERA_INDEX  = 1
HAND_SMOOTH   = 0.18    # EMA alpha for index-fingertip Y (lower = smoother)

# ── Decorative bubbles ────────────────────────────────────────────────────────
NUM_BUBBLES   = 20

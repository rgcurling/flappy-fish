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

OBSTACLE_FILL  = ( 10,  70,  50)   # dark teal pillar body
OBSTACLE_EDGE  = ( 20, 110,  80)   # lighter edge highlight
OBSTACLE_CAP   = ( 15,  90,  60)   # cap facing the gap

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
OBS_GAP       = 195     # vertical gap between top & bottom pillar (px)
OBS_SPEED     = 3.0     # starting speed (px / frame)
OBS_INTERVAL  = 88      # frames between obstacle spawns
# Random range for the gap centre Y position
OBS_GAP_MIN_Y = 130
OBS_GAP_MAX_Y = SCREEN_HEIGHT - 130

# ── Difficulty scaling ────────────────────────────────────────────────────────
SPEED_STEP    = 5       # speed increases every N points
SPEED_MAX     = 7.5     # maximum pillar speed (px / frame)

# ── Hand tracking ─────────────────────────────────────────────────────────────
HAND_SMOOTH   = 0.18    # EMA alpha for index-fingertip Y (lower = smoother)

# ── Decorative bubbles ────────────────────────────────────────────────────────
NUM_BUBBLES   = 20

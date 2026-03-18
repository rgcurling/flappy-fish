# Flappy Fish

An underwater Flappy Bird-style game controlled by your hand through your webcam.

Move your index finger up and down in front of the camera to steer the fish through coral obstacles. No fancy art assets required — everything is drawn with code.

---

## What it is

- Side-scrolling arcade game in the style of Flappy Bird
- Underwater / ocean theme drawn entirely with pygame primitives
- Hand-tracking control via MediaPipe and your webcam
- Keyboard fallback so you can always play even without a working webcam

---

## Requirements

- Python 3.8 – 3.11 (MediaPipe has limited support for 3.12+)
- A webcam (optional — keyboard mode works without one)
- macOS or Windows

---

## Installation

```bash
pip install -r requirements.txt
```

> **macOS tip:** If the install fails, use a virtualenv on Python 3.10 or 3.11:
> ```bash
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> ```

---

## Running the game

From the project root:

```bash
python src/main.py
```

Or from inside `src/`:

```bash
cd src
python main.py
```

---

## Controls

| Action | Hand tracking | Keyboard |
|---|---|---|
| Move fish up | Raise index finger | `SPACE` or `UP` arrow |
| Move fish down | Lower index finger | Let gravity do it |
| Start game | Any key shown on screen | `SPACE` / `ENTER` |
| Restart after death | Same as start | `SPACE` / `R` |
| Toggle control mode | `K` | `K` |
| Pause / resume | `P` | `P` |
| Quit | `ESC` | `ESC` |

### How hand tracking works

1. Your webcam is mirrored so it behaves like a mirror.
2. MediaPipe finds your hand and locates the tip of your index finger.
3. The vertical position of that tip (0 = top, 1 = bottom) is mapped directly to the fish's Y on screen.
4. An exponential moving average smooths out jitter.
5. If your hand leaves frame, the fish freezes at its last position.

---

## Project structure

```
flappy-fish/
├── src/
│   ├── main.py          # Entry point
│   ├── game.py          # State machine, game loop, rendering
│   ├── entities.py      # Fish, ObstaclePair, Bubble classes
│   ├── hand_tracker.py  # Webcam + MediaPipe integration
│   └── config.py        # All tunable constants in one place
├── requirements.txt
└── README.md
```

---

## Tuning gameplay

All constants live in `src/config.py`.

| Constant | What it controls |
|---|---|
| `FISH_LERP` | How snappily the fish follows your hand (0=frozen, 1=instant) |
| `HAND_SMOOTH` | EMA smoothing for the fingertip (lower=smoother/laggier) |
| `OBS_GAP` | Vertical gap between top and bottom pillars |
| `OBS_INTERVAL` | Frames between obstacle spawns |
| `OBS_SPEED` | Starting pillar speed |
| `SPEED_STEP` | Points before each speed increase |
| `GRAVITY` / `FLAP_FORCE` | Physics feel in keyboard mode |

---

## Troubleshooting

**Webcam not detected**
The game prints `[HandTracker] Could not open webcam` and automatically uses keyboard mode. Press `K` at any time to toggle between modes.

On macOS you may need to grant camera permission to your terminal:
`System Settings > Privacy & Security > Camera`

**mediapipe install fails**
Make sure you are on Python 3.8–3.11. Try `pip install mediapipe==0.10.9` for a specific known-good version.

**Lag or frame drops**
The webcam read is synchronous. Try closing other camera-using apps, or lower the webcam resolution in `hand_tracker.py` (currently 640x480).

**Fish too twitchy / sluggish**
Increase `HAND_SMOOTH` toward 1 for more smoothing (at the cost of lag).
Adjust `FISH_LERP` to change how quickly the fish chases your finger.

**Collision feels unfair**
The hitbox is intentionally inset from the visible fish. Adjust the `margin` value in `Fish.rect` inside `entities.py` to make it tighter or more forgiving.

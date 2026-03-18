"""
hand_tracker.py – Webcam capture and MediaPipe hand tracking.

Opens the webcam specified by CAMERA_INDEX in config.py, detects one hand per frame using
MediaPipe Hands, and exposes the index-fingertip's normalised Y
coordinate via get_hand_y().

Smoothing is done with an exponential moving average (EMA) so the fish
does not jitter from frame-to-frame noise.

If the webcam cannot be opened or MediaPipe fails to initialise, the
HandTracker marks itself as unavailable and the game falls back to
keyboard control automatically.
"""

from __future__ import annotations

import sys
from typing import Optional

import cv2
import mediapipe as mp

from config import CAMERA_INDEX


class HandTracker:
    """
    Manages webcam capture and MediaPipe Hands inference.

    Attributes
    ----------
    available : bool
        True when both the webcam and MediaPipe are ready.
        The game checks this on startup to decide which control mode to use.
    """

    # MediaPipe landmark index for the tip of the index finger
    _INDEX_TIP = mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP

    def __init__(self, smooth_factor: float = 0.18) -> None:
        """
        Parameters
        ----------
        smooth_factor : float
            EMA alpha in [0, 1].  Higher = faster response but more jitter.
            Lower = smoother but laggier feel.
        """
        self.smooth_factor: float = smooth_factor
        self._smoothed_y: Optional[float] = None  # last known smoothed position
        self.available: bool = False

        self._cap = None   # cv2.VideoCapture
        self._hands = None  # mp.solutions.hands.Hands

        self._open_mediapipe()
        self._open_webcam()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _open_mediapipe(self) -> None:
        """Initialise the MediaPipe Hands solution."""
        try:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                # Lower confidence thresholds help in varied lighting
                min_detection_confidence=0.70,
                min_tracking_confidence=0.55,
            )
            print("[HandTracker] MediaPipe Hands initialised.")
        except Exception as exc:
            print(f"[HandTracker] MediaPipe init failed: {exc}")
            self._hands = None

    def _open_webcam(self) -> None:
        """Try to open the webcam at CAMERA_INDEX with the appropriate backend.

        On macOS, Continuity Camera (iPhone) typically claims index 0, pushing
        the built-in FaceTime camera to index 1.  Set CAMERA_INDEX in config.py
        to match your setup.  Run  python src/list_cameras.py  to discover
        which index corresponds to which physical camera.
        """
        # On macOS, AVFoundation gives the most reliable results.
        # On other platforms we let OpenCV pick the best available backend.
        backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
        try:
            cap = cv2.VideoCapture(CAMERA_INDEX, backend)
            if cap.isOpened():
                # Smaller resolution = faster reads with no quality loss for tracking
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS,           30)
                self._cap = cap
                # Only mark as available if MediaPipe is also ready
                self.available = self._hands is not None
                if self.available:
                    print(f"[HandTracker] Camera {CAMERA_INDEX} opened – hand tracking active.")
                else:
                    print(f"[HandTracker] Camera {CAMERA_INDEX} open but MediaPipe unavailable.")
            else:
                print(f"[HandTracker] Could not open camera {CAMERA_INDEX} – using keyboard mode.")
                cap.release()
        except Exception as exc:
            print(f"[HandTracker] Webcam error: {exc}")

    # ── Per-frame query ───────────────────────────────────────────────────────

    def get_hand_y(self) -> Optional[float]:
        """
        Capture one frame, run hand detection, and return a smoothed Y.

        Returns
        -------
        float | None
            Normalised Y of the index fingertip (0.0 = top, 1.0 = bottom),
            smoothed with EMA.  Returns the last known position if no hand
            is visible (fish freezes briefly), or None on first detection
            failure (fish stays at its last game position).
        """
        if not self.available or self._cap is None or self._hands is None:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None

        # Mirror horizontally so it feels like looking in a mirror.
        # Moving your hand left → fish moves left; up → fish goes up.
        frame = cv2.flip(frame, 1)

        # MediaPipe requires RGB; OpenCV gives BGR by default.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)

        if not result.multi_hand_landmarks:
            # No hand visible – return the last smoothed position so the
            # fish gently freezes rather than snapping to a default.
            return self._smoothed_y

        # landmark[INDEX_TIP].y is already normalised [0.0, 1.0] by MediaPipe
        tip_y: float = result.multi_hand_landmarks[0].landmark[self._INDEX_TIP].y

        # Exponential Moving Average smoothing
        if self._smoothed_y is None:
            self._smoothed_y = tip_y
        else:
            self._smoothed_y = (
                self.smooth_factor * tip_y
                + (1.0 - self.smooth_factor) * self._smoothed_y
            )

        return self._smoothed_y

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def release(self) -> None:
        """Release webcam and MediaPipe resources.  Call before exiting."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._hands is not None:
            self._hands.close()
            self._hands = None
        print("[HandTracker] Resources released.")

"""
list_cameras.py – Show all available camera indices and their resolutions.

Run this to figure out which index is your Mac's built-in camera vs. an
iPhone (Continuity Camera) or other connected device.

Usage:
    python src/list_cameras.py

Then set CAMERA_INDEX in src/config.py to the index you want.
"""

import sys
import cv2


def main() -> None:
    backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
    print("Scanning camera indices 0–9...\n")
    found = False
    for i in range(10):
        cap = cv2.VideoCapture(i, backend)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"  Index {i}: {w}x{h} @ {fps:.0f} fps")
            cap.release()
            found = True

    if not found:
        print("  No cameras found.")

    print()
    print("Set CAMERA_INDEX in src/config.py to the index of your preferred camera.")
    print("On macOS with Continuity Camera, index 1 is usually the built-in FaceTime camera.")


if __name__ == "__main__":
    main()

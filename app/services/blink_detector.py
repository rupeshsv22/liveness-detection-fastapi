from __future__ import annotations
import time
from typing import List, Tuple

import numpy as np

from app.config import settings
from app.services.face_detector import FaceDetector

# MediaPipe Face Mesh landmark indices for eyes
# Left eye  (from person's perspective)
LEFT_EYE = [362, 385, 387, 263, 373, 380]
# Right eye
RIGHT_EYE = [33, 160, 158, 133, 153, 144]


def _ear(eye_pts: List[Tuple[float, float]]) -> float:
    """Eye Aspect Ratio — p1..p6 as per Soukupova & Cech (2016)."""
    p1, p2, p3, p4, p5, p6 = [np.array(p) for p in eye_pts]
    vertical_1 = np.linalg.norm(p2 - p6)
    vertical_2 = np.linalg.norm(p3 - p5)
    horizontal = np.linalg.norm(p1 - p4)
    return (vertical_1 + vertical_2) / (2.0 * horizontal)


class BlinkDetector:
    """
    Stateful blink detector.
    Call reset() when starting a new challenge session.
    """

    def __init__(self) -> None:
        self._consec_below: int = 0   # frames where EAR < threshold
        self._blink_count: int = 0
        self._blink_timestamps: List[float] = []
        self._eye_closed: bool = False

    def reset(self) -> None:
        self._consec_below = 0
        self._blink_count = 0
        self._blink_timestamps = []
        self._eye_closed = False

    @property
    def blink_count(self) -> int:
        return self._blink_count

    def update(
        self,
        detector: FaceDetector,
        landmarks,
        image_shape: tuple,
    ) -> bool:
        """Process one frame. Returns True if a new blink was just detected."""
        left_pts = detector.get_landmark_pixels(landmarks, LEFT_EYE, image_shape)
        right_pts = detector.get_landmark_pixels(landmarks, RIGHT_EYE, image_shape)

        ear = (_ear(left_pts) + _ear(right_pts)) / 2.0

        if ear < settings.EAR_THRESHOLD:
            self._consec_below += 1
            self._eye_closed = True
        else:
            if self._eye_closed and self._consec_below >= settings.EAR_CONSEC_FRAMES:
                self._blink_count += 1
                self._blink_timestamps.append(time.time())
                self._consec_below = 0
                self._eye_closed = False
                return True
            self._consec_below = 0
            self._eye_closed = False

        return False

    def check_blink_once(self) -> bool:
        return self._blink_count >= 1

    def check_blink_twice(self, window_seconds: float = 5.0) -> bool:
        """Two blinks within the given window."""
        now = time.time()
        recent = [t for t in self._blink_timestamps if now - t <= window_seconds]
        return len(recent) >= 2

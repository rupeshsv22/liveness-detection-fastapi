from __future__ import annotations
import time
from typing import Optional, Tuple

import cv2
import numpy as np

from app.config import settings
from app.services.face_detector import FaceDetector

# MediaPipe Face Mesh indices for 6-point PnP model
# nose tip, chin, left eye corner, right eye corner, left mouth, right mouth
POSE_LANDMARK_IDS = [1, 152, 263, 33, 287, 57]

# Generic 3-D face model (world coordinates, centred at nose tip)
MODEL_3D = np.array([
    [0.0,     0.0,     0.0],     # nose tip
    [0.0,    -63.6,   -12.5],   # chin
    [-43.3,   32.7,   -26.0],   # left eye outer corner
    [43.3,    32.7,   -26.0],   # right eye outer corner
    [-28.9,  -28.9,   -24.1],   # left mouth corner
    [28.9,   -28.9,   -24.1],   # right mouth corner
], dtype=np.float64)


def _rotation_matrix_to_euler(rvec: np.ndarray) -> Tuple[float, float, float]:
    """Return (pitch, yaw, roll) in degrees from a Rodrigues rotation vector."""
    rmat, _ = cv2.Rodrigues(rvec)
    # Decompose: R = Rx * Ry * Rz
    sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
    singular = sy < 1e-6
    if not singular:
        pitch = np.degrees(np.arctan2(rmat[2, 1], rmat[2, 2]))
        yaw   = np.degrees(np.arctan2(-rmat[2, 0], sy))
        roll  = np.degrees(np.arctan2(rmat[1, 0], rmat[0, 0]))
    else:
        pitch = np.degrees(np.arctan2(-rmat[1, 2], rmat[1, 1]))
        yaw   = np.degrees(np.arctan2(-rmat[2, 0], sy))
        roll  = 0.0
    return float(pitch), float(yaw), float(roll)


class HeadPoseDetector:
    """Stateful head-pose tracker. One per WebSocket connection."""

    def __init__(self) -> None:
        self._nod_started_at: Optional[float] = None
        self._nod_base_pitch: Optional[float] = None
        self._nod_down_seen: bool = False

    def reset(self) -> None:
        self._nod_started_at = None
        self._nod_base_pitch = None
        self._nod_down_seen = False

    def estimate(
        self,
        detector: FaceDetector,
        landmarks,
        image_shape: Tuple[int, int],
    ) -> Optional[Tuple[float, float, float]]:
        """Return (pitch, yaw, roll) or None if PnP fails."""
        h, w = image_shape
        pts_2d = np.array(
            detector.get_landmark_pixels(landmarks, POSE_LANDMARK_IDS, image_shape),
            dtype=np.float64,
        )

        focal = w  # approximate focal length
        cam_matrix = np.array([
            [focal, 0,     w / 2],
            [0,     focal, h / 2],
            [0,     0,     1    ],
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, _ = cv2.solvePnP(
            MODEL_3D, pts_2d, cam_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return None

        return _rotation_matrix_to_euler(rvec)

    def check_turn_left(self, yaw: float) -> bool:
        return yaw < -settings.HEAD_YAW_THRESHOLD

    def check_turn_right(self, yaw: float) -> bool:
        return yaw > settings.HEAD_YAW_THRESHOLD

    def check_nod(self, pitch: float, window_seconds: float = 2.0) -> bool:
        """
        Detect a nod: pitch drops > threshold below baseline then returns up
        within `window_seconds`.
        """
        now = time.time()

        if self._nod_base_pitch is None:
            self._nod_base_pitch = pitch
            self._nod_started_at = now
            return False

        # Timeout — reset
        if now - self._nod_started_at > window_seconds:
            self._nod_base_pitch = pitch
            self._nod_started_at = now
            self._nod_down_seen = False
            return False

        delta = pitch - self._nod_base_pitch

        if not self._nod_down_seen:
            if delta > settings.HEAD_PITCH_THRESHOLD:
                self._nod_down_seen = True
        else:
            if delta < settings.HEAD_PITCH_THRESHOLD / 2:
                # Returned to neutral
                self._nod_down_seen = False
                self._nod_base_pitch = None
                return True

        return False

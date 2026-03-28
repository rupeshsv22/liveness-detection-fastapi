from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class FaceResult:
    detected: bool
    face_count: int
    landmarks: Optional[object] = None  # mediapipe NormalizedLandmarkList
    image_shape: Tuple[int, int] = (480, 640)  # (h, w)


class FaceDetector:
    """One MediaPipe FaceMesh instance per WebSocket connection (not thread-safe)."""

    def __init__(self) -> None:
        self._mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = self._mp_face_mesh.FaceMesh(
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame_bgr: np.ndarray) -> FaceResult:
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return FaceResult(detected=False, face_count=0, image_shape=(h, w))

        face_count = len(results.multi_face_landmarks)
        if face_count != 1:
            # Reject multi-face frames
            return FaceResult(detected=True, face_count=face_count, image_shape=(h, w))

        return FaceResult(
            detected=True,
            face_count=1,
            landmarks=results.multi_face_landmarks[0],
            image_shape=(h, w),
        )

    def get_landmark_pixels(
        self,
        landmarks,
        indices: List[int],
        image_shape: Tuple[int, int],
    ) -> List[Tuple[float, float]]:
        """Convert normalized landmarks to pixel coords for given indices."""
        h, w = image_shape
        pts = []
        for i in indices:
            lm = landmarks.landmark[i]
            pts.append((lm.x * w, lm.y * h))
        return pts

    def get_face_roi(
        self,
        frame_bgr: np.ndarray,
        landmarks,
        padding: float = 0.2,
    ) -> Optional[np.ndarray]:
        """Crop the face bounding box with padding."""
        h, w = frame_bgr.shape[:2]
        xs = [lm.x * w for lm in landmarks.landmark]
        ys = [lm.y * h for lm in landmarks.landmark]
        x1 = max(0, int(min(xs) * (1 - padding)))
        y1 = max(0, int(min(ys) * (1 - padding)))
        x2 = min(w, int(max(xs) * (1 + padding)))
        y2 = min(h, int(max(ys) * (1 + padding)))
        if x2 <= x1 or y2 <= y1:
            return None
        return frame_bgr[y1:y2, x1:x2]

    def close(self) -> None:
        self._face_mesh.close()

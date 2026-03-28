from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from app.config import settings
from app.services.blink_detector import BlinkDetector, _ear, LEFT_EYE, RIGHT_EYE


# ── _ear() ────────────────────────────────────────────────────────────────────

class TestEAR:
    def _open_eye_pts(self):
        # Wide-open eye: p2 and p6 are far apart vertically, p1-p4 horizontal
        return [
            (0.0, 0.0),   # p1 left corner
            (0.5, 0.5),   # p2 top-left
            (1.0, 0.5),   # p3 top-right
            (2.0, 0.0),   # p4 right corner
            (1.0, -0.5),  # p5 bottom-right
            (0.5, -0.5),  # p6 bottom-left
        ]

    def _closed_eye_pts(self):
        # Nearly closed: vertical distances tiny
        return [
            (0.0, 0.0),
            (0.5, 0.01),
            (1.0, 0.01),
            (2.0, 0.0),
            (1.0, -0.01),
            (0.5, -0.01),
        ]

    def test_open_eye_ear_above_threshold(self):
        pts = self._open_eye_pts()
        assert _ear(pts) > settings.EAR_THRESHOLD

    def test_closed_eye_ear_below_threshold(self):
        pts = self._closed_eye_pts()
        assert _ear(pts) < settings.EAR_THRESHOLD

    def test_symmetric_eye_returns_positive(self):
        pts = self._open_eye_pts()
        assert _ear(pts) > 0


# ── BlinkDetector ─────────────────────────────────────────────────────────────

def _make_detector_and_landmarks(ear_value: float):
    """Return a (FaceDetector mock, landmarks mock) pair that yields a given EAR."""
    half_ear = ear_value  # both eyes will yield the same EAR, average == ear_value

    # Points that produce the desired EAR when fed to _ear()
    # We need: (v1 + v2) / (2 * h) == ear_value
    # Choose h=2, v1=v2=ear_value*2, giving the exact ratio
    h = 2.0
    v = ear_value * 2.0
    pts = [
        (0.0, 0.0),
        (0.5, v / 2),
        (1.5, v / 2),
        (2.0, 0.0),
        (1.5, -v / 2),
        (0.5, -v / 2),
    ]

    detector = MagicMock()
    detector.get_landmark_pixels.return_value = pts
    landmarks = MagicMock()
    image_shape = (480, 640)
    return detector, landmarks, image_shape


class TestBlinkDetector:
    def test_initial_state(self):
        bd = BlinkDetector()
        assert bd.blink_count == 0
        assert not bd.check_blink_once()
        assert not bd.check_blink_twice()

    def test_reset_clears_state(self):
        bd = BlinkDetector()
        bd._blink_count = 3
        bd._blink_timestamps = [time.time()]
        bd._eye_closed = True
        bd.reset()
        assert bd.blink_count == 0
        assert bd._blink_timestamps == []
        assert not bd._eye_closed

    def test_blink_detected_after_close_then_open(self):
        bd = BlinkDetector()
        # Simulate eyes closed for EAR_CONSEC_FRAMES frames
        det_closed, lm, shape = _make_detector_and_landmarks(0.10)
        det_open, _, _ = _make_detector_and_landmarks(0.40)
        for _ in range(settings.EAR_CONSEC_FRAMES):
            bd.update(det_closed, lm, shape)
        # Open eye — blink should be registered
        detected = bd.update(det_open, lm, shape)
        assert detected
        assert bd.blink_count == 1

    def test_no_blink_if_frames_below_consec_threshold(self):
        bd = BlinkDetector()
        det_closed, lm, shape = _make_detector_and_landmarks(0.10)
        det_open, _, _ = _make_detector_and_landmarks(0.40)
        # Only 1 frame below threshold (need EAR_CONSEC_FRAMES)
        bd.update(det_closed, lm, shape)
        detected = bd.update(det_open, lm, shape)
        assert not detected or settings.EAR_CONSEC_FRAMES <= 1

    def test_check_blink_once_false_before_blink(self):
        bd = BlinkDetector()
        assert not bd.check_blink_once()

    def test_check_blink_once_true_after_blink(self):
        bd = BlinkDetector()
        bd._blink_count = 1
        assert bd.check_blink_once()

    def test_check_blink_twice_requires_two_recent(self):
        bd = BlinkDetector()
        now = time.time()
        bd._blink_count = 2
        bd._blink_timestamps = [now - 1.0, now - 0.5]
        assert bd.check_blink_twice(window_seconds=5.0)

    def test_check_blink_twice_false_if_old(self):
        bd = BlinkDetector()
        old = time.time() - 100.0
        bd._blink_count = 2
        bd._blink_timestamps = [old, old + 0.5]
        assert not bd.check_blink_twice(window_seconds=5.0)

    def test_open_eye_resets_consec_counter(self):
        bd = BlinkDetector()
        det_closed, lm, shape = _make_detector_and_landmarks(0.10)
        det_open, _, _ = _make_detector_and_landmarks(0.40)
        bd.update(det_closed, lm, shape)
        assert bd._consec_below == 1
        bd.update(det_open, lm, shape)
        # After open (without enough consec frames) counter resets
        assert bd._consec_below == 0

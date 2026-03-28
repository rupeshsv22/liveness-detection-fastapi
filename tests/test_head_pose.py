from __future__ import annotations

import time
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest

from app.config import settings
from app.services.head_pose import (
    HeadPoseDetector,
    _rotation_matrix_to_euler,
    MODEL_3D,
    POSE_LANDMARK_IDS,
)


# ── _rotation_matrix_to_euler() ───────────────────────────────────────────────

class TestRotationMatrixToEuler:
    def _zero_rvec(self) -> np.ndarray:
        return np.zeros((3, 1), dtype=np.float64)

    def test_identity_rotation_gives_near_zero_angles(self):
        pitch, yaw, roll = _rotation_matrix_to_euler(self._zero_rvec())
        assert abs(pitch) < 1e-6
        assert abs(yaw) < 1e-6
        assert abs(roll) < 1e-6

    def test_returns_three_floats(self):
        result = _rotation_matrix_to_euler(self._zero_rvec())
        assert len(result) == 3
        for v in result:
            assert isinstance(v, float)

    def test_known_yaw(self):
        # Rotate 30° around Y axis (yaw)
        angle_rad = np.radians(30)
        rvec = np.array([[0.0], [angle_rad], [0.0]])
        pitch, yaw, roll = _rotation_matrix_to_euler(rvec)
        assert abs(yaw - 30.0) < 1.0  # within 1 degree tolerance


# ── HeadPoseDetector checks ───────────────────────────────────────────────────

class TestHeadPoseDetectorChecks:
    def test_check_turn_left_true(self):
        hpd = HeadPoseDetector()
        assert hpd.check_turn_left(-settings.HEAD_YAW_THRESHOLD - 1.0)

    def test_check_turn_left_false(self):
        hpd = HeadPoseDetector()
        assert not hpd.check_turn_left(0.0)
        assert not hpd.check_turn_left(-settings.HEAD_YAW_THRESHOLD + 1.0)

    def test_check_turn_right_true(self):
        hpd = HeadPoseDetector()
        assert hpd.check_turn_right(settings.HEAD_YAW_THRESHOLD + 1.0)

    def test_check_turn_right_false(self):
        hpd = HeadPoseDetector()
        assert not hpd.check_turn_right(0.0)
        assert not hpd.check_turn_right(settings.HEAD_YAW_THRESHOLD - 1.0)

    def test_check_turn_at_threshold_boundary(self):
        hpd = HeadPoseDetector()
        assert not hpd.check_turn_left(-settings.HEAD_YAW_THRESHOLD)
        assert not hpd.check_turn_right(settings.HEAD_YAW_THRESHOLD)


# ── HeadPoseDetector.check_nod() ─────────────────────────────────────────────

class TestHeadPoseDetectorNod:
    def test_initial_call_sets_baseline_returns_false(self):
        hpd = HeadPoseDetector()
        assert not hpd.check_nod(0.0)
        assert hpd._nod_base_pitch == 0.0

    def test_nod_detected(self):
        hpd = HeadPoseDetector()
        # Frame 1: set baseline
        hpd.check_nod(0.0)
        # Frame 2: pitch drops below threshold (nod down)
        hpd.check_nod(settings.HEAD_PITCH_THRESHOLD + 1.0)
        # Frame 3: returns to neutral → nod complete
        assert hpd.check_nod(0.0)

    def test_nod_not_detected_without_down_phase(self):
        hpd = HeadPoseDetector()
        hpd.check_nod(0.0)
        # Returns to "neutral" without going down first
        assert not hpd.check_nod(0.0)

    def test_reset_clears_nod_state(self):
        hpd = HeadPoseDetector()
        hpd.check_nod(5.0)
        hpd.reset()
        assert hpd._nod_base_pitch is None
        assert hpd._nod_started_at is None
        assert not hpd._nod_down_seen

    def test_nod_timeout_resets_baseline(self):
        hpd = HeadPoseDetector()
        hpd.check_nod(0.0)
        # Manually expire the window
        hpd._nod_started_at = time.time() - 100.0
        # Next call should reset baseline, not detect nod
        result = hpd.check_nod(5.0)
        assert not result
        assert hpd._nod_base_pitch == 5.0

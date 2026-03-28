from __future__ import annotations

import os

import pytest

from app.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.EAR_THRESHOLD == 0.21
        assert s.EAR_CONSEC_FRAMES == 2
        assert s.HEAD_YAW_THRESHOLD == 25.0
        assert s.HEAD_PITCH_THRESHOLD == 15.0
        assert s.SPOOF_THRESHOLD == 0.6
        assert s.SPOOF_CHECK_INTERVAL == 5
        assert s.SESSION_TIMEOUT == 60
        assert s.CHALLENGE_TIMEOUT == 30
        assert s.LIVENESS_PASS_THRESHOLD == 70.0
        assert s.MIN_CHALLENGES == 2
        assert s.MAX_CHALLENGES == 3
        assert s.FRAME_WIDTH == 640
        assert s.FRAME_HEIGHT == 480
        assert s.NO_FACE_WARN_FRAMES == 10
        assert s.NO_FACE_FAIL_FRAMES == 20

    def test_min_not_greater_than_max_challenges(self):
        s = Settings()
        assert s.MIN_CHALLENGES <= s.MAX_CHALLENGES

    def test_allowed_origins_default_is_wildcard(self):
        s = Settings()
        assert "*" in s.ALLOWED_ORIGINS

    def test_allowed_origins_from_env(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com,http://b.com")
        # Re-evaluate the class-level default by instantiating inside the test
        import importlib
        import app.config as cfg_module
        importlib.reload(cfg_module)
        assert cfg_module.settings.ALLOWED_ORIGINS == ["http://a.com", "http://b.com"]
        # Reload back to default so other tests aren't affected
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        importlib.reload(cfg_module)

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.config import settings
from app.models.enums import ChallengeType, SessionStatus
from app.models.schemas import ChallengeItem
from app.services.scorer import calculate_liveness_score, is_passing
from app.services.session import SessionData


def _session(
    *,
    num_challenges: int = 2,
    challenges_completed: int = 2,
    spoof_scores: list | None = None,
    duration: float | None = 5.0,
    spoof_detected: bool = False,
) -> SessionData:
    challenges = [
        ChallengeItem(type=ChallengeType.BLINK, instruction="blink", order=i + 1)
        for i in range(num_challenges)
    ]
    s = SessionData(session_id="x", user_id=None, challenges=challenges)
    s.challenges_completed = challenges_completed
    s.spoof_scores = spoof_scores or []
    s.spoof_detected = spoof_detected
    if duration is not None:
        # Set completed_at to created_at + duration
        from datetime import timedelta
        s.completed_at = s.created_at + timedelta(seconds=duration)
    return s


class TestCalculateLivenessScore:
    def test_no_challenges_returns_zero(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        assert calculate_liveness_score(s) == 0.0

    def test_perfect_score(self):
        # All challenges done, no spoof, completed in < 10 s
        s = _session(num_challenges=2, challenges_completed=2, duration=5.0)
        score = calculate_liveness_score(s)
        # challenges ratio = 1.0 -> 60, spoof component = 1.0 -> 30, speed_bonus = 1.0 -> 10
        assert score == 100.0

    def test_zero_challenges_completed(self):
        s = _session(num_challenges=2, challenges_completed=0, duration=5.0)
        score = calculate_liveness_score(s)
        # challenges = 0, spoof = 30, speed = 10
        assert score == 40.0

    def test_high_spoof_score_reduces_result(self):
        s = _session(num_challenges=2, challenges_completed=2, spoof_scores=[1.0], duration=5.0)
        score = calculate_liveness_score(s)
        # challenges = 60, spoof_component = 0 -> 0, speed = 10
        assert score == 70.0

    def test_slow_completion_reduces_speed_bonus(self):
        # Completed in 30 s → speed_bonus = 0
        s = _session(num_challenges=2, challenges_completed=2, duration=30.0)
        score = calculate_liveness_score(s)
        # challenges = 60, spoof = 30, speed = 0
        assert score == 90.0

    def test_very_slow_completion_clamps_at_zero_speed(self):
        # Completed in 100 s → speed_bonus clamped to 0
        s = _session(num_challenges=2, challenges_completed=2, duration=100.0)
        score = calculate_liveness_score(s)
        assert score == 90.0

    def test_none_duration_uses_challenge_timeout(self):
        s = _session(num_challenges=2, challenges_completed=2, duration=None)
        score = calculate_liveness_score(s)
        # duration falls back to CHALLENGE_TIMEOUT (30) => speed_bonus = 0
        assert score == 90.0

    def test_partial_completion(self):
        s = _session(num_challenges=2, challenges_completed=1, duration=5.0)
        score = calculate_liveness_score(s)
        assert score == 70.0  # 0.5*60 + 1.0*30 + 1.0*10

    def test_score_is_rounded_to_two_decimals(self):
        s = _session(num_challenges=3, challenges_completed=2, spoof_scores=[0.1, 0.2], duration=15.0)
        score = calculate_liveness_score(s)
        assert score == round(score, 2)


class TestIsPassing:
    def test_passes_above_threshold(self):
        assert is_passing(settings.LIVENESS_PASS_THRESHOLD, spoof_detected=False)

    def test_passes_at_threshold(self):
        assert is_passing(settings.LIVENESS_PASS_THRESHOLD, spoof_detected=False)

    def test_fails_below_threshold(self):
        assert not is_passing(settings.LIVENESS_PASS_THRESHOLD - 0.01, spoof_detected=False)

    def test_fails_when_spoof_detected_even_with_high_score(self):
        assert not is_passing(100.0, spoof_detected=True)

    def test_fails_with_zero_score_and_spoof(self):
        assert not is_passing(0.0, spoof_detected=True)

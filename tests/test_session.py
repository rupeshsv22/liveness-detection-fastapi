from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from app.models.enums import ChallengeType, SessionStatus
from app.models.schemas import ChallengeItem
from app.services.session import SessionData, SessionManager


def _make_challenges(*types: ChallengeType) -> list[ChallengeItem]:
    return [
        ChallengeItem(type=t, instruction="test", order=i + 1)
        for i, t in enumerate(types)
    ]


# ── SessionData ──────────────────────────────────────────────────────────────

class TestSessionData:
    def test_current_challenge_first(self):
        challenges = _make_challenges(ChallengeType.BLINK, ChallengeType.NOD)
        s = SessionData(session_id="x", user_id=None, challenges=challenges)
        assert s.current_challenge == challenges[0]

    def test_current_challenge_advances(self):
        challenges = _make_challenges(ChallengeType.BLINK, ChallengeType.NOD)
        s = SessionData(session_id="x", user_id=None, challenges=challenges)
        s.current_challenge_index = 1
        assert s.current_challenge == challenges[1]

    def test_current_challenge_none_when_done(self):
        challenges = _make_challenges(ChallengeType.BLINK)
        s = SessionData(session_id="x", user_id=None, challenges=challenges)
        s.current_challenge_index = 1
        assert s.current_challenge is None

    def test_avg_spoof_score_empty(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        assert s.avg_spoof_score == 0.0

    def test_avg_spoof_score_multiple(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        s.spoof_scores = [0.2, 0.4, 0.6]
        assert abs(s.avg_spoof_score - 0.4) < 1e-9

    def test_duration_seconds_none_when_not_completed(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        assert s.duration_seconds is None

    def test_duration_seconds_calculated(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        s.completed_at = datetime.now(timezone.utc)
        # Allow up to a second for timing noise
        assert s.duration_seconds is not None
        assert s.duration_seconds >= 0.0

    def test_touch_updates_last_active(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        before = s.last_active
        time.sleep(0.01)
        s.touch()
        assert s.last_active > before

    def test_is_expired_false_when_recent(self):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        s.touch()
        assert not s.is_expired()

    def test_is_expired_true_when_stale(self, monkeypatch):
        s = SessionData(session_id="x", user_id=None, challenges=[])
        # Simulate last_active far in the past
        s.last_active = time.time() - 10_000
        assert s.is_expired()


# ── SessionManager ───────────────────────────────────────────────────────────

class TestSessionManager:
    def test_create_returns_session(self, manager, sample_challenges):
        session = manager.create(user_id="u1", challenges=sample_challenges)
        assert session.session_id
        assert session.user_id == "u1"
        assert session.challenges == sample_challenges
        assert session.status == SessionStatus.PENDING

    def test_create_unique_ids(self, manager, sample_challenges):
        s1 = manager.create(user_id=None, challenges=sample_challenges)
        s2 = manager.create(user_id=None, challenges=sample_challenges)
        assert s1.session_id != s2.session_id

    def test_get_existing(self, manager, sample_challenges):
        session = manager.create(user_id=None, challenges=sample_challenges)
        fetched = manager.get(session.session_id)
        assert fetched is session

    def test_get_missing_returns_none(self, manager):
        assert manager.get("nonexistent") is None

    def test_get_marks_expired_if_stale(self, manager, sample_challenges):
        session = manager.create(user_id=None, challenges=sample_challenges)
        session.last_active = time.time() - 10_000
        fetched = manager.get(session.session_id)
        assert fetched.status == SessionStatus.EXPIRED

    def test_get_does_not_expire_completed(self, manager, sample_challenges):
        session = manager.create(user_id=None, challenges=sample_challenges)
        session.status = SessionStatus.COMPLETED
        session.last_active = time.time() - 10_000
        fetched = manager.get(session.session_id)
        # Status should NOT be changed to EXPIRED because it is already COMPLETED
        assert fetched.status == SessionStatus.COMPLETED

    def test_delete_removes_session(self, manager, sample_challenges):
        session = manager.create(user_id=None, challenges=sample_challenges)
        manager.delete(session.session_id)
        assert manager.get(session.session_id) is None

    def test_delete_nonexistent_does_not_raise(self, manager):
        manager.delete("does-not-exist")  # should not raise

    def test_create_with_no_user_id(self, manager, sample_challenges):
        session = manager.create(user_id=None, challenges=sample_challenges)
        assert session.user_id is None

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import SessionStatus
from app.services.session import session_manager


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ── /health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ── POST /api/liveness/start ─────────────────────────────────────────────────

class TestStartSession:
    def test_creates_session_with_default_body(self, client):
        resp = client.post("/api/liveness/start")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert isinstance(data["challenges"], list)
        assert len(data["challenges"]) >= 1
        assert "timeout_seconds" in data
        assert "created_at" in data

    def test_creates_session_with_user_id(self, client):
        resp = client.post("/api/liveness/start", json={"user_id": "alice"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"]

    def test_challenge_count_within_bounds(self, client):
        from app.config import settings
        for _ in range(5):
            resp = client.post("/api/liveness/start")
            count = len(resp.json()["challenges"])
            assert settings.MIN_CHALLENGES <= count <= settings.MAX_CHALLENGES

    def test_challenge_has_required_fields(self, client):
        resp = client.post("/api/liveness/start")
        for challenge in resp.json()["challenges"]:
            assert "type" in challenge
            assert "instruction" in challenge
            assert "order" in challenge

    def test_each_call_returns_unique_session_id(self, client):
        ids = {client.post("/api/liveness/start").json()["session_id"] for _ in range(5)}
        assert len(ids) == 5


# ── GET /api/liveness/result/{session_id} ────────────────────────────────────

class TestGetResult:
    def _start(self, client) -> str:
        return client.post("/api/liveness/start").json()["session_id"]

    def test_pending_session_returns_200(self, client):
        sid = self._start(client)
        resp = client.get(f"/api/liveness/result/{sid}")
        assert resp.status_code == 200

    def test_result_fields_present(self, client):
        sid = self._start(client)
        data = client.get(f"/api/liveness/result/{sid}").json()
        assert data["session_id"] == sid
        assert "status" in data
        assert "challenges_completed" in data
        assert "challenges_total" in data

    def test_missing_session_returns_404(self, client):
        resp = client.get("/api/liveness/result/does-not-exist")
        assert resp.status_code == 404

    def test_expired_session_returns_410(self, client):
        import time
        sid = self._start(client)
        # Manually expire the session
        session = session_manager.get(sid)
        session.status = SessionStatus.EXPIRED
        resp = client.get(f"/api/liveness/result/{sid}")
        assert resp.status_code == 410

    def test_completed_session_returns_score(self, client):
        from datetime import datetime, timezone, timedelta
        sid = self._start(client)
        session = session_manager.get(sid)
        session.status = SessionStatus.COMPLETED
        session.liveness_score = 85.0
        session.passed = True
        session.challenges_completed = len(session.challenges)
        session.completed_at = datetime.now(timezone.utc)
        data = client.get(f"/api/liveness/result/{sid}").json()
        assert data["liveness_score"] == 85.0
        assert data["passed"] is True
        assert data["status"] == "COMPLETED"

    def test_avg_spoof_score_rounded(self, client):
        sid = self._start(client)
        session = session_manager.get(sid)
        session.spoof_scores = [0.33333, 0.66666]
        data = client.get(f"/api/liveness/result/{sid}").json()
        assert len(str(data["avg_spoof_score"]).split(".")[-1]) <= 4

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import ChallengeType
from app.models.schemas import ChallengeItem
from app.services.session import SessionManager


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_challenges():
    return [
        ChallengeItem(type=ChallengeType.BLINK, instruction="Blink your eyes once", order=1),
        ChallengeItem(type=ChallengeType.TURN_LEFT, instruction="Turn your head to the left", order=2),
    ]


@pytest.fixture()
def manager():
    """Fresh SessionManager for each test."""
    return SessionManager()

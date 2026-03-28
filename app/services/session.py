from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.config import settings
from app.models.enums import SessionStatus
from app.models.schemas import ChallengeItem


@dataclass
class SessionData:
    session_id: str
    user_id: Optional[str]
    challenges: List[ChallengeItem]
    status: SessionStatus = SessionStatus.PENDING
    current_challenge_index: int = 0
    challenges_completed: int = 0
    spoof_detected: bool = False
    spoof_scores: List[float] = field(default_factory=list)
    liveness_score: Optional[float] = None
    passed: Optional[bool] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: float = field(default_factory=time.time)
    completed_at: Optional[datetime] = None

    @property
    def current_challenge(self) -> Optional[ChallengeItem]:
        if self.current_challenge_index < len(self.challenges):
            return self.challenges[self.current_challenge_index]
        return None

    @property
    def avg_spoof_score(self) -> float:
        if not self.spoof_scores:
            return 0.0
        return sum(self.spoof_scores) / len(self.spoof_scores)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.created_at).total_seconds()

    def touch(self) -> None:
        self.last_active = time.time()

    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > settings.SESSION_TIMEOUT


class SessionManager:
    def __init__(self) -> None:
        self._store: Dict[str, SessionData] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup(self) -> None:
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()

    async def _cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            expired = [
                sid for sid, s in self._store.items() if s.is_expired()
            ]
            for sid in expired:
                session = self._store[sid]
                if session.status in (SessionStatus.PENDING, SessionStatus.IN_PROGRESS):
                    session.status = SessionStatus.EXPIRED
                # Keep completed/failed sessions briefly for result retrieval
                if session.status == SessionStatus.EXPIRED:
                    del self._store[sid]

    def create(self, user_id: Optional[str], challenges: List[ChallengeItem]) -> SessionData:
        session_id = str(uuid.uuid4())
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            challenges=challenges,
        )
        self._store[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SessionData]:
        session = self._store.get(session_id)
        if session is None:
            return None
        if session.is_expired() and session.status in (
            SessionStatus.PENDING, SessionStatus.IN_PROGRESS
        ):
            session.status = SessionStatus.EXPIRED
        return session

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)


session_manager = SessionManager()

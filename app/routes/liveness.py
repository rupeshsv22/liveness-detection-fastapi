from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.enums import SessionStatus
from app.models.schemas import (
    SessionResultResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from app.services.challenge import generate_challenges
from app.services.session import session_manager

router = APIRouter(prefix="/api/liveness", tags=["liveness"])


@router.post("/start", response_model=StartSessionResponse)
async def start_session(body: StartSessionRequest = None):
    if body is None:
        body = StartSessionRequest()

    challenges = generate_challenges()
    session = session_manager.create(user_id=body.user_id, challenges=challenges)

    return StartSessionResponse(
        session_id=session.session_id,
        challenges=session.challenges,
        timeout_seconds=settings.CHALLENGE_TIMEOUT,
        created_at=session.created_at,
    )


@router.get("/result/{session_id}", response_model=SessionResultResponse)
async def get_result(session_id: str):
    session = session_manager.get(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.EXPIRED:
        raise HTTPException(status_code=410, detail="Session expired")

    return SessionResultResponse(
        session_id=session.session_id,
        status=session.status,
        liveness_score=session.liveness_score,
        passed=session.passed,
        challenges_completed=session.challenges_completed,
        challenges_total=len(session.challenges),
        spoof_detected=session.spoof_detected,
        avg_spoof_score=round(session.avg_spoof_score, 4),
        duration_seconds=session.duration_seconds,
        completed_at=session.completed_at,
    )

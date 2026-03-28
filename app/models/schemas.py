from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.enums import ChallengeType, SessionStatus


# ── Request models ────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    user_id: Optional[str] = None


class FrameMessage(BaseModel):
    frame: str  # base64-encoded JPEG
    timestamp: int


# ── Response models ───────────────────────────────────────────────────────────

class ChallengeItem(BaseModel):
    type: ChallengeType
    instruction: str
    order: int


class StartSessionResponse(BaseModel):
    session_id: str
    challenges: List[ChallengeItem]
    timeout_seconds: int
    created_at: datetime


class FrameResponse(BaseModel):
    face_detected: bool
    face_count: int
    current_challenge: Optional[ChallengeItem] = None
    challenge_completed: bool = False
    spoof_score: float = 0.0
    spoof_detected: bool = False
    message: str = ""
    error: Optional[str] = None


class CompletionResponse(BaseModel):
    session_complete: bool = True
    liveness_score: float
    passed: bool


class SessionResultResponse(BaseModel):
    session_id: str
    status: SessionStatus
    liveness_score: Optional[float] = None
    passed: Optional[bool] = None
    challenges_completed: int = 0
    challenges_total: int = 0
    spoof_detected: bool = False
    avg_spoof_score: float = 0.0
    duration_seconds: Optional[float] = None
    completed_at: Optional[datetime] = None

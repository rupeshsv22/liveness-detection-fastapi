from __future__ import annotations

from app.config import settings
from app.services.session import SessionData


def calculate_liveness_score(session: SessionData) -> float:
    """
    liveness_score =
        (challenges_passed / total) * 60
      + (1 - avg_spoof_score)       * 30
      + speed_bonus                 * 10

    Speed bonus: 1.0 if completed in < 10 s, scales linearly to 0.0 at 30 s.
    """
    total = len(session.challenges)
    if total == 0:
        return 0.0

    challenges_ratio = session.challenges_completed / total
    spoof_component = 1.0 - min(session.avg_spoof_score, 1.0)

    duration = session.duration_seconds or settings.CHALLENGE_TIMEOUT
    speed_bonus = max(0.0, 1.0 - (duration - 10.0) / 20.0)
    speed_bonus = min(speed_bonus, 1.0)

    score = (
        challenges_ratio * 60.0
        + spoof_component * 30.0
        + speed_bonus * 10.0
    )
    return round(score, 2)


def is_passing(score: float, spoof_detected: bool) -> bool:
    if spoof_detected:
        return False
    return score >= settings.LIVENESS_PASS_THRESHOLD

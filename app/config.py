import os
from typing import List


class Settings:
    # Eye Aspect Ratio
    EAR_THRESHOLD: float = 0.21
    EAR_CONSEC_FRAMES: int = 2

    # Head pose
    HEAD_YAW_THRESHOLD: float = 25.0
    HEAD_PITCH_THRESHOLD: float = 15.0

    # Anti-spoofing
    SPOOF_THRESHOLD: float = 0.6
    SPOOF_CHECK_INTERVAL: int = 5  # every N frames

    # Session
    SESSION_TIMEOUT: int = 60       # seconds of inactivity
    CHALLENGE_TIMEOUT: int = 30     # seconds per challenge

    # Scoring
    LIVENESS_PASS_THRESHOLD: float = 70.0

    # Challenges
    MIN_CHALLENGES: int = 2
    MAX_CHALLENGES: int = 3

    # Frame
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 480

    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", "*"
    ).split(",")

    # No-face tolerance
    NO_FACE_WARN_FRAMES: int = 10
    NO_FACE_FAIL_FRAMES: int = 20


settings = Settings()

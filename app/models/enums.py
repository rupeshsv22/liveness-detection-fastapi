from enum import Enum


class ChallengeType(str, Enum):
    BLINK = "BLINK"
    BLINK_TWICE = "BLINK_TWICE"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    NOD = "NOD"


class SessionStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

from __future__ import annotations
import random
from typing import List

from app.config import settings
from app.models.enums import ChallengeType
from app.models.schemas import ChallengeItem

_INSTRUCTIONS = {
    ChallengeType.BLINK:       "Blink your eyes once",
    ChallengeType.BLINK_TWICE: "Blink your eyes twice",
    ChallengeType.TURN_LEFT:   "Turn your head to the left",
    ChallengeType.TURN_RIGHT:  "Turn your head to the right",
    ChallengeType.NOD:         "Nod your head down and back up",
}

# Pool used for random selection; always include at least one blink challenge
_POOL: List[ChallengeType] = [
    ChallengeType.BLINK,
    ChallengeType.BLINK_TWICE,
    ChallengeType.TURN_LEFT,
    ChallengeType.TURN_RIGHT,
    ChallengeType.NOD,
]


def generate_challenges() -> List[ChallengeItem]:
    count = random.randint(settings.MIN_CHALLENGES, settings.MAX_CHALLENGES)
    chosen = random.sample(_POOL, k=count)
    return [
        ChallengeItem(type=c, instruction=_INSTRUCTIONS[c], order=i + 1)
        for i, c in enumerate(chosen)
    ]

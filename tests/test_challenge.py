from __future__ import annotations

import pytest

from app.config import settings
from app.models.enums import ChallengeType
from app.models.schemas import ChallengeItem
from app.services.challenge import generate_challenges, _INSTRUCTIONS, _POOL


class TestGenerateChallenges:
    def test_count_within_bounds(self):
        for _ in range(20):
            challenges = generate_challenges()
            assert settings.MIN_CHALLENGES <= len(challenges) <= settings.MAX_CHALLENGES

    def test_no_duplicate_challenges(self):
        for _ in range(20):
            challenges = generate_challenges()
            types = [c.type for c in challenges]
            assert len(types) == len(set(types)), "Duplicate challenge types found"

    def test_all_challenges_have_instructions(self):
        challenges = generate_challenges()
        for c in challenges:
            assert c.instruction, f"Missing instruction for {c.type}"

    def test_order_is_sequential_from_one(self):
        challenges = generate_challenges()
        for i, c in enumerate(challenges):
            assert c.order == i + 1

    def test_all_types_are_valid_challenge_types(self):
        for _ in range(20):
            for c in generate_challenges():
                assert c.type in ChallengeType

    def test_instructions_map_covers_all_pool_types(self):
        for t in _POOL:
            assert t in _INSTRUCTIONS

    def test_challenge_items_are_challenge_item_instances(self):
        challenges = generate_challenges()
        for c in challenges:
            assert isinstance(c, ChallengeItem)

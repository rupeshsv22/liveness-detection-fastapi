from __future__ import annotations

from app.models.enums import ChallengeType, SessionStatus


class TestChallengeType:
    def test_all_values_exist(self):
        expected = {"BLINK", "BLINK_TWICE", "TURN_LEFT", "TURN_RIGHT", "NOD"}
        assert {c.value for c in ChallengeType} == expected

    def test_is_str_enum(self):
        assert isinstance(ChallengeType.BLINK, str)
        assert ChallengeType.BLINK == "BLINK"

    def test_value_is_plain_string(self):
        assert ChallengeType.NOD.value == "NOD"


class TestSessionStatus:
    def test_all_values_exist(self):
        expected = {"PENDING", "IN_PROGRESS", "COMPLETED", "EXPIRED", "FAILED"}
        assert {s.value for s in SessionStatus} == expected

    def test_is_str_enum(self):
        assert isinstance(SessionStatus.PENDING, str)
        assert SessionStatus.COMPLETED == "COMPLETED"

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest

from app.models.enums import ChallengeType
from app.models.schemas import ChallengeItem
from app.routes.ws import _decode_frame, _challenge_to_dict


def _encode_frame(img: np.ndarray) -> str:
    """Encode a BGR numpy image as a base64 JPEG string."""
    _, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf.tobytes()).decode()


class TestDecodeFrame:
    def test_valid_frame_returns_array(self):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        b64 = _encode_frame(img)
        result = _decode_frame(b64)
        assert result is not None
        assert result.shape == (480, 640, 3)

    def test_empty_string_returns_none(self):
        assert _decode_frame("") is None

    def test_invalid_base64_returns_none(self):
        assert _decode_frame("not-valid-base64!!!") is None

    def test_valid_base64_but_not_image_returns_none(self):
        garbage = base64.b64encode(b"random bytes that are not an image").decode()
        assert _decode_frame(garbage) is None


class TestChallengeToDictHelper:
    def test_none_returns_none(self):
        assert _challenge_to_dict(None) is None

    def test_challenge_serialised_correctly(self):
        c = ChallengeItem(type=ChallengeType.BLINK, instruction="Blink your eyes once", order=1)
        result = _challenge_to_dict(c)
        assert result == {
            "type": "BLINK",
            "instruction": "Blink your eyes once",
            "order": 1,
        }

    def test_all_challenge_types_serialise(self):
        for ct in ChallengeType:
            c = ChallengeItem(type=ct, instruction="test", order=1)
            result = _challenge_to_dict(c)
            assert result["type"] == ct.value

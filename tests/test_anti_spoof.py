from __future__ import annotations

import numpy as np
import pytest

from app.services.anti_spoof import compute_spoof_score


class TestComputeSpoofScore:
    def test_none_input_returns_zero(self):
        assert compute_spoof_score(None) == 0.0

    def test_empty_array_returns_zero(self):
        assert compute_spoof_score(np.array([])) == 0.0

    def test_score_in_range(self):
        # Random-noise image simulates a "real" face with high texture variance
        rng = np.random.default_rng(42)
        img = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
        score = compute_spoof_score(img)
        assert 0.0 <= score <= 1.0

    def test_flat_image_high_spoof_score(self):
        # Uniform flat image has no texture → high spoof score
        flat = np.full((100, 100, 3), 128, dtype=np.uint8)
        score = compute_spoof_score(flat)
        assert score > 0.5

    def test_noisy_image_lower_spoof_score(self):
        # Highly varied texture → lower spoof score than flat image
        rng = np.random.default_rng(0)
        noisy = rng.integers(0, 256, (100, 100, 3), dtype=np.uint8)
        flat = np.full((100, 100, 3), 128, dtype=np.uint8)
        assert compute_spoof_score(noisy) < compute_spoof_score(flat)

    def test_returns_float(self):
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        result = compute_spoof_score(img)
        assert isinstance(result, float)

    def test_small_image_handled(self):
        img = np.zeros((10, 10, 3), dtype=np.uint8)
        score = compute_spoof_score(img)
        assert 0.0 <= score <= 1.0

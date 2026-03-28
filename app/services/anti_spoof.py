from __future__ import annotations
import cv2
import numpy as np
from skimage.feature import local_binary_pattern


# LBP parameters
_LBP_RADIUS = 3
_LBP_N_POINTS = 8 * _LBP_RADIUS
_LBP_METHOD = "uniform"


def _lbp_histogram(gray: np.ndarray) -> np.ndarray:
    lbp = local_binary_pattern(gray, _LBP_N_POINTS, _LBP_RADIUS, _LBP_METHOD)
    n_bins = _LBP_N_POINTS + 2
    hist, _ = np.histogram(lbp.ravel(), bins=n_bins, range=(0, n_bins), density=True)
    return hist


def compute_spoof_score(face_roi_bgr: np.ndarray) -> float:
    """
    Return a score in [0.0, 1.0].
    0.0 = likely real, 1.0 = likely spoof (printed photo / screen replay).

    Real faces: high LBP variance (many uniform pattern types occupied).
    Spoof faces: low LBP variance (concentrated in a few bins — flat texture).
    """
    if face_roi_bgr is None or face_roi_bgr.size == 0:
        return 0.0

    # Resize to fixed size for consistent histogram
    face = cv2.resize(face_roi_bgr, (64, 64))
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

    hist = _lbp_histogram(gray)

    # Entropy of the histogram — higher entropy → more varied texture → real face
    # Avoid log(0)
    hist_nonzero = hist[hist > 0]
    entropy = -np.sum(hist_nonzero * np.log2(hist_nonzero))

    # Empirically calibrated range: real ≈ 4.5–6.0 bits; spoof ≈ 1.5–3.5 bits
    MAX_ENTROPY = 6.0
    MIN_ENTROPY = 1.5
    score = 1.0 - np.clip(
        (entropy - MIN_ENTROPY) / (MAX_ENTROPY - MIN_ENTROPY), 0.0, 1.0
    )
    return float(score)

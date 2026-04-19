from __future__ import annotations

import cv2
import numpy as np


def detect_presence(roi_gray: np.ndarray, threshold: float) -> tuple[bool, float, np.ndarray]:
    _, bw = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    filled = float(np.count_nonzero(bw)) / bw.size
    return filled >= threshold, filled, bw

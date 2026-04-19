from __future__ import annotations

from typing import Optional

import cv2
import numpy as np


def compare_template(roi_gray: np.ndarray, template_gray: Optional[np.ndarray], threshold: float) -> tuple[bool, float]:
    if template_gray is None:
        return True, 1.0
    if roi_gray.shape != template_gray.shape:
        template_gray = cv2.resize(template_gray, (roi_gray.shape[1], roi_gray.shape[0]))
    score = float(cv2.matchTemplate(roi_gray, template_gray, cv2.TM_CCOEFF_NORMED)[0, 0])
    return score >= threshold, score


def estimate_angle(mask: np.ndarray) -> float:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    largest = max(contours, key=cv2.contourArea)
    if len(largest) < 5:
        return 0.0
    (_, _), (_, _), angle = cv2.fitEllipse(largest)
    return float(angle)

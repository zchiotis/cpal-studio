from __future__ import annotations

from typing import Tuple

import numpy as np


def evaluate_position(center: Tuple[float, float], expected: Tuple[int, int], tolerance_px: int) -> tuple[bool, float, float]:
    dx = float(center[0] - expected[0])
    dy = float(center[1] - expected[1])
    return abs(dx) <= tolerance_px and abs(dy) <= tolerance_px, dx, dy


def globalize_center(local_center: Tuple[float, float], roi: Tuple[int, int, int, int]) -> tuple[float, float]:
    x, y, _, _ = roi
    return local_center[0] + x, local_center[1] + y

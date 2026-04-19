from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


def save_homography(path: Path, matrix: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, matrix)


def load_homography(path: Path) -> Optional[np.ndarray]:
    if not path.exists():
        return None
    return np.load(path)

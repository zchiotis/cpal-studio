from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Optional, Tuple

import cv2
import numpy as np

from .models import CameraConfig

try:
    from picamera2 import Picamera2
except Exception:  # pragma: no cover - fallback for dev machines
    Picamera2 = None


class CameraService:
    def __init__(self, config: CameraConfig):
        self.config = config
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._camera = None

    def start(self) -> None:
        self._running = True
        self._init_camera()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _init_camera(self) -> None:
        if Picamera2 is None:
            self._camera = None
            return

        self._camera = Picamera2()
        width, height = self.config.resolution
        preview_config = self._camera.create_preview_configuration(main={"size": (width, height), "format": "RGB888"})
        self._camera.configure(preview_config)
        controls = {}
        if self.config.exposure_locked:
            controls["AeEnable"] = False
        if self.config.awb_locked:
            controls["AwbEnable"] = False
        if self.config.analogue_gain is not None:
            controls["AnalogueGain"] = float(self.config.analogue_gain)
        if self.config.exposure_time is not None:
            controls["ExposureTime"] = int(self.config.exposure_time)
        if controls:
            self._camera.set_controls(controls)
        self._camera.start()

    def _capture_loop(self) -> None:
        interval = 1.0 / max(1, self.config.framerate)
        while self._running:
            frame = self._capture_frame()
            with self._lock:
                self._latest_frame = frame
            time.sleep(interval)

    def _capture_frame(self) -> np.ndarray:
        if self._camera is None:
            return self._synthetic_frame()
        frame = self._camera.capture_array()
        if frame.ndim == 3 and frame.shape[2] == 3:
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def _synthetic_frame(self) -> np.ndarray:
        width, height = self.config.resolution
        canvas = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(
            canvas,
            "NO CSI CAMERA",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            datetime.utcnow().strftime("%H:%M:%S"),
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return canvas

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def get_jpeg(self, frame: Optional[np.ndarray] = None, quality: int = 80) -> bytes:
        source = frame if frame is not None else self.get_frame()
        if source is None:
            source = self._synthetic_frame()
        ok, buf = cv2.imencode(".jpg", source, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return b""
        return buf.tobytes()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._camera is not None:
            self._camera.stop()
            self._camera.close()

    @property
    def resolution(self) -> Tuple[int, int]:
        return self.config.resolution

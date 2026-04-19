from __future__ import annotations

import threading
from dataclasses import asdict
from typing import Dict

from .models import GPIOConfig

try:
    from gpiozero import DigitalOutputDevice
except Exception:  # pragma: no cover
    DigitalOutputDevice = None


class _DummyOutput:
    def __init__(self, *_args, **_kwargs):
        self.value = 0

    def on(self):
        self.value = 1

    def off(self):
        self.value = 0

    def pulse(self, on_time: float, off_time: float = 0.0, n: int = 1, background: bool = True):
        self.on()
        self.off()

    def close(self):
        self.off()


class GPIOService:
    def __init__(self, config: GPIOConfig, enabled: bool = True):
        self.config = config
        output_cls = DigitalOutputDevice if (enabled and DigitalOutputDevice) else _DummyOutput
        active_high = config.active_high
        self.pick_ok = output_cls(config.pick_ok_pin, active_high=active_high, initial_value=False)
        self.error = output_cls(config.error_pin, active_high=active_high, initial_value=False)
        self.busy = output_cls(config.busy_pin, active_high=active_high, initial_value=False)
        self._lock = threading.Lock()

    def set_busy(self, value: bool) -> None:
        with self._lock:
            self.busy.on() if value else self.busy.off()

    def set_error(self, value: bool) -> None:
        with self._lock:
            self.error.on() if value else self.error.off()

    def pulse_pick_ok(self) -> None:
        pulse_s = max(self.config.pick_ok_pulse_ms, 10) / 1000.0
        with self._lock:
            self.pick_ok.pulse(on_time=pulse_s, off_time=0.0, n=1, background=True)

    def status(self) -> Dict:
        return {
            "config": asdict(self.config),
            "pick_ok": bool(self.pick_ok.value),
            "error": bool(self.error.value),
            "busy": bool(self.busy.value),
        }

    def close(self) -> None:
        self.pick_ok.close()
        self.error.close()
        self.busy.close()

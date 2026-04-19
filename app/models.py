from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

InspectionMode = Literal[
    "presence_only",
    "presence_position",
    "presence_position_orientation",
]


@dataclass
class CameraConfig:
    resolution: Tuple[int, int] = (640, 480)
    framerate: int = 20
    exposure_locked: bool = False
    awb_locked: bool = False
    analogue_gain: Optional[float] = None
    exposure_time: Optional[int] = None


@dataclass
class GPIOConfig:
    pick_ok_pin: int = 17
    error_pin: int = 27
    busy_pin: int = 22
    pick_ok_pulse_ms: int = 200
    active_high: bool = True


@dataclass
class SlotDefinition:
    slot_id: str
    label: str
    roi: Tuple[int, int, int, int]
    expected_center: Tuple[int, int]
    position_tolerance_px: int = 10
    presence_threshold: float = 0.6
    orientation_threshold: float = 0.2
    orientation_mode: str = "moments"
    inspection_mode: InspectionMode = "presence_position"
    required: bool = True
    template_path: Optional[str] = None


@dataclass
class Recipe:
    name: str
    description: str = ""
    camera: CameraConfig = field(default_factory=CameraConfig)
    gpio: GPIOConfig = field(default_factory=GPIOConfig)
    stable_frames_required: int = 4
    inspection_zone: Optional[Tuple[int, int, int, int]] = None
    slots: List[SlotDefinition] = field(default_factory=list)


@dataclass
class SlotInspectionResult:
    slot_id: str
    label: str
    present: bool
    position_ok: bool
    orientation_ok: bool
    dx: float
    dy: float
    score: float
    fail_reason: Optional[str]
    status: str


@dataclass
class InspectionResult:
    recipe_name: str
    timestamp: str
    all_present: bool
    all_position_ok: bool
    all_orientation_ok: bool
    stable_count: int
    final_result: bool
    slots: List[SlotInspectionResult]

    @classmethod
    def create(cls, recipe_name: str, slots: List[SlotInspectionResult], stable_count: int, final_result: bool) -> "InspectionResult":
        all_present = all(slot.present or not slot.fail_reason == "missing_optional" for slot in slots)
        all_position_ok = all(slot.position_ok for slot in slots)
        all_orientation_ok = all(slot.orientation_ok for slot in slots)
        return cls(
            recipe_name=recipe_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            all_present=all_present,
            all_position_ok=all_position_ok,
            all_orientation_ok=all_orientation_ok,
            stable_count=stable_count,
            final_result=final_result,
            slots=slots,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

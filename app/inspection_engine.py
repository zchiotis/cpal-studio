from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Dict, Optional

import cv2
import numpy as np

from .models import InspectionResult, Recipe, SlotInspectionResult
from .vision.geometry import centroid_from_mask, crop_roi, normalize_gray
from .vision.orientation import compare_template
from .vision.position import evaluate_position, globalize_center
from .vision.presence import detect_presence


class InspectionEngine:
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.template_cache: Dict[str, np.ndarray] = {}
        self.stable_pass_count = 0

    def inspect(self, frame: np.ndarray, recipe: Recipe) -> InspectionResult:
        slots_result = []
        for slot in recipe.slots:
            roi = tuple(slot.roi)
            roi_img = crop_roi(frame, roi)
            roi_gray = normalize_gray(roi_img)
            present, fill_score, mask = detect_presence(roi_gray, slot.presence_threshold)
            centroid_local = centroid_from_mask(mask)
            centroid_global = globalize_center(centroid_local, roi) if centroid_local else None

            pos_ok = True
            dx = 0.0
            dy = 0.0
            if slot.inspection_mode in {"presence_position", "presence_position_orientation"} and centroid_global is not None:
                pos_ok, dx, dy = evaluate_position(centroid_global, tuple(slot.expected_center), slot.position_tolerance_px)

            orient_ok = True
            orient_score = 1.0
            if slot.inspection_mode == "presence_position_orientation":
                template = self._load_template(slot.template_path)
                orient_ok, orient_score = compare_template(roi_gray, template, slot.orientation_threshold)

            fail_reason = None
            if not present:
                fail_reason = "missing" if slot.required else "missing_optional"
            elif not pos_ok:
                fail_reason = "position_error"
            elif not orient_ok:
                fail_reason = "orientation_error"

            status = "pass" if fail_reason is None or fail_reason == "missing_optional" else "fail"

            slots_result.append(
                SlotInspectionResult(
                    slot_id=slot.slot_id,
                    label=slot.label,
                    present=present,
                    position_ok=pos_ok,
                    orientation_ok=orient_ok,
                    dx=dx,
                    dy=dy,
                    score=min(fill_score, orient_score),
                    fail_reason=fail_reason,
                    status=status,
                )
            )

        group_pass = all(s.status == "pass" for s in slots_result)
        self.stable_pass_count = self.stable_pass_count + 1 if group_pass else 0
        final = group_pass and self.stable_pass_count >= recipe.stable_frames_required
        return InspectionResult.create(recipe.name, slots_result, self.stable_pass_count, final)

    def _load_template(self, template_path: Optional[str]) -> Optional[np.ndarray]:
        if not template_path:
            return None
        if template_path in self.template_cache:
            return self.template_cache[template_path]
        path = self.template_dir / template_path
        if not path.exists():
            return None
        template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if template is not None:
            self.template_cache[template_path] = template
        return template

    def build_overlay(self, frame: np.ndarray, recipe: Recipe, result: InspectionResult) -> np.ndarray:
        drawn = frame.copy()
        slot_result_map = {s.slot_id: s for s in result.slots}
        for slot in recipe.slots:
            x, y, w, h = slot.roi
            sres = slot_result_map.get(slot.slot_id)
            color = (0, 255, 0) if sres and sres.status == "pass" else (0, 0, 255)
            cv2.rectangle(drawn, (x, y), (x + w, y + h), color, 2)
            cv2.putText(drawn, f"{slot.label}:{sres.status if sres else 'n/a'}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        banner = "PASS" if result.final_result else "WAIT/FAIL"
        cv2.putText(drawn, f"{recipe.name} | {banner} | stable={result.stable_count}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        return drawn

    def save_slot_template(self, frame: np.ndarray, recipe: Recipe) -> None:
        for slot in recipe.slots:
            roi = tuple(slot.roi)
            template_name = slot.template_path or f"{recipe.name}_{slot.slot_id}.png"
            roi_img = crop_roi(frame, roi)
            gray = normalize_gray(roi_img)
            cv2.imwrite(str(self.template_dir / template_name), gray)
            slot.template_path = template_name

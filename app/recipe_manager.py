from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from .models import CameraConfig, GPIOConfig, Recipe, SlotDefinition


class RecipeManager:
    def __init__(self, recipe_dir: Path, template_dir: Path):
        self.recipe_dir = recipe_dir
        self.template_dir = template_dir
        self.recipe_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def list_recipes(self) -> List[str]:
        return sorted(path.stem for path in self.recipe_dir.glob("*.json"))

    def get(self, name: str) -> Optional[Recipe]:
        path = self.recipe_dir / f"{name}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return self._from_dict(data)

    def save(self, recipe: Recipe) -> Path:
        path = self.recipe_dir / f"{recipe.name}.json"
        payload = asdict(recipe)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return path

    def delete(self, name: str) -> None:
        path = self.recipe_dir / f"{name}.json"
        if path.exists():
            path.unlink()

    def _from_dict(self, data: Dict) -> Recipe:
        camera = CameraConfig(**data.get("camera", {}))
        gpio = GPIOConfig(**data.get("gpio", {}))
        slots = [SlotDefinition(**slot) for slot in data.get("slots", [])]
        return Recipe(
            name=data["name"],
            description=data.get("description", ""),
            camera=camera,
            gpio=gpio,
            stable_frames_required=data.get("stable_frames_required", 4),
            inspection_zone=tuple(data["inspection_zone"]) if data.get("inspection_zone") else None,
            slots=slots,
        )

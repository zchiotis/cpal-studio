from __future__ import annotations

import signal
import threading
import time
from pathlib import Path
from typing import Dict

import cv2
from flask import Flask

from .camera_service import CameraService
from .gpio_service import GPIOService
from .inspection_engine import InspectionEngine
from .models import CameraConfig, GPIOConfig
from .recipe_manager import RecipeManager
from .result_logger import ResultLogger
from .utils import DEFAULT_CONFIG_PATH, ensure_runtime_dirs, load_json, setup_logging
from .web import bp as web_bp


def create_app(config_path: Path | None = None) -> Flask:
    path = config_path or DEFAULT_CONFIG_PATH
    raw_config = load_json(path)
    ensure_runtime_dirs(raw_config)
    logger = setup_logging(Path(raw_config["paths"]["logs"]))

    camera = CameraService(CameraConfig(**raw_config["camera"]))
    recipes = RecipeManager(Path(raw_config["paths"]["recipes"]), Path(raw_config["paths"]["templates"]))
    gpio = GPIOService(GPIOConfig(**raw_config["gpio"]), enabled=raw_config["gpio"].get("enabled", True))
    engine = InspectionEngine(Path(raw_config["paths"]["templates"]))
    result_logger = ResultLogger(Path(raw_config["paths"]["db"]))

    state: Dict = {
        "armed": False,
        "system_state": "idle",
        "recipe": raw_config.get("inspection", {}).get("active_recipe"),
        "last_result": None,
        "overlay_frame": None,
    }

    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    app.register_blueprint(web_bp)
    app.config["services"] = {
        "camera": camera,
        "recipes": recipes,
        "gpio": gpio,
        "engine": engine,
        "logger": result_logger,
        "raw_config": raw_config,
        "config_path": path,
        "state": state,
    }

    camera.start()
    worker = threading.Thread(target=_inspection_loop, args=(app,), daemon=True)
    worker.start()

    def _graceful_shutdown(*_args):
        logger.info("Shutdown signal received")
        state["armed"] = False
        gpio.set_busy(False)
        camera.stop()
        gpio.close()

    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    return app


def _inspection_loop(app: Flask) -> None:
    with app.app_context():
        s = app.config["services"]
        cfg = s["raw_config"]
        snapshot_dir = Path(cfg["paths"]["snapshots"])

        while True:
            frame = s["camera"].get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            if not s["state"].get("armed"):
                s["state"]["overlay_frame"] = frame
                time.sleep(0.05)
                continue

            s["gpio"].set_busy(True)
            s["state"]["system_state"] = "inspecting"
            recipe_name = s["state"].get("recipe")
            recipe = s["recipes"].get(recipe_name) if recipe_name else None
            if recipe is None:
                s["state"]["system_state"] = "recipe_missing"
                s["gpio"].set_error(True)
                time.sleep(0.2)
                continue

            if recipe.inspection_zone:
                x, y, w, h = recipe.inspection_zone
                frame = frame[y : y + h, x : x + w]

            result = s["engine"].inspect(frame, recipe)
            overlay = s["engine"].build_overlay(frame, recipe, result)
            s["state"]["overlay_frame"] = overlay
            s["state"]["last_result"] = result.to_dict()
            s["logger"].log_result(result.to_dict())

            if result.final_result:
                s["gpio"].set_error(False)
                s["gpio"].pulse_pick_ok()
                s["state"]["system_state"] = "pass"
            else:
                fail = any(slot["status"] == "fail" for slot in result.to_dict()["slots"])
                s["gpio"].set_error(fail)
                s["state"]["system_state"] = "fail" if fail else "inspecting"
                if fail and cfg["inspection"].get("save_fail_snapshots", True):
                    snap_name = f"fail_{int(time.time() * 1000)}.jpg"
                    cv2.imwrite(str(snapshot_dir / snap_name), overlay)

            time.sleep(0.02)


def main() -> None:
    app = create_app()
    cfg = app.config["services"]["raw_config"]["server"]
    app.run(host=cfg["host"], port=cfg["port"], debug=cfg.get("debug", False), threaded=True)


if __name__ == "__main__":
    main()

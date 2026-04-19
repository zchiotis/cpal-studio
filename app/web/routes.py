from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import cv2
from flask import Response, current_app, jsonify, redirect, render_template, request, url_for

from . import bp
from ..models import CameraConfig, GPIOConfig, Recipe, SlotDefinition


def _services():
    return current_app.config["services"]


@bp.route("/")
def dashboard():
    s = _services()
    return render_template(
        "dashboard.html",
        recipe=s["state"]["recipe"],
        last_result=s["state"]["last_result"],
        system_state=s["state"]["system_state"],
    )


@bp.route("/health")
def health():
    s = _services()
    return jsonify({"status": "ok", "recipe": s["state"]["recipe"], "ts": datetime.now(timezone.utc).isoformat()})


@bp.route("/stream.mjpg")
def stream():
    s = _services()

    def generate():
        while True:
            frame = s["state"].get("overlay_frame") or s["camera"].get_frame()
            jpeg = s["camera"].get_jpeg(frame)
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
            time.sleep(0.05)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@bp.route("/api/state")
def api_state():
    s = _services()
    return jsonify(
        {
            "recipe": s["state"]["recipe"],
            "system_state": s["state"]["system_state"],
            "last_result": s["state"]["last_result"],
            "gpio": s["gpio"].status(),
        }
    )


@bp.route("/teach", methods=["GET", "POST"])
def teach():
    s = _services()
    manager = s["recipes"]

    if request.method == "POST":
        payload = request.get_json(force=True)
        name = payload["name"]
        slots = [SlotDefinition(**slot) for slot in payload.get("slots", [])]
        recipe = Recipe(
            name=name,
            description=payload.get("description", ""),
            camera=CameraConfig(**payload.get("camera", {})),
            gpio=GPIOConfig(**payload.get("gpio", {})),
            stable_frames_required=int(payload.get("stable_frames_required", 4)),
            inspection_zone=tuple(payload["inspection_zone"]) if payload.get("inspection_zone") else None,
            slots=slots,
        )
        frame = s["camera"].get_frame()
        if frame is not None:
            s["engine"].save_slot_template(frame, recipe)
        manager.save(recipe)
        return jsonify({"saved": True, "recipe": recipe.name})

    return render_template("teach.html", recipe_names=manager.list_recipes())


@bp.route("/recipes", methods=["GET", "POST"])
def recipes():
    s = _services()
    manager = s["recipes"]
    if request.method == "POST":
        selected = request.form.get("recipe_name", "")
        if selected:
            s["state"]["recipe"] = selected
        return redirect(url_for("web.recipes"))

    recipes_data = []
    for name in manager.list_recipes():
        rec = manager.get(name)
        if rec:
            recipes_data.append(rec)
    return render_template("recipes.html", recipes=recipes_data, active_recipe=s["state"]["recipe"])


@bp.route("/recipes/<name>", methods=["GET"])
def recipe_edit(name: str):
    s = _services()
    rec = s["recipes"].get(name)
    if rec is None:
        return redirect(url_for("web.recipes"))
    return render_template("recipe_edit.html", recipe=asdict(rec))


@bp.route("/recipes/<name>/delete", methods=["POST"])
def delete_recipe(name: str):
    s = _services()
    s["recipes"].delete(name)
    if s["state"]["recipe"] == name:
        s["state"]["recipe"] = None
    return redirect(url_for("web.recipes"))


@bp.route("/logs")
def logs():
    s = _services()
    rows = s["logger"].get_latest(limit=100)
    return render_template("logs.html", rows=rows)


@bp.route("/io")
def io_page():
    s = _services()
    return render_template("io.html", io=s["gpio"].status())


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    s = _services()
    config_path: Path = s["config_path"]
    config = s["raw_config"]
    if request.method == "POST":
        config["inspection"]["enabled"] = request.form.get("enabled") == "on"
        config["inspection"]["save_fail_snapshots"] = request.form.get("save_fail_snapshots") == "on"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return redirect(url_for("web.settings"))
    return render_template("settings.html", config=config)


@bp.route("/api/arm", methods=["POST"])
def arm():
    s = _services()
    s["state"]["armed"] = True
    s["state"]["system_state"] = "armed"
    return jsonify({"armed": True})


@bp.route("/api/disarm", methods=["POST"])
def disarm():
    s = _services()
    s["state"]["armed"] = False
    s["state"]["system_state"] = "idle"
    s["gpio"].set_busy(False)
    return jsonify({"armed": False})

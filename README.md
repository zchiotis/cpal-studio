# Machine Vision Pi (Raspberry Pi 3B)

Production-oriented Flask + OpenCV inspection appliance for conveyor pick validation using a CSI camera (Picamera2), GPIO outputs, and recipe-based ROI teach mode.

## Features

- ROI-first deterministic inspection pipeline (presence, position, orientation checks).
- Web HMI for operators: dashboard, teach, recipes, logs, I/O, settings.
- GPIO handshaking with PLC/robot:
  - GPIO17 = PICK_OK pulse (default 200 ms)
  - GPIO27 = ERROR
  - GPIO22 = BUSY
- SQLite result logging.
- Per-slot fail reasons and optional fail snapshots.
- Native Raspberry Pi deployment first; Docker artifacts included for future use.

## Project Structure

```text
config/
  app_config.json
data/
  recipes/
  templates/
  calibration/
  snapshots/
  logs/
app/
  main.py
  camera_service.py
  inspection_engine.py
  gpio_service.py
  recipe_manager.py
  result_logger.py
  models.py
  utils.py
  vision/
  web/
systemd/
  machine-vision.service
docker/
  Dockerfile
  docker-compose.yml
```

## Raspberry Pi OS Setup (Native Target)

1. Install packages:
   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-dev libatlas-base-dev libopenjp2-7 libtiff5
   ```
2. Clone repository to target folder, example `/opt/machine-vision-pi`.
3. Create venv and install dependencies:
   ```bash
   cd /opt/machine-vision-pi
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Verify CSI camera:
   ```bash
   libcamera-hello
   ```
5. Run app:
   ```bash
   python -m app.main
   ```
6. Open from LAN browser: `http://<pi-ip>:5000`.

## systemd Autostart

```bash
sudo cp systemd/machine-vision.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable machine-vision
sudo systemctl start machine-vision
sudo systemctl status machine-vision
```

## Update Procedure

```bash
cd /opt/machine-vision-pi
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart machine-vision
```

## Teach Workflow

1. Open **Teach** page.
2. Draw slot ROIs over live stream.
3. Save recipe.
4. Template snapshots are automatically captured from current frame.
5. Activate recipe in **Recipes** page.
6. Arm from **Dashboard**.

## Inspection Logic Summary

- Process only configured ROIs.
- Presence: Otsu threshold + filled area ratio.
- Position: centroid vs taught center with tolerance.
- Orientation: ROI template match score threshold.
- Debounce: `stable_frames_required` consecutive full-pass frames required before OK pulse.

## Configuration

Global config: `config/app_config.json`
- camera defaults
- GPIO mapping
- active recipe
- path locations

Recipes are JSON files in `data/recipes/` and include slot definitions, tolerances, camera/gpio overrides, and debounce settings.

## Health Endpoint

`GET /health` returns JSON system status for supervisor/monitoring integration.

## Notes for Docker (Secondary)

Docker files are included in `docker/` for future portability. Native install remains the primary production mode for Raspberry Pi GPIO + CSI camera access.

## Known Extension Points

- Per-recipe camera controls override at runtime.
- PLC cycle handshake with rising-edge trigger inputs.
- Calibration UI and homography-based rectification.
- More robust orientation checks for symmetric parts.

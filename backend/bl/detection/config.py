import os
from pathlib import Path

# backend/bl/detection/config.py → repo root is parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = _REPO_ROOT / "trained_model" / "guardian_backend_model.onnx"
NAMES_PATH = MODEL_PATH.parent / "names.txt"
PERSON_MODEL_PATH = _REPO_ROOT / "trained_model" / "yolov8n_person.onnx"
INPUT_SIZE = 640

# Matches ultralytics' own model.predict() defaults (conf=0.25, iou=0.7), so live detections
# match what the training notebook's evaluate_threat()/report video showed on the same footage.
WEAPON_CONF_THRESHOLD = float(os.environ.get("GUARDIAN_WEAPON_CONF_THRESHOLD", "0.25"))
WEAPON_IOU_THRESHOLD = float(os.environ.get("GUARDIAN_WEAPON_IOU_THRESHOLD", "0.7"))

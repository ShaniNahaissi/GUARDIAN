import os
from pathlib import Path

# backend/bl/detection/config.py → repo root is parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = _REPO_ROOT / "trained_model" / "guardian_backend_model.onnx"
NAMES_PATH = MODEL_PATH.parent / "names.txt"
PERSON_MODEL_PATH = _REPO_ROOT / "trained_model" / "yolov8n_person.onnx"
# Second, independently-trained weapon model (guns/knife) ensembled with the primary detector for
# higher recall -- see JoaoAssalim/Weapons-and-Knives-Detector-with-YOLOv8 (MIT), which ships a
# ready-to-use ONNX export. Optional: pipeline runs fine without it if the file is missing.
SECONDARY_WEAPON_MODEL_PATH = _REPO_ROOT / "trained_model" / "external" / "weapon_secondary.onnx"
INPUT_SIZE = 640

# Matches ultralytics' own model.predict() defaults (conf=0.25, iou=0.7), so live detections
# match what the training notebook's evaluate_threat()/report video showed on the same footage.
WEAPON_CONF_THRESHOLD = float(os.environ.get("GUARDIAN_WEAPON_CONF_THRESHOLD", "0.25"))
WEAPON_IOU_THRESHOLD = float(os.environ.get("GUARDIAN_WEAPON_IOU_THRESHOLD", "0.7"))

# CLAHE contrast boost + unsharp-mask sharpening applied only to the frame fed into the detector
# model (never to the frame shown to viewers) -- see YoloOnnxDetector._preprocess.
ENHANCE_DETECTION_INPUT = os.environ.get("GUARDIAN_ENHANCE_DETECTION_INPUT", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

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

# CLAHE contrast boost + unsharp-mask sharpening applied only to the frame fed into the detector
# model (never to the frame shown to viewers) -- see YoloOnnxDetector._preprocess.
ENHANCE_DETECTION_INPUT = os.environ.get("GUARDIAN_ENHANCE_DETECTION_INPUT", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)

# --- Pipeline tuning knobs (added for stability fixes) ------------------------------------

# Minimum temporal-action-classifier confidence required to override a Suspect's label with an
# active threat classification (Shooting/Violence). Lower = more sensitive but more false positives.
ACTION_CONF_THRESHOLD = float(os.environ.get("GUARDIAN_ACTION_CONF_THRESHOLD", "0.50"))

# EMA smoothing factor for bounding box coordinates (0.0 = full history, 1.0 = raw/no smoothing).
# 0.6 gives ~60% weight to the latest detection, 40% to the running average — enough to tame
# frame-to-frame jitter without introducing perceptible lag.
BBOX_SMOOTH_ALPHA = float(os.environ.get("GUARDIAN_BBOX_SMOOTH_ALPHA", "0.6"))

# How many consecutive missed-detection frames a weapon (Gun/Knife) track survives before being
# dropped. Weapons are small and intermittently detected; 0 (the old default) kills them instantly.
WEAPON_GHOST_FRAMES = int(os.environ.get("GUARDIAN_WEAPON_GHOST_FRAMES", "3"))

# Same as above but for Suspect tracks. Suspects are larger and more reliably detected, but still
# benefit from brief persistence through momentary occlusions.
SUSPECT_GHOST_FRAMES = int(os.environ.get("GUARDIAN_SUSPECT_GHOST_FRAMES", "5"))

# Confidence decay multiplier applied per missed frame (ghost tracks). 0.85 = 15% decay per frame,
# gentler than the old 0.7 (30%) which injected too much noise into temporal feature vectors.
CONFIDENCE_DECAY = float(os.environ.get("GUARDIAN_CONFIDENCE_DECAY", "0.85"))

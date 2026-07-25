from pathlib import Path

# backend/bl/detection/config.py → repo root is parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = _REPO_ROOT / "trained_model" / "guardian_backend_model.onnx"
NAMES_PATH = MODEL_PATH.parent / "names.txt"
PERSON_MODEL_PATH = _REPO_ROOT / "trained_model" / "yolov8n_person.onnx"
INPUT_SIZE = 640

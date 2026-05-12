import os

from bl.detection.config import NAMES_PATH


def load_class_names() -> dict[int, str]:
    names: dict[int, str] = {}
    raw = os.environ.get("GUARDIAN_CLASS_NAMES", "").strip()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if ":" not in part:
                continue
            key, val = part.split(":", 1)
            try:
                names[int(key.strip())] = val.strip()
            except ValueError:
                continue
    if NAMES_PATH.exists():
        for i, line in enumerate(NAMES_PATH.read_text(encoding="utf-8").splitlines()):
            line = line.strip()
            if line:
                names.setdefault(i, line)
    return names

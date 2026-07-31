from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bl.detection.yolo import YoloOnnxDetector

detector: YoloOnnxDetector | None = None
person_detector: YoloOnnxDetector | None = None
secondary_weapon_detector: YoloOnnxDetector | None = None
CLASS_NAMES: dict[int, str] = {}

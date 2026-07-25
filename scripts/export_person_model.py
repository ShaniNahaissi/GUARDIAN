"""One-off offline export: pretrained YOLOv8n -> ONNX for person detection.

Switched from YOLOv8s to YOLOv8n (nano): the pipeline runs this model on every
frame just to catch people the weapon detector misses, so its cost is pure
overhead relative to the weapon detector -- the nano variant is roughly a
third of the small variant's compute for the one class (COCO id 0, person)
this pipeline actually keeps (see pipeline.py's _merge_detections).

Not a runtime dependency of the backend (ultralytics/torch stay out of
backend/requirements.txt). Run locally once:

    pip install ultralytics
    python scripts/export_person_model.py

If this fails with `ImportError: libxcb.so.1` (or similar) on import cv2,
ultralytics pulled in the GUI opencv-python build transitively, which needs
X11 libs most training/export containers don't have. Fix by forcing the
headless build back in afterward:

    pip uninstall -y opencv-python opencv-python-headless
    pip install --force-reinstall --no-deps opencv-python-headless

Then move the resulting yolov8n.onnx to trained_model/yolov8n_person.onnx
(replacing the old yolov8s_person.onnx -- also update/delete that file, since
config.py now points at the yolov8n_person.onnx path).
"""

from ultralytics import YOLO

if __name__ == "__main__":
    YOLO("yolov8n.pt").export(format="onnx", imgsz=640, opset=12)

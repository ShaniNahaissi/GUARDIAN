"""One-off offline export: pretrained YOLOv8s -> ONNX for person detection.

Not a runtime dependency of the backend (ultralytics/torch stay out of
backend/requirements.txt). Run locally once:

    pip install ultralytics
    python scripts/export_person_model.py

Then move the resulting yolov8s.onnx to trained_model/yolov8s_person.onnx.
"""

from ultralytics import YOLO

if __name__ == "__main__":
    YOLO("yolov8s.pt").export(format="onnx", imgsz=640, opset=12)

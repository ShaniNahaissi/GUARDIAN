#!/usr/bin/env python3
"""Diagnoses whether ONNX Runtime is actually running the detectors on GPU.

`ort.get_available_providers()` only reports what the installed onnxruntime *build* was
compiled with -- it can list "CUDAExecutionProvider" even when the matching CUDA/cuDNN
shared libraries aren't actually present, in which case session creation silently falls back
to CPU. This script checks both: the build's advertised providers, and what a real
InferenceSession for Guardian's own detector actually negotiates -- plus a wall-clock timing
so "is this fast" has a concrete number instead of a guess.

Run from inside temporal_training/: `python check_gpu.py`
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import onnxruntime as ort

from detection import MODEL_PATH, PERSON_MODEL_PATH, YoloOnnxDetector, load_class_names


def _check_one(label: str, model_path: Path, class_names: dict[int, str]) -> None:
    print(f"\n--- {label}: {model_path.name} ---")
    if not model_path.exists():
        print(f"  SKIPPED: file not found at {model_path}")
        return

    det = YoloOnnxDetector(model_path, class_names)
    providers_used = det.session.get_providers()
    print(f"  Providers actually in use: {providers_used}")

    if "CUDAExecutionProvider" in providers_used:
        print("  -> GPU is active for this model. Good.")
    else:
        print("  -> Running on CPU. This is almost certainly why things are slow.")

    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    for _ in range(3):
        det.predict(frame)  # warmup (session/provider init, memory allocation)

    n = 20
    t0 = time.perf_counter()
    for _ in range(n):
        det.predict(frame)
    elapsed_ms = (time.perf_counter() - t0) * 1000 / n
    print(f"  Avg inference+postprocess time: {elapsed_ms:.1f} ms/frame ({n} frames)")
    if elapsed_ms > 200:
        print("  -> That's slow for a single YOLOv8-sized model call. Expect ~5-30ms on a "
              "real GPU, vs. hundreds of ms+ on CPU.")


def main() -> None:
    print(f"onnxruntime version: {ort.__version__}")
    available = ort.get_available_providers()
    print(f"Available providers (compiled into this onnxruntime build): {available}")

    if "CUDAExecutionProvider" not in available:
        print(
            "\nCUDAExecutionProvider is NOT in the available providers list -- the installed "
            "'onnxruntime' package is CPU-only. Fix: uninstall it and install 'onnxruntime-gpu' "
            "matched to the container's CUDA version instead:\n"
            "    pip uninstall -y onnxruntime onnxruntime-gpu\n"
            "    pip install onnxruntime-gpu\n"
            "Also confirm the GPU is visible at all: `nvidia-smi` should list it from inside "
            "this same container/environment."
        )
        return

    print("CUDAExecutionProvider is available in this build -- checking real sessions below.")
    _check_one("Primary detector", MODEL_PATH, load_class_names())
    _check_one("Person detector", PERSON_MODEL_PATH, {0: "person"})


if __name__ == "__main__":
    main()

import os

import onnxruntime as ort


def select_onnx_providers() -> list[str]:
    want_cuda = os.environ.get("GUARDIAN_ORT_CUDA", "1").strip().lower() not in ("0", "false", "no")
    available = ort.get_available_providers()
    providers: list[str] = []
    if want_cuda and "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    if "TensorrtExecutionProvider" in available and os.environ.get("GUARDIAN_ORT_TRT", "").strip() == "1":
        providers.append("TensorrtExecutionProvider")
    providers.append("CPUExecutionProvider")
    return providers

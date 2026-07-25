#!/usr/bin/env bash
# Fixes "ImportError: libcudart.so.13: cannot open shared object file" after
# `pip install onnxruntime-gpu` -- as of onnxruntime 1.27, the default PyPI wheel is linked
# against CUDA 13, but `nvidia-smi` reporting "CUDA Version: 13.0" only means the driver
# *supports up to* CUDA 13 -- it does not mean the CUDA 13 userspace runtime libraries are
# installed in this container. The CUDA-13 pip package ecosystem (nvidia-*-cu13) is also
# still mid-transition (some packages deprecated in favor of unsuffixed ones), so this pins
# onnxruntime-gpu back to a mature CUDA-12-linked build instead -- NVIDIA drivers are
# backward compatible with older CUDA runtimes, so this works fine on a CUDA-13-capable driver.
#
# Usage: bash fix_onnxruntime_gpu.sh
set -euo pipefail

echo "==> Removing existing onnxruntime / onnxruntime-gpu and any CUDA 13 pip runtime packages"
pip uninstall -y onnxruntime onnxruntime-gpu \
    nvidia-cuda-runtime-cu13 nvidia-cublas-cu13 nvidia-cudnn-cu13 nvidia-cudss-cu13 nvidia-nccl-cu13 \
    >/dev/null 2>&1 || true

echo "==> Installing onnxruntime-gpu==1.22.0 (CUDA 12-linked) + matching CUDA 12 runtime libs"
pip install -q \
    "onnxruntime-gpu==1.22.0" \
    "nvidia-cuda-runtime-cu12" \
    "nvidia-cublas-cu12" \
    "nvidia-cudnn-cu12"

echo "==> Locating installed CUDA 12 library directories"
LIB_DIRS="$(python3 - <<'EOF'
import importlib.util
import os

dirs = []
for pkg in ("nvidia.cuda_runtime", "nvidia.cublas", "nvidia.cudnn"):
    spec = importlib.util.find_spec(pkg)
    if not spec or not spec.submodule_search_locations:
        continue
    lib_dir = os.path.join(list(spec.submodule_search_locations)[0], "lib")
    if os.path.isdir(lib_dir):
        dirs.append(lib_dir)
print(":".join(dirs))
EOF
)"

if [ -z "$LIB_DIRS" ]; then
    echo "WARNING: could not auto-locate the nvidia CUDA lib directories."
    echo "Find them manually, e.g.: python3 -c \"import nvidia.cudnn, os; print(os.path.dirname(nvidia.cudnn.__file__))\""
else
    export LD_LIBRARY_PATH="$LIB_DIRS:${LD_LIBRARY_PATH:-}"
    echo "==> LD_LIBRARY_PATH set for THIS shell:"
    echo "    $LD_LIBRARY_PATH"
    echo ""
    echo "IMPORTANT: this only applies to the current shell. Jupyter kernels (and any new"
    echo "shell) won't see it unless you also add this line to ~/.bashrc (or wherever your"
    echo "container sets env vars) and restart the kernel/shell:"
    echo ""
    echo "    export LD_LIBRARY_PATH=\"$LIB_DIRS:\$LD_LIBRARY_PATH\""
fi

echo ""
echo "==> Verifying"
python3 check_gpu.py

"""1D-CNN temporal action classifier: PyTorch training model + a zero-dependency NumPy
mirror for offline validation, mirroring the style of
backend/bl/detection/temporal_action.py's NumPyGRUClassifier without touching that
(production) file.

Chosen over a GRU per the task brief's own preference order (1D CNN first, GRU only "if it
has a strong reason") and because it trains more easily: fully parallel across the 30-step
sequence (no BPTT), simpler loss landscape, no gate equations to get subtly wrong when
hand-porting to NumPy. Promoting this model into the live pipeline (swapping
backend/bl/detection/pipeline.py's classifier) is an intentional, separate follow-up -- not
done automatically here, since it changes production inference behavior.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    torch = None
    nn = None
    F = None

INPUT_DIM = 12
HIDDEN_CHANNELS = 32
NUM_CLASSES = 3  # Normal, Shooting, Violence -- Stabbing dropped, see detection.py's ACTION_CLASSES
KERNEL_SIZE = 5


if torch is not None:
    class TemporalCNNClassifier(nn.Module):
        """PyTorch training model: two same-padded Conv1d layers over the time axis,
        global-average-pooled, then a linear classifier head."""

        def __init__(self, input_dim: int = INPUT_DIM, hidden_channels: int = HIDDEN_CHANNELS, num_classes: int = NUM_CLASSES) -> None:
            super().__init__()
            pad = KERNEL_SIZE // 2
            self.conv1 = nn.Conv1d(input_dim, hidden_channels, kernel_size=KERNEL_SIZE, padding=pad)
            self.conv2 = nn.Conv1d(hidden_channels, hidden_channels, kernel_size=KERNEL_SIZE, padding=pad)
            self.fc = nn.Linear(hidden_channels, num_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x: (batch, seq_len, input_dim) -> (batch, input_dim, seq_len)
            x = x.transpose(1, 2)
            x = F.relu(self.conv1(x))
            x = F.relu(self.conv2(x))
            x = x.mean(dim=2)
            return self.fc(x)
else:
    class TemporalCNNClassifier:  # pragma: no cover - torch not installed
        pass


def export_to_numpy_weights_cnn(model, output_path: Path) -> None:
    """Exports trained PyTorch conv1d/fc weights to a NumPy-compatible .npz file, loadable
    by NumPyCNNClassifier below."""
    state_dict = model.state_dict()
    np.savez_compressed(
        output_path,
        conv1_w=state_dict["conv1.weight"].cpu().numpy(),  # (hidden, in, kernel)
        conv1_b=state_dict["conv1.bias"].cpu().numpy(),
        conv2_w=state_dict["conv2.weight"].cpu().numpy(),  # (hidden, hidden, kernel)
        conv2_b=state_dict["conv2.bias"].cpu().numpy(),
        fc_w=state_dict["fc.weight"].cpu().numpy(),        # (num_classes, hidden)
        fc_b=state_dict["fc.bias"].cpu().numpy(),
    )


def conv1d_same(x: np.ndarray, w: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Same-padding 1D convolution, stride 1. x: (in_ch, seq_len), w: (out_ch, in_ch, kernel),
    b: (out_ch,) -> (out_ch, seq_len)."""
    out_ch, in_ch, kernel = w.shape
    pad = kernel // 2
    seq_len = x.shape[1]
    x_padded = np.pad(x, ((0, 0), (pad, pad)))
    out = np.empty((out_ch, seq_len), dtype=np.float32)
    for t in range(seq_len):
        window = x_padded[:, t:t + kernel]  # (in_ch, kernel)
        out[:, t] = np.tensordot(w, window, axes=([1, 2], [0, 1])) + b
    return out


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


class NumPyCNNClassifier:
    """Zero-dependency NumPy mirror of TemporalCNNClassifier. Loads exported weights when a
    path is given; otherwise initializes deterministic (seed-42) random weights, matching the
    fallback behavior of NumPyGRUClassifier in backend/bl/detection/temporal_action.py."""

    def __init__(self, weights_path: Path | None = None) -> None:
        if weights_path is not None:
            data = np.load(weights_path)
            self.conv1_w, self.conv1_b = data["conv1_w"], data["conv1_b"]
            self.conv2_w, self.conv2_b = data["conv2_w"], data["conv2_b"]
            self.fc_w, self.fc_b = data["fc_w"], data["fc_b"]
        else:
            rng = np.random.default_rng(42)
            self.conv1_w = rng.normal(0, 0.1, (HIDDEN_CHANNELS, INPUT_DIM, KERNEL_SIZE)).astype(np.float32)
            self.conv1_b = np.zeros(HIDDEN_CHANNELS, dtype=np.float32)
            self.conv2_w = rng.normal(0, 0.1, (HIDDEN_CHANNELS, HIDDEN_CHANNELS, KERNEL_SIZE)).astype(np.float32)
            self.conv2_b = np.zeros(HIDDEN_CHANNELS, dtype=np.float32)
            self.fc_w = rng.normal(0, 0.1, (NUM_CLASSES, HIDDEN_CHANNELS)).astype(np.float32)
            self.fc_b = np.zeros(NUM_CLASSES, dtype=np.float32)

    def forward(self, seq: np.ndarray) -> np.ndarray:
        """seq shape: (seq_len, input_dim) -> class probabilities, shape (num_classes,)."""
        x = np.ascontiguousarray(seq.T, dtype=np.float32)  # (input_dim, seq_len)
        x = _relu(conv1d_same(x, self.conv1_w, self.conv1_b))
        x = _relu(conv1d_same(x, self.conv2_w, self.conv2_b))
        pooled = x.mean(axis=1)  # (hidden_channels,)
        logits = self.fc_w @ pooled + self.fc_b
        exp_logits = np.exp(logits - np.max(logits))  # stable softmax
        return exp_logits / np.sum(exp_logits)

    def predict(self, seq: np.ndarray) -> tuple[int, float]:
        probs = self.forward(seq)
        cls_idx = int(np.argmax(probs))
        return cls_idx, float(probs[cls_idx])

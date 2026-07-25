"""Plain assert-based smoke test for model.py's NumPy conv1d port -- runs locally with no
PyTorch/GPU installed. Run directly: `python test_model.py`.

Full PyTorch<->NumPy numerical parity (export -> reload -> compare on real trained weights)
is checked in temporal_training.ipynb's inference-examples cell, where torch is actually
available (remote GPU server)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import model as m  # noqa: E402


def test_conv1d_same_hand_computed() -> None:
    # 1 input channel, 1 output channel, kernel=3, identity-ish: picks out the center tap.
    x = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)  # (in_ch=1, seq_len=4)
    w = np.array([[[0.0, 1.0, 0.0]]], dtype=np.float32)     # (out_ch=1, in_ch=1, kernel=3)
    b = np.array([0.0], dtype=np.float32)
    out = m.conv1d_same(x, w, b)
    np.testing.assert_allclose(out, [[1.0, 2.0, 3.0, 4.0]])  # center tap => passthrough

    # Sum-of-window kernel with a bias.
    w_sum = np.array([[[1.0, 1.0, 1.0]]], dtype=np.float32)
    b_sum = np.array([10.0], dtype=np.float32)
    out_sum = m.conv1d_same(x, w_sum, b_sum)
    # same-padding zeros at the edges: [0+1+2, 1+2+3, 2+3+4, 3+4+0] + 10
    np.testing.assert_allclose(out_sum, [[13.0, 16.0, 19.0, 17.0]])


def test_numpy_cnn_classifier_shapes_and_probabilities() -> None:
    clf = m.NumPyCNNClassifier()  # deterministic random-init fallback
    seq = np.random.default_rng(0).normal(size=(30, 12)).astype(np.float32)

    probs = clf.forward(seq)
    assert probs.shape == (m.NUM_CLASSES,)
    assert np.all(probs >= 0.0)
    np.testing.assert_allclose(probs.sum(), 1.0, atol=1e-5)

    cls_idx, score = clf.predict(seq)
    assert 0 <= cls_idx < m.NUM_CLASSES
    assert np.isclose(score, probs[cls_idx])

    # Deterministic seed => same input always yields the same prediction.
    clf2 = m.NumPyCNNClassifier()
    np.testing.assert_allclose(clf2.forward(seq), probs)


def test_export_import_roundtrip(tmp_path=None) -> None:
    import tempfile

    clf = m.NumPyCNNClassifier()
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "weights.npz"
        np.savez_compressed(
            out_path,
            conv1_w=clf.conv1_w, conv1_b=clf.conv1_b,
            conv2_w=clf.conv2_w, conv2_b=clf.conv2_b,
            fc_w=clf.fc_w, fc_b=clf.fc_b,
        )
        reloaded = m.NumPyCNNClassifier(weights_path=out_path)

    seq = np.random.default_rng(1).normal(size=(30, 12)).astype(np.float32)
    np.testing.assert_allclose(clf.forward(seq), reloaded.forward(seq))


if __name__ == "__main__":
    test_conv1d_same_hand_computed()
    test_numpy_cnn_classifier_shapes_and_probabilities()
    test_export_import_roundtrip()
    print("OK: all model.py smoke tests passed")

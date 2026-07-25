"""Plain assert-based smoke test for dataset_builder.py's pure logic (category mapping,
history/stride sampling gate) -- runs locally with no GPU, real dataset, or the YOLO/
supervision stack installed. Run directly: `python test_dataset_builder.py`."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dataset_builder as db  # noqa: E402


def test_category_mapping() -> None:
    assert db._classify_category("Normal Videos") == "Normal"
    assert db._classify_category("Fighting") == "Violence"
    assert db._classify_category("Assault") == "Violence"
    assert db._classify_category("Shooting") == "Shooting"
    assert db._classify_category("Burglary") is None
    assert db._classify_category("Road Accidents") is None

    # Real-world regression: this exact Kaggle mirror folder name ("Normal-Videos-Part-1")
    # was silently skipped by the old exact-dict-key matcher.
    assert db._classify_category("Normal-Videos-Part-1") == "Normal"
    assert db._classify_category("Normal-Videos-Part-2") == "Normal"
    assert db._classify_category("Testing_Normal_Videos_Anomaly") == "Normal"


def test_feature_extraction_and_sampling_gate() -> None:
    extractor = db.TemporalFeatureExtractor(window_size=db.WINDOW_SIZE)
    frame_shape = (480, 640)
    last_saved = -db.DEFAULT_STRIDE
    saved_frames = []

    for frame_seq in range(60):
        tracked_list = [
            {"track_id": 1, "bbox": [100 + frame_seq, 100, 160 + frame_seq, 200], "class_id": 2, "confidence": 0.9}
        ]
        sequences = extractor.update_and_extract(tracked_list, frame_shape, frame_seq)
        assert 1 in sequences
        assert sequences[1].shape == (db.WINDOW_SIZE, 12)

        if len(extractor.history[1]) < db.WINDOW_SIZE:
            continue
        if frame_seq - last_saved < db.DEFAULT_STRIDE:
            continue
        last_saved = frame_seq
        saved_frames.append(frame_seq)

    # window=30, stride=15, 60 frames -> history fills at frame 29, then one save every 15 frames
    assert saved_frames == [29, 44, 59]


def test_merge_person_detections() -> None:
    from detection import Detection, merge_person_detections

    gun = Detection(xyxy=(0, 0, 10, 10), score=0.9, label="Gun", class_id=0)
    primary_suspect = Detection(xyxy=(100, 100, 200, 300), score=0.6, label="Suspect", class_id=2)
    # Same physical person as primary_suspect (heavily overlapping box), higher score.
    overlapping_person = Detection(xyxy=(105, 100, 205, 300), score=0.8, label="person", class_id=0)
    # A distinct person elsewhere in frame, only picked up by the person detector.
    distinct_person = Detection(xyxy=(400, 400, 460, 600), score=0.7, label="person", class_id=0)

    merged = merge_person_detections([gun, primary_suspect], [overlapping_person, distinct_person])

    assert gun in merged  # weapons pass through untouched
    suspects = [d for d in merged if d.class_id == 2]
    assert len(suspects) == 2  # overlapping pair deduped to one, distinct person kept separately
    assert any(d.xyxy == distinct_person.xyxy for d in suspects)
    # the deduped overlapping pair should keep the higher-scoring (person-detector) box
    assert any(d.score == 0.8 for d in suspects)


def test_discover_units(tmp_path=None) -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Shooting").mkdir()
        (root / "Shooting" / "v1.mp4").write_bytes(b"fake")
        (root / "Burglary").mkdir()
        (root / "Burglary" / "v2.mp4").write_bytes(b"fake")
        (root / "Assault").mkdir()
        (root / "Assault" / "v3.avi").write_bytes(b"fake")

        units, skipped = db.discover_units(root)

    classes_found = sorted(cls for cls, _ in units)
    assert classes_found == ["Shooting", "Violence"]
    assert skipped == {"Burglary": 1}


def test_discover_units_max_per_class(tmp_path=None) -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Normal").mkdir()
        for i in range(10):
            (root / "Normal" / f"v{i}.mp4").write_bytes(b"fake")

        units, _ = db.discover_units(root, max_per_class=3)
        units_again, _ = db.discover_units(root, max_per_class=3)  # same seed -> same sample

    assert len(units) == 3
    assert units == units_again


def test_iter_frames_step_and_cap(tmp_path=None) -> None:
    import tempfile

    import numpy as np

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp) / "unit1"
        frame_dir.mkdir()
        for i in range(10):
            img = np.full((4, 4, 3), i, dtype=np.uint8)
            db.cv2.imwrite(str(frame_dir / f"{i:03d}.jpg"), img)

        all_frames = list(db.iter_frames(frame_dir))
        assert len(all_frames) == 10

        stepped = list(db.iter_frames(frame_dir, frame_step=3))
        assert len(stepped) == 4  # frames 0, 3, 6, 9

        capped = list(db.iter_frames(frame_dir, frame_step=1, max_frames=4))
        assert len(capped) == 4

        stepped_and_capped = list(db.iter_frames(frame_dir, frame_step=2, max_frames=3))
        assert len(stepped_and_capped) == 3


def _drive_adaptive(gen, interesting_at):
    """Runs an iter_frames_adaptive generator to exhaustion, reporting is_interesting=True
    for every yielded frame index in `interesting_at`. Returns the list of yielded indices."""
    yielded_idxs = []
    is_interesting = None
    while True:
        try:
            frame_idx, _frame = next(gen) if is_interesting is None else gen.send(is_interesting)
        except StopIteration:
            return yielded_idxs
        yielded_idxs.append(frame_idx)
        is_interesting = frame_idx in interesting_at


def test_iter_frames_adaptive_frame_dir() -> None:
    import tempfile

    import numpy as np

    with tempfile.TemporaryDirectory() as tmp:
        frame_dir = Path(tmp) / "unit1"
        frame_dir.mkdir()
        for i in range(20):
            db.cv2.imwrite(str(frame_dir / f"{i:03d}.jpg"), np.full((4, 4, 3), i, dtype=np.uint8))

        # "interesting" (active_step=1) for frames 0-3, then idle (idle_step=4) from frame 4 on.
        gen = db.iter_frames_adaptive(frame_dir, active_step=1, idle_step=4)
        idxs = _drive_adaptive(gen, interesting_at=set(range(4)))
        assert idxs == [0, 1, 2, 3, 4, 8, 12, 16]

        # never interesting -> pure idle_step=5 walk from the start.
        gen2 = db.iter_frames_adaptive(frame_dir, active_step=1, idle_step=5)
        idxs2 = _drive_adaptive(gen2, interesting_at=set())
        assert idxs2 == [0, 5, 10, 15]

        # always interesting -> pure active_step=1 walk (every frame), same as iter_frames.
        gen3 = db.iter_frames_adaptive(frame_dir, active_step=1, idle_step=6)
        idxs3 = _drive_adaptive(gen3, interesting_at=set(range(20)))
        assert idxs3 == list(range(20))

        # max_frames caps total yielded regardless of stepping pattern.
        gen4 = db.iter_frames_adaptive(frame_dir, active_step=1, idle_step=4, max_frames=3)
        idxs4 = _drive_adaptive(gen4, interesting_at=set())
        assert len(idxs4) == 3


if __name__ == "__main__":
    test_category_mapping()
    test_feature_extraction_and_sampling_gate()
    test_merge_person_detections()
    test_discover_units()
    test_discover_units_max_per_class()
    test_iter_frames_step_and_cap()
    test_iter_frames_adaptive_frame_dir()
    print("OK: all dataset_builder smoke tests passed")

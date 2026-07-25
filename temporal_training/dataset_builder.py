#!/usr/bin/env python3
"""Phase 1+2 of the temporal-training pipeline: turns raw UCF-Crime videos into a labeled
dataset of 30-frame/12-dim feature sequences, using Guardian's detection stack (YOLO ONNX
detector + ByteTrack tracker + 12D feature extractor) via the self-contained copies in
detection.py. The detector and its weights are never modified -- only run as-is. This file
has no dependency on backend/ -- only detection.py (same folder) and trained_model/ (for
the actual .onnx weights) need to travel with it.

UCF-Crime maps directly onto Guardian's 3 action classes: Shooting -> Shooting,
Fighting/Assault -> Violence, Normal(*) -> Normal. All other UCF-Crime categories (Abuse,
Arrest, Arson, Burglary, Explosion, RoadAccidents, Robbery, Shoplifting, Stealing, Vandalism)
are out of scope for a weapon/violence model and are skipped.

(A fourth class, "Stabbing", was dropped from Guardian's action taxonomy entirely -- UCF-Crime
has no matching category and no other real data source is planned for it. Removed from
GUARDIAN_CLASSES/ACTION_CLASSES here, in detection.py, in backend/bl/detection/temporal_action.py,
and from the frontend admin dashboard.)
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))  # so `import detection` works regardless of cwd

from detection import TemporalFeatureExtractor  # noqa: E402  (needs sys.path set up first)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("guardian.temporal_dataset")

# The official CRCV/UCF release is split by the authors into several independent zips; the
# full set (all 14 categories + ~950 normal-training videos) is ~100GB+ and takes days to
# download. We only need Shooting/Fighting/Assault (-> Guardian's Shooting/Violence classes)
# plus some Normal videos, so we fetch only the pieces that can contain those:
#   - Anomaly-Videos-Part-{1,2,3,4}.zip: the 13 anomaly categories are split across these 4
#     zips by the authors in an order that isn't documented anywhere public, so we can't
#     cherry-pick just the one containing Shooting -- but all 4 together are only ~25GB
#     (vs. 100GB+ for the full corpus), and downloading all 4 guarantees Shooting/Fighting/
#     Assault are included wherever they landed.
#   - Normal_Videos_for_Event_Recognition.zip: a small (~1GB) real-footage Normal set --
#     used instead of Testing_Normal_Videos.zip (4.7GB) or the two Training-Normal-Videos
#     zips (72GB combined), since MAX_VIDEOS_PER_CLASS caps how many Normal videos we
#     actually use anyway.
# Mirrored (unmodified, same filenames/sizes) from the official release on HuggingFace
# (jinmang2/ucf_crime) -- this avoids a known TLS cert issue on crcv.ucf.edu directly and
# HF's resolve/ URLs are plain redirect-following HTTP downloads, no auth required.
UCF_CRIME_HF_BASE = "https://huggingface.co/datasets/jinmang2/ucf_crime/resolve/main"
UCF_CRIME_FILES = [
    "Anomaly-Videos-Part-1.zip",
    "Anomaly-Videos-Part-2.zip",
    "Anomaly-Videos-Part-3.zip",
    "Anomaly-Videos-Part-4.zip",
    "Normal_Videos_for_Event_Recognition.zip",
]

WINDOW_SIZE = 30
DEFAULT_STRIDE = 15  # ponytail: fixed-stride sampler (50% overlap); revisit with motion-based
                      # sampling only if per-class sequence counts end up too sparse/imbalanced.

VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
FRAME_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
MEDIA_EXTS = VIDEO_EXTS | FRAME_EXTS

GUARDIAN_CLASSES = ["Normal", "Shooting", "Violence"]

# Substring match (not exact-dict lookup) since real Kaggle mirrors number/prefix/suffix
# category folders in ways we can't fully predict up front -- e.g. "Normal-Videos-Part-1"
# normalizes to "normalvideospart1", and "Testing_Normal_Videos_Anomaly" to
# "testingnormalvideosanomaly" -- neither was in any hardcoded exact-key list.
CATEGORY_KEYWORD_TO_CLASS = [
    ("normal", "Normal"),
    ("shooting", "Shooting"),
    ("fighting", "Violence"),
    ("assault", "Violence"),
]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _classify_category(name: str) -> str | None:
    # Substring, not prefix: real mirrors put the category word in the middle too, e.g.
    # "Testing_Normal_Videos_Anomaly" -> "testingnormalvideosanomaly". Safe for UCF-Crime's
    # known 14 categories -- none of the other names contain "normal"/"shooting"/"fighting"/
    # "assault" as a substring.
    norm = _normalize(name)
    for keyword, guardian_class in CATEGORY_KEYWORD_TO_CLASS:
        if keyword in norm:
            return guardian_class
    return None


def download_official_ucf_crime(
    dest_dir: str | Path,
    files: list[str] = UCF_CRIME_FILES,
    base_url: str = UCF_CRIME_HF_BASE,
) -> Path:
    """Downloads + extracts just the UCF-Crime zip files that can contain Shooting/Fighting/
    Assault/Normal (see UCF_CRIME_FILES's comment for why these specific files and not the
    full ~100GB+ corpus), from the HuggingFace mirror of the official release. Each zip is
    extracted into its own subfolder under a shared `UCF_Crimes/` root so discover_units's
    recursive category walk sees every category from every part in one place. Resumable/
    idempotent per-file: skips a download if its zip is already fully present, skips
    extraction if that part's extract folder already has content."""
    import zipfile

    import requests

    dest_dir = Path(dest_dir)
    extract_root = dest_dir / "UCF_Crimes"
    extract_root.mkdir(parents=True, exist_ok=True)

    def _fetch(url: str, zip_path: Path) -> None:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            if zip_path.exists() and total and zip_path.stat().st_size == total:
                logger.info("%s already fully downloaded (%d bytes) -- skipping.", zip_path.name, total)
                return
            logger.info("Downloading %s (%.1f GB) -> %s", url, total / 1e9, zip_path)
            with open(zip_path, "wb") as f, tqdm(total=total or None, unit="B", unit_scale=True, desc=zip_path.name) as pbar:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    pbar.update(len(chunk))

    for filename in files:
        part_extract_dir = extract_root / Path(filename).stem
        if part_extract_dir.exists() and any(part_extract_dir.rglob("*")):
            logger.info("%s already extracted at %s -- skipping.", filename, part_extract_dir)
            continue

        zip_path = dest_dir / filename
        _fetch(f"{base_url}/{filename}", zip_path)

        logger.info("Extracting %s -> %s", zip_path, part_extract_dir)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(part_extract_dir)

    return extract_root


def iter_frames(path: Path, frame_step: int = 1, max_frames: int | None = None) -> Iterator[np.ndarray]:
    """Yields ordered BGR frames from either a video file or a directory of ordered frame
    images -- so the builder works whether the Kaggle mirror ships raw video or pre-extracted
    frames.

    frame_step > 1 skips frames (keeps every frame_step-th one) to cut detector calls on long
    videos; max_frames caps how many (post-skip) frames are yielded, to bound very long videos
    (UCF-Crime's Normal category in particular has some very long clips). Both are purely a
    speed/size lever for dataset building -- see the notebook's dataset-size cell."""
    count = 0

    def _keep() -> bool:
        nonlocal count
        if max_frames is not None and count >= max_frames:
            return False
        count += 1
        return True

    if path.is_dir():
        for i, fp in enumerate(sorted(p for p in path.iterdir() if p.suffix.lower() in FRAME_EXTS)):
            if i % frame_step != 0 or not _keep():
                continue
            img = cv2.imread(str(fp))
            if img is not None:
                yield img
        return

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        logger.warning("Could not open video: %s", path)
        return
    try:
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if i % frame_step == 0:
                if not _keep():
                    break
                yield frame
            i += 1
    finally:
        cap.release()


def iter_frames_adaptive(
    path: Path,
    active_step: int = 1,
    idle_step: int = 1,
    max_frames: int | None = None,
):
    """Two-speed frame walker for one video/frame-dir: advances by `active_step` after a
    frame the caller flags as interesting (weapon/person/suspect seen), or by the larger
    `idle_step` otherwise. Skips the expensive detect+track+extract work across long empty
    stretches -- UCF-Crime's Normal category in particular has very long clips with nothing
    happening most of the time -- while keeping fine-grained sampling once something is
    actually being tracked, which is what the 30-frame sequences need.

    Drive it as a generator: prime with `frame_idx, frame = next(gen)`, then feed back
    `frame_idx, frame = gen.send(is_interesting)` after each detection pass, until
    StopIteration. Video files are read sequentially even while idling (frame-accurate
    seeking via CAP_PROP_POS_FRAMES is unreliable across codecs) -- decode cost for skipped
    frames is trivial next to the two-detector inference it lets you skip. Frame directories
    index directly (true random access, no decode waste)."""
    is_dir = path.is_dir()
    if is_dir:
        files = sorted(p for p in path.iterdir() if p.suffix.lower() in FRAME_EXTS)
    else:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            logger.warning("Could not open video: %s", path)
            return

    idx = 0
    yielded = 0
    pending_skip = 0  # frames to read-and-discard before the next real read (video only)
    try:
        while True:
            if max_frames is not None and yielded >= max_frames:
                return

            if is_dir:
                if idx >= len(files):
                    return
                frame = cv2.imread(str(files[idx]))
                if frame is None:
                    return
            else:
                for _ in range(pending_skip):
                    ok, _discarded = cap.read()
                    if not ok:
                        return
                ok, frame = cap.read()
                if not ok:
                    return

            is_interesting = yield (idx, frame)
            yielded += 1
            step = active_step if is_interesting else idle_step
            idx += step
            pending_skip = step - 1
    finally:
        if not is_dir:
            cap.release()


def discover_units(
    data_root: Path,
    max_per_class: int | None = None,
    seed: int = 42,
) -> tuple[list[tuple[str, Path]], Counter]:
    """Recursively finds UCF-Crime category directories under data_root and returns
    [(guardian_class, video_or_frame_dir_path), ...] plus a Counter of skipped (unmapped)
    category directory names -> unit count, for the dataset-statistics section.

    max_per_class caps how many video/frame units are kept per Guardian class (a random,
    seeded sample, not just the first N encountered) -- the main lever for cutting a 32GB/
    multi-day UCF-Crime build down to something tractable without touching detection quality."""
    by_class: dict[str, list[Path]] = {}
    skipped: Counter = Counter()

    for dirpath in sorted(p for p in data_root.rglob("*") if p.is_dir()):
        children = list(dirpath.iterdir())
        video_files = [c for c in children if c.is_file() and c.suffix.lower() in VIDEO_EXTS]
        frame_dirs = [
            c for c in children
            if c.is_dir() and any(f.suffix.lower() in FRAME_EXTS for f in c.iterdir() if f.is_file())
        ]
        dir_units = video_files + frame_dirs
        if not dir_units:
            continue

        guardian_class = _classify_category(dirpath.name)
        if guardian_class is None:
            skipped[dirpath.name] += len(dir_units)
            continue
        by_class.setdefault(guardian_class, []).extend(dir_units)

    rng = np.random.default_rng(seed)
    units: list[tuple[str, Path]] = []
    for guardian_class, paths in by_class.items():
        if max_per_class is not None and len(paths) > max_per_class:
            idxs = rng.choice(len(paths), size=max_per_class, replace=False)
            paths = [paths[i] for i in idxs]
        units.extend((guardian_class, p) for p in paths)

    return units, skipped


def _detections_to_sv(detections, sv_module):
    if not detections:
        return sv_module.Detections.empty()
    xyxy = np.array([[*d.xyxy] for d in detections], dtype=np.float32)
    conf = np.array([d.score for d in detections], dtype=np.float32)
    cls = np.array([d.class_id for d in detections], dtype=np.int32)
    return sv_module.Detections(xyxy=xyxy, confidence=conf, class_id=cls)


def process_unit(
    unit_path: Path,
    guardian_class: str,
    detector,
    out_dir: Path,
    unit_id: str,
    stride: int = DEFAULT_STRIDE,
    person_detector=None,
    frame_step: int = 1,
    idle_frame_step: int | None = None,
    max_frames_per_video: int | None = None,
) -> int:
    """Runs detect -> track -> feature-extract over one video/frame unit and saves every
    accepted 30-frame sequence as a .npy file under out_dir/guardian_class/. Returns the
    number of sequences saved. Imports supervision/tracker lazily so the pure discovery/
    sampling logic above stays importable without the full detection stack installed.

    If person_detector is given, its "person" detections are merged in as additional Suspect
    tracks (see detection.merge_person_detections) -- catches suspects the primary Gun/Knife/
    Suspect detector misses on footage outside its own training domain. It's also skipped
    outright on any frame where the primary detector already found a Suspect -- no need to
    pay for a second forward pass once a person is already confirmed that frame.

    frame_step is the "active" step (used once something interesting has been seen);
    idle_frame_step (defaults to frame_step, i.e. no adaptive behavior) is the larger step
    used while nothing has been detected -- see iter_frames_adaptive for the full rationale.
    max_frames_per_video caps total (post-skip) frames processed."""
    import supervision as sv
    from detection import get_byte_tracker, merge_person_detections, remove_byte_tracker

    idle_step = idle_frame_step if idle_frame_step is not None else frame_step

    stream_id = f"dataset_builder::{unit_id}"
    tracker = get_byte_tracker(stream_id)
    extractor = TemporalFeatureExtractor(window_size=WINDOW_SIZE)
    saved = 0
    last_saved_frame: dict[int, int] = {}

    frame_source = iter_frames_adaptive(unit_path, frame_step, idle_step, max_frames_per_video)
    is_interesting = None  # None => prime the generator with next(), not send()

    try:
        while True:
            try:
                if is_interesting is None:
                    frame_seq, frame = next(frame_source)
                else:
                    frame_seq, frame = frame_source.send(is_interesting)
            except StopIteration:
                break

            h, w = frame.shape[:2]
            detections = detector.predict(frame)
            has_primary_suspect = any(d.class_id == 2 for d in detections)
            if person_detector is not None and not has_primary_suspect:
                detections = merge_person_detections(detections, person_detector.predict(frame))

            tracked_list = tracker.update_with_detections(_detections_to_sv(detections, sv))
            is_interesting = any(t["class_id"] in (0, 1, 2) for t in tracked_list)
            sequences = extractor.update_and_extract(tracked_list, (h, w), frame_seq)

            for track_id, seq_feat in sequences.items():
                if len(extractor.history.get(track_id, [])) < WINDOW_SIZE:
                    continue  # skip left-padded partial windows; only save full history
                if frame_seq - last_saved_frame.get(track_id, -stride) < stride:
                    continue
                last_saved_frame[track_id] = frame_seq
                out_path = out_dir / guardian_class / f"{unit_id}__t{track_id}_f{frame_seq}.npy"
                np.save(out_path, seq_feat)
                saved += 1
    finally:
        frame_source.close()
        remove_byte_tracker(stream_id)

    return saved


def build_dataset(
    data_root: str | Path,
    out_dir: str | Path = "sequences",
    stride: int = DEFAULT_STRIDE,
    use_person_detector: bool = True,
    max_videos_per_class: int | None = None,
    frame_step: int = 1,
    idle_frame_step: int | None = None,
    max_frames_per_video: int | None = None,
) -> dict:
    """Full Phase 1+2 driver: discovers UCF-Crime units under data_root, runs the existing
    detector/tracker/extractor over each, and writes labeled sequences under out_dir. Returns
    a stats dict consumed by the notebook's dataset-statistics section.

    When use_person_detector is True (default) and trained_model/yolov8s_person.onnx is
    present, its "person" detections are merged in as extra Suspect tracks -- see
    detection.merge_person_detections. Falls back to the primary detector alone (with a
    warning) if the person-detector weights aren't found. Also skipped outright on any frame
    where the primary detector already found a Suspect that frame.

    max_videos_per_class / frame_step / idle_frame_step / max_frames_per_video are the
    runtime-vs-coverage dials: the full UCF-Crime Normal/Shooting/Fighting/Assault subset can
    still be tens of GB and take days to run frame-by-frame through two detectors -- cap
    videos per class, skip frames, and/or cap frames per video to make a build tractable.
    idle_frame_step (bigger than frame_step) skips aggressively while nothing has been
    detected recently and drops back to frame_step once something is being tracked -- see
    discover_units/iter_frames_adaptive docstrings for what each trades off."""
    from detection import MODEL_PATH, PERSON_MODEL_PATH, YoloOnnxDetector, load_class_names

    data_root = Path(data_root)
    out_dir = Path(out_dir)
    for cls in GUARDIAN_CLASSES:
        (out_dir / cls).mkdir(parents=True, exist_ok=True)

    units, skipped_categories = discover_units(data_root, max_per_class=max_videos_per_class)
    if not units:
        logger.warning("No matching UCF-Crime category folders found under %s", data_root)

    detector = YoloOnnxDetector(MODEL_PATH, load_class_names())

    person_detector = None
    if use_person_detector:
        if PERSON_MODEL_PATH.exists():
            person_detector = YoloOnnxDetector(PERSON_MODEL_PATH, {0: "person"})
            logger.info("Person detector enabled: %s", PERSON_MODEL_PATH)
        else:
            logger.warning("Person detector requested but not found at %s -- continuing without it.", PERSON_MODEL_PATH)

    videos_per_class: Counter = Counter()
    sequences_per_class: Counter = Counter()

    progress = tqdm(units, desc="Building dataset", unit="video")
    for i, (guardian_class, unit_path) in enumerate(progress):
        unit_id = f"{_normalize(guardian_class)}-{i:05d}-{unit_path.stem}"
        n_saved = process_unit(
            unit_path, guardian_class, detector, out_dir, unit_id, stride,
            person_detector=person_detector, frame_step=frame_step, idle_frame_step=idle_frame_step,
            max_frames_per_video=max_frames_per_video,
        )
        videos_per_class[guardian_class] += 1
        sequences_per_class[guardian_class] += n_saved
        progress.set_postfix(class_=guardian_class, sequences=sum(sequences_per_class.values()))
        logger.info("[%d/%d] %s (%s) -> %d sequences", i + 1, len(units), unit_path.name, guardian_class, n_saved)

    stats = {
        "videos_per_class": dict(videos_per_class),
        "sequences_per_class": dict(sequences_per_class),
        "skipped_categories": dict(skipped_categories),
    }
    logger.info("Dataset build complete: %s", stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the UCF-Crime temporal-sequence dataset")
    parser.add_argument("--data-root", type=str, required=True, help="Root folder of the downloaded UCF-Crime dataset")
    parser.add_argument("--out", type=str, default=str(Path(__file__).resolve().parent / "sequences"))
    parser.add_argument("--stride", type=int, default=DEFAULT_STRIDE)
    parser.add_argument("--no-person-detector", action="store_true", help="Disable the supplementary yolov8s_person.onnx detector")
    parser.add_argument("--max-videos-per-class", type=int, default=None, help="Cap videos processed per Guardian class (random seeded sample)")
    parser.add_argument("--frame-step", type=int, default=1, help="Active step: process every Nth frame once something's being tracked")
    parser.add_argument("--idle-frame-step", type=int, default=None, help="Idle step: bigger skip while nothing's been detected recently (defaults to --frame-step, i.e. no adaptive skipping)")
    parser.add_argument("--max-frames-per-video", type=int, default=None, help="Cap frames processed per video/unit")
    args = parser.parse_args()

    stats = build_dataset(
        args.data_root, args.out, args.stride,
        use_person_detector=not args.no_person_detector,
        max_videos_per_class=args.max_videos_per_class,
        frame_step=args.frame_step,
        idle_frame_step=args.idle_frame_step,
        max_frames_per_video=args.max_frames_per_video,
    )
    print(stats)


if __name__ == "__main__":
    main()

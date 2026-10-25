import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from sports_vision.config import PipelineConfig
from sports_vision.homography import PitchCalibration
from sports_vision.pipeline import SportsVisionPipeline
from sports_vision.result_bundle import (
    DEFAULT_RESULT_MEMORY_LIMIT_BYTES,
    collect_results,
)


def _write_tiny_video(path: Path, *, frames: int = 8) -> None:
    width, height = 320, 192
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 8.0, (width, height)
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not initialize the tiny MP4 fixture")
    try:
        for index in range(frames):
            image = np.full((height, width, 3), (42, 116, 46), dtype=np.uint8)
            cv2.line(image, (0, height // 2), (width, height // 2), (245, 245, 245), 2)
            cv2.circle(image, (40 + index * 20, 90), 7, (250, 250, 250), -1)
            writer.write(image)
    finally:
        writer.release()


def test_writes_inspectable_evidence_json(tmp_path: Path):
    evidence = {
        "model": "yolo26n.pt",
        "tracker": "bytetrack.yaml",
        "device": "cpu",
        "frames_processed": 8,
        "download_names": ["annotated.mp4", "summary.json", "tracking.csv"],
        "bundle_size_bytes": 10_584,
        "peak_rss_bytes": 1_157_881_856,
    }
    evidence_path = tmp_path / "nested" / "real-inference-evidence.json"

    _write_evidence(evidence_path, evidence)

    assert json.loads(evidence_path.read_text(encoding="utf-8")) == evidence


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_REAL_INFERENCE") != "1",
    reason="set RUN_REAL_INFERENCE=1 for the bounded model smoke test",
)
def test_real_yolo26n_bytetrack_produces_downloadable_bundle_with_memory_evidence():
    import resource

    cv2.setNumThreads(1)
    frame_count = 8
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        video_path = root / "tiny-match.mp4"
        output_dir = root / "output"
        _write_tiny_video(video_path, frames=frame_count)

        calibration = PitchCalibration(
            image_points=np.asarray([[0, 0], [319, 0], [319, 191], [0, 191]]),
            field_points=np.asarray([[0, 0], [105, 0], [105, 68], [0, 68]]),
        )
        config = PipelineConfig(
            detector_model="yolo26n.pt",
            tracker="bytetrack.yaml",
            device="cpu",
            confidence=0.05,
            image_size=320,
            draw_minimap=False,
        )
        summary = SportsVisionPipeline(calibration, config).run(video_path, output_dir)
        bundle = collect_results(output_dir, summary)

    # The source and output directory are gone: this mirrors a Streamlit rerun.
    summary_bytes = json.dumps(bundle["summary"], indent=2).encode("utf-8")
    downloads = {
        "annotated.mp4": bundle["video"],
        "tracking.csv": bundle["csv"],
        "summary.json": summary_bytes,
        **{name: content for name, content in bundle["reports"]},
    }
    assert summary["frames_processed"] == frame_count
    assert downloads["annotated.mp4"]
    assert downloads["tracking.csv"].startswith(b"frame,time_s,")
    assert json.loads(downloads["summary.json"])["frames_processed"] == frame_count
    assert all(content for content in downloads.values())
    assert bundle["size_bytes"] <= DEFAULT_RESULT_MEMORY_LIMIT_BYTES

    peak_rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    evidence = {
        "model": config.detector_model,
        "tracker": config.tracker,
        "device": config.device,
        "frames_processed": summary["frames_processed"],
        "download_names": sorted(downloads),
        "bundle_size_bytes": bundle["size_bytes"],
        "peak_rss_bytes": peak_rss_bytes,
    }
    print("REAL_INFERENCE_EVIDENCE=" + json.dumps(evidence, sort_keys=True))

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from sports_vision.config import PipelineConfig
from sports_vision.homography import PitchCalibration
from sports_vision.pipeline import SportsVisionPipeline

st.set_page_config(page_title="Sports Vision Analyst", layout="wide")
st.title("Sports Vision Analyst")
st.caption("Single-camera football tracking, metric mapping, speed, distance, possession, formations and optional pose keypoints.")

video = st.file_uploader("Match video", type=["mp4", "mov", "avi", "mkv"])
calibration_file = st.file_uploader("Calibration JSON", type=["json"])

with st.sidebar:
    model = st.text_input("Detection model", "yolo26n.pt")
    tracker = st.selectbox("Tracker", ["bytetrack.yaml", "botsort.yaml"])
    device = st.text_input("Device", "auto")
    conf = st.slider("Confidence", 0.05, 0.90, 0.25, 0.05)
    imgsz = st.select_slider("Image size", options=[640, 960, 1280, 1536], value=1280)
    pose = st.checkbox("Export pose keypoints", False)

if video and calibration_file and st.button("Analyze match", type="primary"):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        input_path = tmp / video.name
        input_path.write_bytes(video.getbuffer())
        calibration_path = tmp / "calibration.json"
        calibration_path.write_bytes(calibration_file.getbuffer())
        out_dir = tmp / "output"
        calibration = PitchCalibration.load(calibration_path)
        config = PipelineConfig(
            detector_model=model,
            tracker=tracker,
            device=device,
            confidence=conf,
            image_size=imgsz,
            enable_pose=pose,
        )
        progress = st.status("Running computer-vision pipeline…", expanded=True)
        try:
            summary = SportsVisionPipeline(calibration, config).run(input_path, out_dir)
            progress.update(label="Analysis complete", state="complete")
            st.video(str(out_dir / "annotated.mp4"))
            c1, c2, c3 = st.columns(3)
            c1.metric("Team 1 distance", f"{summary['team_distance_m']['1'] / 1000:.2f} km")
            c2.metric("Team 2 distance", f"{summary['team_distance_m']['2'] / 1000:.2f} km")
            c3.metric("Frames", summary["frames_processed"])
            st.json(summary)
            st.download_button("Download tracking CSV", (out_dir / "tracking.csv").read_bytes(), "tracking.csv", "text/csv")
            st.download_button("Download summary JSON", json.dumps(summary, indent=2), "summary.json", "application/json")
            st.download_button("Download annotated video", (out_dir / "annotated.mp4").read_bytes(), "annotated.mp4", "video/mp4")
            for report in summary["outputs"]["reports"]:
                st.image(str(out_dir / report), caption=report)
        except Exception as exc:
            progress.update(label="Analysis failed", state="error")
            st.exception(exc)
else:
    st.info("Create the calibration once with sports-vision-calibrate, then upload the match and that JSON here.")

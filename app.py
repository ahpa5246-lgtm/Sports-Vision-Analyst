from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st

from sports_vision.config import PipelineConfig
from sports_vision.homography import PitchCalibration
from sports_vision.pipeline import SportsVisionPipeline
from sports_vision.result_bundle import collect_results

st.set_page_config(page_title="Sports Vision Analyst", layout="wide")
st.title("Sports Vision Analyst")
st.caption("Review match footage, calibrate the pitch, then inspect tracking evidence.")
page = st.sidebar.radio("Workspace", ["Analyze", "Results", "Calibration guide"])
st.sidebar.caption("Local session • Results remain available across downloads until replaced or cleared.")

if page == "Calibration guide":
    st.header("Map the pitch before measuring movement")
    st.write("Use sports-vision-calibrate to select corresponding image and pitch points, then export the calibration JSON.")
    st.code("sports-vision-calibrate --help")
    st.warning("Calibration is camera-specific. A moving camera or mismatched calibration can make speed and distance unreliable.")
    st.write("Check the mapped pitch and player positions before interpreting the reports. Tracking IDs are not verified player identities.")
elif page == "Analyze":
    st.header("Prepare a match")
    video = st.file_uploader("Match video", type=["mp4", "mov", "avi", "mkv"])
    calibration_file = st.file_uploader("Calibration JSON", type=["json"])
    with st.expander("Detection settings", expanded=False):
        model = st.text_input("Detection model", "yolo26n.pt")
        tracker = st.selectbox("Tracker", ["bytetrack.yaml", "botsort.yaml"])
        device = st.text_input("Device", "auto")
        conf = st.slider("Confidence", 0.05, 0.90, 0.25, 0.05)
        imgsz = st.select_slider("Image size", options=[640, 960, 1280, 1536], value=1280)
        pose = st.checkbox("Export pose keypoints", False)
    if st.button("Analyze match", type="primary", disabled=not (video and calibration_file)):
        progress = st.status("Running computer-vision pipeline…", expanded=True)
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp = Path(tmp_dir)
                # Upload names never become paths on the server.
                input_path = tmp / ("match" + Path(video.name).suffix.lower())
                input_path.write_bytes(video.getbuffer())
                calibration_path = tmp / "calibration.json"
                calibration_path.write_bytes(calibration_file.getbuffer())
                calibration = PitchCalibration.load(calibration_path)
                config = PipelineConfig(detector_model=model, tracker=tracker, device=device,
                    confidence=conf, image_size=imgsz, enable_pose=pose)
                out_dir = tmp / "output"
                summary = SportsVisionPipeline(calibration, config).run(input_path, out_dir)
                bundle = collect_results(out_dir, summary)
            # Publish atomically only after every output has been copied.
            st.session_state["analysis_result"] = bundle
            progress.update(label="Analysis complete", state="complete")
            st.success("Open Results to review the match and download reports.")
        except Exception as exc:
            progress.update(label="Analysis failed", state="error")
            st.error(f"Could not analyze this match: {exc}")
            if "analysis_result" in st.session_state:
                st.info("Your previous successful result is still available in Results.")
else:
    st.header("Match results")
    result = st.session_state.get("analysis_result")
    if result is None:
        st.info("No completed analysis yet. Open Analyze to upload a match and calibration.")
    else:
        summary = result["summary"]
        st.video(result["video"])
        c1, c2, c3 = st.columns(3)
        c1.metric("Team 1 distance", f"{summary['team_distance_m']['1'] / 1000:.2f} km")
        c2.metric("Team 2 distance", f"{summary['team_distance_m']['2'] / 1000:.2f} km")
        c3.metric("Frames", summary["frames_processed"])
        st.caption(f"Session result size: {result['size_bytes'] / (1024 * 1024):.1f} MB")
        st.caption("Distances depend on calibration and tracking quality; inspect footage before drawing conclusions.")
        st.download_button("Download tracking CSV", result["csv"], "tracking.csv", "text/csv")
        st.download_button("Download summary JSON", json.dumps(summary, indent=2), "summary.json", "application/json")
        st.download_button("Download annotated video", result["video"], "annotated.mp4", "video/mp4")
        for name, content in result["reports"]:
            st.image(content, caption=name)
        with st.expander("Raw analysis summary"):
            st.json(summary)
        if st.button("Clear results"):
            del st.session_state["analysis_result"]
            st.rerun()

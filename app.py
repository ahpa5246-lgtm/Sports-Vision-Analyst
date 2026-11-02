from __future__ import annotations

import io
import json
import math
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from sports_vision.config import PipelineConfig
from sports_vision.homography import PitchCalibration
from sports_vision.pipeline import SportsVisionPipeline
from sports_vision.result_bundle import collect_results
from sports_vision.frame_review import decode_annotated_frame

st.set_page_config(page_title="Sports Vision Analyst", layout="wide")
st.title("Sports Vision Analyst")
st.caption("Review match footage, calibrate the pitch, then inspect tracking evidence.")
page = st.sidebar.radio("Workspace", ["Analyze", "Results", "Calibration guide"])
st.sidebar.caption("Local session • Results remain available across downloads until replaced or cleared.")


@st.cache_data(max_entries=4, show_spinner=False)
def _load_tracking_csv(csv_bytes: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(csv_bytes))


@st.cache_data(max_entries=8, show_spinner=False)
def _cached_annotated_frame(video_bytes: bytes, frame_index: int, suffix: str):
    return decode_annotated_frame(video_bytes, frame_index, suffix)


def _format_metric(value, unit: str = "", decimals: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    formatted = f"{number:.{decimals}f}"
    return f"{formatted} {unit}".strip()


def _team_label(value) -> str:
    try:
        team = int(value)
    except (TypeError, ValueError):
        return "Unassigned"
    return "Unassigned" if team == 0 else f"Team {team}"

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
        review_mode = st.radio(
            "Review mode",
            ["Video playback", "Frame review"],
            horizontal=True,
            key="results_review_mode",
        )
        if review_mode == "Video playback":
            st.video(result["video"], format=result["video_mime_type"])
        else:
            st.subheader("Selected frame")
            try:
                tracking = _load_tracking_csv(result["csv"])
            except Exception as exc:
                st.error(f"Could not read the tracking data: {exc}")
                tracking = None

            frame_count = int(summary.get("frames_processed") or 0)
            fps = float(summary.get("fps") or 0.0)
            if frame_count < 1:
                st.info("This analysis contains no decoded video frames.")
            elif not math.isfinite(fps) or fps <= 0:
                st.error("The analysis does not contain a valid frame rate, so frame time cannot be calculated.")
            elif tracking is not None:
                required_columns = {
                    "frame", "time_s", "track_id", "team", "x_m", "y_m",
                    "speed_kmh", "distance_m", "confidence",
                }
                missing_columns = sorted(required_columns.difference(tracking.columns))
                if missing_columns:
                    st.error("The tracking file is missing required columns: " + ", ".join(missing_columns))
                else:
                    frame_values = pd.to_numeric(tracking["frame"], errors="coerce").dropna()
                    initial_frame = 0
                    if not frame_values.empty:
                        initial_frame = min(max(int(frame_values.min()), 0), frame_count - 1)

                    current_frame = st.session_state.get("frame_review_index")
                    if not isinstance(current_frame, int) or not 0 <= current_frame < frame_count:
                        st.session_state["frame_review_index"] = initial_frame

                    if frame_count > 1:
                        frame_index = st.slider(
                            "Frame index",
                            min_value=0,
                            max_value=frame_count - 1,
                            key="frame_review_index",
                            help="Frame numbers start at zero. The timestamp is derived from the source frame rate.",
                        )
                    else:
                        frame_index = 0
                        st.caption("This result contains a single frame.")

                    numeric_frames = pd.to_numeric(tracking["frame"], errors="coerce")
                    frame_rows = tracking.loc[numeric_frames == frame_index].copy()
                    frame_times = pd.to_numeric(frame_rows["time_s"], errors="coerce").dropna()
                    frame_time = float(frame_times.iloc[0]) if not frame_times.empty else frame_index / fps

                    try:
                        suffix = Path(result["video_filename"]).suffix or ".webm"
                        frame_image = _cached_annotated_frame(result["video"], frame_index, suffix)
                        st.image(
                            frame_image,
                            caption=f"Frame {frame_index} · {frame_time:.3f} s",
                            width="stretch",
                        )
                    except Exception as exc:
                        st.error(f"Could not decode frame {frame_index}: {exc}")

                    st.caption(
                        "Track IDs are temporary tracker labels, not verified player identities. "
                        "Metric values depend on camera calibration and tracking quality."
                    )
                    st.subheader("Tracked objects on this frame")
                    if frame_rows.empty:
                        st.info("No tracked objects were recorded on this frame.")
                    else:
                        frame_table = frame_rows[["track_id", "team", "speed_kmh", "distance_m"]].copy()
                        frame_table["team"] = frame_table["team"].map(_team_label)
                        frame_table = frame_table.rename(
                            columns={
                                "track_id": "Track ID",
                                "team": "Team",
                                "speed_kmh": "Speed (km/h)",
                                "distance_m": "Distance (m)",
                            }
                        )
                        st.dataframe(frame_table, hide_index=True, width="stretch")

                        track_ids = sorted(
                            int(value)
                            for value in pd.to_numeric(frame_rows["track_id"], errors="coerce").dropna().unique()
                        )
                        if track_ids:
                            if st.session_state.get("frame_review_track_id") not in track_ids:
                                st.session_state["frame_review_track_id"] = track_ids[0]
                            selected_track = st.selectbox(
                                "Track ID",
                                track_ids,
                                key="frame_review_track_id",
                            )
                            selected_rows = frame_rows[
                                pd.to_numeric(frame_rows["track_id"], errors="coerce") == selected_track
                            ]
                            selected = selected_rows.iloc[0]
                            team_column, speed_column, distance_column = st.columns(3)
                            team_column.metric("Team", _team_label(selected["team"]))
                            speed_column.metric("Speed", _format_metric(selected["speed_kmh"], "km/h"))
                            distance_column.metric("Distance", _format_metric(selected["distance_m"], "m"))
                            st.caption(
                                "Pitch position: "
                                f"X {_format_metric(selected['x_m'], 'm')} · "
                                f"Y {_format_metric(selected['y_m'], 'm')} · "
                                f"Detection confidence {_format_metric(selected['confidence'], '', 2)}"
                            )

        c1, c2, c3 = st.columns(3)
        c1.metric("Team 1 distance", f"{summary['team_distance_m']['1'] / 1000:.2f} km")
        c2.metric("Team 2 distance", f"{summary['team_distance_m']['2'] / 1000:.2f} km")
        c3.metric("Frames", summary["frames_processed"])
        st.caption(f"Session result size: {result['size_bytes'] / (1024 * 1024):.1f} MB")
        st.caption("Distances depend on calibration and tracking quality; inspect footage before drawing conclusions.")
        st.download_button("Download tracking CSV", result["csv"], "tracking.csv", "text/csv")
        st.download_button("Download summary JSON", json.dumps(summary, indent=2), "summary.json", "application/json")
        st.download_button("Download annotated video", result["video"], result["video_filename"], result["video_mime_type"])
        for name, content in result["reports"]:
            st.image(content, caption=name)
        with st.expander("Raw analysis summary"):
            st.json(summary)
        if st.button("Clear results"):
            del st.session_state["analysis_result"]
            st.rerun()

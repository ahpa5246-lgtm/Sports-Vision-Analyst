from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

_SUPPORTED_VIDEO_SUFFIXES = {".webm", ".mp4", ".mov", ".avi", ".mkv"}


def decode_annotated_frame(video_bytes: bytes, frame_index: int, suffix: str = ".webm") -> np.ndarray:
    """Decode one zero-based frame from an in-memory annotated video.

    The video is written to a short-lived temporary file because OpenCV's
    VideoCapture does not accept a Python bytes buffer as a video container.
    The returned image is RGB for direct use with Streamlit.
    """
    if not isinstance(video_bytes, (bytes, bytearray, memoryview)) or not video_bytes:
        raise ValueError("Annotated video bytes are empty.")
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
        raise ValueError("Frame index must be a non-negative integer.")

    normalized_suffix = suffix.strip().lower()
    if not normalized_suffix.startswith("."):
        normalized_suffix = f".{normalized_suffix}"
    if normalized_suffix not in _SUPPORTED_VIDEO_SUFFIXES:
        raise ValueError(f"Unsupported annotated video extension: {normalized_suffix}")

    with TemporaryDirectory(prefix="sports-vision-frame-") as temporary_directory:
        video_path = Path(temporary_directory) / f"annotated{normalized_suffix}"
        video_path.write_bytes(bytes(video_bytes))
        capture = cv2.VideoCapture(str(video_path))
        try:
            if not capture.isOpened():
                raise ValueError("Could not open the annotated video for frame review.")

            total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if total_frames > 0 and frame_index >= total_frames:
                raise IndexError(f"Frame {frame_index} is outside the {total_frames}-frame video.")

            seeked = capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            next_frame = capture.get(cv2.CAP_PROP_POS_FRAMES)
            if (
                not ok
                or frame is None
                or not seeked
                or (next_frame > 0 and round(next_frame) - 1 != frame_index)
            ):
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                for _ in range(frame_index + 1):
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        raise IndexError(f"Could not decode frame {frame_index}.")
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        finally:
            capture.release()

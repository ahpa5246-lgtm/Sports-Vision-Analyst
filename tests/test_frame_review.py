from __future__ import annotations

import cv2
import numpy as np
import pytest

from sports_vision.frame_review import decode_annotated_frame


def _make_three_frame_video(tmp_path):
    video_path = tmp_path / "three-frames.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        5.0,
        (32, 24),
    )
    assert writer.isOpened(), "The test OpenCV build must provide the MJPG encoder."
    for color in ((0, 0, 255), (0, 255, 0), (255, 0, 0)):
        writer.write(np.full((24, 32, 3), color, dtype=np.uint8))
    writer.release()
    return video_path.read_bytes()


def test_decodes_the_requested_frame_as_rgb(tmp_path):
    video_bytes = _make_three_frame_video(tmp_path)

    frame = decode_annotated_frame(video_bytes, 1, ".avi")

    assert frame.shape == (24, 32, 3)
    channel_means = frame.mean(axis=(0, 1))
    assert channel_means[1] > channel_means[0] + 100
    assert channel_means[1] > channel_means[2] + 100


def test_rejects_empty_video_negative_index_and_out_of_range_index(tmp_path):
    with pytest.raises(ValueError, match="empty"):
        decode_annotated_frame(b"", 0)

    video_bytes = _make_three_frame_video(tmp_path)
    with pytest.raises(ValueError, match="non-negative"):
        decode_annotated_frame(video_bytes, -1, ".avi")
    with pytest.raises(IndexError, match="outside"):
        decode_annotated_frame(video_bytes, 3, ".avi")


def test_rejects_unsupported_video_extension():
    with pytest.raises(ValueError, match="Unsupported"):
        decode_annotated_frame(b"not-a-video", 0, ".gif")

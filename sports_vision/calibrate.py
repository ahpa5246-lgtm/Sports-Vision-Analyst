from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from .homography import PitchCalibration


def parse_field_points(value: str) -> np.ndarray:
    points = []
    for pair in value.split(";"):
        x, y = pair.split(",")
        points.append((float(x), float(y)))
    arr = np.asarray(points, dtype=np.float32)
    if len(arr) < 4:
        raise argparse.ArgumentTypeError("At least four field points are required")
    return arr


def main() -> None:
    parser = argparse.ArgumentParser(description="Click image landmarks corresponding to known pitch coordinates")
    parser.add_argument("video")
    parser.add_argument("--output", default="calibration.json")
    parser.add_argument("--frame", type=int, default=0, help="Frame index used for calibration")
    parser.add_argument("--pitch-length", type=float, default=105.0)
    parser.add_argument("--pitch-width", type=float, default=68.0)
    parser.add_argument(
        "--field-points",
        type=parse_field_points,
        default=parse_field_points("0,0;105,0;105,68;0,68"),
        help='Known meter coordinates in click order, e.g. "0,0;105,0;105,68;0,68"',
    )
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise FileNotFoundError(args.video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, args.frame))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("Could not read requested calibration frame")

    target = args.field_points
    clicks: list[tuple[float, float]] = []
    display = frame.copy()
    window = "Sports Vision calibration"

    def redraw() -> None:
        nonlocal display
        display = frame.copy()
        for idx, (x, y) in enumerate(clicks):
            cv2.circle(display, (int(x), int(y)), 7, (0, 255, 255), -1)
            cv2.putText(display, str(idx + 1), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        next_idx = min(len(clicks), len(target) - 1)
        text = f"Click {len(clicks)+1}/{len(target)} -> field {target[next_idx].tolist()} | U undo | R reset | Enter save | Esc cancel"
        cv2.rectangle(display, (0, 0), (display.shape[1], 38), (0, 0, 0), -1)
        cv2.putText(display, text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    def mouse(event, x, y, flags, param) -> None:
        if event == cv2.EVENT_LBUTTONDOWN and len(clicks) < len(target):
            clicks.append((float(x), float(y)))
            redraw()

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, mouse)
    redraw()
    while True:
        cv2.imshow(window, display)
        key = cv2.waitKey(20) & 0xFF
        if key == 27:
            cv2.destroyAllWindows()
            raise SystemExit(1)
        if key in (ord("u"), ord("U")) and clicks:
            clicks.pop()
            redraw()
        elif key in (ord("r"), ord("R")):
            clicks.clear()
            redraw()
        elif key in (10, 13) and len(clicks) == len(target):
            break
    cv2.destroyAllWindows()

    calibration = PitchCalibration(
        image_points=np.asarray(clicks, dtype=np.float32),
        field_points=target,
        pitch_length_m=args.pitch_length,
        pitch_width_m=args.pitch_width,
    )
    _ = calibration.matrix
    calibration.save(Path(args.output))
    print(f"Saved {args.output}")


if __name__ == "__main__":
    main()

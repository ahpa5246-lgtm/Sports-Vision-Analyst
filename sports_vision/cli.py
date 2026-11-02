from __future__ import annotations

import argparse
import json

from .config import PipelineConfig
from .homography import PitchCalibration
from .pipeline import SportsVisionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Single-camera football analytics")
    parser.add_argument("video", help="Input match video")
    parser.add_argument("--calibration", required=True, help="Calibration JSON created by sports-vision-calibrate")
    parser.add_argument("--output", default="runs/match", help="Output directory")
    parser.add_argument("--model", default="yolo26n.pt", help="Ultralytics detection model or custom weights")
    parser.add_argument("--pose-model", default="yolo26n-pose.pt", help="Ultralytics pose model")
    parser.add_argument("--tracker", default="bytetrack.yaml", help="Ultralytics tracker config")
    parser.add_argument("--device", default="auto", help="auto, cpu, 0, 0,1, mps, ...")
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.50)
    parser.add_argument("--pose", action="store_true", help="Export associated pose keypoints to poses.jsonl")
    parser.add_argument("--pose-stride", type=int, default=5)
    parser.add_argument("--no-minimap", action="store_true")
    parser.add_argument("--person-class", type=int, default=0)
    parser.add_argument("--ball-class", type=int, default=32)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    calibration = PitchCalibration.load(args.calibration)
    config = PipelineConfig(
        detector_model=args.model,
        pose_model=args.pose_model,
        tracker=args.tracker,
        confidence=args.conf,
        iou=args.iou,
        image_size=args.imgsz,
        device=args.device,
        person_class=args.person_class,
        ball_class=args.ball_class,
        enable_pose=args.pose,
        pose_stride=max(1, args.pose_stride),
        draw_minimap=not args.no_minimap,
    )
    summary = SportsVisionPipeline(calibration, config).run(args.video, args.output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

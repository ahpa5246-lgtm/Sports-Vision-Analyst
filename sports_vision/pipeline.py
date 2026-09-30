from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .analytics import FormationEstimator, MatchAnalytics
from .config import PipelineConfig
from .homography import PitchCalibration
from .report import generate_reports
from .team_classifier import TeamColorClassifier
from .visualize import annotate_frame, overlay_minimap, render_minimap


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    denom = area_a + area_b - inter
    return float(inter / denom) if denom > 0 else 0.0


class SportsVisionPipeline:
    def __init__(self, calibration: PitchCalibration, config: PipelineConfig | None = None) -> None:
        self.calibration = calibration
        self.config = config or PipelineConfig()

    def _load_models(self):
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError('Ultralytics is required. Install with: pip install -e ".[vision]"') from exc
        detector = YOLO(self.config.detector_model)
        pose = YOLO(self.config.pose_model) if self.config.enable_pose else None
        return detector, pose

    def _pose_rows(self, pose_model: Any, frame: np.ndarray, players: list[dict], frame_idx: int, time_s: float) -> list[dict]:
        if pose_model is None or frame_idx % max(1, self.config.pose_stride) != 0 or not players:
            return []
        device = None if self.config.device == "auto" else self.config.device
        result = pose_model.predict(
            frame,
            conf=self.config.confidence,
            imgsz=self.config.image_size,
            device=device,
            verbose=False,
        )[0]
        if result.boxes is None or result.keypoints is None:
            return []
        boxes = result.boxes.xyxy.detach().cpu().numpy()
        keypoints = result.keypoints.data.detach().cpu().numpy()
        rows: list[dict] = []
        for box, kpts in zip(boxes, keypoints):
            best = max(players, key=lambda p: _iou(np.asarray(p["bbox"], dtype=float), box), default=None)
            if best is None:
                continue
            overlap = _iou(np.asarray(best["bbox"], dtype=float), box)
            if overlap < 0.25:
                continue
            rows.append(
                {
                    "frame": frame_idx,
                    "time_s": round(time_s, 4),
                    "track_id": int(best["track_id"]),
                    "keypoints": np.asarray(kpts).round(3).tolist(),
                }
            )
        return rows

    def run(self, video_path: str | Path, output_dir: str | Path) -> dict:
        detector, pose_model = self._load_models()
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise FileNotFoundError(f"Could not open video: {video_path}")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        annotated_path = output_dir / "annotated.mp4"
        writer = cv2.VideoWriter(
            str(annotated_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Could not initialize MP4 writer. Install an OpenCV/FFmpeg build with MP4 support.")

        analytics = MatchAnalytics(self.config.max_player_speed_kmh)
        classifier = TeamColorClassifier(outlier_distance=self.config.team_outlier_distance)
        formations = FormationEstimator()
        records: list[dict] = []
        pose_path = output_dir / "poses.jsonl"
        pose_file = pose_path.open("w", encoding="utf-8") if self.config.enable_pose else None
        last_ball_field: tuple[float, float] | None = None
        formation_stride = max(1, int(round(fps * self.config.formation_interval_s)))
        device = None if self.config.device == "auto" else self.config.device

        frame_idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                time_s = frame_idx / fps
                result = detector.track(
                    frame,
                    persist=True,
                    tracker=self.config.tracker,
                    conf=self.config.confidence,
                    iou=self.config.iou,
                    imgsz=self.config.image_size,
                    classes=[self.config.person_class, self.config.ball_class],
                    device=device,
                    verbose=False,
                )[0]

                players: list[dict] = []
                ball: dict | None = None
                if result.boxes is not None and len(result.boxes):
                    xyxy = result.boxes.xyxy.detach().cpu().numpy()
                    cls = result.boxes.cls.detach().cpu().numpy().astype(int)
                    conf = result.boxes.conf.detach().cpu().numpy()
                    ids = result.boxes.id.detach().cpu().numpy().astype(int) if result.boxes.id is not None else np.full(len(xyxy), -1)
                    ball_candidates: list[tuple[float, np.ndarray]] = []

                    for box, class_id, score, track_id in zip(xyxy, cls, conf, ids):
                        if class_id == self.config.ball_class:
                            ball_candidates.append((float(score), box))
                            continue
                        if class_id != self.config.person_class or track_id < 0:
                            continue
                        x1, y1, x2, y2 = box
                        ix1, iy1 = max(0, int(x1)), max(0, int(y1))
                        ix2, iy2 = min(width, int(x2)), min(height, int(y2))
                        crop = frame[iy1:iy2, ix1:ix2]
                        team = classifier.observe(int(track_id), crop)
                        foot = (float((x1 + x2) / 2.0), float(y2))
                        field_pos = self.calibration.project(foot)
                        if not self.calibration.in_bounds(field_pos, margin_m=4.0):
                            continue
                        state = analytics.update_player(int(track_id), time_s, field_pos, team)
                        player = {
                            "track_id": int(track_id),
                            "team": int(team),
                            "bbox": [float(v) for v in box],
                            "confidence": float(score),
                            "foot_pixel": foot,
                            "field_position": field_pos,
                            "speed_kmh": state.speed_kmh,
                            "distance_m": state.distance_m,
                        }
                        players.append(player)
                        records.append(
                            {
                                "frame": frame_idx,
                                "time_s": round(time_s, 4),
                                "track_id": int(track_id),
                                "team": int(team),
                                "x_m": round(field_pos[0], 3),
                                "y_m": round(field_pos[1], 3),
                                "speed_kmh": round(state.speed_kmh, 3),
                                "distance_m": round(state.distance_m, 3),
                                "confidence": round(float(score), 4),
                                "bbox_x1": round(float(x1), 2),
                                "bbox_y1": round(float(y1), 2),
                                "bbox_x2": round(float(x2), 2),
                                "bbox_y2": round(float(y2), 2),
                            }
                        )

                    if ball_candidates:
                        _, best_box = max(ball_candidates, key=lambda item: item[0])
                        bx = float((best_box[0] + best_box[2]) / 2.0)
                        by = float((best_box[1] + best_box[3]) / 2.0)
                        projected = self.calibration.project((bx, by))
                        if self.calibration.in_bounds(projected, margin_m=6.0):
                            if last_ball_field is None or math.dist(last_ball_field, projected) < 18.0:
                                last_ball_field = projected
                                ball = {"pixel": (bx, by), "field_position": projected}

                analytics.update_possession(last_ball_field if ball is not None else None, players)
                if frame_idx % formation_stride == 0:
                    for team in (1, 2):
                        team_positions = [p["field_position"] for p in players if p["team"] == team]
                        formations.observe(team, team_positions)

                if pose_file is not None:
                    for row in self._pose_rows(pose_model, frame, players, frame_idx, time_s):
                        pose_file.write(json.dumps(row, separators=(",", ":")) + "\n")

                rendered = annotate_frame(frame, players, ball)
                if self.config.draw_minimap:
                    minimap = render_minimap(
                        players,
                        ball["field_position"] if ball else None,
                        self.calibration.pitch_length_m,
                        self.calibration.pitch_width_m,
                    )
                    rendered = overlay_minimap(rendered, minimap)
                writer.write(rendered)
                frame_idx += 1
        finally:
            cap.release()
            writer.release()
            if pose_file is not None:
                pose_file.close()

        csv_path = output_dir / "tracking.csv"
        fieldnames = [
            "frame", "time_s", "track_id", "team", "x_m", "y_m", "speed_kmh", "distance_m",
            "confidence", "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer_csv = csv.DictWriter(fh, fieldnames=fieldnames)
            writer_csv.writeheader()
            writer_csv.writerows(records)

        report_files = generate_reports(
            records,
            output_dir,
            self.calibration.pitch_length_m,
            self.calibration.pitch_width_m,
        )
        summary = {
            "input": str(video_path),
            "frames_processed": frame_idx,
            "source_frames_reported": total_frames,
            "fps": fps,
            "resolution": [width, height],
            "pitch_m": [self.calibration.pitch_length_m, self.calibration.pitch_width_m],
            "formations": formations.summary(),
            **analytics.summary(),
            "outputs": {
                "annotated_video": annotated_path.name,
                "tracking_csv": csv_path.name,
                "pose_jsonl": pose_path.name if self.config.enable_pose else None,
                "reports": report_files,
            },
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

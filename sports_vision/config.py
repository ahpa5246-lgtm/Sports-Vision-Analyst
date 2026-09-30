from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PipelineConfig:
    detector_model: str = "yolo26n.pt"
    pose_model: str = "yolo26n-pose.pt"
    tracker: str = "bytetrack.yaml"
    confidence: float = 0.25
    iou: float = 0.50
    image_size: int = 1280
    device: str = "auto"
    person_class: int = 0
    ball_class: int = 32
    enable_pose: bool = False
    pose_stride: int = 5
    formation_interval_s: float = 2.0
    max_player_speed_kmh: float = 45.0
    team_outlier_distance: float = 42.0
    draw_minimap: bool = True

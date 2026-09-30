from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


@dataclass(slots=True)
class PitchCalibration:
    image_points: np.ndarray
    field_points: np.ndarray
    pitch_length_m: float = 105.0
    pitch_width_m: float = 68.0

    def __post_init__(self) -> None:
        self.image_points = np.asarray(self.image_points, dtype=np.float32)
        self.field_points = np.asarray(self.field_points, dtype=np.float32)
        if self.image_points.ndim != 2 or self.image_points.shape[1] != 2:
            raise ValueError("image_points must have shape (N, 2)")
        if self.field_points.shape != self.image_points.shape:
            raise ValueError("field_points must match image_points")
        if len(self.image_points) < 4:
            raise ValueError("At least four point correspondences are required")
        if self.pitch_length_m <= 0 or self.pitch_width_m <= 0:
            raise ValueError("Pitch dimensions must be positive")

    @classmethod
    def load(cls, path: str | Path) -> "PitchCalibration":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            image_points=np.asarray(data["image_points"], dtype=np.float32),
            field_points=np.asarray(data["field_points"], dtype=np.float32),
            pitch_length_m=float(data.get("pitch_length_m", 105.0)),
            pitch_width_m=float(data.get("pitch_width_m", 68.0)),
        )

    def save(self, path: str | Path) -> None:
        payload = {
            "pitch_length_m": self.pitch_length_m,
            "pitch_width_m": self.pitch_width_m,
            "image_points": self.image_points.tolist(),
            "field_points": self.field_points.tolist(),
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @property
    def matrix(self) -> np.ndarray:
        if len(self.image_points) == 4:
            return cv2.getPerspectiveTransform(self.image_points, self.field_points)
        matrix, mask = cv2.findHomography(self.image_points, self.field_points, method=cv2.RANSAC)
        if matrix is None:
            raise ValueError("Could not estimate homography from calibration points")
        if mask is not None and int(mask.sum()) < 4:
            raise ValueError("Homography has fewer than four inlier correspondences")
        return matrix

    def project(self, point: tuple[float, float] | np.ndarray) -> tuple[float, float]:
        pts = np.asarray(point, dtype=np.float32).reshape(1, 1, 2)
        out = cv2.perspectiveTransform(pts, self.matrix).reshape(2)
        return float(out[0]), float(out[1])

    def project_many(self, points: Iterable[tuple[float, float]]) -> np.ndarray:
        arr = np.asarray(list(points), dtype=np.float32)
        if arr.size == 0:
            return np.empty((0, 2), dtype=np.float32)
        return cv2.perspectiveTransform(arr.reshape(-1, 1, 2), self.matrix).reshape(-1, 2)

    def in_bounds(self, point: tuple[float, float], margin_m: float = 2.0) -> bool:
        x, y = point
        return (
            -margin_m <= x <= self.pitch_length_m + margin_m
            and -margin_m <= y <= self.pitch_width_m + margin_m
        )

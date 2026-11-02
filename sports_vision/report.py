from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .visualize import draw_pitch


def _heatmap_image(points: list[tuple[float, float]], pitch_length: float, pitch_width: float, width: int = 840) -> np.ndarray:
    height = int(width * pitch_width / pitch_length)
    grid = np.zeros((68, 105), dtype=np.float32)
    for x, y in points:
        if 0 <= x <= pitch_length and 0 <= y <= pitch_width:
            gx = min(grid.shape[1] - 1, max(0, int(x / pitch_length * grid.shape[1])))
            gy = min(grid.shape[0] - 1, max(0, int(y / pitch_width * grid.shape[0])))
            grid[gy, gx] += 1.0
    grid = cv2.GaussianBlur(grid, (0, 0), 2.2)
    if float(grid.max()) > 0:
        grid = grid / float(grid.max())
    heat = (grid * 255).astype(np.uint8)
    heat = cv2.resize(heat, (width, height), interpolation=cv2.INTER_CUBIC)
    heat = cv2.applyColorMap(heat, cv2.COLORMAP_TURBO)
    pitch = draw_pitch(width, height)
    return cv2.addWeighted(pitch, 0.35, heat, 0.65, 0)


def generate_reports(records: list[dict], out_dir: Path, pitch_length: float, pitch_width: float) -> list[str]:
    created: list[str] = []
    for team in (1, 2):
        points = [(float(r["x_m"]), float(r["y_m"])) for r in records if int(r["team"]) == team]
        if not points:
            continue
        img = _heatmap_image(points, pitch_length, pitch_width)
        name = f"team_{team}_heatmap.png"
        cv2.imwrite(str(out_dir / name), img)
        created.append(name)
    return created

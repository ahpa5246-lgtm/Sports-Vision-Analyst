from __future__ import annotations

import cv2
import numpy as np


TEAM_COLORS = {0: (180, 180, 180), 1: (255, 90, 60), 2: (60, 90, 255)}
BALL_COLOR = (30, 220, 255)


def field_to_canvas(point: tuple[float, float], width: int, height: int, pitch_length: float, pitch_width: float) -> tuple[int, int]:
    x, y = point
    px = int(np.clip(x / pitch_length, 0, 1) * (width - 1))
    py = int(np.clip(y / pitch_width, 0, 1) * (height - 1))
    return px, py


def draw_pitch(width: int, height: int) -> np.ndarray:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (50, 120, 50)
    white = (235, 235, 235)
    t = max(1, width // 240)
    cv2.rectangle(img, (3, 3), (width - 4, height - 4), white, t)
    cv2.line(img, (width // 2, 3), (width // 2, height - 4), white, t)
    cv2.circle(img, (width // 2, height // 2), max(8, int(height * 0.135)), white, t)
    box_w, box_h = int(width * 0.16), int(height * 0.59)
    y1 = (height - box_h) // 2
    cv2.rectangle(img, (3, y1), (box_w, y1 + box_h), white, t)
    cv2.rectangle(img, (width - box_w - 4, y1), (width - 4, y1 + box_h), white, t)
    return img


def render_minimap(
    players: list[dict],
    ball_position: tuple[float, float] | None,
    pitch_length: float,
    pitch_width: float,
    width: int = 360,
) -> np.ndarray:
    height = int(width * pitch_width / pitch_length)
    canvas = draw_pitch(width, height)
    for p in players:
        team = int(p.get("team", 0))
        x, y = field_to_canvas(p["field_position"], width, height, pitch_length, pitch_width)
        cv2.circle(canvas, (x, y), 5, TEAM_COLORS.get(team, TEAM_COLORS[0]), -1, cv2.LINE_AA)
        cv2.putText(canvas, str(p["track_id"]), (x + 6, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 255, 255), 1, cv2.LINE_AA)
    if ball_position is not None:
        x, y = field_to_canvas(ball_position, width, height, pitch_length, pitch_width)
        cv2.circle(canvas, (x, y), 4, BALL_COLOR, -1, cv2.LINE_AA)
    return canvas


def annotate_frame(frame: np.ndarray, players: list[dict], ball: dict | None) -> np.ndarray:
    out = frame.copy()
    for p in players:
        x1, y1, x2, y2 = map(int, p["bbox"])
        team = int(p.get("team", 0))
        color = TEAM_COLORS.get(team, TEAM_COLORS[0])
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"#{p['track_id']} T{team or '?'} {p.get('speed_kmh', 0.0):.1f} km/h"
        cv2.putText(out, label, (x1, max(18, y1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, color, 2, cv2.LINE_AA)
        fx, fy = map(int, p["foot_pixel"])
        cv2.circle(out, (fx, fy), 3, color, -1, cv2.LINE_AA)
    if ball is not None:
        bx, by = map(int, ball["pixel"])
        cv2.circle(out, (bx, by), 8, BALL_COLOR, 2, cv2.LINE_AA)
        cv2.putText(out, "BALL", (bx + 8, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, BALL_COLOR, 2, cv2.LINE_AA)
    return out


def overlay_minimap(frame: np.ndarray, minimap: np.ndarray, margin: int = 16) -> np.ndarray:
    h, w = minimap.shape[:2]
    fh, fw = frame.shape[:2]
    if h + 2 * margin > fh or w + 2 * margin > fw:
        scale = min((fw - 2 * margin) / max(w, 1), (fh - 2 * margin) / max(h, 1), 1.0)
        minimap = cv2.resize(minimap, (max(1, int(w * scale)), max(1, int(h * scale))))
        h, w = minimap.shape[:2]
    x1, y1 = fw - w - margin, margin
    roi = frame[y1 : y1 + h, x1 : x1 + w]
    frame[y1 : y1 + h, x1 : x1 + w] = cv2.addWeighted(roi, 0.18, minimap, 0.82, 0)
    return frame

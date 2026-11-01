from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class PlayerAccumulator:
    track_id: int
    max_speed_kmh: float = 45.0
    team: int = 0
    distance_m: float = 0.0
    speed_kmh: float = 0.0
    top_speed_kmh: float = 0.0
    last_position: tuple[float, float] | None = None
    last_time_s: float | None = None
    speed_window: deque[float] = field(default_factory=lambda: deque(maxlen=5))
    samples: int = 0

    def update(self, time_s: float, position: tuple[float, float], team: int = 0) -> None:
        if team:
            self.team = team
        self.samples += 1
        if self.last_position is not None and self.last_time_s is not None:
            dt = time_s - self.last_time_s
            if dt > 1e-6:
                step = math.dist(self.last_position, position)
                raw_speed = (step / dt) * 3.6
                if raw_speed <= self.max_speed_kmh:
                    self.distance_m += step
                    self.speed_window.append(raw_speed)
                    self.speed_kmh = float(np.median(np.asarray(self.speed_window, dtype=np.float32)))
                    self.top_speed_kmh = max(self.top_speed_kmh, self.speed_kmh)
        self.last_position = position
        self.last_time_s = time_s


class MatchAnalytics:
    def __init__(self, max_player_speed_kmh: float = 45.0) -> None:
        self.max_player_speed_kmh = max_player_speed_kmh
        self.players: dict[int, PlayerAccumulator] = {}
        self.possession_frames: Counter[int] = Counter()

    def update_player(self, track_id: int, time_s: float, position: tuple[float, float], team: int) -> PlayerAccumulator:
        state = self.players.setdefault(
            track_id,
            PlayerAccumulator(track_id=track_id, max_speed_kmh=self.max_player_speed_kmh),
        )
        state.update(time_s, position, team)
        return state

    def update_possession(
        self,
        ball_position: tuple[float, float] | None,
        visible_players: list[dict],
        max_control_distance_m: float = 3.0,
    ) -> None:
        if ball_position is None:
            return
        candidates = [p for p in visible_players if p.get("team", 0) in (1, 2)]
        if not candidates:
            return
        nearest = min(candidates, key=lambda p: math.dist(ball_position, p["field_position"]))
        if math.dist(ball_position, nearest["field_position"]) <= max_control_distance_m:
            self.possession_frames[int(nearest["team"])] += 1

    def summary(self) -> dict:
        total_possession = sum(self.possession_frames.values())
        possession = {
            str(team): (100.0 * self.possession_frames[team] / total_possession if total_possession else 0.0)
            for team in (1, 2)
        }
        players = {}
        for tid, state in sorted(self.players.items()):
            players[str(tid)] = {
                "team": state.team,
                "distance_m": round(state.distance_m, 2),
                "top_speed_kmh": round(state.top_speed_kmh, 2),
                "samples": state.samples,
            }
        team_distance = {
            str(team): round(sum(p.distance_m for p in self.players.values() if p.team == team), 2)
            for team in (1, 2)
        }
        return {"players": players, "team_distance_m": team_distance, "possession_pct": possession}


COMMON_FORMATIONS = [
    (4, 4, 2),
    (4, 3, 3),
    (3, 5, 2),
    (3, 4, 3),
    (5, 3, 2),
    (5, 4, 1),
    (4, 2, 3, 1),
    (4, 1, 4, 1),
    (3, 4, 2, 1),
]


def _kmeans_1d(values: np.ndarray, k: int, iterations: int = 30) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    if len(values) < k:
        raise ValueError("Not enough values for requested clusters")
    centers = np.quantile(values, np.linspace(0.1, 0.9, k)).astype(np.float32)
    labels = np.zeros(len(values), dtype=np.int32)
    for _ in range(iterations):
        distances = np.abs(values[:, None] - centers[None, :])
        new_labels = distances.argmin(axis=1)
        new_centers = centers.copy()
        for i in range(k):
            members = values[new_labels == i]
            if len(members):
                new_centers[i] = float(members.mean())
        if np.array_equal(new_labels, labels) and np.allclose(new_centers, centers):
            break
        labels, centers = new_labels, new_centers
    order = np.argsort(centers)
    remap = np.zeros(k, dtype=np.int32)
    remap[order] = np.arange(k)
    return remap[labels], centers[order]


class FormationEstimator:
    """Conservative common-formation estimator from metric player positions."""

    def __init__(self) -> None:
        self.observations: dict[int, Counter[str]] = defaultdict(Counter)

    @staticmethod
    def estimate(positions: list[tuple[float, float]]) -> str | None:
        if len(positions) < 9:
            return None
        xs = np.asarray([p[0] for p in positions], dtype=np.float32)
        extreme_candidates = {int(xs.argmin()), int(xs.argmax())}
        best: tuple[float, str] | None = None

        for gk_idx in extreme_candidates:
            own_goal_left = gk_idx == int(xs.argmin())
            outfield = np.delete(xs, gk_idx)
            for k in (3, 4):
                if len(outfield) < k:
                    continue
                labels, _ = _kmeans_1d(outfield, k)
                counts = [int(np.sum(labels == i)) for i in range(k)]
                if not own_goal_left:
                    counts = counts[::-1]
                for template in COMMON_FORMATIONS:
                    if len(template) != k:
                        continue
                    missing = 10 - len(outfield)
                    l1 = sum(abs(a - b) for a, b in zip(counts, template))
                    score = float(l1 + max(0, missing) * 0.35)
                    if best is None or score < best[0]:
                        best = (score, "-".join(map(str, template)))
        return best[1] if best else None

    def observe(self, team: int, positions: list[tuple[float, float]]) -> str | None:
        formation = self.estimate(positions)
        if formation:
            self.observations[team][formation] += 1
        return formation

    def summary(self) -> dict[str, str | None]:
        result: dict[str, str | None] = {}
        for team in (1, 2):
            counter = self.observations.get(team)
            result[str(team)] = counter.most_common(1)[0][0] if counter else None
        return result

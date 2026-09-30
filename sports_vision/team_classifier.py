from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np


class TeamColorClassifier:
    """Online jersey-color clustering with stable team IDs and outlier rejection."""

    def __init__(self, min_tracks: int = 6, outlier_distance: float = 42.0) -> None:
        self.min_tracks = min_tracks
        self.outlier_distance = outlier_distance
        self.track_features: dict[int, np.ndarray] = {}
        self.track_seen: defaultdict[int, int] = defaultdict(int)
        self.centers: np.ndarray | None = None
        self._observations = 0

    @staticmethod
    def _feature(crop_bgr: np.ndarray) -> np.ndarray | None:
        if crop_bgr is None or crop_bgr.size == 0:
            return None
        h, w = crop_bgr.shape[:2]
        if h < 18 or w < 10:
            return None
        y1, y2 = int(h * 0.18), int(h * 0.58)
        x1, x2 = int(w * 0.18), int(w * 0.82)
        torso = crop_bgr[y1:y2, x1:x2]
        if torso.size == 0:
            return None
        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        mask = (hsv[..., 1] >= 28) & (hsv[..., 2] >= 35) & (hsv[..., 2] <= 245)
        lab = cv2.cvtColor(torso, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
        selected = lab[mask.reshape(-1)]
        if len(selected) < 25:
            selected = lab
        return np.median(selected, axis=0).astype(np.float32)

    def observe(self, track_id: int, crop_bgr: np.ndarray) -> int:
        feat = self._feature(crop_bgr)
        if feat is None:
            return self.classify(track_id)
        self._observations += 1
        self.track_seen[track_id] += 1
        if track_id in self.track_features:
            alpha = 0.18
            self.track_features[track_id] = (1.0 - alpha) * self.track_features[track_id] + alpha * feat
        else:
            self.track_features[track_id] = feat

        if len(self.track_features) >= self.min_tracks and (
            self.centers is None or self._observations % 20 == 0
        ):
            self._refit()
        return self.classify(track_id)

    def _refit(self) -> None:
        data = np.asarray([f for _, f in sorted(self.track_features.items())], dtype=np.float32)
        if len(data) < 2:
            return
        k = 3 if len(data) >= 8 else 2
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        counts = np.bincount(labels.reshape(-1), minlength=k)
        keep = np.argsort(counts)[-2:]
        new_centers = centers[keep].astype(np.float32)

        if self.centers is not None:
            same = np.linalg.norm(new_centers[0] - self.centers[0]) + np.linalg.norm(new_centers[1] - self.centers[1])
            swapped = np.linalg.norm(new_centers[1] - self.centers[0]) + np.linalg.norm(new_centers[0] - self.centers[1])
            if swapped < same:
                new_centers = new_centers[::-1]
        self.centers = new_centers

    def classify(self, track_id: int) -> int:
        feat = self.track_features.get(track_id)
        if feat is None or self.centers is None:
            return 0
        distances = np.linalg.norm(self.centers - feat[None, :], axis=1)
        idx = int(np.argmin(distances))
        if float(distances[idx]) > self.outlier_distance:
            return 0
        return idx + 1

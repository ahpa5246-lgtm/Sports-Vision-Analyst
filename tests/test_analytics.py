from sports_vision.analytics import FormationEstimator, PlayerAccumulator


def test_distance_and_speed_reject_impossible_jump():
    p = PlayerAccumulator(track_id=1, max_speed_kmh=45.0)
    p.update(0.0, (0.0, 0.0), 1)
    p.update(1.0, (5.0, 0.0), 1)
    assert abs(p.distance_m - 5.0) < 1e-6
    assert abs(p.speed_kmh - 18.0) < 1e-6
    p.update(2.0, (100.0, 0.0), 1)
    assert abs(p.distance_m - 5.0) < 1e-6


def test_formation_estimator_recognizes_433_like_shape():
    points = [
        (4, 34),
        (25, 8), (24, 25), (24, 43), (25, 60),
        (52, 17), (50, 34), (52, 51),
        (78, 13), (81, 34), (78, 55),
    ]
    assert FormationEstimator.estimate(points) == "4-3-3"

import pytest

from sports_vision.analytics import PlayerAccumulator


@pytest.mark.parametrize(
    ("time_s", "position"),
    [
        (float("nan"), (1.0, 0.0)),
        (float("inf"), (1.0, 0.0)),
        (2.0, (float("nan"), 0.0)),
        (2.0, (float("inf"), 0.0)),
        (2.0, (0.0, float("-inf"))),
    ],
)
def test_non_finite_samples_do_not_mutate_tracking_state(time_s, position):
    player = PlayerAccumulator(track_id=1)
    player.update(0.0, (0.0, 0.0), team=1)

    player.update(time_s, position, team=2)

    assert player.team == 1
    assert player.samples == 1
    assert player.last_time_s == 0.0
    assert player.last_position == (0.0, 0.0)

    player.update(1.0, (1.0, 0.0), team=1)

    assert player.distance_m == pytest.approx(1.0)
    assert player.last_time_s == 1.0
    assert player.samples == 2


def test_out_of_order_sample_does_not_rewind_tracking_state():
    player = PlayerAccumulator(track_id=1)
    player.update(0.0, (0.0, 0.0), team=1)
    player.update(1.0, (1.0, 0.0), team=1)

    player.update(0.5, (20.0, 0.0), team=2)

    assert player.team == 1
    assert player.samples == 2
    assert player.last_time_s == 1.0
    assert player.last_position == (1.0, 0.0)

    player.update(2.0, (2.0, 0.0), team=1)

    assert player.distance_m == pytest.approx(2.0)
    assert player.last_time_s == 2.0
    assert player.samples == 3

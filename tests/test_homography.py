import numpy as np

from sports_vision.homography import PitchCalibration


def test_corner_mapping_and_center():
    calibration = PitchCalibration(
        image_points=np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=np.float32),
        field_points=np.array([[0, 0], [105, 0], [105, 68], [0, 68]], dtype=np.float32),
    )
    assert np.allclose(calibration.project((0, 0)), (0, 0), atol=1e-4)
    assert np.allclose(calibration.project((50, 25)), (52.5, 34.0), atol=1e-3)
    assert calibration.in_bounds((52.5, 34.0))
    assert not calibration.in_bounds((130.0, 34.0), margin_m=0)

import numpy as np
import pytest
from shapely.geometry import box

from predictors.predictors.floorplans import FloorplanPredictor


@pytest.mark.parametrize("pixels_per_meter", [40.0, 80.0])
@pytest.mark.parametrize(
    "roi, expected_predicted_shapes",
    [
        ([(0, 0, 100, 100)], (box(25.0, 25.0, 75.0, 75.0),)),
        ([(50, 50, 100, 100)], (box(62.5, 62.5, 87.5, 87.5),)),
        (
            [(0, 0, 50, 50), (50, 50, 100, 100)],
            (
                box(12.5, 12.5, 37.5, 37.5),
                box(62.5, 62.5, 87.5, 87.5),
            ),
        ),
    ],
)
def test_predict(roi, pixels_per_meter, expected_predicted_shapes, fake_predictor):
    input_image = np.zeros((200, 200, 3), dtype="uint8")
    labels, shapes = FloorplanPredictor().predict(
        fake_predictor, image=input_image, roi=roi, pixels_per_meter=pixels_per_meter
    )
    assert shapes == expected_predicted_shapes


@pytest.mark.parametrize(
    "roi, pixels_per_meter, expected_cropped_and_scaled_image",
    [
        ([(0, 0, 1, 1)], 20.0, np.zeros((2, 2, 3), dtype="uint8")),
        ([(2, 0, 4, 2)], 20.0, np.ones((4, 4, 3), dtype="uint8")),
        ([(2, 0, 4, 2)], 40.0, np.ones((2, 2, 3), dtype="uint8")),
        ([(2, 0, 4, 2)], 80.0, np.ones((1, 1, 3), dtype="uint8")),
    ],
)
def test_predict_calls_predictor_with_scaled_and_cropped_image(
    roi, pixels_per_meter, expected_cropped_and_scaled_image, fake_predictor
):
    input_image = np.array(
        [
            [[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1]],
            [[0, 0, 0], [0, 0, 0], [1, 1, 1], [1, 1, 1]],
            [[2, 2, 2], [2, 2, 2], [3, 3, 3], [3, 3, 3]],
            [[2, 2, 2], [2, 2, 2], [3, 3, 3], [3, 3, 3]],
        ],
        dtype="uint8",
    )

    FloorplanPredictor().predict(
        fake_predictor, image=input_image, roi=roi, pixels_per_meter=pixels_per_meter
    )
    ((image_passed_to_predictor,), _) = fake_predictor.predict.call_args
    np.testing.assert_array_equal(
        image_passed_to_predictor, expected_cropped_and_scaled_image
    )

from typing import Tuple

from shapely.affinity import translate
from shapely.geometry import Polygon

from predictors.predictors.base import MultiClassPrediction
from predictors.predictors.constants import ClassLabel
from predictors.predictors.icons import IconPredictor
from predictors.predictors.roi import RoiPredictor
from predictors.predictors.spaces import SpacePredictor
from predictors.predictors.walls import WallPredictor


class FloorplanPredictor:
    def __init__(self, *args, **kwargs):
        self.roi_predictor = RoiPredictor()
        self.icons_predictor = IconPredictor()
        self.wall_predictor = WallPredictor()
        self.space_predictor = SpacePredictor()

    def predict_walls(self, image) -> MultiClassPrediction:
        return self._predict(self.wall_predictor, image)

    def predict_icons(self, image) -> MultiClassPrediction:
        return self._predict(self.icons_predictor, image)

    def predict_spaces(self, image) -> MultiClassPrediction:
        return self._predict(self.space_predictor, image)

    def _predict(self, predictor, image) -> MultiClassPrediction:
        labels: Tuple[ClassLabel, ...] = tuple()
        shapes: Tuple[Polygon, ...] = tuple()
        for bbox in self.roi_predictor.predict(image=image):
            xmin, ymin, xmax, ymax = map(int, bbox.bounds)
            image_roi = image[ymin:ymax, xmin:xmax, :]

            predicted_labels, predicted_shapes = predictor.predict(image_roi)
            labels += predicted_labels
            shapes += predicted_shapes
            shapes = tuple(translate(s, xoff=xmin, yoff=ymin) for s in shapes)

        return labels, shapes

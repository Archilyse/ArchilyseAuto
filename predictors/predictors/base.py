from typing import Tuple, Union

from shapely.geometry import Polygon

from predictors.predictors.constants import ClassLabel

MultiClassPrediction = Tuple[Tuple[ClassLabel, ...], Tuple[Polygon, ...]]
SingleClassPrediction = Tuple[Polygon, ...]


class BasePredictor:
    def predict(self, image) -> Union[SingleClassPrediction, MultiClassPrediction]:
        """predicts labels and shapes"""
        raise NotImplementedError

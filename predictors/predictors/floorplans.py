from typing import Dict, List, Optional, Tuple

import numpy as np
import PIL.Image
from shapely.affinity import scale, translate
from shapely.geometry import Polygon

from predictors.predictors.base import BasePredictor, MultiClassPrediction
from predictors.predictors.constants import ClassLabel


def get_models() -> Dict[str, BasePredictor]:
    from predictors.predictors.icons import IconPredictor
    from predictors.predictors.roi import RoiPredictor
    from predictors.predictors.spaces import SpacePredictor
    from predictors.predictors.walls import WallPredictor

    return {
        "roi": RoiPredictor(),
        "icons_v1": IconPredictor(version=1),
        "icons_v2": IconPredictor(version=2),
        "walls": WallPredictor(),
        "spaces": SpacePredictor(),
    }


class FloorplanPredictor:
    TARGET_PIXELS_PER_METER = 40

    @classmethod
    def _get_image_roi_scaled(
        cls,
        image,
        roi_bbox: Tuple[int, int, int, int],
        pixels_per_meter: Optional[float] = None,
    ):
        xmin, ymin, xmax, ymax = roi_bbox
        image_cropped = image[ymin:ymax, xmin:xmax, :]
        if pixels_per_meter:
            target_scale_factor = cls.TARGET_PIXELS_PER_METER / pixels_per_meter
            cropped_height, cropped_width = image_cropped.shape[:2]
            image_cropped_and_scaled = np.array(
                PIL.Image.fromarray(image_cropped).resize(
                    (
                        int(target_scale_factor * cropped_width),
                        int(target_scale_factor * cropped_height),
                    )
                )
            )
            return image_cropped_and_scaled
        return image_cropped

    @classmethod
    def _transform_shape(
        cls,
        shape: Polygon,
        roi_bbox: Tuple[int, int, int, int],
        pixels_per_meter: Optional[float] = None,
    ):
        if pixels_per_meter:
            target_scale_factor = pixels_per_meter / cls.TARGET_PIXELS_PER_METER
            shape = scale(
                shape,
                xfact=target_scale_factor,
                yfact=target_scale_factor,
                origin=(0, 0),
            )
        xmin, ymin = roi_bbox[:2]
        return translate(shape, xoff=xmin, yoff=ymin)

    @classmethod
    def predict(
        cls,
        model: BasePredictor,
        image,
        roi: List[Tuple[int, int, int, int]],
        pixels_per_meter: Optional[float] = None,
    ) -> MultiClassPrediction:
        labels: Tuple[ClassLabel, ...] = tuple()
        shapes: Tuple[Polygon, ...] = tuple()

        for roi_bbox in roi:
            image_roi = cls._get_image_roi_scaled(
                image=image, roi_bbox=roi_bbox, pixels_per_meter=pixels_per_meter
            )
            predicted_labels, predicted_shapes = model.predict(image_roi)
            labels += predicted_labels
            shapes += tuple(
                cls._transform_shape(s, roi_bbox, pixels_per_meter)
                for s in predicted_shapes
            )
        return labels, shapes

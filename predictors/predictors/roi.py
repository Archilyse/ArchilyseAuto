import cv2
from shapely import affinity
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from predictors.predictors.base import BasePredictor, SingleClassPrediction
from predictors.predictors.utils.geometry import get_polygons
from predictors.predictors.yolo import darknet


class RoiPredictor(BasePredictor):
    def __init__(self, threshold=0.5, roi_scale=1.1):
        # TODO Hardcoded paths
        self.network = darknet.load_network(
            config_file="resources/yolo-roi.cfg",
            weights="resources/yolo-roi-latest.weights",
            batch_size=1,
        )
        self.threshold = threshold
        self.roi_scale = roi_scale

    def predict(self, image) -> SingleClassPrediction:
        original_height, original_width = image.shape[:2]
        darknet_width = darknet.network_width(self.network)
        darknet_height = darknet.network_height(self.network)
        darknet_image = self._resized_darknet_image(
            darknet_height, darknet_width, image
        )

        detections = darknet.detect_image(
            self.network, ["layout"], darknet_image, thresh=self.threshold
        )

        results = []
        for _, confidence, bbox in detections:
            if float(confidence) > self.threshold:
                bbox_scaled = self._resize_box(
                    darknet.bbox2points(bbox),
                    original_size=(original_width, original_height),
                    resized_size=(darknet_width, darknet_height),
                )
                results.append(bbox_scaled)

        union = unary_union(results)
        return tuple(get_polygons(union))

    @staticmethod
    def _resized_darknet_image(darknet_height, darknet_width, image):
        """Darknet doesn't accept numpy images.
        Create one with image we reuse for each detect
        """
        darknet_image = darknet.make_image(darknet_width, darknet_height, 3)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_resized = cv2.resize(
            image_rgb, (darknet_width, darknet_height), interpolation=cv2.INTER_LINEAR
        )
        darknet.copy_image_from_bytes(darknet_image, image_resized.tobytes())
        return darknet_image

    def _resize_box(
        self,
        box_points,
        original_size,
        resized_size,
    ) -> Polygon:
        ratio = (original_size[0] / resized_size[0], original_size[1] / resized_size[1])
        xmin, ymin, xmax, ymax = box_points
        xmin = xmin * ratio[0]
        ymin = ymin * ratio[1]
        xmax = xmax * ratio[0]
        ymax = ymax * ratio[1]
        scaled_box = affinity.scale(
            box(xmin, ymin, xmax, ymax),
            xfact=self.roi_scale,
            yfact=self.roi_scale,
            origin="center",
        )
        # trim scaled box to image size
        scaled_box = scaled_box.intersection(
            box(0, 0, original_size[0], original_size[1])
        )
        return scaled_box

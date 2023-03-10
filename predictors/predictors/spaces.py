from detectron2 import model_zoo
from detectron2.config import get_cfg

from predictors.predictors.base import BasePredictor, MultiClassPrediction
from predictors.predictors.constants import ClassLabel
from predictors.predictors.utils.detectron import TiledPredictor
from predictors.predictors.utils.geometry import mask_to_shape


class SpacePredictor(BasePredictor):
    BUFFER_PX = 40
    UNBUFFER_PX = 30

    def __init__(self):
        # NOTE: For foreground prediction getting the instances correct doesn't matter
        # as we are union-ing all spaces later anyway
        self.predictor = TiledPredictor(
            self.config(), max_instance_size=100, merge_threshold=0.1, tile_size=1024
        )

    @staticmethod
    def config():
        import torch

        from predictors.tasks.logging import logger

        cfg = get_cfg()
        cfg.merge_from_file(
            model_zoo.get_config_file(
                "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
            )
        )
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 11
        cfg.MODEL.WEIGHTS = "resources/spaces_model_final.pth"
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
        cfg.MODEL.DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
        logger.info(f"SpacePredictor using device {cfg.MODEL.DEVICE}")
        return cfg

    def predict(self, image) -> MultiClassPrediction:
        instances = self.predictor(image)["instances"].to("cpu")

        space_masks = instances.pred_masks
        space_polygons = tuple(map(mask_to_shape, space_masks))

        labels = (ClassLabel.SPACE,) * len(space_polygons)
        shapes = space_polygons

        return labels, shapes

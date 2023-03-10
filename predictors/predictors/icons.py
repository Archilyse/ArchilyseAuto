import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg

from predictors.predictors.base import BasePredictor, MultiClassPrediction
from predictors.predictors.constants import ClassLabel
from predictors.predictors.utils.detectron import TiledPredictor
from predictors.predictors.utils.geometry import mask_to_shape


class IconPredictor(BasePredictor):
    LABELS = [
        ClassLabel.TOILET,
        ClassLabel.BATHTUB,
        ClassLabel.SINK,
        ClassLabel.SHOWER,
    ]

    def __init__(self):
        self.predictor = TiledPredictor(
            self.config(), max_instance_size=100, merge_threshold=0.8, tile_size=800
        )

    @staticmethod
    def config():
        from predictors.tasks.logging import logger

        cfg = get_cfg()
        cfg.merge_from_file(
            model_zoo.get_config_file(
                "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
            )
        )
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 4
        cfg.MODEL.WEIGHTS = "resources/icons_model_final.pth"
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.9
        cfg.MODEL.DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

        logger.info(f"IconPredictor using device {cfg.MODEL.DEVICE}")
        return cfg

    def index_to_label(self, index) -> ClassLabel:
        return self.LABELS[index]

    def predict(self, image) -> MultiClassPrediction:
        instances = self.predictor(image)["instances"].to("cpu")
        labels = tuple(map(self.index_to_label, instances.pred_classes))
        shapes = tuple(
            mask_to_shape(mask).minimum_rotated_rectangle
            for mask in instances.pred_masks
        )
        return labels, shapes

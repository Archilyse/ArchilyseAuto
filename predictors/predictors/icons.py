from collections import defaultdict

import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg

from predictors.predictors.base import BasePredictor, MultiClassPrediction
from predictors.predictors.constants import ClassLabel
from predictors.predictors.utils.detectron import TiledPredictor
from predictors.predictors.utils.geometry import mask_to_shape


class IconModelConfig:
    def __init__(
        self,
        weights,
        class_labels,
        confidence_thresholds,
        max_instance_size,
        merge_threshold,
        tile_size,
    ):
        self.tile_size = tile_size
        self.merge_threshold = merge_threshold
        self.max_instance_size = max_instance_size
        self.weights = weights
        self.class_labels = class_labels
        self.confidence_thresholds = confidence_thresholds


MODEL_CONFIG = {
    1: IconModelConfig(
        class_labels=[
            ClassLabel.TOILET,
            ClassLabel.BATHTUB,
            ClassLabel.SINK,
            ClassLabel.SHOWER,
        ],
        max_instance_size=100,
        merge_threshold=0.8,
        tile_size=800,
        weights="resources/icons_model_final.pth",
        confidence_thresholds=defaultdict(lambda: 0.9),
    ),
    2: IconModelConfig(
        class_labels=[
            ClassLabel.TOILET,
            ClassLabel.BATHTUB,
            ClassLabel.SINK,
            ClassLabel.SHOWER,
            ClassLabel.STAIRS,
            ClassLabel.ELEVATOR,
            ClassLabel.WINDOW,
            ClassLabel.DOOR,
        ],
        max_instance_size=400,
        merge_threshold=0.4,
        tile_size=1024,
        weights="resources/icons_model_final_2.pth",
        confidence_thresholds=defaultdict(
            lambda: 0.9,
            {
                ClassLabel.WINDOW: 0.5,
                ClassLabel.DOOR: 0.5,
            },
        ),
    ),
}


class IconPredictor(BasePredictor):
    def __init__(self, version: int):
        self.icon_model_config = MODEL_CONFIG[version]
        self.predictor = TiledPredictor(
            self.detectron_cfg(self.icon_model_config),
            max_instance_size=self.icon_model_config.max_instance_size,
            merge_threshold=self.icon_model_config.merge_threshold,
            tile_size=self.icon_model_config.tile_size,
        )

    @staticmethod
    def detectron_cfg(icon_model_config):
        from predictors.tasks.utils.logging import logger

        cfg = get_cfg()
        cfg.merge_from_file(
            model_zoo.get_config_file(
                "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
            )
        )
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(icon_model_config.class_labels)
        cfg.MODEL.WEIGHTS = icon_model_config.weights
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = min(
            icon_model_config.confidence_thresholds[label]
            for label in icon_model_config.class_labels
        )
        cfg.MODEL.DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

        logger.info(f"IconPredictor using device {cfg.MODEL.DEVICE}")
        return cfg

    def index_to_label(self, label_index) -> ClassLabel:
        return self.icon_model_config.class_labels[label_index]

    def score_filter(self, label_index, score):
        return (
            score
            >= self.icon_model_config.confidence_thresholds[
                self.index_to_label(label_index)
            ]
        )

    def predict(self, image) -> MultiClassPrediction:
        instances = self.predictor(image)["instances"].to("cpu")
        labels = tuple(
            self.index_to_label(label_index)
            for label_index, score in zip(instances.pred_classes, instances.scores)
            if self.score_filter(label_index, score)
        )
        shapes = tuple(
            mask_to_shape(mask).minimum_rotated_rectangle
            for label_index, mask, score in zip(
                instances.pred_classes, instances.pred_masks, instances.scores
            )
            if self.score_filter(label_index, score)
        )
        return labels, shapes

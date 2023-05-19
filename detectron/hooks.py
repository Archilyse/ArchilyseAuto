import os
import random
from pathlib import Path

import detectron2.utils.comm as comm
import mlflow
import torch
from detectron2.data import DatasetCatalog, MetadataCatalog
from detectron2.engine import HookBase
from evaluator import BBoxEvaluator
from outputs import generate_plots
from tiled_trainer import TiledPredictor


class ValidationLoss(HookBase):
    def __init__(
        self,
        data_loader,
        n_val_loss: int = 100,
    ):
        super().__init__()
        self._loader = iter(data_loader)
        self.validation_loss_every_n_iterations = n_val_loss
        self.iterations_til_validation = 0

    def after_step(self):
        if self.iterations_til_validation != 0:
            self.iterations_til_validation -= 1
            return
        self.iterations_til_validation = self.validation_loss_every_n_iterations

        data = next(self._loader)
        with torch.no_grad():
            loss_dict = self.trainer.model(data)

            losses = sum(loss_dict.values())
            assert torch.isfinite(losses).all(), loss_dict

            loss_dict_reduced = {
                "val_" + k: v.item() for k, v in comm.reduce_dict(loss_dict).items()
            }
            losses_reduced = sum(loss for loss in loss_dict_reduced.values())
            if comm.is_main_process():
                self.trainer.storage.put_scalars(
                    total_val_loss=losses_reduced, **loss_dict_reduced
                )


class MLFlowHook(HookBase):
    """
    A custom hook class that logs artifacts, metrics, and parameters to MLflow.
    """

    def __init__(self, cfg, n_val_loss):
        super().__init__()
        self.cfg = cfg.clone()
        self.validation_loss_every_n_iterations = n_val_loss
        self.iterations_til_validation = 0

    def after_step(self):
        if self.iterations_til_validation != 0:
            self.iterations_til_validation -= 1
            return
        self.iterations_til_validation = self.validation_loss_every_n_iterations

        with torch.no_grad():
            latest_metrics = self.trainer.storage.latest()
            for k, v in latest_metrics.items():
                mlflow.log_metric(key=k, value=v[0], step=v[1])

    def after_train(self):
        with torch.no_grad():
            with open(os.path.join(self.cfg.OUTPUT_DIR, "model-config.yaml"), "w") as f:
                f.write(self.cfg.dump())


class EvaluationHook:
    def __init__(self, trainer, tile_size):
        self.trainer, self.tile_size = trainer, tile_size
        self._sample_images = []

    def _get_latest_weights(self):
        cfg = self.trainer.cfg
        if cfg.SOLVER.MAX_ITER == self.trainer.iter:
            return Path(cfg.OUTPUT_DIR, "model_final.pth").as_posix()
        return Path(
            cfg.OUTPUT_DIR, f"model_{str(self.trainer.iter).zfill(7)}.pth"
        ).as_posix()

    def _get_sample_images(self, cfg):
        """Returns a fixed list of sample images"""
        if not self._sample_images:
            self._sample_images = random.sample(
                DatasetCatalog.get(cfg.DATASETS.TEST[0]), 20
            )
        return self._sample_images

    def _get_cfg(self):
        cfg = self.trainer.cfg.clone()
        cfg.MODEL.WEIGHTS = self._get_latest_weights()
        return cfg

    def __call__(self):
        cfg = self._get_cfg()
        dataset_dicts = DatasetCatalog.get(cfg.DATASETS.TEST[0])
        dataset_metadata = MetadataCatalog.get(cfg.DATASETS.TEST[0])

        predictor = TiledPredictor(
            cfg=cfg,
            tile_size=self.tile_size,
            max_instance_size=100,
            merge_threshold=0.8,
        )

        (
            dataset_evaluations,
            predictions_by_image,
            evaluations_by_image,
        ) = BBoxEvaluator(
            predictor=predictor,
            dataset_dicts=dataset_dicts,
            thing_classes=dataset_metadata.thing_classes,
            min_score=cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST,
        ).evaluate()

        output_dir = Path(cfg.OUTPUT_DIR, str(self.trainer.iter).zfill(7))
        output_dir.mkdir(parents=True, exist_ok=True)
        generate_plots(
            self._get_sample_images(cfg),
            dataset_metadata,
            predictions_by_image,
            evaluations_by_image,
            output_dir=output_dir,
        )

        return dataset_evaluations

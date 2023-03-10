import os

import detectron2.utils.comm as comm
import mlflow
import torch
from detectron2.data import build_detection_train_loader
from detectron2.engine import HookBase


class ValidationLoss(HookBase):
    def __init__(self, cfg, n_val_loss: int = 100):
        super().__init__()
        self.cfg = cfg.clone()
        self.cfg.DATASETS.TRAIN = self.cfg.DATASETS.TEST
        self.cfg.DATASETS.TEST = []
        self._loader = iter(build_detection_train_loader(self.cfg))
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

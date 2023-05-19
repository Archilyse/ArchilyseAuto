import warnings
from contextlib import contextmanager

from constants import N_VAL_LOSS
from dataset_utils import IconTileMapper
from detectron2.data import build_detection_train_loader
from detectron2.engine import DefaultTrainer, hooks
from hooks import EvaluationHook, MLFlowHook, ValidationLoss


@contextmanager
def supress_shapely_warning():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="invalid value encountered in intersection"
        )
        yield


class IconTrainer(DefaultTrainer):
    def build_hooks(self):
        hooks_ = super().build_hooks()
        # has to be added before PeriodicWriter!
        val_loss = ValidationLoss(
            data_loader=self.build_val_loader(cfg=self.cfg), n_val_loss=N_VAL_LOSS
        )
        hooks_.insert(-1, val_loss)
        hooks_.insert(
            -1,
            hooks.EvalHook(
                self.cfg.TEST.EVAL_PERIOD, EvaluationHook(tile_size=1024, trainer=self)
            ),
        )
        hooks_.insert(-1, MLFlowHook(cfg=self.cfg, n_val_loss=N_VAL_LOSS))
        return hooks_

    @classmethod
    def build_val_loader(cls, cfg):
        val_cfg = cfg.clone()
        val_cfg.DATASETS.TRAIN = val_cfg.DATASETS.TEST
        val_cfg.DATASETS.TEST = []
        return cls.build_train_loader(val_cfg)

    @classmethod
    def build_test_loader(cls, *args, **kwargs):
        with supress_shapely_warning():
            return super().build_test_loader(*args, **kwargs)

    @staticmethod
    def dataset_mapper(cfg):
        return IconTileMapper(
            cfg,
            tile_sizes=list(range(256, 1280, 128)),
            is_train=True,
            recompute_boxes=True,
        )

    @classmethod
    def build_train_loader(cls, cfg):
        with supress_shapely_warning():
            yield from build_detection_train_loader(
                cfg,
                mapper=cls.dataset_mapper(cfg),
            )

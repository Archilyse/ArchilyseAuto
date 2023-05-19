import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

import hydra
import mlflow
import torch
from constants import MLFLOW_TRACKING_URI, THING_COLORS
from dataset_utils import register_datasets
from detectron2.config import get_cfg
from detectron2.engine import launch
from detectron2.utils.comm import get_local_rank
from detectron2.utils.logger import setup_logger
from omegaconf import DictConfig, OmegaConf
from outputs import generate_metrics
from trainer import IconTrainer

logger = setup_logger()


def get_keys(cfg, parent=""):
    for child in cfg:
        if isinstance(cfg[child], DictConfig):
            yield from get_keys(cfg[child], parent=f"{parent}.{child}")
        else:
            yield f"{parent}.{child}", cfg[child]


def setup_mlflow(cfg):
    mlflow.set_tracking_uri(uri=MLFLOW_TRACKING_URI)
    mlflow.set_experiment(experiment_name=cfg.mlflow.EXPERIMENT_NAME)
    mlflow.start_run(run_name=cfg.mlflow.RUN_NAME)
    for k, v in get_keys(cfg):
        mlflow.log_param(k, v)


def train(cfg, coco_directory: Path, thing_classes: List[str]):
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    register_datasets(
        cfg=cfg,
        coco_directory=coco_directory,
        thing_classes=thing_classes,
        thing_colors=[THING_COLORS[thing_class] for thing_class in thing_classes],
    )
    trainer = IconTrainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()


def get_detectron_cfg(cfg):
    detectron_cfg = get_cfg()
    with NamedTemporaryFile(mode="w") as tmp_cfg_file:
        tmp_cfg_file.write(OmegaConf.to_yaml(cfg.instance_segmentation.detectron2))
        tmp_cfg_file.flush()
        os.fsync(tmp_cfg_file.fileno())
        detectron_cfg.merge_from_file(tmp_cfg_file.name)
    return detectron_cfg


@hydra.main(
    version_base=None,
    config_path=Path(os.path.realpath(__file__))
    .parent.parent.joinpath("conf")
    .as_posix(),
    config_name="config",
)
def run(cfg: DictConfig) -> None:
    setup_mlflow(cfg)

    detectron_cfg = get_detectron_cfg(cfg)
    train(
        cfg=detectron_cfg,
        coco_directory=Path(cfg.instance_segmentation.DATASET_DIR),
        thing_classes=cfg.instance_segmentation.THING_CLASSES,
    )

    if get_local_rank() == 0:
        generate_metrics(cfg=detectron_cfg)


if __name__ == "__main__":
    if torch.cuda.device_count() > 1:
        launch(run, torch.cuda.device_count(), args=(), dist_url="auto")
    else:
        run()

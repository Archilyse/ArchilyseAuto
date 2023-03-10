import json
import os
import random
from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2
import hydra
import mlflow
import pandas as pd
import torch
from dataset_utils import filter_coco_json
from detectron2.config import get_cfg
from detectron2.data import DatasetCatalog, MetadataCatalog
from detectron2.data.datasets import register_coco_instances
from detectron2.engine import DefaultPredictor, DefaultTrainer, launch
from detectron2.utils.comm import get_local_rank
from detectron2.utils.logger import setup_logger
from detectron2.utils.visualizer import ColorMode, Visualizer
from evaluator import COCOEvaluatorDetailed
from hooks import MLFlowHook, ValidationLoss
from matplotlib import pyplot
from omegaconf import DictConfig, OmegaConf

logger = setup_logger()

N_VAL_LOSS = 100
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
THING_COLORS = {
    "TOILET": (0, 255, 255),
    "BATHTUB": (255, 0, 255),
    "SINK": (0, 128, 0),
    "SHOWER": (192, 126, 24),
}


class TrainerWithValLoss(DefaultTrainer):
    """
    Custom Trainer deriving from the "DefaultTrainer"

    Overloads build_hooks to add a hook to calculate loss on the test set during training.
    """

    def build_hooks(self):
        hooks = super().build_hooks()
        # has to be added before PeriodicWriter!
        hooks.insert(-1, ValidationLoss(cfg=self.cfg, n_val_loss=N_VAL_LOSS))
        hooks.insert(-1, MLFlowHook(cfg=self.cfg, n_val_loss=N_VAL_LOSS))
        return hooks

    @classmethod
    def build_evaluator(cls, cfg, dataset_name):
        return COCOEvaluatorDetailed(
            dataset_name, cfg, False, output_dir=cfg.OUTPUT_DIR
        )


class CocoTrainingJob:
    def __init__(self, config, coco_directory: Path, thing_classes):
        self.coco_directory = coco_directory
        self.config = config
        self.thing_classes = thing_classes

    def register_datasets(self):
        thing_colors = [THING_COLORS[thing_class] for thing_class in self.thing_classes]
        for dataset, dataset_name in [
            ("validation", self.config.DATASETS.TEST[0]),
            ("train", self.config.DATASETS.TRAIN[0]),
        ]:
            filtered_coco_json = Path(f"coco-{dataset}-filtered.json")
            filter_coco_json(
                input_filename=self.coco_directory.joinpath(dataset, "coco.json"),
                output_filename=filtered_coco_json,
                thing_classes=self.thing_classes,
            )
            register_coco_instances(
                dataset_name,
                dict(thing_colors=thing_colors),
                filtered_coco_json,
                self.coco_directory.joinpath(dataset, "images"),
            )

    def get_model_trainer(self):
        self.trainer = TrainerWithValLoss(self.config)
        self.trainer.resume_or_load(resume=False)
        return self.trainer

    def train(self):
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        self.register_datasets()
        return self.get_model_trainer().train()

    def generate_plots(self):
        self.config.MODEL.WEIGHTS = Path(
            self.config.OUTPUT_DIR, "model_final.pth"
        ).as_posix()
        predictor = DefaultPredictor(self.config)

        test_metadata = MetadataCatalog.get(self.config.DATASETS.TEST[0])
        dataset_dicts = DatasetCatalog.get(self.config.DATASETS.TEST[0])

        output_directory = Path(self.config.OUTPUT_DIR, "plots")
        output_directory.mkdir(parents=True, exist_ok=True)

        for d in random.sample(dataset_dicts, 30):
            img = cv2.imread(d["file_name"])
            img_with_ground_truth = self._draw_ground_truth(d, img, test_metadata)
            img_with_predictions = self._draw_predictions(img, predictor, test_metadata)

            self._plot(img_with_ground_truth, img_with_predictions)

            output_path = output_directory.joinpath(Path(d["file_name"]).name)
            pyplot.savefig(
                output_path.as_posix(), bbox_inches="tight", dpi=300, pad_inches=0
            )

        mlflow.log_artifacts(output_directory.as_posix(), "test-set-predictions")

    @staticmethod
    def _plot(img_with_ground_truth, img_with_predictions):
        fig = pyplot.figure(figsize=(10, 7))
        fig.add_subplot(1, 2, 1)
        pyplot.imshow(img_with_ground_truth)
        pyplot.title("Ground Truth")
        fig.add_subplot(1, 2, 2)
        pyplot.imshow(img_with_predictions)
        pyplot.title("Predictions")

    @staticmethod
    def _draw_ground_truth(d, img, test_metadata):
        ground_truth_visualizer = Visualizer(
            img[:, :, ::-1],
            metadata=test_metadata,
            instance_mode=ColorMode.SEGMENTATION,
        )
        out = ground_truth_visualizer.draw_dataset_dict(d)
        im_with_ground_truth = out.get_image()[:, :, ::-1]
        return im_with_ground_truth

    @staticmethod
    def _draw_predictions(img, predictor, test_metadata):
        outputs = predictor(img)
        pred_visualizer = Visualizer(
            img[:, :, ::-1],
            metadata=test_metadata,
            instance_mode=ColorMode.SEGMENTATION,
        )
        out = pred_visualizer.draw_instance_predictions(outputs["instances"].to("cpu"))
        im_with_predictions = out.get_image()[:, :, ::-1]
        return im_with_predictions


def generate_metrics(output_directory: Path):
    with output_directory.joinpath("metrics.json").open() as fh:
        df = pd.DataFrame([json.loads(line) for line in fh.readlines()])
        df = df.sort_values("iteration").fillna(method="ffill")

        # export metrics per iteration (for Dagshub)
        melted_df = pd.melt(
            df, id_vars=["iteration"], var_name="Name", value_name="Value"
        )
        melted_df = melted_df.rename({"iteration": "Step"}, axis="columns").sort_values(
            ["Step", "Name"]
        )
        melted_df["Timestamp"] = melted_df["Step"]
        melted_df = melted_df[["Name", "Value", "Timestamp", "Step"]]
        melted_df.dropna().to_csv(output_directory.joinpath("metrics.csv"), index=False)

        # export metrics (only final iteration, for DVC metrics)
        metrics_dvc = (
            df.sort_values("iteration")
            .iloc[-1:, :]
            .dropna(axis=1)
            .set_index("iteration")
            .to_dict(orient="records")[0]
        )
        with output_directory.joinpath("metrics_dvc.json").open("w") as fh:
            json.dump(metrics_dvc, fh, indent=3)


def get_keys(cfg, parent=""):
    for child in cfg:
        if isinstance(cfg[child], DictConfig):
            yield from get_keys(cfg[child], parent=f"{parent}.{child}")
        else:
            yield (f"{parent}.{child}", cfg[child])


@hydra.main(
    version_base=None,
    config_path=Path(os.path.realpath(__file__))
    .parent.parent.joinpath("conf")
    .as_posix(),
    config_name="config",
)
def run(cfg: DictConfig) -> None:
    mlflow.set_tracking_uri(uri=MLFLOW_TRACKING_URI)
    mlflow.set_experiment(experiment_name=cfg.mlflow.EXPERIMENT_NAME)
    mlflow.start_run(run_name=cfg.mlflow.RUN_NAME)
    for k, v in get_keys(cfg):
        mlflow.log_param(k, v)

    detectron_cfg = get_cfg()
    with NamedTemporaryFile(mode="w") as tmp_cfg_file:
        tmp_cfg_file.write(OmegaConf.to_yaml(cfg.instance_segmentation.detectron2))
        tmp_cfg_file.flush()
        os.fsync(tmp_cfg_file.fileno())
        detectron_cfg.merge_from_file(tmp_cfg_file.name)

    training_job = CocoTrainingJob(
        config=detectron_cfg,
        thing_classes=cfg.instance_segmentation.THING_CLASSES,
        coco_directory=Path(cfg.instance_segmentation.DATASET_DIR),
    )

    training_job.train()

    if get_local_rank() == 0:
        output_directory = Path(training_job.config.OUTPUT_DIR)
        training_job.generate_plots()
        generate_metrics(output_directory=output_directory)
        output_directory.joinpath("metrics.json").unlink()


if __name__ == "__main__":
    if torch.cuda.device_count() > 1:
        launch(run, torch.cuda.device_count(), args=(), dist_url="auto")
    else:
        run()

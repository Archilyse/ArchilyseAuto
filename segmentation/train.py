import os
import warnings
from pathlib import Path
from typing import Optional

import hydra
import pytorch_lightning as pl
import torch
import torchvision
from augmentation import training_augmentation, validation_augmentation
from dataset import COCOSegementationDataset, ImageOnlyDataset
from model import FloorplanModel, get_preprocessing_fn
from omegaconf import DictConfig
from preprocessing import preprocessing
from torch.utils.data import DataLoader
from tqdm import tqdm

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def get_coco_dataset(
    path: Path, cfg: DictConfig, is_train: bool, max_num: Optional[bool] = None
):
    preprocessing_fn = get_preprocessing_fn(
        encoder=cfg.MODEL.ENCODER, encoder_weights=cfg.MODEL.ENCODER_WEIGHTS
    )
    if is_train:
        augmentation = training_augmentation(
            pad_size=cfg.MODEL.PAD_SIZE,
            crop_size=cfg.MODEL.CROP_SIZE if cfg.MODEL.CROP_ENABLED else None,
            max_size=cfg.MODEL.MAX_SIZE if cfg.MODEL.RESIZE_ENABLED else None,
            scaling=cfg.MODEL.SCALING_LIMITS if cfg.MODEL.SCALING_ENABLED else None,
        )
    else:
        augmentation = validation_augmentation(
            pad_size=cfg.MODEL.PAD_SIZE,
            crop_size=cfg.MODEL.CROP_SIZE if cfg.MODEL.CROP_ENABLED else None,
            max_size=cfg.MODEL.MAX_SIZE if cfg.MODEL.RESIZE_ENABLED else None,
            scaling=cfg.MODEL.SCALING_LIMITS if cfg.MODEL.SCALING_ENABLED else None,
        )

    return COCOSegementationDataset(
        coco_json_path=path.joinpath("coco.json"),
        image_dir=path.joinpath("images"),
        augmentation=augmentation,
        preprocessing=preprocessing(preprocessing_fn),
        category_names=cfg.MODEL.CLASSES,
        add_background_dim=cfg.MODEL.BACKGROUND_DIM,
        max_num=max_num,
    )


def get_train_loader(train_dataset, cfg) -> DataLoader:
    return DataLoader(
        train_dataset,
        batch_size=cfg.SOLVER.BATCH_SIZE,
        shuffle=True,
        num_workers=cfg.DATALOADER.NUM_WORKERS,
    )


def get_validation_loader(validation_dataset, cfg) -> DataLoader:
    return DataLoader(
        validation_dataset,
        batch_size=cfg.SOLVER.BATCH_SIZE,
        shuffle=False,
        num_workers=cfg.DATALOADER.NUM_WORKERS,
    )


def get_keys(cfg, parent=""):
    for child in cfg:
        if isinstance(cfg[child], DictConfig):
            yield from get_keys(cfg[child], parent=f"{parent}.{child}")
        else:
            yield (f"{parent}.{child}", cfg[child])


def compute_mean_std(folder):
    transform_img = torchvision.transforms.Compose(
        [
            torchvision.transforms.Resize(256),
            torchvision.transforms.CenterCrop(256),
            torchvision.transforms.ToTensor(),
        ]
    )

    image_data = ImageOnlyDataset(root=folder, transform=transform_img)

    loader = DataLoader(image_data, batch_size=100, shuffle=False, num_workers=0)

    mean = 0.0
    std = 0.0
    for images in tqdm(loader):
        batch_samples = images.size(
            0
        )  # batch size (the last batch can have smaller size!)
        images = images.view(batch_samples, images.size(1), -1)
        mean += images.mean(2).sum(0)
        std += images.std(2).sum(0)

    mean /= len(loader)
    std /= len(loader)
    return mean, std


@hydra.main(
    version_base=None,
    config_path=Path(os.path.realpath(__file__))
    .parent.parent.joinpath("conf")
    .as_posix(),
    config_name="config",
)
def run(cfg: DictConfig) -> None:
    warnings.filterwarnings("ignore")

    mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    experiment_name = "DeeplabV3"
    run_name = cfg.mlflow.RUN_NAME

    config = cfg.semantic_segmentation

    # training
    train_dataset = get_coco_dataset(
        path=Path(config.DATASET.PATH).joinpath("train"),
        cfg=config,
        is_train=True,
    )
    train_loader = get_train_loader(train_dataset=train_dataset, cfg=config)

    # validation
    validation_dataset = get_coco_dataset(
        path=Path(config.DATASET.PATH).joinpath("validation"),
        cfg=config,
        is_train=False,
    )
    validation_loader = get_validation_loader(
        validation_dataset=validation_dataset, cfg=config
    )

    class_names = (["BACKGROUND"] if config.MODEL.BACKGROUND_DIM else []) + list(
        config.MODEL.CLASSES
    )
    pl_model = FloorplanModel(
        class_names=class_names,
        ignore_class_indexes=config.MODEL.IGNORE_IN_LOSS,
        learning_rate=config.SOLVER.LEARNING_RATE,
        loss_function=config.MODEL.LOSS_FUNCTION,
        encoder=config.MODEL.ENCODER,
        encoder_weights=config.MODEL.ENCODER_WEIGHTS,
        activation=config.MODEL.ACTIVATION,
        output_directory=Path(config.OUTPUT_DIR),
        validation_dataset=validation_dataset,
        experiment_name=experiment_name,
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_experiment_name=experiment_name,
        mlflow_run_name=run_name,
        tversky_params=config.MODEL.TVERSKY_PARAMS,
        config=dict(get_keys(config)),
        mean=config.MODEL.IMAGE_MEAN,
        std=config.MODEL.IMAGE_STD,
    )
    trainer = pl.Trainer(
        gpus=torch.cuda.device_count(), max_epochs=config.SOLVER.EPOCHS
    )

    trainer.fit(
        pl_model,
        train_dataloaders=train_loader,
        val_dataloaders=validation_loader,
    )


if __name__ == "__main__":
    run()

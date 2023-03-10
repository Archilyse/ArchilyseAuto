import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import List

import click
import pandas as pd
from PIL import Image
from shapely import wkt
from tqdm import tqdm

from aurora.bin.coco.label import CocoLabel, get_class_labels
from aurora.bin.coco.utils import train_test_split_dataframe
from aurora.handlers.coco.coco_writer import CocoWriter
from aurora.handlers.coco.sample_generator import Sample, SampleGenerator

random.seed(42)


def generate_samples(
    image_input_folder: Path,
    image_output_folder: Path,
    geometries_dataframe: pd.DataFrame,
    plan_id: int,
    tiling_enabled: bool,
    tile_size: int,
    tile_stride: int,
) -> List[Sample]:
    image_file_path = image_input_folder.joinpath(f"{plan_id}.jpg")
    with Image.open(image_file_path) as plan_image:
        image_height = plan_image.height
        image_width = plan_image.width

    geometries = defaultdict(list)
    for _, row in geometries_dataframe[
        (geometries_dataframe.plan_id == plan_id)
    ].iterrows():
        for class_label in get_class_labels(
            entity_type=row.entity_type, entity_subtype=row.entity_subtype
        ):
            geometries[class_label.name].append(wkt.loads(row.geometry))

    if tiling_enabled:
        return SampleGenerator.get_samples_tiled(
            image_file_path=image_file_path,
            image_width=image_width,
            image_height=image_height,
            geometries=geometries,
            tile_size=tile_size,
            tile_stride=tile_stride,
            tile_output_path=image_output_folder,
        )

    return SampleGenerator.get_samples(
        image_file_path=image_file_path,
        image_width=image_width,
        image_height=image_height,
        geometries=geometries,
    )


def export_coco_dataset_and_copy_images(
    image_input_folder: Path,
    output_folder: Path,
    geometries_dataframe: pd.DataFrame,
    noimages: bool,
    version: str,
    tiling_enabled: bool,
    tile_size: int,
    tile_stride: int,
):
    image_output_folder = output_folder.joinpath("images/")
    image_output_folder.mkdir(parents=True, exist_ok=False)

    samples = []
    for plan_id in tqdm(geometries_dataframe.plan_id.unique()):
        samples += generate_samples(
            image_input_folder=image_input_folder,
            image_output_folder=image_output_folder,
            geometries_dataframe=geometries_dataframe,
            plan_id=plan_id,
            tiling_enabled=tiling_enabled,
            tile_size=tile_size,
            tile_stride=tile_stride,
        )

        if not tiling_enabled and not noimages:
            shutil.copy(
                image_input_folder.joinpath(f"{plan_id}.jpg"),
                image_output_folder.joinpath(f"{plan_id}.jpg"),
            )

    CocoWriter.export(
        samples=samples,
        destination_file_path=output_folder.joinpath("coco.json"),
        version=version,
        category_ids={label.name: label.value for label in CocoLabel},
    )


@click.command()
@click.option(
    "--test_ratio", default=0.1, type=float, help="Ratio of plans in test dataset."
)
@click.option("--version", type=str, help="Version of the dataset.")
@click.option(
    "--tiling_enabled", type=bool, default=False, help="whether tiling is enabled."
)
@click.option(
    "--tile_size", type=int, help="The tiles' size (e.g. 512 means 512x512px tiles)."
)
@click.option("--tile_stride", type=int, help="The tiles' stride")
@click.option("--noimages", default=False, type=bool, help="Do not export images.")
@click.argument("input_folder", type=click.Path(exists=True))
@click.argument("input_geometries_path", type=click.Path(exists=True))
@click.argument("coco_output_folder", type=click.Path(exists=False))
def make_coco_dataset(
    input_folder: Path,
    input_geometries_path: Path,
    coco_output_folder: Path,
    test_ratio: float,
    noimages: bool,
    version: str,
    tiling_enabled: bool,
    tile_size: int,
    tile_stride: int,
):
    input_folder, coco_output_folder = Path(input_folder), Path(coco_output_folder)
    image_input_folder = input_folder.joinpath("images/")

    geometries_dataframe = pd.read_csv(input_geometries_path)
    (
        test_geometries_dataframe,
        validation_geometries_dataframe,
        train_geometries_dataframe,
    ) = train_test_split_dataframe(
        geometries_dataframe, ratios=[test_ratio, test_ratio, 1 - 2 * test_ratio]
    )

    export_coco_dataset_and_copy_images(
        image_input_folder=image_input_folder,
        output_folder=coco_output_folder.joinpath("test"),
        geometries_dataframe=test_geometries_dataframe,
        noimages=noimages,
        version=version,
        tiling_enabled=tiling_enabled,
        tile_size=tile_size,
        tile_stride=tile_stride,
    )

    export_coco_dataset_and_copy_images(
        image_input_folder=image_input_folder,
        output_folder=coco_output_folder.joinpath("validation"),
        geometries_dataframe=validation_geometries_dataframe,
        noimages=noimages,
        version=version,
        tiling_enabled=tiling_enabled,
        tile_size=tile_size,
        tile_stride=tile_stride,
    )

    export_coco_dataset_and_copy_images(
        image_input_folder=image_input_folder,
        output_folder=coco_output_folder.joinpath("train"),
        geometries_dataframe=train_geometries_dataframe,
        noimages=noimages,
        version=version,
        tiling_enabled=tiling_enabled,
        tile_size=tile_size,
        tile_stride=tile_stride,
    )


if __name__ == "__main__":
    make_coco_dataset()

"""Rescale and crop images / geometries, apply blacklists and make images black/white"""
from pathlib import Path
from typing import List

import click
import pandas as pd
from PIL import Image
from shapely import wkt
from shapely.affinity import scale, translate
from shapely.geometry import box
from shapely.ops import unary_union
from tqdm import tqdm


def geometry_transform(geometry, pixels_per_meter, height):
    return translate(
        scale(geometry, xfact=pixels_per_meter, yfact=-pixels_per_meter, origin=(0, 0)),
        yoff=height,
    )


def create_label_txt(
    plan_id: int,
    image_input_folder: Path,
    label_output_folder: Path,
    plan_dataframe: pd.DataFrame,
    geometries_dataframe: pd.DataFrame,
):
    pixels_per_meter = plan_dataframe[
        plan_dataframe.plan_id == plan_id
    ].pixels_per_meter.iloc[0]
    plan_geometries_dataframe = geometries_dataframe[
        (geometries_dataframe.plan_id == plan_id)
    ]
    plan_image = Image.open(image_input_folder.joinpath(f"{plan_id}.jpg"))

    roi = box(
        *unary_union(
            [
                geometry_transform(
                    geometry=wkt.loads(row.geometry),
                    pixels_per_meter=pixels_per_meter,
                    height=plan_image.height,
                )
                for _, row in plan_geometries_dataframe.iterrows()
            ]
        ).bounds
    )
    centroid_x = roi.centroid.x / plan_image.width
    centroid_y = roi.centroid.y / plan_image.height
    roi_width = abs(roi.bounds[0] - roi.bounds[2]) / plan_image.width
    roi_height = abs(roi.bounds[1] - roi.bounds[3]) / plan_image.height
    with open(label_output_folder.joinpath(f"{plan_id}.txt"), "w") as f:
        f.write(f"0 {centroid_x} {centroid_y} {roi_width} {roi_height}")


@click.command()
@click.option("--blacklist_path", "-b", multiple=True, type=click.Path(exists=True))
@click.argument("input_folder", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path(exists=False))
def create_image_labels(
    input_folder: click.Path,
    blacklist_path: List[click.Path],
    output_folder: click.Path,
):
    input_folder = Path(input_folder)

    geometries_dataframe = pd.read_csv(input_folder.joinpath("geometries.csv"))
    plan_dataframe = pd.read_csv(input_folder.joinpath("plans.csv"))
    image_input_folder = input_folder.joinpath("images/")
    label_output_folder = Path(output_folder)
    label_output_folder.mkdir(parents=True, exist_ok=True)

    all_plan_ids = set(plan_dataframe.plan_id.unique())
    blacklisted_plan_ids = set(
        pd.concat([pd.read_csv(Path(path)) for path in blacklist_path]).plan_id.unique()
    )
    plan_ids = list(all_plan_ids - blacklisted_plan_ids)

    for plan_id in tqdm(plan_ids):
        create_label_txt(
            plan_id=plan_id,
            image_input_folder=image_input_folder,
            label_output_folder=label_output_folder,
            plan_dataframe=plan_dataframe,
            geometries_dataframe=geometries_dataframe,
        )


if __name__ == "__main__":
    create_image_labels()

"""Rescale and crop images / geometries, apply blacklists and make images black/white"""
from pathlib import Path
from typing import List, Union

import click
import pandas as pd
from PIL import Image
from shapely import wkt
from shapely.affinity import scale, translate
from shapely.geometry import box
from shapely.ops import unary_union
from tqdm.contrib.concurrent import process_map


def crop_image_and_geometries(
    plan_id: int,
    image_input_folder: Path,
    image_output_folder: Path,
    plan_dataframe: pd.DataFrame,
    geometries_dataframe: pd.DataFrame,
    roi_scale: Union[float, None],
    target_pixels_per_meter: Union[float, None],
    as_grayscale: bool,
):
    pixels_per_meter = plan_dataframe[
        plan_dataframe.plan_id == plan_id
    ].pixels_per_meter.iloc[0]
    plan_geometries_dataframe = geometries_dataframe[
        (geometries_dataframe.plan_id == plan_id)
    ]

    plan_image = Image.open(image_input_folder.joinpath(f"{plan_id}.jpg"))
    if as_grayscale:
        plan_image = plan_image.convert("L")

    if target_pixels_per_meter is not None:
        image_scale = target_pixels_per_meter / pixels_per_meter
        plan_image = plan_image.resize(
            (int(image_scale * plan_image.width), int(image_scale * plan_image.height))
        )
        pixels_per_meter = target_pixels_per_meter

    def geometry_transform(geometry):
        return translate(
            scale(
                geometry, xfact=pixels_per_meter, yfact=-pixels_per_meter, origin=(0, 0)
            ),
            yoff=plan_image.height,
        )

    if roi_scale:
        roi = scale(
            box(
                *unary_union(
                    [
                        geometry_transform(wkt.loads(row.geometry))
                        for _, row in plan_geometries_dataframe.iterrows()
                    ]
                ).bounds
            ),
            roi_scale,
            roi_scale,
            origin="center",
        )
    else:
        roi = ((0, 0), (plan_image.width, plan_image.height))

    for i, row in plan_geometries_dataframe.iterrows():
        plan_geometries_dataframe.loc[i, "geometry"] = wkt.dumps(
            translate(
                geometry_transform(wkt.loads(row.geometry)),
                -roi.bounds[0],
                -roi.bounds[1],
            )
        )

    image_cropped = plan_image.crop(roi.bounds)
    image_cropped.save(image_output_folder.joinpath(f"{plan_id}.jpg"))

    return plan_geometries_dataframe


@click.command()
@click.option(
    "--roi_scale",
    default=1.05,
    help="scale of the cropped ROI in percent (default 5% overlap beyond the annotation)",
    required=False,
)
@click.option(
    "--target_pixels_per_meter", default=None, help="pixels per meter in final image"
)
@click.option(
    "--as_grayscale", default=False, type=bool, help="convert images to black/white"
)
@click.option("--blacklist_path", "-b", multiple=True, type=click.Path(exists=True))
@click.argument("input_folder", type=click.Path(exists=True))
@click.argument("output_folder", type=click.Path(exists=False))
def rescale_and_crop_images(
    input_folder: click.Path,
    output_folder: click.Path,
    blacklist_path: List[click.Path],
    target_pixels_per_meter: Union[None, float],
    roi_scale: Union[float, None] = None,
    as_grayscale: bool = False,
):
    input_folder, output_folder = (
        Path(input_folder),
        Path(output_folder),
    )
    if target_pixels_per_meter is not None:
        target_pixels_per_meter = float(target_pixels_per_meter)

    geometries_dataframe = pd.read_csv(input_folder.joinpath("geometries.csv"))
    plan_dataframe = pd.read_csv(input_folder.joinpath("plans.csv"))
    image_input_folder = input_folder.joinpath("images/")

    geometries_output_path = output_folder.joinpath("geometries.csv")
    image_output_folder = output_folder.joinpath("images/")
    image_output_folder.mkdir(parents=True, exist_ok=True)

    all_plan_ids = set(plan_dataframe.plan_id.unique())
    blacklisted_plan_ids = set(
        pd.concat([pd.read_csv(Path(path)) for path in blacklist_path]).plan_id.unique()
    )
    plan_ids = list(all_plan_ids - blacklisted_plan_ids)

    new_geometries_dataframe = pd.concat(
        [
            row
            for row in process_map(
                crop_image_and_geometries,
                plan_ids,
                [image_input_folder] * len(plan_ids),
                [image_output_folder] * len(plan_ids),
                [plan_dataframe] * len(plan_ids),
                [geometries_dataframe] * len(plan_ids),
                [roi_scale] * len(plan_ids),
                [target_pixels_per_meter] * len(plan_ids),
                [as_grayscale] * len(plan_ids),
            )
            if row is not None
        ],
        axis=0,
    )
    new_geometries_dataframe.to_csv(geometries_output_path, index=None)


if __name__ == "__main__":
    rescale_and_crop_images()

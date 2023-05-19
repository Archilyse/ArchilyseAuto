"""Rescale and crop images / geometries, apply blacklists and make images black/white"""
import warnings
from pathlib import Path
from typing import List, Union

import click
import pandas as pd
from PIL import Image
from PIL.Image import DecompressionBombWarning
from shapely import wkt
from shapely.affinity import rotate, scale, translate
from shapely.geometry import box
from shapely.ops import unary_union
from tqdm.contrib.concurrent import process_map

warnings.filterwarnings("ignore", category=DecompressionBombWarning, module="PIL")


def masterplan_transform_required(plan):
    return (
        plan.masterplan_scale_factor != 1.0
        or plan.masterplan_shift_y != 0.0
        or plan.masterplan_shift_x != 0.0
        or plan.masterplan_rotation != 0.0
    )


def transform_geometry(geometry, plan, plan_image, target_scale):
    if masterplan_transform_required(plan):
        actual_plan_scale = plan.pixels_per_meter / plan.masterplan_scale_factor
        geometry = rotate(
            translate(
                scale(
                    geometry,
                    xfact=actual_plan_scale,
                    yfact=-actual_plan_scale,
                    origin=(0, 0),
                ),
                yoff=plan_image.height
                + plan.masterplan_shift_y / plan.masterplan_scale_factor,
                xoff=-plan.masterplan_shift_x / plan.masterplan_scale_factor,
            ),
            angle=-plan.masterplan_rotation,
            origin=(plan_image.width / 2, plan_image.height / 2),
        )
        if target_scale is None:
            return geometry

        target_scale_factor = target_scale / actual_plan_scale
        return scale(
            geometry,
            xfact=target_scale_factor,
            yfact=target_scale_factor,
            origin=(0, 0),
        )

    # NOTE to avoid changing images which were already processed we have to do the target scaling in this method
    # even though it would be preferable to do the scaling in a separate method together with the image.
    if target_scale is None:
        target_scale = plan.pixels_per_meter
    target_scale_factor = target_scale / plan.pixels_per_meter
    return translate(
        scale(geometry, xfact=target_scale, yfact=-target_scale, origin=(0, 0)),
        yoff=int(plan_image.height * target_scale_factor),
    )


def roi_crop(image, geometries, roi_scale):
    roi = scale(
        box(*unary_union(geometries.geometry).bounds),
        roi_scale,
        roi_scale,
        origin="center",
    )
    geometries["geometry"] = [
        translate(
            geometry,
            -roi.bounds[0],
            -roi.bounds[1],
        )
        for geometry in geometries.geometry
    ]
    return image.crop(roi.bounds), geometries


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
    plan = plan_dataframe[plan_dataframe.plan_id == plan_id].iloc[0]
    plan_geometries = geometries_dataframe[(geometries_dataframe.plan_id == plan_id)][
        [
            "site_id",
            "plan_id",
            "entity_type",
            "entity_subtype",
            "geometry",
        ]
    ].drop_duplicates()
    plan_image = Image.open(image_input_folder.joinpath(f"{plan_id}.jpg"))

    plan_geometries["geometry"] = [
        transform_geometry(
            geometry=wkt.loads(geom_wkt),
            plan=plan,
            plan_image=plan_image,
            target_scale=target_pixels_per_meter,
        )
        for geom_wkt in plan_geometries.geometry
    ]

    if as_grayscale:
        plan_image = plan_image.convert("L")

    if target_pixels_per_meter is not None:
        actual_plan_scale = plan.pixels_per_meter / plan.masterplan_scale_factor
        target_scale_factor = target_pixels_per_meter / actual_plan_scale
        plan_image = plan_image.resize(
            (
                int(target_scale_factor * plan_image.width),
                int(target_scale_factor * plan_image.height),
            )
        )

    if roi_scale:
        plan_image, plan_geometries = roi_crop(
            image=plan_image, geometries=plan_geometries, roi_scale=roi_scale
        )

    plan_image.save(image_output_folder.joinpath(f"{plan_id}.jpg"))
    return plan_geometries


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
                max_workers=4,
                chunksize=8,
            )
            if row is not None
        ],
        axis=0,
    )
    new_geometries_dataframe.to_csv(geometries_output_path, index=None)


if __name__ == "__main__":
    rescale_and_crop_images()

"""
Creates data/blacklist_cleanup.csv which creates plan_ids blacklisted because of one of these reasons:
 - plans/geometries that do either not have an existing/readable image or that do not have any geometries
 - images that do not have matching plan ids in plans.csv or whose plan id appears in orphaned_plan_ids.csv
"""
from functools import partial
from pathlib import Path

import click
import pandas as pd
from PIL import Image
from tqdm.contrib.concurrent import process_map

DATA_PATH = Path("/home/mfranzen/projects/deep-learning/data/swiss-dwellings/")


def assert_image_is_readable(images_path: Path, plan_id: int):
    try:
        with Image.open(images_path.joinpath(f"{plan_id}.jpg")):
            pass
    except BaseException:
        raise AssertionError("Image not readable")


def assert_image_exists(images_path: Path, plan_id: int):
    assert images_path.joinpath(f"{plan_id}.jpg").exists(), "image does not exist"


def assert_has_geometries(geometries_dataframe: pd.DataFrame, plan_id: int):
    assert (
        geometries_dataframe[geometries_dataframe.plan_id == plan_id].shape[0] > 0
    ), "plan_id has no geometries"


def assert_has_unique_metadata(plan_dataframe: pd.DataFrame, plan_id: int):
    assert (
        plan_dataframe[plan_dataframe.plan_id == plan_id].shape[0] == 1
    ), "plan_id has no unqiue metadata"


def assert_all(
    images_path: Path,
    geometries_dataframe: pd.DataFrame,
    plan_dataframe: pd.DataFrame,
    plan_id: int,
):
    assertion_funcs = [
        partial(assert_image_is_readable, images_path=images_path),
        partial(assert_image_exists, images_path=images_path),
        partial(assert_has_geometries, geometries_dataframe=geometries_dataframe),
        partial(assert_has_unique_metadata, plan_dataframe=plan_dataframe),
    ]

    try:
        for assertion_func in assertion_funcs:
            assertion_func(plan_id=plan_id)
    except AssertionError as err:
        return plan_id, str(err)

    return (None, None)


@click.command()
@click.argument("input_folder", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path(exists=False))
def cleanup(input_folder: Path, output_path: Path):
    input_folder, output_path = Path(input_folder), Path(output_path)

    images_path = input_folder.joinpath("images")
    geometries_dataframe = pd.read_csv(input_folder.joinpath("geometries.csv"))
    plan_dataframe = pd.read_csv(input_folder.joinpath("plans.csv"))
    image_paths = list(images_path.glob("*.jpg"))

    all_plan_ids = list(
        map(
            int,
            set(geometries_dataframe.plan_id.values)
            | set(plan_dataframe.plan_id.values)
            | {int(image_path.stem) for image_path in image_paths},
        )
    )

    blacklist_dataframe = pd.DataFrame(
        process_map(
            assert_all,
            [images_path] * len(all_plan_ids),
            [geometries_dataframe] * len(all_plan_ids),
            [plan_dataframe] * len(all_plan_ids),
            all_plan_ids,
        ),
        columns=["plan_id", "reason"],
    )

    output_path.parent.mkdir(exist_ok=True, parents=True)
    blacklist_dataframe.dropna().to_csv(output_path, index=None)


if __name__ == "__main__":
    cleanup()

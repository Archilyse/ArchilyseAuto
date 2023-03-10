import io
import logging
from typing import List, Tuple

import numpy as np
import shapely
from celery.result import AsyncResult
from matplotlib import pyplot
from matplotlib.collections import PatchCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path

from predictors.celery_conf.celery_app import celery_app
from predictors.predictors.base import MultiClassPrediction
from predictors.predictors.constants import COLORS, ClassLabel

logger = logging.getLogger("demo-app")


def plot_polygon(ax, poly, **kwargs):
    if not isinstance(poly, shapely.geometry.MultiPolygon):
        poly = shapely.geometry.MultiPolygon([poly])

    patches = []
    for geom in poly.geoms:
        if geom.is_empty:
            continue

        path = Path.make_compound_path(
            Path(np.asarray(geom.exterior.coords)[:, :2]),
            *[Path(np.asarray(ring.coords)[:, :2]) for ring in geom.interiors],
        )

        patches.append(PathPatch(path, **kwargs))

    collection = PatchCollection(patches, **kwargs)

    ax.add_collection(collection, autolim=True)
    return collection


def as_svg(image, labels, shapes, alpha=0.7) -> io.BytesIO:
    image_out = io.BytesIO()

    pyplot.clf()

    fig, ax = pyplot.subplots()
    ax.set_axis_off()
    ax.imshow(image, alpha=0.0)
    for label, shape in zip(labels, shapes):
        if isinstance(
            shape, (shapely.geometry.MultiPolygon, shapely.geometry.GeometryCollection)
        ):
            for geom in shape.geoms:
                if not isinstance(geom, shapely.geometry.Polygon):
                    continue

                plot_polygon(
                    ax, geom, facecolor=[v / 255.0 for v in COLORS[label]], alpha=alpha
                )
        else:
            if not isinstance(shape, shapely.geometry.Polygon):
                continue

            plot_polygon(
                ax, shape, facecolor=[v / 255.0 for v in COLORS[label]], alpha=alpha
            )

    pyplot.axis("off")
    pyplot.savefig(
        image_out, bbox_inches="tight", dpi=350, pad_inches=0, transparent=True
    )
    pyplot.close()

    image_out.seek(0)
    return image_out


def deserialize_tasks_results(labels, shapes):
    labels = [ClassLabel[label] for label in labels]
    shapes = [shapely.from_wkt(shape) for shape in shapes]
    return labels, shapes


def _get_labels_shapes_from_tasks(task_ids: List[str]) -> MultiClassPrediction:
    task_results = [AsyncResult(id=task_id, app=celery_app) for task_id in task_ids]

    labels: Tuple = tuple()
    shapes: Tuple = tuple()
    if all([r.ready() for r in task_results]):
        for task_result in task_results:
            task_labels, task_shapes = deserialize_tasks_results(*task_result.get())
            labels += tuple(task_labels)
            shapes += tuple(task_shapes)
        return labels, shapes
    raise ValueError("Tasks are not ready yet")

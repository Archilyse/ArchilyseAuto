import io

import numpy as np
from matplotlib import pyplot
from matplotlib.collections import PatchCollection
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from shapely.geometry import Polygon, mapping, shape

from predictors.predictors.constants import COLORS, ClassLabel
from predictors.predictors.utils.geometry import get_polygons


def _plot_polygon(ax, polygon: Polygon, **kwargs):
    patches = []
    if not polygon.is_empty:
        path = Path.make_compound_path(
            Path(np.asarray(polygon.exterior.coords)[:, :2]),
            *[Path(np.asarray(ring.coords)[:, :2]) for ring in polygon.interiors],
        )
        patches.append(PathPatch(path, **kwargs))

    collection = PatchCollection(patches, **kwargs)

    ax.add_collection(collection, autolim=True)
    return collection


def as_svg(labels, shapes, image_shape, alpha=0.7) -> io.BytesIO:
    image_out = io.BytesIO()
    pyplot.clf()

    fig, ax = pyplot.subplots()
    for label, shape_ in zip(labels, shapes):
        for polygon in get_polygons(shape_):
            _plot_polygon(
                ax, polygon, facecolor=[v / 255.0 for v in COLORS[label]], alpha=alpha
            )

    ax.set_axis_off()
    ax.set_xlim(0, image_shape[1])
    ax.set_ylim(image_shape[0], 0)
    ax.set_aspect(1)

    pyplot.savefig(
        image_out,
        bbox_inches="tight",
        dpi=350,
        pad_inches=0,
        transparent=True,
        format="svg",
    )
    pyplot.close(fig)

    image_out.seek(0)
    return image_out


def as_geojson(labels, shapes):
    features = [
        {
            "type": "Feature",
            "geometry": mapping(shape_),
            "properties": {"label": label.name},
        }
        for label, shape_ in zip(labels, shapes)
    ]
    return {"type": "FeatureCollection", "features": features}


def from_geojson(geojson):
    return tuple(
        zip(
            *[
                (ClassLabel[feature["properties"]["label"]], shape(feature["geometry"]))
                for feature in geojson["features"]
            ]
        )
    )

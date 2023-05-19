from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from predictors.predictors.utils.geometry import get_polygons


def generate_background_shapes(image_shape, shapes):
    BUFFER_PX = 40
    UNBUFFER_PX = 40

    image_bbox = box(0, 0, *image_shape[:2][::-1])

    # First we buffer/unbuffer the geometries to remove gaps between them
    shapes_union = (
        unary_union(shapes)
        .buffer(BUFFER_PX, cap_style=3, join_style=2)
        .buffer(-UNBUFFER_PX, cap_style=3, join_style=2)
    )

    # Then we only keep the shell of the unary union to remove holes in them,
    # thus we have the shell of all geometries
    shapes_union_polygon_exterior = [
        Polygon(shell=polygon.exterior)  # nosec
        for polygon in get_polygons(shapes_union)
    ]

    # Then we remove this shell from the entire image
    return tuple(
        get_polygons(image_bbox.difference(unary_union(shapes_union_polygon_exterior)))
    )

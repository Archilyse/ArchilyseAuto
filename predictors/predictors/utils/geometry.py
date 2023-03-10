from itertools import tee
from math import atan2, pi
from operator import itemgetter
from typing import List, Tuple, Union

import numpy as np
from numpy import array, dot, ndarray
from numpy.linalg import linalg
from shapely.affinity import rotate, translate
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def get_parameters_of_minimum_rotated_rectangle(
    polygon: Union[MultiPolygon, Polygon],
    rotation_axis_convention: str = "upper_left",
    return_annotation_convention: bool = True,
    align_short_side_to_x_axis: bool = False,
) -> List[float]:
    """
    Returns a minimum rotated rectangle with annotation parametrization depending on the use case:
    1. If the resulting rectangle still needs to be processed in the backend, it will not have its Y-axis inverted
    2. If the resulting rectangle needs to fulfill the Editor requirements, it will have its Y-axis inverted and
        its angle will be a result of subtraction of 360 from the angle to X-axis.

    rotation_axis: the rotation point for the annotation rectangle on the lower left or upper left edge. The
        rotation axis is always determined after rotating the geometry to its equilibrium state, such that its
        longest edge is lined-up parallel to the X-axis.
        If align_short_side_to_x_axis is set to True, the short side is lined up parallel to the X-axis instead.
            This is necessary to be able to correctly represent elements in the react planner (see
            IfcToReactPlannerMapper._infer_angle_from_walls)
    return_annotation_convention: if True the angle is returned clockwise and the y coordinate inverted

    returns [x, y, dx, dy, angle] where:
    x: rotation axis x coordinate
    y: rotation axis y coordinate
    dx: x-extension of the axis aligned bounding box
    dy: y-extension of the axis aligned bounding box
    angle: rotation angle of the resulting annotation rectangle in degrees from its equilibrium state where
        negative values are counterclockwise and positive values are clockwise.
    """
    bounding_box = polygon.minimum_rotated_rectangle
    coords = [coord for coord in bounding_box.exterior.coords]

    i, j = (
        get_indexes_long_side(coords=coords)
        if not align_short_side_to_x_axis
        else get_indexes_short_side(coords=coords)
    )
    angle = get_angle_to_horizontal_axis(p1=coords[i], p2=coords[j])

    rotation_axis = get_rotation_axis(
        coords=coords,
        angle=angle,
        axis_index=i,
        rotation_axis_convention=rotation_axis_convention,
    )

    # offset the bounding box to the 'equilibrium state' such that it is aligned with X-axis
    axis_aligned_bounding_box = rotate(
        geom=bounding_box, angle=-angle, origin=rotation_axis
    )

    dx, dy = (
        abs(axis_aligned_bounding_box.bounds[0] - axis_aligned_bounding_box.bounds[2]),
        abs(axis_aligned_bounding_box.bounds[1] - axis_aligned_bounding_box.bounds[3]),
    )
    if return_annotation_convention:
        return [rotation_axis.x, -rotation_axis.y, dx, dy, 360 - angle]
    return [rotation_axis.x, rotation_axis.y, dx, dy, angle]


def get_indexes_long_side(coords: List[Tuple[float, float]]) -> Tuple[int, int]:
    if Point(coords[0]).distance(Point(coords[1])) > Point(coords[1]).distance(
        Point(coords[2])
    ):
        return 0, 1
    return 1, 2


def get_indexes_short_side(coords: List[Tuple[float, float]]) -> Tuple[int, int]:
    if Point(coords[0]).distance(Point(coords[1])) > Point(coords[1]).distance(
        Point(coords[2])
    ):
        return 1, 2
    return 0, 1


def get_angle_to_horizontal_axis(
    p1: Tuple[float, float], p2: Tuple[float, float]
) -> float:
    return (
        atan2(
            (p2[1] - p1[1]),
            (p2[0] - p1[0]),
        )
        * 360
        / (2 * pi)
    )


def get_rotation_axis(
    coords: List[Tuple[float, float]],
    angle: float,
    axis_index: int,
    rotation_axis_convention: str,
) -> Point:
    axis_alligned_coords = [
        rotate(geom=Point(coord), angle=-angle, origin=coords[axis_index])
        for coord in coords
    ]
    xmin, ymin, ymax = (
        min([coord.x for coord in axis_alligned_coords]),
        min([coord.y for coord in axis_alligned_coords]),
        max([coord.y for coord in axis_alligned_coords]),
    )

    upper_left_point = Point(xmin, ymax)
    lower_left_point = Point(xmin, ymin)

    current_rotation_axis = Point(coords[axis_index])

    if current_rotation_axis.distance(
        upper_left_point
    ) > current_rotation_axis.distance(lower_left_point):
        return (
            Point(coords[axis_index + 3])
            if rotation_axis_convention == "upper_left"
            else current_rotation_axis
        )
    return (
        current_rotation_axis
        if rotation_axis_convention == "upper_left"
        else Point(coords[axis_index + 3])
    )


def get_polygon_from_pos_dim_angle(
    pos: Tuple[float, float],
    dim: Tuple[float, float],
    angle: float,
    centroid=True,
) -> Polygon:
    """Extract a 2d polygon from bounding box parameters

    this aabb starts at the origin like follows:
            dim[0]
            -----
            |    |
            |    | dim[1]
            |    |
            o----
          (0,0)

    Returns:
        Polygon: A shapely polygon
    """
    polygon = get_polygon_from_dim(dim=dim, centroid=centroid)
    polygon = rotate_translate_polygon(
        polygon=polygon, x_off=pos[0], y_off=pos[1], angle=angle
    )
    return polygon


def get_polygon_from_dim(dim: Tuple[float, float], centroid: bool = True) -> Polygon:
    """Extract a 2d polygon from bounding box parameters

    this build starts at the origin - if centroid is true - as follows:
            dim[0]
            ------
            |(0,0)|
            |  o  | dim[1]
            |     |
             -----

    where as centroid is false it is build as follows:

            dim[0]
            -----
            |    |
            |    | dim[1]
            |    |
            o----
            (0,0)

    Args:
        dim ([float]): The 2d dimensions of the bounding box
        centroid: if source is centroid or lower left corner

    Returns:
        Polygon: A shapely polygon
    """
    if centroid:
        points = (
            np.array(
                [
                    [-dim[0], -dim[1]],
                    [dim[0], -dim[1]],
                    [dim[0], dim[1]],
                    [-dim[0], dim[1]],
                ]
            )
            / 2
        )
    else:
        v1 = np.asarray([0, 0])
        v2 = v1 + np.asarray([dim[0], 0])
        v3 = v1 + np.asarray([dim[0], dim[1]])
        v4 = v1 + np.asarray([0, dim[1]])
        points = [v1, v2, v3, v4]

    return Polygon(points)


def rotate_translate_polygon(
    polygon: Polygon,
    x_off: float,
    y_off: float,
    angle: float,
    pivot: Tuple[float, float] = (0, 0),
) -> Polygon:
    if angle:
        polygon = rotate(polygon, -angle, origin=(pivot[0], pivot[1]))
    polygon = translate(polygon, xoff=x_off, yoff=y_off)
    return polygon


def pairwise(iterable):
    """https://docs.python.org/3/library/itertools.html s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def get_sides_as_lines_by_length(polygon: Polygon) -> List[LineString]:
    """Takes a polygon as input and returns all sides as Linestrings
    in length size ordered sequence increasing

    Args:
        polygon (Polygon): shapely polygon

    Returns:
        List[LineString]: List of Sides as LineString
    """
    return sorted(
        [
            LineString([point_a, point_b])
            for point_a, point_b in pairwise(orient(polygon=polygon).exterior.coords[:])
        ],
        key=lambda x: x.length,
    )


def get_center_line_from_rectangle(
    polygon: Polygon, only_longest: bool = True
) -> Tuple:
    """Given a rectangle polygon it returns the line starting in the middle of the shorter side and ending
    in the center of the other most short side of the polygon as per the image:

               +-----------------------------------+
               |                                   |
             a +-----------------------------------+ b
               |                                   |
               +-----------------------------------+

    If only longest is False also the shorter centerline is returned

    """
    four_sides = get_sides_as_lines_by_length(polygon=polygon)
    shortest_line = four_sides[0]
    other_sides_sorted_by_most_parallel = sorted(
        [
            (
                other_line,
                abs(
                    dot_product_normalised_linestrings(
                        line_a=shortest_line, line_b=other_line
                    )
                ),
            )
            for other_line in four_sides[1:]
        ],
        key=itemgetter(1),
        reverse=True,
    )
    parallel_side = other_sides_sorted_by_most_parallel[0][0]
    if only_longest:
        return (LineString([shortest_line.centroid, parallel_side.centroid]),)

    return LineString([shortest_line.centroid, parallel_side.centroid]), LineString(
        [
            other_sides_sorted_by_most_parallel[1][0].centroid,
            other_sides_sorted_by_most_parallel[2][0].centroid,
        ]
    )


def dot_product_normalised_linestrings(
    line_a: LineString, line_b: LineString
) -> Union[ndarray, float]:
    """
    The returned value is between [-1,1]
    """
    coords_a = line_a.coords
    coords_b = line_b.coords
    a_x1, a_y1, a_x2, a_y2 = (
        coords_a[0][0],
        coords_a[0][1],
        coords_a[1][0],
        coords_a[1][1],
    )
    b_x1, b_y1, b_x2, b_y2 = (
        coords_b[0][0],
        coords_b[0][1],
        coords_b[1][0],
        coords_b[1][1],
    )

    v_a = array([a_x2 - a_x1, a_y2 - a_y1])

    v_b = array([b_x2 - b_x1, b_y2 - b_y1])

    return round(
        dot(v_a / linalg.norm(v_a), v_b / linalg.norm(v_b)), ndigits=6
    )  # rounding is necessary to avoid values below and above 1


def mask_to_shape(mask):
    """ATTENTION this closes holes!"""
    from skimage import measure

    mask_shape = unary_union(
        [
            pol
            for c in measure.find_contours(mask, 0.99)
            if (pol := Polygon(np.round(np.flip(c, axis=1)))).is_valid
        ]
    )
    if mask_shape.is_empty:
        return Polygon()
    return mask_shape


def get_polygons(geom):
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon):
        yield from geom.geoms
    elif isinstance(geom, GeometryCollection):
        for nested_geom in geom.geoms:
            yield from get_polygons(nested_geom)

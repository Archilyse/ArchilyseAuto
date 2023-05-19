from enum import Enum
from itertools import chain
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import segmentation_models_pytorch as smp
import torch
from PIL import Image
from shapely.affinity import rotate, scale, translate
from shapely.geometry import (
    CAP_STYLE,
    JOIN_STYLE,
    LineString,
    MultiLineString,
    Point,
    Polygon,
    box,
)
from skimage.measure import profile_line
from skimage.morphology import dilation, medial_axis, skeletonize, square
from skimage.transform import probabilistic_hough_line

from predictors.predictors.base import BasePredictor, MultiClassPrediction
from predictors.predictors.constants import ClassLabel
from predictors.predictors.utils.geometry import (
    get_center_line_from_rectangle,
    get_polygons,
    mask_to_shape,
)
from predictors.predictors.utils.tiling import (
    get_image_tile_bounds,
    pad_image_if_needed,
    unpad_image_if_needed,
)


class SegmentationLabel(Enum):
    BACKGROUND = 0
    SPACES = 1
    SEPARATORS = 2
    WALLS = 3
    RAILINGS = 4
    OPENINGS = 5
    WINDOWS = 6
    DOORS = 7


class WallPredictor(BasePredictor):
    CLASSES = [
        SegmentationLabel.BACKGROUND,
        SegmentationLabel.SPACES,
        SegmentationLabel.SEPARATORS,
        SegmentationLabel.WALLS,
        SegmentationLabel.RAILINGS,
        SegmentationLabel.OPENINGS,
        SegmentationLabel.WINDOWS,
        SegmentationLabel.DOORS,
    ]
    TILE_SIZE = 1024
    ENCODER = "resnet101"
    ENCODER_WEIGHTS = "imagenet"

    TORCH_MODEL_PATH = Path("resources/walls_model_latest.pth")
    TORCH_DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

    def __init__(self, model_path: Optional[Path] = None):
        from predictors.tasks.utils.logging import logger

        if model_path is None:
            model_path = self.TORCH_MODEL_PATH

        logger.info(f"WallPredictor using device {self.TORCH_DEVICE}")
        self.model = torch.load(
            model_path, map_location=torch.device(self.TORCH_DEVICE)
        )

    def preprocess(self, image, **kwargs):
        return (
            smp.encoders.get_preprocessing_fn(self.ENCODER, self.ENCODER_WEIGHTS)(image)
            .transpose(2, 0, 1)
            .astype("float32")
        )

    def predict(self, image) -> MultiClassPrediction:
        pred_mask = self.predict_tiled(image=image)

        wall_mask = np.clip(
            np.maximum.reduce(
                [
                    pred_mask[SegmentationLabel.SEPARATORS.value],
                    pred_mask[SegmentationLabel.WALLS.value],
                    pred_mask[SegmentationLabel.OPENINGS.value],
                    pred_mask[SegmentationLabel.DOORS.value],
                    pred_mask[SegmentationLabel.WINDOWS.value],
                ]
            )
            - dilation(pred_mask[SegmentationLabel.RAILINGS.value], square(3)),
            0,
            1,
        )
        window_mask = pred_mask[SegmentationLabel.WINDOWS.value]
        door_mask = pred_mask[SegmentationLabel.DOORS.value]

        wall_shapes = MaskPostprocessor.get_rectangles(
            mask=wall_mask,
            pred_threshold=0.08,
            hough_threshold=11,
            hough_min_length=13,
            hough_max_gap=15,
            hough_angles=np.arange(0, np.pi, np.pi / 64),
            segment_min_width=1,
            segment_min_length=10,
            segment_width_percentiles=25,
            segment_min_width_percentile=50,
            segment_snap_distance=20,
            corner_scale_distance=30,
        )
        wall_labels = (ClassLabel.WALL,) * len(wall_shapes)

        railing_shapes = self.predict_railings(pred_mask=pred_mask)
        railing_labels = (ClassLabel.RAILING,) * len(railing_shapes)

        door_shapes = [
            self.adjust_geometry_to_wall(opening=shape, wall=wall)
            for shape in get_polygons(mask_to_shape(door_mask > 0.001))
            for wall in wall_shapes
            if shape.intersects(wall)
        ]
        door_shapes = [s for s in door_shapes if s is not None and not s.is_empty]
        door_labels = (ClassLabel.DOOR,) * len(door_shapes)

        window_shapes = [
            self.adjust_geometry_to_wall(opening=shape, wall=wall)
            for shape in get_polygons(mask_to_shape(window_mask > 0.001))
            for wall in wall_shapes
            if shape.intersects(wall)
        ]
        window_shapes = [s for s in window_shapes if s is not None and not s.is_empty]
        window_labels = (ClassLabel.WINDOW,) * len(window_shapes)

        labels = wall_labels + railing_labels + door_labels + window_labels
        shapes = (
            wall_shapes + railing_shapes + tuple(door_shapes) + tuple(window_shapes)
        )
        return labels, tuple(shapes)

    def predict_railings(self, pred_mask: np.ndarray) -> Tuple[Polygon, ...]:
        railing_polygons = MaskPostprocessor.get_rectangles(
            mask=np.maximum.reduce(
                [
                    pred_mask[SegmentationLabel.RAILINGS.value],
                ]
            ),
            segment_min_width=0.5,
            segment_min_length=5,
        )

        return tuple(railing_polygons)

    def predict_tiled(self, image: Image) -> np.array:
        image = np.asarray(image)
        width, height = image.shape[:2]

        mask = np.zeros((width, height, len(self.CLASSES)))
        for x1, y1, x2, y2 in get_image_tile_bounds(
            width=width,
            height=height,
            tile_size=self.TILE_SIZE,
            tile_stride=self.TILE_SIZE - 128,
        ):
            tile = pad_image_if_needed(
                image[x1:x2, y1:y2, :],
                min_width=self.TILE_SIZE,
                min_height=self.TILE_SIZE,
            )
            preprocessed_tile = self.preprocess(tile)
            x_tensor = (
                torch.from_numpy(preprocessed_tile).to(self.TORCH_DEVICE).unsqueeze(0)
            )
            pred_mask = (
                self.model(x_tensor).detach().squeeze().cpu().numpy().transpose(1, 2, 0)
            )
            unpadded_pred_mask = unpad_image_if_needed(
                pred_mask, original_width=x2 - x1, original_height=y2 - y1
            )
            mask[x1:x2, y1:y2, :] = np.maximum(
                mask[x1:x2, y1:y2, :],
                unpadded_pred_mask,
            )
        return mask.transpose(2, 0, 1)

    @classmethod
    def adjust_geometry_to_wall(
        cls, opening: Polygon, wall: Polygon, buffer_width: Optional[float] = None
    ) -> Polygon:
        """Adjust opening to the separator it belongs to prevent the opening from not
        covering completely the separator.
        This is a legacy method used in the old editor, still used for the ifc import.
        """
        long_line, short_line = get_center_line_from_rectangle(
            opening.minimum_rotated_rectangle, only_longest=False
        )
        scaled_opening_orthogonal_axis = scale(short_line, 5, 5)

        opening_normal = np.array(long_line.coords[1]) - np.array(long_line.coords[0])
        axis_left = translate(
            scaled_opening_orthogonal_axis, *(-opening_normal / 2)
        ).intersection(wall)
        axis_right = translate(
            scaled_opening_orthogonal_axis, *(opening_normal / 2)
        ).intersection(wall)

        if isinstance(axis_left, MultiLineString):
            axis_left = sorted(
                filter(lambda z: not z.is_empty, axis_left.geoms),
                key=lambda z: z.distance(opening),
            )[0]

        if isinstance(axis_right, MultiLineString):
            axis_right = sorted(
                filter(lambda z: not z.is_empty, axis_right.geoms),
                key=lambda z: z.distance(opening),
            )[0]

        center_left, center_right = axis_left.centroid, axis_right.centroid

        if center_right.is_empty or center_left.is_empty:
            return None

        center_axis = LineString([center_left, center_right])
        normal_axis = rotate(center_axis, 90, origin="centroid").intersection(wall)
        return center_axis.buffer(
            normal_axis.length / 2,
            join_style=JOIN_STYLE.mitre,
            cap_style=CAP_STYLE.flat,
        )


class MaskPostprocessor:
    @staticmethod
    def _get_rectangles_from_line(
        line,
        corners,
        medial_axis_distance,
        segment_min_width,
        segment_min_length,
        segment_width_percentile,
        segment_min_width_percentile,
        segment_snap_distance,
    ):
        intersecting_corners = []
        for corner in corners:
            if line.distance(corner) < segment_min_length / 2:
                intersecting_corners.append(line.interpolate(line.project(corner)))

        intersecting_corners_sorted = [
            c for c in sorted(intersecting_corners, key=lambda z: line.project(z))
        ]

        rectangles = []
        for segment_start, segment_end in zip(
            intersecting_corners_sorted[:-1], intersecting_corners_sorted[1:]
        ):
            segment_widths = profile_line(
                image=medial_axis_distance.T,
                src=segment_start.coords[0],
                dst=segment_end.coords[0],
            )
            min_segment_width = np.percentile(
                segment_widths, segment_min_width_percentile
            )
            segment_width = np.percentile(segment_widths, segment_width_percentile)
            if (
                min_segment_width > segment_min_width
                and segment_start.distance(segment_end) > segment_min_length
            ):
                rectangle = LineString([segment_start, segment_end]).buffer(
                    segment_width, cap_style=3, join_style=2
                )
                rectangles.append(rectangle)
        return rectangles

    @classmethod
    def get_rectangles(
        cls,
        mask,
        pred_threshold=0.5,
        hough_threshold=10,
        hough_min_length=10,
        hough_max_gap=5,
        hough_angles=None,
        segment_min_width=1,
        segment_min_length=20,
        segment_width_percentiles=25,
        segment_min_width_percentile=50,
        segment_snap_distance=20,
        corner_scale_distance=20,
    ) -> Tuple[Polygon, ...]:
        wall_mask_gray = (mask > pred_threshold).astype(np.uint8)
        _, medial_axis_distance = medial_axis(wall_mask_gray, return_distance=True)
        line_proposals, corners = cls._get_line_proposals(
            mask=wall_mask_gray,
            hough_threshold=hough_threshold,
            hough_min_length=hough_min_length,
            hough_max_gap=hough_max_gap,
            hough_angles=hough_angles,
            corner_scale_distance=corner_scale_distance,
        )

        rectangles = chain(
            *[
                cls._get_rectangles_from_line(
                    line=line,
                    corners=corners,
                    medial_axis_distance=medial_axis_distance,
                    segment_min_width=segment_min_width,
                    segment_min_length=segment_min_length,
                    segment_width_percentile=segment_width_percentiles,
                    segment_min_width_percentile=segment_min_width_percentile,
                    segment_snap_distance=segment_snap_distance,
                )
                for line in line_proposals
            ]
        )

        return tuple([r for r in rectangles if r is not None and not r.is_empty])

    @classmethod
    def _get_line_proposals(
        cls,
        mask,
        hough_threshold=10,
        hough_min_length=10,
        hough_max_gap=5,
        hough_angles=None,
        corner_scale_distance=20,
    ):
        if hough_angles is None:
            hough_angles = np.arange(0, np.pi, np.pi / 32)

        width, height = mask.shape[:2]
        maxdim = max(height, width)
        skeleton = skeletonize(mask, method="lee")
        image_box = box(0, 0, height, width)

        line_segments = []
        lines = []
        for start, end in probabilistic_hough_line(
            skeleton,
            threshold=hough_threshold,
            line_length=hough_min_length,
            line_gap=hough_max_gap,
            theta=hough_angles,
        ):
            line_segments.append(LineString([start, end]))
            lines.append(
                scale(LineString([start, end]), maxdim, maxdim).intersection(image_box)
            )

        corners = []
        for i, line in enumerate(line_segments):
            for _, other_line in enumerate(line_segments[i + 1 :], start=i + 1):
                scaled_line = scale(
                    line,
                    1 + corner_scale_distance / line.length,
                    1 + corner_scale_distance / line.length,
                )
                scaled_other_line = scale(
                    other_line,
                    1 + corner_scale_distance / other_line.length,
                    1 + corner_scale_distance / other_line.length,
                )
                intersection = scaled_line.intersection(scaled_other_line)
                if isinstance(intersection, Point) and not intersection.is_empty:
                    corners.append(intersection)

        return lines, corners

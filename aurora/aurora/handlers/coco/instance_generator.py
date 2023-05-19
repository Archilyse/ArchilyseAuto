from dataclasses import dataclass
from itertools import groupby
from math import ceil
from typing import List, Union

import numpy as np
from rasterio.features import rasterize
from shapely.geometry import Polygon


@dataclass
class Instance:
    label: str
    iscrowd: int
    segmentation: Union[list, dict]
    bbox_absolute: list
    area: float


class InstanceGenerator:
    @classmethod
    def generate_instance(
        cls,
        geometry: Polygon,
        label: str,
        image_width: int,
        image_height: int,
        force_rle: bool = False,
        force_polygon: bool = False,
    ) -> Instance:
        iscrowd = 0

        return Instance(
            label=label,
            bbox_absolute=cls.get_bounding_box(geometry=geometry),
            iscrowd=iscrowd,
            segmentation=cls.get_segmentation(
                geometry=geometry,
                image_width=image_width,
                image_height=image_height,
                force_rle=force_rle,
                force_polygon=force_polygon,
            ),
            area=geometry.area,
        )

    @staticmethod
    def binary_mask_to_rle(binary_mask):
        rle = {"counts": [], "size": list(binary_mask.shape)}
        counts = rle.get("counts")
        for i, (value, elements) in enumerate(groupby(binary_mask.ravel(order="F"))):
            if i == 0 and value == 1:
                counts.append(0)
            counts.append(len(list(elements)))
        return rle

    @classmethod
    def get_segmentation(
        cls,
        geometry: Polygon,
        image_width: int,
        image_height: int,
        force_rle: bool = False,
        force_polygon: bool = False,
    ) -> Union[List[float], dict]:
        if force_rle or (force_polygon is False and geometry.interiors):
            binary_mask = cls.get_mask(
                geometry=geometry,
                image_width=image_width,
                image_height=image_height,
            )
            return cls.binary_mask_to_rle(binary_mask=np.asfortranarray(binary_mask))

        return [np.array(geometry.exterior.coords).ravel().tolist()]

    @classmethod
    def get_mask(
        cls, geometry: Polygon, image_width: int, image_height: int
    ) -> np.array:
        return rasterize(
            [geometry], out_shape=(image_height, image_width), dtype=np.uint8
        )

    @classmethod
    def get_bbox_width_height(cls, geometry: Polygon) -> List[float]:
        x1, y1, x2, y2 = geometry.bounds
        width, height = ceil(x2 - x1), ceil(y2 - y1)

        return [x1, y1, x2, y2, width, height]

    @classmethod
    def get_bounding_box(cls, geometry: Polygon) -> List[float]:
        x1, y1, _, _, width, height = cls.get_bbox_width_height(geometry=geometry)

        return [x1, y1, width, height]

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, List

from PIL import Image
from shapely.affinity import translate
from shapely.geometry import MultiPolygon, Polygon, box

from aurora.handlers.coco.instance_generator import Instance, InstanceGenerator


@dataclass
class Sample:
    filepath: Path
    width: int
    height: int
    detections: List[Instance]


class SampleGenerator:
    @staticmethod
    def get_samples(
        image_file_path: Path,
        image_width: int,
        image_height: int,
        geometries: DefaultDict[str, List[Polygon]],
    ) -> List[Sample]:
        detections = [
            InstanceGenerator.generate_instance(
                geometry=geometry,
                label=class_label,
                image_width=image_width,
                image_height=image_height,
            )
            for class_label, class_geometries in geometries.items()
            for geometry in class_geometries
        ]

        if detections:
            return [
                Sample(
                    filepath=image_file_path,
                    width=image_width,
                    height=image_height,
                    detections=detections,
                )
            ]

        return []

    @classmethod
    def get_samples_tiled(
        cls,
        image_file_path: Path,
        image_width: int,
        image_height: int,
        geometries: DefaultDict[str, List[Polygon]],
        tile_size: int,
        tile_stride: int,
        tile_output_path: Path,
    ) -> List[Sample]:
        image = Image.open(image_file_path)
        samples = []

        for tile_index, (x1, y1, x2, y2) in enumerate(
            cls.get_tile_bounds(
                width=image_width,
                height=image_height,
                tile_size=tile_size,
                tile_stride=tile_stride,
            )
        ):
            tile_box = box(x1, y1, x2, y2)
            tile_image_path = tile_output_path.joinpath(
                f"{image_file_path.stem}.{tile_index}{image_file_path.suffix}"
            )

            tile_geometries: DefaultDict[str, list] = defaultdict(List)
            for label, label_geometries in geometries.items():
                for geometry in label_geometries:
                    if tile_box.intersects(geometry):
                        tile_geometry = translate(
                            tile_box.intersection(geometry), xoff=-x1, yoff=-y1
                        )

                        if isinstance(tile_geometry, MultiPolygon):
                            tile_geometries[label] += [
                                geom for geom in tile_geometry.geoms
                            ]
                        elif isinstance(tile_geometry, Polygon):
                            tile_geometries[label].append(tile_geometry)

            if sum([len(v) for v in tile_geometries.values()]) == 0:
                # No geometries in tile
                continue

            tile_image = image.crop((x1, y1, x2, y2))
            tile_image.save(tile_image_path, quality=100)
            samples += cls.get_samples(
                image_file_path=tile_image_path,
                image_width=tile_image.width,
                image_height=tile_image.height,
                geometries=tile_geometries,
            )

        return samples

    @staticmethod
    def get_tile_bounds(width: int, height: int, tile_size: int, tile_stride: float):
        N, M = math.ceil(width / tile_stride), math.ceil(height / tile_stride)
        for i in range(N):
            for j in range(M):
                x1, y1 = i * tile_stride, j * tile_stride
                x2, y2 = min(tile_stride * i + tile_size, width), min(
                    tile_stride * j + tile_size, height
                )

                if x2 == width and (x2 - x1) < tile_size / 4:
                    continue
                if y2 == height and (y2 - y1) < tile_size / 4:
                    continue

                yield (x1, y1, x2, y2)

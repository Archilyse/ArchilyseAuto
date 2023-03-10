import math
from itertools import product

import cv2
import numpy as np
from detectron2.engine import DefaultPredictor
from detectron2.structures import Boxes, Instances
from shapely.geometry import box


class TiledPredictor(DefaultPredictor):
    def __init__(self, cfg, tile_size, max_instance_size, merge_threshold):
        self.max_instance_size = max_instance_size
        self.tile_size = tile_size
        self.stride = self.tile_size - self.max_instance_size
        self.merge_threshold = merge_threshold
        assert self.stride >= self.max_instance_size

        super().__init__(cfg)

    def _get_tile_slices(self, tile, shape):
        height, width = shape[:2]
        from_row, from_col = [rc * self.stride for rc in tile]
        to_row = min(height, from_row + self.tile_size)
        to_col = min(width, from_col + self.tile_size)
        if len(shape) == 3:
            return slice(from_row, to_row), slice(from_col, to_col), slice(0, shape[2])
        return slice(from_row, to_row), slice(from_col, to_col)

    def _tile_image(self, image):
        height, width = image.shape[:2]
        rows, cols = math.ceil(height / self.stride), math.ceil(width / self.stride)
        return [
            (row, col, image[self._get_tile_slices(tile=(row, col), shape=image.shape)])
            for row, col in product(range(rows), range(cols))
        ]

    def _get_tiled_instances(self, image):
        for row, col, image_tile in self._tile_image(image=image):
            instances = super().__call__(image_tile)["instances"].to("cpu")
            if instances.pred_masks.any():
                yield row, col, list(
                    zip(
                        instances.pred_masks,
                        instances.pred_boxes,
                        instances.pred_classes,
                        instances.scores,
                    )
                )

    @staticmethod
    def _filter_instances(tiled_instances):
        """This method excludes instances touching the tile borders"""
        return [
            (row, col, non_border_touching)
            for row, col, instances in tiled_instances
            if (
                non_border_touching := [
                    (pred_mask, (xmin, ymin, xmax, ymax), pred_class, score)
                    for pred_mask, (
                        xmin,
                        ymin,
                        xmax,
                        ymax,
                    ), pred_class, score in instances
                    if int(xmin) > 0 < int(ymin)
                    and math.ceil(xmax) < pred_mask.shape[1]
                    and math.ceil(ymax) < pred_mask.shape[0]
                ]
            )
        ]

    def _untile_instances(self, tiled_instances, image_shape):
        untiled_instances = []
        for row, col, instances in tiled_instances:
            for pred_mask, pred_box, pred_class, score in instances:
                untiled_mask = np.zeros(image_shape[:2], dtype=bool)
                untiled_mask[
                    self._get_tile_slices(tile=(row, col), shape=image_shape[:2])
                ] = pred_mask
                untiled_bbox = [
                    pred_box[0] + col * self.stride,
                    pred_box[1] + row * self.stride,
                    pred_box[2] + col * self.stride,
                    pred_box[3] + row * self.stride,
                ]
                untiled_instances.append(
                    (untiled_mask, untiled_bbox, pred_class, score)
                )
        return untiled_instances

    @staticmethod
    def _intersection_ij(pred_mask_i, pred_mask_j):
        return 1 - (np.sum(pred_mask_i + pred_mask_j) - np.sum(pred_mask_i)) / np.sum(
            pred_mask_j
        )

    def _get_instances_to_merge(self, instances):
        masks_and_classes = [(mask, class_) for mask, _, class_, _ in instances]
        return [
            (i, j)
            for i, j, intersection in sorted(
                [
                    (i, j, self._intersection_ij(mask_i, mask_j))
                    for i, (mask_i, class_i) in enumerate(masks_and_classes)
                    for j, (mask_j, class_j) in enumerate(masks_and_classes)
                    if i != j and class_i == class_j
                ],
                key=lambda iji: iji[2],
                reverse=True,
            )
            if intersection > self.merge_threshold
        ]

    def _merge_instances(self, instances: list):
        instances_to_merge = self._get_instances_to_merge(instances)
        merged_instances = []
        while instances_to_merge:
            i, j = instances_to_merge[0]
            mask, bbox, class_, score = instances[i]
            mask += instances[j][0]
            bbox = box(*instances[j][1]).union(box(*bbox)).bounds
            instances[i] = mask, bbox, class_, score
            instances_to_merge = [ij for ij in instances_to_merge if j not in ij]
            merged_instances.append(j)
        for i in sorted(merged_instances, reverse=True):
            del instances[i]
        return instances

    def _predict(self, image):
        merged_instances = self._merge_instances(
            instances=self._untile_instances(
                tiled_instances=self._filter_instances(
                    tiled_instances=self._get_tiled_instances(image=image)
                ),
                image_shape=image.shape,
            )
        )

        pred_masks, pred_boxes, pred_classes, scores = map(
            np.array, zip(*merged_instances) if merged_instances else [[]] * 4
        )

        image_instances = Instances(image_size=image.shape[:2])
        image_instances.set("pred_classes", pred_classes)
        image_instances.set("scores", scores)
        image_instances.set("pred_boxes", Boxes(pred_boxes))
        image_instances.set("pred_masks", pred_masks)

        return {"instances": image_instances}

    def __call__(self, image):
        return self._predict(image)

    def model(self, dataset_dicts):
        return [self._predict(cv2.imread(d["file_name"])) for d in dataset_dicts]

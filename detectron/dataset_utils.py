import json
import random
from collections import defaultdict
from pathlib import Path
from typing import List

import detectron2.data.transforms as T
from detectron2.data import DatasetMapper
from detectron2.data.datasets import register_coco_instances


def filter_coco_json(
    input_filename: Path,
    output_filename: Path,
    thing_classes: List[str],
):
    with open(input_filename) as f:
        coco = json.load(f)

    categories_filtered = {
        cat["id"]: cat for cat in coco["categories"] if cat["name"] in thing_classes
    }
    new_category_ids = {
        cat["id"]: thing_classes.index(cat["name"]) + 1
        for cat in categories_filtered.values()
    }

    images_by_id = {img["id"]: img for img in coco["images"]}

    annotations_by_image_id = defaultdict(list)
    for ann in coco["annotations"]:
        if ann["category_id"] in categories_filtered:
            annotations_by_image_id[ann["image_id"]].append(ann)

    filtered_images = []
    filtered_annotations = []
    new_img_id = 1
    new_ann_id = 1

    for img_id, annotations in annotations_by_image_id.items():
        filtered_images.append({**images_by_id[img_id], "id": new_img_id})
        for ann in annotations:
            filtered_annotations.append(
                {
                    **ann,
                    "category_id": new_category_ids[ann["category_id"]],
                    "image_id": new_img_id,
                    "id": new_ann_id,
                }
            )
            new_ann_id += 1
        new_img_id += 1

    coco["images"] = filtered_images
    coco["annotations"] = filtered_annotations
    coco["categories"] = [
        {**cat, "id": new_category_ids[cat["id"]]}
        for cat in categories_filtered.values()
    ]

    with open(output_filename, mode="w") as f:
        json.dump(coco, f)


def register_datasets(cfg, coco_directory, thing_classes, thing_colors):
    for dataset, dataset_name in [
        ("validation", cfg.DATASETS.TEST[0]),
        ("train", cfg.DATASETS.TRAIN[0]),
    ]:
        filtered_coco_json = Path(f"coco-{dataset}-filtered.json")
        filter_coco_json(
            input_filename=coco_directory.joinpath(dataset, "coco.json"),
            output_filename=filtered_coco_json,
            thing_classes=thing_classes,
        )
        register_coco_instances(
            dataset_name,
            dict(thing_colors=thing_colors),
            filtered_coco_json.as_posix(),
            coco_directory.joinpath(dataset, "images").as_posix(),
        )


class RandomTileMapper:
    def __init__(self, cfg, tile_sizes, **kwargs):
        self.mapper = self.get_mapper(cfg, tile_sizes, **kwargs)

    @staticmethod
    def get_mapper(cfg, tile_sizes, **kwargs):
        return [
            DatasetMapper(
                cfg,
                **kwargs,
                augmentations=[
                    T.RandomFlip(vertical=False, horizontal=True, prob=1 / 3),
                    T.RandomFlip(vertical=True, horizontal=False, prob=1 / 3),
                    T.FixedSizeCrop((tile_size, tile_size), pad=False),
                    T.ResizeShortestEdge(
                        short_edge_length=[640, 672, 704, 736, 768, 800],
                        max_size=1333,
                        sample_style="choice",
                    ),
                ],
            )
            for tile_size in tile_sizes
        ]

    @staticmethod
    def has_instances(mapped):
        return len(mapped["instances"].gt_boxes) > 0

    def try_map(self, mapper, dataset_dict):
        mapped = mapper(dataset_dict)
        if self.has_instances(mapped):
            return mapped

    def __call__(self, dataset_dict):
        mapped = None
        max_retries = 50

        i = 0
        mapper = random.choice(self.mapper)
        while i < max_retries and not (
            mapped := self.try_map(
                dataset_dict=dataset_dict,
                mapper=mapper,
            )
        ):
            i += 1
        return mapped


class SpaceTileMapper(RandomTileMapper):
    @staticmethod
    def has_complete_space(mapped):
        for bbox in mapped["instances"].gt_boxes.to("cpu"):
            h, w = mapped["image"].shape[1:]
            xmin, ymin, xmax, ymax = bbox.numpy()
            touches_borders = xmin < 1 or ymin < 1 or xmax > w - 1 or ymax > h - 1
            if not touches_borders:
                return True
        return False

    def try_map(self, mapper, dataset_dict):
        mapped = super().try_map(mapper, dataset_dict)
        if mapped and self.has_complete_space(mapped):
            return mapped


class IconTileMapper(RandomTileMapper):
    @staticmethod
    def has_border_touching_instances(mapped):
        for bbox in mapped["instances"].gt_boxes.to("cpu"):
            h, w = mapped["image"].shape[1:]
            xmin, ymin, xmax, ymax = bbox.numpy()
            touches_borders = xmin < 1 or ymin < 1 or xmax > w - 1 or ymax > h - 1
            if touches_borders:
                return True
        return False

    def try_map(self, mapper, dataset_dict):
        mapped = super().try_map(mapper, dataset_dict)
        if mapped and not self.has_border_touching_instances(mapped):
            return mapped

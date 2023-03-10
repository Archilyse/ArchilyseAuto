import json
from collections import defaultdict
from pathlib import Path


def _touches_border(annotation, image_width, image_height) -> bool:
    return (
        annotation["bbox"][0] < 1
        or annotation["bbox"][1] < 1
        or annotation["bbox"][0] + annotation["bbox"][2] > image_width - 1
        or annotation["bbox"][1] + annotation["bbox"][3] > image_height - 1
    )


def _is_tiling_artefact(annotation, image_width, image_height) -> bool:
    return annotation["area"] <= 90 and _touches_border(
        annotation, image_width, image_height
    )


def filter_coco_json(input_filename: Path, output_filename: Path, thing_classes):
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
        if ann["category_id"] in categories_filtered and not _is_tiling_artefact(
            annotation=ann,
            image_width=images_by_id[ann["image_id"]]["width"],
            image_height=images_by_id[ann["image_id"]]["height"],
        ):
            annotations_by_image_id[ann["image_id"]].append(ann)

    filtered_images = []
    filtered_annotations = []
    new_img_id = 1
    new_ann_id = 1

    for img_id, annotations in annotations_by_image_id.items():
        if any(
            _touches_border(
                annotation=ann,
                image_width=images_by_id[img_id]["width"],
                image_height=images_by_id[img_id]["height"],
            )
            for ann in annotations
        ):
            continue

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

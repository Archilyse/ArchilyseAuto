from datetime import datetime
from pathlib import Path
from typing import Dict, List

from tqdm import tqdm

from aurora.handlers.coco.model import (
    CocoAnnotation,
    CocoCategory,
    CocoDataset,
    CocoImage,
    CocoInfo,
    CocoSchema,
)
from aurora.handlers.coco.sample_generator import Sample


class CocoWriter:
    @staticmethod
    def export(
        samples: List[Sample],
        destination_file_path: Path,
        version: str,
        category_ids: Dict[str, int],
    ):
        categories_by_label: Dict[str, CocoCategory] = {}
        images: List[CocoImage] = []
        annotations: List[CocoAnnotation] = []

        for image_id, sample in tqdm(enumerate(samples)):
            images.append(
                CocoImage(
                    id=image_id,
                    file_name=sample.filepath.name,
                    date_captured=datetime.now(),
                    width=sample.width,
                    height=sample.height,
                )
            )

            for annotation_id, instance in enumerate(
                sample.detections, start=len(annotations)
            ):
                if not categories_by_label.get(instance.label):
                    categories_by_label[instance.label] = CocoCategory(
                        id=category_ids[instance.label],
                        name=instance.label,
                        supercategory="None",
                    )

                annotations.append(
                    CocoAnnotation(
                        id=annotation_id,
                        image_id=image_id,
                        category_id=categories_by_label[instance.label].id,
                        segmentation=instance.segmentation,
                        bbox=instance.bbox_absolute,
                        iscrowd=instance.iscrowd,
                        area=instance.area,
                    )
                )

        dataset = CocoDataset(
            info=CocoInfo(
                year=str(datetime.now().year),
                version=version,
                description="COCO dataset of Archilyse Floorplans",
                url="https://www.archilyse.com/data",
                date_created=datetime.now(),
            ),
            images=images,
            annotations=annotations,
            categories=list(categories_by_label.values()),
        )

        destination_file_path.parent.mkdir(parents=True, exist_ok=True)
        with destination_file_path.open("w") as fh:
            fh.write(CocoSchema().dumps(dataset))

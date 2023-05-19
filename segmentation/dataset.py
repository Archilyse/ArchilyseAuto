from pathlib import Path
from typing import Optional

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pycocotools.coco import COCO


class COCOSegementationDataset:
    def __init__(
        self,
        coco_json_path: Path,
        image_dir: Path,
        category_names: list,
        augmentation: Optional[list] = None,
        preprocessing: Optional[list] = None,
        add_background_dim: bool = False,
        max_num: Optional[int] = None,
    ):
        self.coco = COCO(coco_json_path)
        self.image_dir = image_dir
        self.image_ids = np.array(self.coco.getImgIds())
        self.category_names = np.array(category_names)
        self.category_ids = np.array(
            [self.coco.getCatIds(catNms=[c])[0] for c in category_names]
        )
        self.augmentation = augmentation
        self.preprocessing = preprocessing
        self.add_background_dim = add_background_dim
        self.max_num = max_num

    def __getitem__(self, i):
        image = self.get_image(img_id=self.image_ids[i])
        mask = self.get_mask_one_hot(img_id=self.image_ids[i])
        mask = mask.astype("float")

        if self.augmentation:
            sample = self.augmentation(image=image, mask=mask)
            image, mask = sample["image"], sample["mask"]

        if self.preprocessing:
            sample = self.preprocessing(image=image, mask=mask)
            image, mask = sample["image"], sample["mask"]

        if self.add_background_dim:
            is_background = np.sum(mask, axis=0) == 0
            mask = np.stack([is_background, *mask])

        return image, mask

    def __len__(self):
        return len(self.image_ids) if self.max_num is None else self.max_num

    def get_image(self, img_id: int) -> np.ndarray:
        coco_image = self.coco.loadImgs(ids=[img_id])[0]
        return cv2.imread(self.image_dir.joinpath(coco_image["file_name"]).as_posix())

    def get_mask_one_hot(self, img_id: int, binarized: bool = True) -> np.ndarray:
        """
        Returns mask as array of shape (image_height, image_width, n_classes)
        where the kth dimensions of pixel (y,x) is True exactly if it contains
        an object of class k.
        """
        coco_image = self.coco.loadImgs(ids=[img_id])[0]

        masks_one_hot = []
        for cat_id in self.category_ids:
            cat_mask = np.zeros(shape=(coco_image["height"], coco_image["width"]))
            for ann in self.coco.loadAnns(
                ids=self.coco.getAnnIds(imgIds=[img_id], catIds=[cat_id])
            ):
                ann_mask = self.coco.annToMask(ann)
                cat_mask = np.maximum(cat_mask, ann_mask * cat_id)

            if binarized:
                cat_mask = cat_mask > 0
            masks_one_hot.append(cat_mask)

        return np.stack(masks_one_hot, axis=-1)

    def get_mask_flat(self, mask_one_hot: np.ndarray) -> np.ndarray:
        """Transforms the mask to shape (image_height, image_width, 1) where
        the value at position (y,x) is 0 if no object is at this position or
        k if class of id k is at this position.

        In case that multiple classes are at position k, the order of self.category_names
        determines the value (e.g. for category_names=["A", "B"], B overrides A).
        """
        mask_flat = np.zeros(shape=(mask_one_hot.shape[0], mask_one_hot.shape[1], 1))

        cat_ids = self.category_ids
        for i, cat_id in enumerate(cat_ids):
            mask_flat[mask_one_hot[:, :, i] > 0, :] = cat_id

        return mask_flat

    def get_mask_rgb(self, mask_flat: np.ndarray, values=None) -> np.ndarray:
        """Transforms the flattened mask as returned by `get_mask_flat` to an
        ndarray of shape (image_height, image_width, 3) where each class has
        exactly one color.
        """
        if values is None:
            values = self.category_ids

        mask_rgb = np.zeros(shape=(mask_flat.shape[0], mask_flat.shape[1], 3))
        for i, value in enumerate(values):
            rgb = plt.cm.tab20(i)
            mask_rgb[mask_flat[:, :, 0] == value, :] = rgb[:3]

        return mask_rgb

    def visualize(self, i):
        image, mask = self[i]
        image = image.transpose(1, 2, 0)
        mask = mask.transpose(1, 2, 0)
        mask_rgb = self.get_mask_rgb(mask_flat=self.get_mask_flat(mask_one_hot=mask))

        f, axes = plt.subplots(
            1,
            2 + len(self.category_ids),
            figsize=(10 * (len(self.category_ids) + 2), 10),
        )
        axes[0].imshow(image)
        axes[1].imshow(mask_rgb)
        for i, (ax, category_name) in enumerate(
            zip(axes[2:], self.category_names),
            start=1 if self.add_background_dim else 0,
        ):
            ax.title.set_text(category_name)
            ax.imshow(mask[:, :, i])

        return f


class ImageOnlyDataset:
    def __init__(self, root, transform=None):
        self.image_paths = list(root.glob("*.*"))
        self.transform = transform

    def __getitem__(self, index):
        image_path = self.image_paths[index].as_posix()
        with Image.open(image_path) as image:
            transformed_image = self.transform(image.convert("RGB"))
            return transformed_image

    def __len__(self):
        return len(self.image_paths)

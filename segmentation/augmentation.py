from typing import Optional, Tuple

import albumentations as album


def training_augmentation(
    pad_size: int = 1024,
    crop_size: Optional[int] = None,
    max_size: Optional[int] = None,
    scaling: Optional[Tuple[float, float]] = None,
):
    transforms = []
    if max_size:
        transforms.append(album.LongestMaxSize(max_size=max_size))

    if scaling:
        transforms.append(
            album.augmentations.geometric.resize.RandomScale(
                scale_limit=scaling, always_apply=True
            )
        )

    transforms.append(
        album.PadIfNeeded(
            min_height=pad_size,
            min_width=pad_size,
            always_apply=True,
            border_mode=0,
            value=[255, 255, 255],
        )
    )
    if crop_size:
        transforms.append(
            album.RandomCrop(height=crop_size, width=crop_size, always_apply=True)
        )

    transforms.append(
        album.OneOf(
            [
                album.HorizontalFlip(p=1),
                album.VerticalFlip(p=1),
                album.RandomRotate90(p=1),
            ],
            p=0.75,
        )
    )

    return album.Compose(transforms)


def validation_augmentation(
    pad_size: int = 1024,
    crop_size: Optional[int] = None,
    max_size: Optional[int] = None,
    scaling: Optional[Tuple[float, float]] = None,
):
    return training_augmentation(
        pad_size=pad_size, crop_size=crop_size, max_size=max_size, scaling=scaling
    )

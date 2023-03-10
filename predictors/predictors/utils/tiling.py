import numpy as np


def get_image_tile_bounds(width: int, height: int, tile_size: int, tile_stride: float):
    N, M = int(np.ceil(width / tile_stride)), int(np.ceil(height / tile_stride))
    for i in range(N):
        for j in range(M):
            x1, y1 = i * tile_stride, j * tile_stride
            x2, y2 = min(tile_stride * i + tile_size, width), min(
                tile_stride * j + tile_size, height
            )

            yield (x1, y1, x2, y2)


def pad_image_if_needed(
    image: np.array,
    min_width: int,
    min_height: int,
    color: tuple = (255, 255, 255),
):
    width, height = image.shape[:2]
    pad_x = max(min_width, width) - width
    pad_y = max(min_height, height) - height

    if pad_x > 0 or pad_y > 0:
        result = np.full((width + pad_x, height + pad_y, 3), color)
        result[
            pad_x // 2 : pad_x // 2 + width, pad_y // 2 : pad_y // 2 + height, :
        ] = image
        return result

    return image


def unpad_image_if_needed(
    image: np.array,
    original_width: int,
    original_height: int,
):
    width, height = image.shape[:2]
    pad_x, pad_y = width - original_width, height - original_height
    return image[
        pad_x // 2 : pad_x // 2 + original_width,
        pad_y // 2 : pad_y // 2 + original_height,
    ]

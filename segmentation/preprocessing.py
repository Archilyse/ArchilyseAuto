import albumentations as album


def to_tensor(x, **kwargs):
    return x.transpose(2, 0, 1).astype("float32")


def preprocessing(preprocessing_fn=None):
    _transform = []
    if preprocessing_fn:
        _transform.append(album.Lambda(image=preprocessing_fn))
    _transform.append(album.Lambda(image=to_tensor, mask=to_tensor))

    return album.Compose(_transform)

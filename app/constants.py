from predictors.predictors.constants import ClassLabel

PIXEL_TO_METER_RATIO = 40
LABELS_CONSIDERED_BATH_EXCLUSIVE = {
    ClassLabel.TOILET,
    ClassLabel.BATHTUB,
    ClassLabel.SINK,
    ClassLabel.SHOWER,
}

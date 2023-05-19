from collections import defaultdict

from shapely.ops import unary_union

from predictors.predictors.constants import ClassLabel
from predictors.predictors.utils.geometry import get_polygons

PIXEL_TO_METER_RATIO = 40
LABELS_CONSIDERED_BATH_EXCLUSIVE = {
    ClassLabel.TOILET,
    ClassLabel.BATHTUB,
    ClassLabel.SINK,
    ClassLabel.SHOWER,
}


def calculate_stats(labels, shapes):
    room_count, bathroom_count, room_space, bathroom_space = get_room_stats(
        labels=labels, shapes=shapes
    )
    elems_stats = get_elements_stats(labels=labels, shapes=shapes)
    # Avoiding wall, railing and spaces count as those make not much sense
    return {
        "room_count": room_count,
        "bathroom_count": bathroom_count,
        "door_count": elems_stats.get("door_count", 0),
        "window_count": elems_stats.get("window_count", 0),
        "toilet_count": elems_stats.get("toilet_count", 0),
        "bathtub_count": elems_stats.get("bathtub_count", 0),
        "sink_count": elems_stats.get("sink_count", 0),
        "shower_count": elems_stats.get("shower_count", 0),
        "room_space": room_space,
        "bathroom_space": bathroom_space,
        "wall_space": elems_stats.get("wall_space", 0),
        "railing_space": elems_stats.get("railing_space", 0),
        "door_space": elems_stats.get("door_space", 0),
        "window_space": elems_stats.get("window_space", 0),
        "toilet_space": elems_stats.get("toilet_space", 0),
        "bathtub_space": elems_stats.get("bathtub_space", 0),
        "sink_space": elems_stats.get("sink_space", 0),
        "shower_space": elems_stats.get("shower_space", 0),
    }


def get_room_stats(labels, shapes):
    from predictors.predictors.constants import ClassLabel

    room_count = 0
    bathroom_count = 0
    room_pols = []
    bathroom_pols = []
    bath_pols = unary_union(
        [
            pol
            for pol, label in zip(shapes, labels)
            if label in LABELS_CONSIDERED_BATH_EXCLUSIVE
        ]
    )
    for pol, label in zip(shapes, labels):
        if label == ClassLabel.SPACE:
            if pol.intersects(bath_pols):
                bathroom_count += 1
                bathroom_pols.append(pol)
            else:
                room_count += 1
                room_pols.append(pol)
    room_space = unary_union(room_pols).area / PIXEL_TO_METER_RATIO**2
    bathroom_space = unary_union(bathroom_pols).area / PIXEL_TO_METER_RATIO**2
    return room_count, bathroom_count, room_space, bathroom_space


def get_elements_stats(labels, shapes):
    elements = defaultdict(list)
    for pol, label in zip(shapes, labels):
        elements[label].append(pol)
    result = {}
    for label, pols in elements.items():
        pols_union = unary_union(pols)
        result[f"{label.name.lower()}_count"] = len(tuple(get_polygons(pols_union)))
        result[f"{label.name.lower()}_space"] = (
            pols_union.area / PIXEL_TO_METER_RATIO**2
        )

    return result

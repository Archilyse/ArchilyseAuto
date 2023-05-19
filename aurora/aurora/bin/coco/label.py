from enum import Enum, auto
from typing import Set


class CocoLabel(Enum):
    SPACE = auto()
    # SHAFT = auto() # noqa:E800

    # # separators
    SEPARATOR = auto()
    WALL = auto()
    RAILING = auto()
    COLUMN = auto()
    WALL_UNION = auto()
    WALL_UNION_EX_OPENINGS = auto()
    RAILING_UNION = auto()

    # # Openings
    OPENING = auto()
    WINDOW = auto()
    DOOR = auto()

    # # Features
    FEATURE = auto()
    SINK = auto()
    TOILET = auto()
    BATHTUB = auto()
    SHOWER = auto()
    KITCHEN = auto()
    KITCHEN_UNION = auto()
    SINK_UNION = auto()
    BATHTUB_UNION = auto()
    TOILET_UNION = auto()
    SHOWER_UNION = auto()
    STAIRS = auto()  # noqa:E800
    STAIRS_UNION = auto()  # noqa:E800
    ELEVATOR = auto()  # noqa:E800
    ELEVATOR_UNION = auto()  # noqa:E800
    WINDOW_UNION = auto()
    DOOR_UNION = auto()

    # # Undefined
    IGNORE = auto()


def get_class_labels(entity_type: str, entity_subtype: str) -> Set[CocoLabel]:
    labels: Set[CocoLabel] = set()

    if entity_type == "area":
        return labels

    if entity_subtype.upper() in {label.name for label in CocoLabel}:
        labels.add(CocoLabel[entity_subtype.upper()])

    if entity_type.upper() in {label.name for label in CocoLabel}:
        labels.add(CocoLabel[entity_type.upper()])

    return labels

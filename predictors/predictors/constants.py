from enum import Enum


class ClassLabel(Enum):
    WALL = 0
    DOOR = 1
    WINDOW = 2
    KITCHEN = 3
    TOILET = 4
    SINK = 5
    SHOWER = 6
    BATHTUB = 7
    RAILING = 8
    SPACE = 9
    BACKGROUND = 10
    FOREGROUND = 11


COLORS = {
    ClassLabel.WALL: (42, 121, 161),
    ClassLabel.WINDOW: (255, 0, 0),
    ClassLabel.RAILING: (128, 0, 128),
    ClassLabel.DOOR: (0, 255, 0),
    ClassLabel.TOILET: (0, 255, 255),
    ClassLabel.BATHTUB: (255, 0, 255),
    ClassLabel.SINK: (0, 128, 0),
    ClassLabel.SHOWER: (192, 126, 24),
    ClassLabel.KITCHEN: (255, 255, 0),
    ClassLabel.SPACE: (250, 250, 210),
    ClassLabel.BACKGROUND: (0, 0, 0),
}

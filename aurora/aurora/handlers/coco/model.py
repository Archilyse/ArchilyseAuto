from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union

import marshmallow_dataclass


@dataclass
class CocoImage:
    id: int
    file_name: str
    date_captured: datetime
    width: int
    height: int


@dataclass
class CocoAnnotation:
    id: int
    image_id: int
    category_id: int
    segmentation: Union[List[List[float]], Dict[str, List[int]]]
    bbox: List[float]
    area: float
    iscrowd: bool = False


@dataclass
class CocoCategory:
    id: int
    name: str
    supercategory: str


@dataclass
class CocoLicense:
    id: int
    name: str
    url: str


@dataclass
class CocoInfo:
    year: str
    version: Optional[str]
    description: str
    url: str
    date_created: datetime


@dataclass
class CocoDataset:
    info: CocoInfo
    images: List[CocoImage]
    annotations: List[CocoAnnotation]
    categories: List[CocoCategory]
    licenses: List[CocoLicense] = field(default_factory=list)


CocoSchema = marshmallow_dataclass.class_schema(CocoDataset)

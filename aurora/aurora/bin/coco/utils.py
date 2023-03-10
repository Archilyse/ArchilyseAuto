import operator
import random
from itertools import accumulate
from typing import Iterator, Optional

import pandas as pd


def train_test_split_dataframe(
    geometries_dataframe: pd.DataFrame, ratios: Optional[list] = None
) -> Iterator[pd.DataFrame]:
    ratios = ratios or [0.2, 0.8]
    site_ids = list(geometries_dataframe.site_id.unique())
    random.shuffle(site_ids)

    for start, end in zip(
        accumulate([0] + ratios, operator.add), accumulate(ratios, operator.add)
    ):
        set_site_ids = site_ids[int(start * len(site_ids)) : int(end * len(site_ids))]
        yield geometries_dataframe[geometries_dataframe.site_id.isin(set_site_ids)]

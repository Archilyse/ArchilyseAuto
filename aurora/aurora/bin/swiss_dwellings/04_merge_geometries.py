from pathlib import Path
from typing import Set, Union

import click
import pandas as pd
from shapely import wkt
from shapely.geometry import CAP_STYLE, JOIN_STYLE, MultiPolygon, Polygon
from shapely.ops import unary_union
from tqdm import tqdm

AREA_UNION_BUFFER_PX = 0.25


def geometry_type_filter(rows, entity_types=None, entity_subtypes=None):
    if all([entity_types, entity_subtypes]):
        return rows.entity_type.isin(entity_types) & rows.entity_subtype.isin(
            entity_subtypes
        )
    elif entity_subtypes:
        return rows.entity_subtype.isin(entity_subtypes)
    elif entity_types:
        return rows.entity_type.isin(entity_types)
    raise ValueError("This payaso does not have entity_types nor entity_subtypes, wtf?")


def union_geometry_types(
    geometries: pd.DataFrame,
    output_type: str,
    entity_types: Union[Set[str], None] = None,
    entity_subtypes: Union[Set[str], None] = None,
    buffer_in_pixels: float = 0,
    exclude_subtypes: Union[Set[str], None] = None,
    output_only_one_geometry: bool = False,
):
    buffer_styles = dict(join_style=JOIN_STYLE.mitre, cap_style=CAP_STYLE.square)

    if entity_types is None:
        entity_types = set()

    if entity_subtypes is None:
        entity_subtypes = set()

    if exclude_subtypes is None:
        exclude_subtypes = set()

    geometries_out = []
    for (site_id, plan_id), rows in tqdm(
        list(geometries.groupby(["site_id", "plan_id"]))
    ):
        filter_ = geometry_type_filter(rows, entity_types, entity_subtypes)
        geoms_buffered = unary_union(
            [
                wkt.loads(area.geometry).buffer(buffer_in_pixels, **buffer_styles)
                for _, area in rows[filter_].iterrows()
                if area.entity_subtype not in exclude_subtypes
            ]
        )
        geoms_union = geoms_buffered.buffer(-buffer_in_pixels, **buffer_styles)
        if isinstance(geoms_union, Polygon):
            geoms_union = MultiPolygon([geoms_union])

        if not output_only_one_geometry:
            geometries_out += [
                (site_id, plan_id, wkt.dumps(geom), output_type, output_type)
                for geom in geoms_union.geoms
            ]
        else:
            # Output the single multipolygon for all elements
            geometries_out += [
                (site_id, plan_id, wkt.dumps(geoms_union), output_type, output_type)
            ]

    return geometries_out


def walls_union_difference_openings(
    geometries: pd.DataFrame, output_only_one_geometry: bool = False
):
    walls_union = union_geometry_types(
        geometries=geometries,
        entity_types={"separator"},
        entity_subtypes={"WALL"},
        output_type="WALL_UNION_EX_OPENINGS",
    )
    openings_union_by_plan_id = {
        plan_id: unary_union([wkt.loads(geom_wkt) for geom_wkt in rows["geometry"]])
        for plan_id, rows in geometries[(geometries.entity_type == "opening")].groupby(
            "plan_id"
        )
    }

    geometries_out = []
    for site_id, plan_id, walls_wkt, output_type, _ in walls_union:
        walls_ex_openings = wkt.loads(walls_wkt).difference(
            openings_union_by_plan_id.get(plan_id, Polygon())
        )
        if isinstance(walls_ex_openings, Polygon):
            walls_ex_openings = MultiPolygon([walls_ex_openings])

        if not output_only_one_geometry:
            geometries_out += [
                (site_id, plan_id, wkt.dumps(wall), output_type, output_type)
                for wall in walls_ex_openings.geoms
            ]
        else:
            # Output the single multipolygon for all elements
            geometries_out += [
                (
                    site_id,
                    plan_id,
                    wkt.dumps(unary_union(walls_ex_openings)),
                    output_type,
                    output_type,
                )
            ]

    return geometries_out


@click.command()
@click.argument("input_geometries", type=click.Path(exists=True))
@click.argument("output_geometries", type=click.Path(exists=False))
def merge_areas(
    input_geometries: click.Path,
    output_geometries: click.Path,
):
    columns = ["site_id", "plan_id", "geometry", "entity_type", "entity_subtype"]
    geometries_in = pd.read_csv(Path(input_geometries))[columns].drop_duplicates()
    geometries_merged = union_geometry_types(
        geometries=geometries_in,
        entity_types={"area"},
        output_type="SPACE",
        buffer_in_pixels=AREA_UNION_BUFFER_PX,
        exclude_subtypes=set(),
    )
    geometries_merged += walls_union_difference_openings(
        geometries=geometries_in, output_only_one_geometry=True
    )
    geometries_merged += union_geometry_types(
        geometries=geometries_in,
        entity_types={"separator"},
        entity_subtypes={"RAILING"},
        output_type="RAILING_UNION",
        buffer_in_pixels=AREA_UNION_BUFFER_PX,
        output_only_one_geometry=True,
    )
    geometries_merged += union_geometry_types(
        geometries=geometries_in,
        entity_types={"separator"},
        entity_subtypes={"WALL"},
        output_type="WALL_UNION",
        buffer_in_pixels=AREA_UNION_BUFFER_PX,
        output_only_one_geometry=True,
    )
    geometries_merged += union_geometry_types(
        geometries=geometries_in,
        entity_types={"opening"},
        entity_subtypes={"DOOR", "ENTRANCE_DOOR"},
        output_type="DOOR_UNION",
        buffer_in_pixels=AREA_UNION_BUFFER_PX,
    )
    geometries_merged += union_geometry_types(
        geometries=geometries_in,
        entity_types={"opening"},
        entity_subtypes={"WINDOW"},
        output_type="WINDOW_UNION",
        buffer_in_pixels=AREA_UNION_BUFFER_PX,
    )
    for entity_subtype in [
        "TOILET",
        "SINK",
        "SHOWER",
        "KITCHEN",
        "BATHTUB",
        "ELEVATOR",
        "STAIRS",
    ]:
        geometries_merged += union_geometry_types(
            geometries=geometries_in,
            entity_types={"feature"},
            entity_subtypes={entity_subtype},
            output_type=f"{entity_subtype}_UNION",
            buffer_in_pixels=AREA_UNION_BUFFER_PX,
        )

    pd.concat(
        [geometries_in, pd.DataFrame(geometries_merged, columns=columns)],
        ignore_index=True,
    ).to_csv(Path(output_geometries))


if __name__ == "__main__":
    merge_areas()

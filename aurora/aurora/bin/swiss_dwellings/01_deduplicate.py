"""
Creates data/blacklist_deduplication.csv which contains each plan that is a duplicate of another plan
"""

import warnings
from pathlib import Path
from typing import Iterator, List, Tuple

import click
import imagehash
import numpy as np
import pandas as pd
from PIL import Image
from PIL.Image import DecompressionBombWarning
from scipy.sparse import diags
from sklearn.cluster import DBSCAN
from tqdm.contrib.concurrent import process_map

warnings.filterwarnings("ignore", category=DecompressionBombWarning, module="PIL")


def compute_image_hash(image_path: Path) -> Tuple[Path, str]:
    with Image.open(image_path) as image:
        return imagehash.crop_resistant_hash(image)


def compute_image_hash_difference(i: int, image_hashes: list):
    distance_matrix_row = np.zeros(len(image_hashes))
    for j in range(i + 1, len(image_hashes)):
        distance_matrix_row[j] = image_hashes[i] - image_hashes[j]
    return distance_matrix_row


def compute_image_distance_matrix(image_hashes_list: List[Path]) -> np.array:
    distance_matrix = np.array(
        process_map(
            compute_image_hash_difference,
            range(len(image_hashes_list)),
            [image_hashes_list for _ in range(len(image_hashes_list))],
            chunksize=8,
        )
    )
    return distance_matrix + distance_matrix.T - diags(distance_matrix.diagonal())


def get_cluster_representative_image(
    clustering: DBSCAN, distance_matrix: np.array
) -> Iterator[Tuple[int, List[int]]]:
    for cluster in set(clustering.labels_):
        samples = np.where(clustering.labels_ == cluster)[0]
        representative_sample = min(
            samples, key=lambda i: (distance_matrix[i, samples].mean(axis=1))
        )
        yield representative_sample, samples


@click.command()
@click.option(
    "--similarity_threshold", default=0.22, help="Maximum similarity of images."
)
@click.argument("input_folder", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path(exists=False))
def deduplciate_images(
    input_folder: Path, output_path: Path, similarity_threshold: float
):
    input_folder, output_path = Path(input_folder), Path(output_path)
    image_paths = list(input_folder.glob("*.jpg"))
    image_hashes = [
        hash
        for hash in process_map(compute_image_hash, image_paths, chunksize=8)
        if hash is not None
    ]
    distance_matrix = compute_image_distance_matrix(image_hashes_list=image_hashes)
    clustering = DBSCAN(metric="precomputed", min_samples=1, eps=similarity_threshold)
    clustering.fit(distance_matrix)

    blacklisted_plan_ids = []
    for i, cluster in get_cluster_representative_image(
        clustering=clustering, distance_matrix=distance_matrix
    ):
        for sample in cluster:
            image_path = image_paths[sample]
            if sample != i:
                blacklisted_plan_ids.append((int(image_path.stem), f"duplicate of {i}"))

    output_path.parent.mkdir(exist_ok=True, parents=True)
    pd.DataFrame(blacklisted_plan_ids, columns=["plan_id", "reason"]).dropna().to_csv(
        output_path, index=None
    )


if __name__ == "__main__":
    deduplciate_images()

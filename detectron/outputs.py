import json
from pathlib import Path

import cv2
import mlflow
import pandas as pd
from detectron2.structures import BoxMode
from detectron2.utils.visualizer import ColorMode, Visualizer
from matplotlib import pyplot


def _draw_ground_truth(img, dataset_dict, dataset_metadata):
    ground_truth_visualizer = Visualizer(
        img[:, :, ::-1],
        metadata=dataset_metadata,
        instance_mode=ColorMode.SEGMENTATION,
    )
    out = ground_truth_visualizer.draw_dataset_dict(dataset_dict)
    im_with_ground_truth = out.get_image()[:, :, ::-1]
    return im_with_ground_truth


def _draw_predictions(img, predictions, dataset_metadata):
    pred_visualizer = Visualizer(
        img[:, :, ::-1], metadata=dataset_metadata, instance_mode=ColorMode.SEGMENTATION
    )
    out = pred_visualizer.draw_dataset_dict(
        {"annotations": [{**p, "bbox_mode": BoxMode.XYWH_ABS} for p in predictions]}
    )
    im_with_predictions = out.get_image()[:, :, ::-1]
    return im_with_predictions


def _plot_aps_footnote(evaluations, thing_classes):
    footnote = ""
    for thing_class in thing_classes:
        footnote += f'{thing_class}: Precision={evaluations[thing_class]["precision"]} Recall={evaluations[thing_class]["recall"]} \n '
    pyplot.figtext(
        0.5,
        0.01,
        footnote,
        ha="center",
        fontsize=11,
        bbox={"facecolor": "orange", "alpha": 0.5, "pad": 5},
    )


def _plot(dataset_dict, dataset_metadata, predictions, evaluations, output_dir):
    img = cv2.imread(dataset_dict["file_name"])
    img_gt = _draw_ground_truth(img, dataset_dict, dataset_metadata)
    img_pr = _draw_predictions(img, predictions, dataset_metadata)

    fig, (ax1, ax2) = pyplot.subplots(1, 2, figsize=(10, 7))
    fig.set_dpi(350)
    ax1.imshow(img_gt)
    ax1.set_title("Ground Truth")
    ax2.imshow(img_pr)
    ax2.set_title("Predictions")

    _plot_aps_footnote(evaluations, dataset_metadata.thing_classes)

    output_path = output_dir.joinpath(Path(dataset_dict["file_name"]).name)
    pyplot.savefig(output_path.as_posix(), bbox_inches="tight", dpi=300, pad_inches=0)
    pyplot.close(fig)


def generate_plots(
    dataset_dicts,
    dataset_metadata,
    predictions_by_image,
    evaluations_by_image,
    output_dir,
):
    output_plots_dir = output_dir.joinpath("plots")
    output_plots_dir.mkdir(parents=True, exist_ok=True)
    for dataset_dict in dataset_dicts:
        _plot(
            dataset_dict,
            dataset_metadata,
            predictions_by_image[dataset_dict["file_name"]],
            evaluations_by_image[dataset_dict["file_name"]],
            output_dir=output_plots_dir,
        )
    mlflow.log_artifacts(output_plots_dir.as_posix(), output_dir.name)


def generate_metrics(cfg):
    output_directory = Path(cfg.OUTPUT_DIR)
    with output_directory.joinpath("metrics.json").open() as fh:
        df = pd.DataFrame([json.loads(line) for line in fh.readlines()])
        df = df.sort_values("iteration").fillna(method="ffill")

        # export metrics per iteration (for Dagshub)
        melted_df = pd.melt(
            df, id_vars=["iteration"], var_name="Name", value_name="Value"
        )
        melted_df = melted_df.rename({"iteration": "Step"}, axis="columns").sort_values(
            ["Step", "Name"]
        )
        melted_df["Timestamp"] = melted_df["Step"]
        melted_df = melted_df[["Name", "Value", "Timestamp", "Step"]]
        melted_df.dropna().to_csv(output_directory.joinpath("metrics.csv"), index=False)

        # export metrics (only final iteration, for DVC metrics)
        metrics_dvc = (
            df.sort_values("iteration")
            .iloc[-1:, :]
            .dropna(axis=1)
            .set_index("iteration")
            .to_dict(orient="records")[0]
        )
        with output_directory.joinpath("metrics_dvc.json").open("w") as fh:
            json.dump(metrics_dvc, fh, indent=3)

    output_directory.joinpath("metrics.json").unlink()

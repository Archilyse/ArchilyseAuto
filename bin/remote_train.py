import os

import click
from google.cloud import aiplatform


def init():
    STAGING_BUCKET = "gs://vertex_ai_staging_custom_jobs"

    aiplatform.init(
        project=os.getenv("GCP_PROJECT_ID"),
        location=os.getenv("GCP_REGION"),
        staging_bucket=STAGING_BUCKET,
    )


@click.command()
@click.option("-model", "-M", prompt=True, type=click.Choice(["detectron", "deeplab", "dataset"]))
@click.option("-commit_hash", "-c", prompt=True, type=click.STRING)
@click.option("-display_name", "-n", prompt=True, type=click.STRING)
@click.option(
    "-machine_type",
    "-m",
    prompt="machine type",
    type=click.STRING,
    default="n1-highmem-4",
)
@click.option(
    "-accelerator_type",
    "-a",
    prompt="GPU type",
    type=click.STRING,
    default="NVIDIA_TESLA_T4",
)
@click.option("-accelerator_count", "-N", prompt="Num GPUs", type=click.INT, default=1)
@click.option(
    "-S",
    "extra_args",
    type=click.STRING,
    help="Pass just as we would usually with the -S option, e.g. `conf/detectron2/remote.yaml:SOLVER.MAX_ITER=5000`",
    default=(),
    multiple=True
)
def remote_train(
    model,
    commit_hash,
    display_name,
    machine_type,
    accelerator_type,
    accelerator_count,
    extra_args,
):
    CMDARGS = []
    if model == "detectron":
        CMDARGS = ["--train_detectron", commit_hash]
    elif model ==  "deeplab":
        CMDARGS = ["--train_deeplab", commit_hash]
    elif model == "dataset":
        CMDARGS = ["--dataset", commit_hash]
    else:
        raise ValueError("Invalid model provided")
    
    if model in {"detectron", "deeplab"}:
        extra_args_list = [f"conf/mlflow/default.yaml:RUN_NAME={display_name}"] + list(extra_args)
        CMDARGS.extend([f'-S "{a.strip()}"' for a in extra_args_list])

    dvc_version = os.getenv("DVC_IMAGE_VERSION")
    init()
    job = aiplatform.CustomContainerTrainingJob(
        display_name=display_name,
        container_uri=f"gcr.io/aurora-223611/dvc_detectron:{dvc_version}",
    )
    job.run(
        args=CMDARGS,
        machine_type=machine_type,
        accelerator_type=accelerator_type,
        accelerator_count=accelerator_count,
        sync=False,
    )


if __name__ == "__main__":
    remote_train()

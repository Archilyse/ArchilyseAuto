#!/usr/bin/env bash
source .venv/bin/activate
set -x -e

if [ $# -lt 2 ]; then
    echo "Illegal number of arguments" && exit 1
fi

FLAG="$1"
COMMIT_HASH="$2"

if [ $# -gt 2 ]; then
    REMAINING_ARGS="$(echo "$*" | awk -F" " '{for (i=3; i<NF; i++) printf $i " "; print $NF}')"
else
    REMAINING_ARGS=""
fi

export $(grep -v '^#' docker/secrets/mlflow.env | xargs)

git fetch
git config --global user.name "Michael Franzen (DVC)"
git config --global user.email "franzen@archilyse.com"

BRANCH_NAME=$(git name-rev $COMMIT_HASH | cut -d" " -f2 | head -n 1)
RUN_ID=$(date +"%Y%m%d%H%M%S")
EXPERIMENT_NAME="$(echo "$BRANCH_NAME" | sed 's/\//-/g')_$COMMIT_HASH_$RUN_ID"

create_output_directory() {
    mkdir -p /home/appuser/src/output
}

update_repo() {
    git reset --hard $COMMIT_HASH
    git checkout $COMMIT_HASH
    pip install -r requirements.txt
}

run_training_detectron() {
    dvc pull dataset-export-coco dataset-export-coco-tiled
    if python3.8 -c "import torch; print(torch.cuda.get_device_name(0));"; then
        COMMAND="dvc exp run -s --pull -v -n '$EXPERIMENT_NAME' $REMAINING_ARGS train-detectron"
        eval ${COMMAND[@]}
    else
        echo "No gpu. Exiting." && exit -1
    fi
}

run_training_deeplab() {
    dvc pull dataset-export-coco
    if python3.8 -c "import torch; print(torch.cuda.get_device_name(0));"; then
        COMMAND="dvc exp run -s --pull -v -n '$EXPERIMENT_NAME' $REMAINING_ARGS train-deeplab"
        eval ${COMMAND[@]}
    else
        echo "No gpu. Exiting." && exit -1
    fi
}

update_dataset() {
    dvc pull
    COMMAND="dvc exp run --pull -v -n '$EXPERIMENT_NAME' $REMAINING_ARGS dataset-export-coco"
    eval ${COMMAND[@]}
}

push_experiment() {
    dvc exp push origin $EXPERIMENT_NAME
    dvc exp branch $EXPERIMENT_NAME experiment/$EXPERIMENT_NAME
    git push --set-upstream origin experiment/$EXPERIMENT_NAME
}

create_output_directory
update_repo

case "$FLAG" in
  --dataset)
    update_dataset
    ;;
  --train_detectron)
    run_training_detectron
    ;;
  --train_deeplab)
    run_training_deeplab
    ;;
  --all)
    update_dataset
    run_training_detectron
    run_training_deeplab
    ;;
esac

push_experiment
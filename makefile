-include .env
-include docker/.env
-include docker/secrets/mlflow.env

PYTHON_VERSION=$(shell cat .python-version)
COMMIT_HASH := $(shell git rev-parse HEAD)

DOCKER_ENV_ARGS := $(shell < .env xargs) $(shell < docker/.env xargs)
DOCKER_DETECTRON := GCP_PROJECT_ID=$(GCP_PROJECT_ID) \
	GCP_REGION=$(GCP_REGION) \
	PYTHON_VERSION=$(PYTHON_VERSION) \
	DETECTRON_BASE_IMAGE_VERSION=$(DETECTRON_BASE_IMAGE_VERSION) \
	DVC_IMAGE_VERSION=$(DVC_IMAGE_VERSION) \
	MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI}" \
	MLFLOW_TRACKING_USERNAME=$(MLFLOW_TRACKING_USERNAME) \
	MLFLOW_TRACKING_PASSWORD=$(MLFLOW_TRACKING_PASSWORD)
DOCKER_DEV := $(DOCKER_DETECTRON) COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker-compose --project-directory docker -f docker/docker-compose.yml
DOCKER_DEV_BUILD_PARALLEL := $(DOCKER_DEV) build

FOLDERS_TO_FORMAT := aurora/ app/ segmentation/ predictors/ tests/

format:
	black $(FOLDERS_TO_FORMAT)
	isort $(FOLDERS_TO_FORMAT)
	pflake8 $(FOLDERS_TO_FORMAT)
	mypy $(FOLDERS_TO_FORMAT)

format_fe:
	cd demo/ui && npm run format

## NOTE: Tests require node 16.18.0+ to work
tests_fe:
	cd demo/ui && npm run test

static_analysis:
	pflake8 $(FOLDERS_TO_FORMAT)
	mypy $(FOLDERS_TO_FORMAT)
	bandit -r --severity-level medium -q $(FOLDERS_TO_FORMAT)

fe_static_analysis:
	cd demo/ui && npm run format:check && npm run lint:check

docker_down:
	$(DOCKER_DEV) down -v --remove-orphans

install_demo_ui_dependencies:
	cd demo/ui && npm install

run_demo_ui_locally:
	cd demo/ui && npm run dev

run_api_locally:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

################ Detectron / DVC ################

_detectron_docker_pull_or_push_base_image:
	# tries to pull the base image of DETECTRON_BASE_IMAGE_VERSION (see .env), otherwise builds and pushes it
	docker pull $(GCR_REPO)/detectron2_base:$(DETECTRON_BASE_IMAGE_VERSION) || ( \
	docker build -t $(GCR_REPO)/detectron2_base:$(DETECTRON_BASE_IMAGE_VERSION) -f docker/detectron2_base.Dockerfile . && \
	docker push $(GCR_REPO)/detectron2_base:$(DETECTRON_BASE_IMAGE_VERSION) \
	)

dvc_detectron_docker_build: _detectron_docker_pull_or_push_base_image
	$(DOCKER_DETECTRON) docker-compose -f docker/docker-compose.yml build dvc_detectron

dvc_detectron_docker_push: dvc_detectron_docker_build
	# builds & pushes the detectron 2 image for the current commit
	docker push $(GCR_REPO)/dvc_detectron:$(DVC_IMAGE_VERSION)

dvc_detectron_docker_run_update_dataset: dvc_detectron_docker_build
	$(DOCKER_DETECTRON) docker-compose -f docker/docker-compose.yml run dvc_detectron --dataset $(COMMIT_HASH)

dvc_detectron_docker_run_train: dvc_detectron_docker_build
	$(DOCKER_DETECTRON) docker-compose -f docker/docker-compose.yml run dvc_detectron --train_detectron $(COMMIT_HASH)

remote_training:
	$(DOCKER_DETECTRON) python bin/remote_train.py

train_locally:
	FORCE_CUDA="1" \
	TORCH_CUDA_ARCH_LIST="Kepler;Kepler+Tesla;Maxwell;Maxwell+Tegra;Pascal;Volta;Turing" \
	$(DOCKER_DETECTRON) .venv-detectron/bin/python detectron/training_job.py instance_segmentation.detectron2=local mlflow.RUN_NAME="detectron_local_test"

train_locally_deeplab:
	FORCE_CUDA="1" \
	TORCH_CUDA_ARCH_LIST="Kepler;Kepler+Tesla;Maxwell;Maxwell+Tegra;Pascal;Volta;Turing" \
	$(DOCKER_DETECTRON) .venv-detectron/bin/python segmentation/train.py semantic_segmentation=local mlflow.RUN_NAME="deeplab_local_test"

################ YOLO ################
yolo_prepare_data_folder:
	dvc repro yolo_gen_labels -s &&\
	python bin/copy_yolo_labels_images.py &&\
	gcloud storage cp gs://archilyse_darknet_yolo/initial_weights/yolov4.conv.137 darknet_yolo/

yolo_build:
	$(DOCKER_DEV_BUILD_PARALLEL) darknet_yolo

yolo_push:
	docker push $(GCR_REPO)/darknet_yolo

yolo_run:
	$(DOCKER_DETECTRON) docker-compose -f docker/docker-compose.yml run darknet_yolo --entrypoint bash

################ DEMO APP ################
docker_build_base_api:
	$(DOCKER_DETECTRON) docker build -f docker/api_base.Dockerfile . -t ${GCR_REPO}/api_base:${API_BASE_IMAGE_VERSION}

docker_build_base_prediction_worker:
	$(DOCKER_DETECTRON) docker build -f docker/prediction_worker_base.Dockerfile . -t ${GCR_REPO}/prediction_worker_base:${PREDICTION_WORKER_BASE_IMAGE_VERSION}

docker_build_base: docker_build_base_api docker_build_base_prediction_worker

docker_build:
	$(DOCKER_DEV_BUILD_PARALLEL) api router prediction_worker

docker_build_push_gpu:
	$(DOCKER_DEV_BUILD_PARALLEL) prediction_gpu_worker && \
	read -p "Enter tag (pr number): " tag; \
    docker tag gcr.io/aurora-223611/prediction_gpu_worker gcr.io/aurora-223611/prediction_gpu_worker:$$tag; \
    docker push gcr.io/aurora-223611/prediction_gpu_worker:$$tag;

docker_up:
	$(DOCKER_DEV) up --remove-orphans --abort-on-container-exit api router prediction_worker

docker_up_multi_workers:
	$(DOCKER_DEV) up --remove-orphans --scale prediction_worker=3 api router prediction_worker

docker_run:
	$(DOCKER_DEV) run api

docker_up_daemonize:
	$(DOCKER_DEV) up --remove-orphans -d router prediction_worker

docker_up_daemonize_multi_workers:
	$(DOCKER_DEV) up --remove-orphans --scale prediction_worker=2 -d router prediction_worker

################ Tensorboard ################

docker_build_tensorboard:
	$(DOCKER_DEV_BUILD_PARALLEL) tensorboard

run_tensorboard:
	$(DOCKER_DEV) run --service-ports --rm tensorboard

experiment_detectron:
	$(DOCKER_DETECTRON) python bin/remote_train.py \
		-M "detectron" \
		-c $(COMMIT_HASH) \
		-n "icons-custom-hook-101" \
		-m "n1-highmem-4" \
		-a "NVIDIA_TESLA_T4" \
		-N 1 \
		-S "conf/instance_segmentation/detectron2/remote.yaml:SOLVER.BASE_LR=0.025" \
		-S "conf/instance_segmentation/detectron2/remote.yaml:SOLVER.MAX_ITER=20000" \
		-S "conf/instance_segmentation/detectron2/remote.yaml:SOLVER.STEPS=[2000,4000,6000,8000,10000,12000,14000,16000,18000]"


experiment_deeplab:
	$(DOCKER_DETECTRON) python bin/remote_train.py \
		-M "deeplab" \
		-c $(COMMIT_HASH) \
		-n "deeplab-baseline-no-spaces" \
		-m "n1-highmem-8" \
		-a "NVIDIA_TESLA_T4" \
		-N 1 \
		-S "conf/semantic_segmentation/remote.yaml:SOLVER.LEARNING_RATE=0.0001" \
		-S "conf/semantic_segmentation/remote.yaml:MODEL.CLASSES=["WALL_UNION_EX_OPENINGS","RAILING","WINDOW","DOOR"]"

remote_dataset:
	$(DOCKER_DETECTRON) python bin/remote_train.py \
		-M "dataset" \
		-c $(COMMIT_HASH) \
		-n "deeplab-dataset-main" \
		-m "e2-standard-32" \
		-a "NVIDIA_TESLA_T4" \
		-N 0

# *********** UTILS ******************
# ************************************
profile_code:
	$(DOCKER_DEV) run --rm \
	--workdir="/code" \
	--entrypoint python \
	-v $(shell pwd)/profiling/:/code/profiling \
	--  prediction_worker -m cProfile -o /code/profiling/prof/myLog.profile profiling/code_to_profile.py \
    && gprof2dot -f pstats profiling/prof/myLog.profile -o profiling/prof/callingGraph.dot \
	&& dot -Tsvg profiling/prof/callingGraph.dot > profiling/prof/profile.svg \
	&& xdg-open profiling/prof/profile.svg


update_resources:
	mkdir -p resources && \
	gsutil -m cp gs://archilyse-aurora/temp-model/icons_model_final.pth \
	gs://archilyse-aurora/temp-model/icons_model_final_2.pth \
    gs://archilyse_darknet_yolo/6k-iter-a100/yolo-roi-latest.weights \
    gs://archilyse-aurora/temp-model/walls_model_2023_03_02_v2.pth \
    gs://archilyse-aurora/temp-model/spaces_model_final.pth \
    resources
	mv resources/walls_model_2023_03_02_v2.pth resources/walls_model_latest.pth


# *********** TESTS ******************
# ************************************

redis_up:  ## Start up redis
	$(DOCKER_DEV) up --remove-orphans -d redis

tests_locally: redis_up
	$(DOCKER_ENV_ARGS) REDIS_HOST=localhost pytest tests/ --maxfail=30 -s --lf || true
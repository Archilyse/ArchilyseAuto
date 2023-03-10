ARG PREDICTION_WORKER_BASE_IMAGE_VERSION
ARG ML_IMAGES_BUCKET_CREDENTIALS_FILE
ARG GCR_REPO
FROM $GCR_REPO/prediction_worker_base:$PREDICTION_WORKER_BASE_IMAGE_VERSION as base

COPY $ML_IMAGES_BUCKET_CREDENTIALS_FILE $ML_IMAGES_BUCKET_CREDENTIALS_FILE

#Copy resources
COPY ./resources /code/resources/
COPY ./darknet_yolo/cfg/yolo-obj.cfg /code/resources/yolo-roi.cfg

WORKDIR /code

COPY ./predictors/ /code/predictors/
RUN pip install --no-cache-dir --upgrade -e predictors

COPY docker/entrypoints/worker_entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/tini", "--", "/bin/bash", "/entrypoint.sh"]

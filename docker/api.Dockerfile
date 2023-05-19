ARG API_BASE_IMAGE_VERSION
ARG ML_IMAGES_BUCKET_CREDENTIALS_FILE
ARG GCR_REPO
FROM $GCR_REPO/api_base:$API_BASE_IMAGE_VERSION as base

COPY $ML_IMAGES_BUCKET_CREDENTIALS_FILE $ML_IMAGES_BUCKET_CREDENTIALS_FILE

COPY ./app/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./predictors /code/predictors
COPY ./common /code/common

WORKDIR /code

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
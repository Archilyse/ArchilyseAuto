ARG DETECTRON_BASE_IMAGE_VERSION
ARG GCR_REPO

FROM $GCR_REPO/detectron2_base:$DETECTRON_BASE_IMAGE_VERSION as base

ARG GCP_PROJECT_ID
ARG GCP_REGION
ARG PYTHON_VERSION

# Install depedendencies
RUN sudo apt-get update && sudo apt-get install -y curl

# Install & Configure gcloud
RUN curl -sSL https://sdk.cloud.google.com | bash
ENV PATH $PATH:/home/appuser/google-cloud-sdk/bin

COPY docker/secrets /home/appuser/secrets
RUN sudo chown -R appuser /home/appuser/secrets

ENV GOOGLE_APPLICATION_CREDENTIALS "/home/appuser/secrets/gce_service_account_credentials.json"
RUN gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS
RUN gcloud config set project $GCP_PROJECT_ID
RUN gcloud config set compute/zone $GCP_REGION

# Setup Code
WORKDIR /home/appuser/src/
RUN sudo chown -R appuser .

## Code
RUN mkdir /home/appuser/.ssh && mv /home/appuser/secrets/github.key /home/appuser/.ssh/id_rsa
RUN ssh-keyscan github.com >> /home/appuser/.ssh/known_hosts    
RUN git clone git@github.com:Archilyse/deep-learning.git .

## Install Python 3.10 + depedencies
RUN sudo apt-get update && sudo apt-get install -y ncurses-dev libffi-dev libreadline-dev libbz2-dev liblzma-dev libsqlite3-dev libssl-dev
RUN git clone https://github.com/pyenv/pyenv.git /home/appuser/.pyenv
RUN /home/appuser/.pyenv/bin/pyenv install $PYTHON_VERSION
RUN /home/appuser/.pyenv/versions/$PYTHON_VERSION/bin/python -m venv .venv

COPY aurora/ aurora/
COPY app/ app/
COPY detectron/ detectron/
RUN sudo chown -R appuser .
RUN .venv/bin/python -m pip install -r requirements.txt

# Extra Dependencies Detectron
RUN python3.8 -m pip install shapely mlflow

# Extra Dependencies DeeplabV3+
RUN python3.8 -m pip install -U \
    pip install segmentation-models-pytorch=="0.3.2" \
    pytorch-lightning=="1.8.5" \
    albumentations=="1.3.0" \
    pycocotools=="2.0.6" \
    pytorch-lightning=="1.8.5"

# Entrypoint (NOTE: We don't use the cloned one here to allow for changes in the script.)

COPY docker/secrets docker/secrets
COPY docker/entrypoints/detectron2_entrypoint.sh /home/appuser/entrypoint.sh
ENTRYPOINT ["/bin/bash", "/home/appuser/entrypoint.sh"]

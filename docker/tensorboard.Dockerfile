FROM python:3.11

COPY secrets /secrets

ENV GCSFUSE_REPO gcsfuse-focal
RUN apt-get update && apt-get install -y curl
RUN echo "deb https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | \
    tee /etc/apt/sources.list.d/gcsfuse.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

RUN apt-get update && apt-get install -y gcsfuse

RUN pip install tensorboard

RUN mkdir -p /live_bucket
COPY entrypoints/tensorboard_entrypoint.sh entrypoint.sh

EXPOSE 6006
ENTRYPOINT ["/entrypoint.sh"]
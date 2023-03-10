#!/usr/bin/env bash

set -e

bash wait-for-it.sh --timeout=10 "${RABBITMQ_HOST}":"${RABBITMQ_PORT}"

mkdir -p /root/pysal_data

if [[ "$*" == *--worker* ]]; then
    : "${WORKER_QUEUES:?Need to set WORKER_QUEUE when running a worker}"
    : "${WORKER_NAME:?Need to set WORKER_NAME when running a worker}"
    : "${WORKER_HOST_IP_ADDRESS:?Need to set WORKER_HOST_IP_ADDRESS when running a worker}"
    celery --app predictors.celery_conf.celery_app worker --queues "${WORKER_QUEUES}" -Ofair --loglevel=INFO --hostname "${WORKER_NAME}"@"${WORKER_HOST_IP_ADDRESS}"
elif [[ "$*" == *--flower* ]]; then
    celery --app workers_config.celery_app \
    flower \
    --conf=/src/celery_workers/workers_config/flower_config.py \
    --broker_api=https://"${RABBITMQ_USER}":"${RABBITMQ_PASSWORD}"@"${RABBITMQ_HOST}":"${RABBITMQ_MANAGEMENT_PORT}"/api/
fi

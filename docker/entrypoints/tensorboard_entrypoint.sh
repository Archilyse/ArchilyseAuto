#!/usr/bin/env bash

set -e

GOOGLE_APPLICATION_CREDENTIALS="/secrets/gce_service_account_credentials.json" \
gcsfuse archilyse-aurora-live /live_bucket

read -p 'EXPERIMENT_ID: ' experiment_id
folder=/live_bucket/"$experiment_id"
mkdir -p "$folder"  # Necessary to see folder contents
tensorboard --port 6006 --bind_all --logdir "$folder"
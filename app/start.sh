#!/usr/bin/env bash
set -e

if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
  gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
fi

gunicorn --bind :"$PORT" --workers 1 --threads 8 --timeout 0 main:app

exec "$@"
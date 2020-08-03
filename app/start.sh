#!/usr/bin/env bash
set -e

gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
gunicorn --bind :"$PORT" --workers 1 --threads 8 --timeout 0 main:app

exec "$@"
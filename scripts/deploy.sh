#!/usr/bin/env bash
set -euo pipefail

: "${APP_NAME:?missing APP_NAME}"
: "${APP_DIR:?missing APP_DIR}"

echo "[deploy.sh] app=$APP_NAME app_dir=$APP_DIR at=$(date -Is) host=$(hostname)"

echo "[deploy.sh] done at=$(date -Is)"

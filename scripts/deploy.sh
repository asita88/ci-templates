#!/usr/bin/env bash
set -euo pipefail

: "${APP_DIR:?missing APP_DIR}"
: "${CURRENT_DIR:?missing CURRENT_DIR}"
: "${RELEASE_DIR:?missing RELEASE_DIR}"
OLD_DIR="${OLD_DIR:-}"

echo "[deploy.sh] app_dir=$APP_DIR current=$CURRENT_DIR release=$RELEASE_DIR old=${OLD_DIR:-<none>} at=$(date -Is) host=$(hostname)"

copy_if_exists() {
  local src="$1" dst="$2"
  if [ -e "$src" ]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  fi
}

# If there is an old version, copy config forward.
# Replace these paths with your project's conventions.
if [ -n "$OLD_DIR" ] && [ -d "$OLD_DIR" ]; then
  if [ -d "$OLD_DIR/config" ] && [ ! -d "$CURRENT_DIR/config" ]; then
    cp -a "$OLD_DIR/config" "$CURRENT_DIR/config"
  fi

  copy_if_exists "$OLD_DIR/.env" "$CURRENT_DIR/.env"
  copy_if_exists "$OLD_DIR/appsettings.json" "$CURRENT_DIR/appsettings.json"
fi

# First deploy bootstrap example (no overwrite).
if [ ! -f "$CURRENT_DIR/.env" ] && [ -f "$CURRENT_DIR/.env.example" ]; then
  cp -n "$CURRENT_DIR/.env.example" "$CURRENT_DIR/.env"
fi

# Restart / reload (choose one):
# supervisorctl restart <app_name>
# pm2 restart <app_name>
# nginx -s reload

echo "[deploy.sh] done at=$(date -Is)"


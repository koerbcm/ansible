#!/usr/bin/env bash
set -euo pipefail

# Reference only: back up the live Graylog compose, .env, and related helper files from docker1.
# Adjust the source paths to match the live host before use.

BACKUP_ROOT="${BACKUP_ROOT:-/mnt/backups/graylog/config}"
SOURCE_DIR="${SOURCE_DIR:-/opt/stacks/graylog7}"
TIMESTAMP="$(date +%F-%H%M%S)"
DEST_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${DEST_DIR}"

cp -a "${SOURCE_DIR}/compose.yml" "${DEST_DIR}/"

if [ -f "${SOURCE_DIR}/.env" ]; then
  cp -a "${SOURCE_DIR}/.env" "${DEST_DIR}/"
fi

if [ -f "/usr/local/bin/docker_opensearch_snapshot.sh" ]; then
  cp -a "/usr/local/bin/docker_opensearch_snapshot.sh" "${DEST_DIR}/"
fi

# Optional retention example: keep 30 days.
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +

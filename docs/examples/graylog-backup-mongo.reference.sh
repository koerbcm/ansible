#!/usr/bin/env bash
set -euo pipefail

# Reference only: nightly Graylog MongoDB backup from docker1 to the NAS-backed backup mount.
# Adjust container names and destination paths to match the live host before use.

BACKUP_ROOT="${BACKUP_ROOT:-/mnt/backups/graylog/mongo}"
MONGO_CONTAINER="${MONGO_CONTAINER:-mongodb}"
TIMESTAMP="$(date +%F-%H%M%S)"
DEST_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${DEST_DIR}"

docker exec "${MONGO_CONTAINER}" mongodump \
  --uri="mongodb://localhost:27017/graylog" \
  --archive \
  --gzip > "${DEST_DIR}/graylog-mongo.archive.gz"

# Optional retention example: keep 14 days.
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +

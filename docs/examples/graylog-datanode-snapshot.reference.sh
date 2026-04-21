#!/usr/bin/env bash
set -euo pipefail

# Reference only: create an OpenSearch/DataNode snapshot into the NAS-backed snapshot path.
# This assumes the DataNode HTTP API is reachable locally without authentication.

SNAPSHOT_REPO="${SNAPSHOT_REPO:-graylog_local_backup}"
SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/mnt/backups/graylog/opensearch-snapshots}"
SNAPSHOT_REPO_LOCATION="${SNAPSHOT_REPO_LOCATION:-/mnt/backups}"
OPENSEARCH_URL="${OPENSEARCH_URL:-http://127.0.0.1:9200}"
SNAPSHOT_NAME="${SNAPSHOT_NAME:-graylog-$(date +%F-%H%M%S)}"

mkdir -p "${SNAPSHOT_ROOT}"

curl -fsSL -X PUT "${OPENSEARCH_URL}/_snapshot/${SNAPSHOT_REPO}" \
  -H 'Content-Type: application/json' \
  -d "{
    \"type\": \"fs\",
    \"settings\": {
      \"location\": \"${SNAPSHOT_REPO_LOCATION}\",
      \"compress\": true
    }
  }"

curl -fsSL -X PUT "${OPENSEARCH_URL}/_snapshot/${SNAPSHOT_REPO}/${SNAPSHOT_NAME}?wait_for_completion=true" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "*",
    "ignore_unavailable": true,
    "include_global_state": true
  }'

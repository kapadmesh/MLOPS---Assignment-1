#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"
ENV_FILE="$SCRIPT_DIR/.env"
ACTION="${1:-Up}"

if [[ ! -f "$ENV_FILE" ]]; then
    printf 'Create %s from .env.example and set GRAFANA_ADMIN_PASSWORD first.\n' \
        "$ENV_FILE" >&2
    exit 1
fi

case "$ACTION" in
    Up)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build
        ;;
    Down)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
        ;;
    Logs)
        docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail=100 api
        ;;
    *)
        printf 'Usage: %s [Up|Down|Logs]\n' "$0" >&2
        exit 2
        ;;
esac

#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/compose.yaml"
ACTION="${1:-Up}"

case "$ACTION" in
    Up)
        docker compose -f "$COMPOSE_FILE" up -d --build
        ;;
    Down)
        docker compose -f "$COMPOSE_FILE" down
        ;;
    Logs)
        docker compose -f "$COMPOSE_FILE" logs --tail=100 api
        ;;
    *)
        printf 'Usage: %s [Up|Down|Logs]\n' "$0" >&2
        exit 2
        ;;
esac

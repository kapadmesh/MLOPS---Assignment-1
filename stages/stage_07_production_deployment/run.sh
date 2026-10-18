#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -ne 1 ]]; then
    printf 'Usage: %s <kubectl-context>\n' "$0" >&2
    exit 2
fi
exec bash "$SCRIPT_DIR/deploy.sh" "$1"

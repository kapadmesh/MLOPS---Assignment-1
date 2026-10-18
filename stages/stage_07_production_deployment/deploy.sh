#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -ne 1 ]]; then
    printf 'Usage: %s <kubectl-context>\n' "$0" >&2
    exit 2
fi
CONTEXT="$1"

kubectl --context "$CONTEXT" apply -k "$SCRIPT_DIR" || {
    printf 'Kubernetes apply failed.\n' >&2
    exit 1
}
kubectl --context "$CONTEXT" -n heart-disease rollout status \
    deployment/heart-disease-api --timeout=180s || {
    printf 'Deployment did not become ready. Check pod events and logs.\n' >&2
    exit 1
}
kubectl --context "$CONTEXT" -n heart-disease get deployments,pods,services -o wide

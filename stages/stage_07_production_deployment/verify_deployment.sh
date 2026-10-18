#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
if [[ $# -lt 1 || $# -gt 2 ]]; then
    printf 'Usage: %s <kubectl-context> [base-url]\n' "$0" >&2
    exit 2
fi
CONTEXT="$1"
BASE_URL="${2:-http://localhost:8080}"
OUTPUT_DIR="$PROJECT_ROOT/artifacts/stage_07/evidence"
mkdir -p "$OUTPUT_DIR"

kubectl --context "$CONTEXT" -n heart-disease rollout status \
    deployment/heart-disease-api --timeout=180s || {
    printf 'Deployment is not ready.\n' >&2
    exit 1
}
kubectl --context "$CONTEXT" -n heart-disease get deployments,pods,services -o wide \
    2>&1 | tee "$OUTPUT_DIR/deployment_state.txt"
bash "$PROJECT_ROOT/stages/stage_06_model_containerization/verify_endpoint.sh" \
    "$BASE_URL" "$OUTPUT_DIR"
kubectl --context "$CONTEXT" -n heart-disease logs \
    -l app=heart-disease-api --all-containers=true --prefix --tail=200 \
    2>&1 | tee "$OUTPUT_DIR/api_requests.log"

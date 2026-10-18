#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
BASE_URL="${1:-http://localhost:8000}"
OUTPUT_DIR="${2:-$PROJECT_ROOT/artifacts/stage_06/verification}"
PYTHON="${PYTHON:-python3}"
BASE_URL="${BASE_URL%/}"
mkdir -p "$OUTPUT_DIR"

health="$(curl --fail --silent --show-error "$BASE_URL/health")"
ready="$(curl --fail --silent --show-error "$BASE_URL/ready")"
printf '%s\n' "$health" | "$PYTHON" -c \
    'import json,sys; assert json.load(sys.stdin).get("status") == "alive", "Health check failed"'
printf '%s\n' "$ready" | "$PYTHON" -c \
    'import json,sys; assert json.load(sys.stdin).get("status") == "ready", "Readiness check failed"'

curl --fail --silent --show-error \
    -H 'Content-Type: application/json' \
    --data-binary "@$SCRIPT_DIR/sample_request.json" \
    "$BASE_URL/predict" > "$OUTPUT_DIR/prediction_response.json"
"$PYTHON" - "$OUTPUT_DIR/prediction_response.json" <<'PY'
import json
import math
import sys
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert result["prediction"] in (0, 1), "Prediction must be binary"
assert 0 <= result["confidence"] <= 1, "Confidence is out of range"
probabilities = result["class_probabilities"]
assert set(probabilities) == {"0", "1"}, "Expected probabilities for classes 0 and 1"
assert math.isclose(sum(probabilities.values()), 1, abs_tol=1e-6), (
    "Probabilities do not sum to one"
)
print(json.dumps(result, indent=2))
PY

curl --fail --silent --show-error "$BASE_URL/metrics" > "$OUTPUT_DIR/metrics.txt"
if ! grep -q 'model_predictions_total' "$OUTPUT_DIR/metrics.txt"; then
    printf 'Prediction metrics are missing.\n' >&2
    exit 1
fi

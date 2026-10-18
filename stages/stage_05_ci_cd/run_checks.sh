#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON="${1:-python3}"
REPORTS="$PROJECT_ROOT/artifacts/stage_05/reports"
mkdir -p "$REPORTS"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
cd "$PROJECT_ROOT"

run_logged() {
    local log_path="$1"
    shift
    "$@" 2>&1 | tee "$log_path"
}

run_logged "$REPORTS/lint.log" "$PYTHON" -m ruff check stages
run_logged "$REPORTS/tests.log" "$PYTHON" -m pytest \
    "--junitxml=$REPORTS/junit.xml" \
    --cov=stages.stage_05_ci_cd \
    --cov=stages.stage_06_model_containerization \
    "--cov-report=xml:$REPORTS/coverage.xml"
run_logged "$REPORTS/training.log" "$PYTHON" -m stages.stage_05_ci_cd.train

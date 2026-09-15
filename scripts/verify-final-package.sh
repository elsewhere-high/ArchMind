#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
: "${CONDA_PREFIX:?Activate a Conda environment before running checks}"
export PYTHONDONTWRITEBYTECODE=1
python3 tests/validate-final-secret-scan.py --workspace
python3 tests/test-public-safety.py
python3 tests/validate-public-safety.py
python3 tests/check-markdown-links.py
sh tests/validate-static.sh
python3 tests/test-runtime-bootstrap.py
python3 tests/test-skill-evidence-min-001.py
python3 tests/test-human-gate.py
python3 scripts/validate-schemas.py
printf 'LOCAL_CHECKS_PASS\n'

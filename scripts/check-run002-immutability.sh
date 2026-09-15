#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
input_dir="$project_root/samples/skill-evidence/01_input/source"
expected_manifest="8a0ce2271c18caf258b97ff0f195df7211819a868626f7974312f82ad145a92b"
actual_manifest=$(shasum -a 256 "$input_dir/SHA256SUMS" | awk '{print $1}')
if [[ "$actual_manifest" != "$expected_manifest" ]]; then
  echo "INPUT_IMMUTABILITY_GUARD_FAIL manifest changed" >&2
  exit 1
fi
(cd "$input_dir" && shasum -a 256 -c SHA256SUMS >/dev/null)
echo "INPUT_IMMUTABILITY_GUARD_PASS"

#!/bin/sh
set -u

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=runtime-lib.sh
. "$project_dir/scripts/runtime-lib.sh"
runtime_load_env "$project_dir"

failures=0
skips=0
worker_failures=0
worker_skips=0
temporary_dir=$(mktemp -d "${TMPDIR:-/tmp}/archmind-health.XXXXXX")
trap 'rm -rf "$temporary_dir"' EXIT HUP INT TERM

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  failures=$((failures + 1))
}

skip() {
  printf 'SKIPPED_WITH_REASON %s\n' "$1"
  skips=$((skips + 1))
}

check_json_resource() {
  label=$1
  json_file=$2
  shift 2
  output=$(python3 "$project_dir/scripts/runtime-resource-check.py" "$@" < "$json_file" 2>&1)
  code=$?
  case "$code" in
    0) pass "$label" ;;
    3) skip "$label: $output" ;;
    *) fail "$label: $output" ;;
  esac
  return "$code"
}

resolve_uri() {
  variable=$1
  archive=$2
  eval "uri=\${$variable-}"
  if [ -z "$uri" ] && [ -n "${PACKAGE_URI_BASE:-}" ]; then
    uri="${PACKAGE_URI_BASE%/}/$archive"
  fi
  printf '%s\n' "$uri"
}

printf 'RUNTIME HEALTHCHECK mode=read-only-no-business-task\n'

if ! runtime_engine=$(runtime_select_engine 2>/dev/null); then
  fail "container engine selection failed"
  printf 'RUNTIME_HEALTHCHECK_FAIL failures=%s skipped=%s\n' "$failures" "$skips" >&2
  exit 1
fi

if ! "$runtime_engine" info >/dev/null 2>&1; then
  fail "container engine daemon is not reachable"
  printf 'RUNTIME_HEALTHCHECK_FAIL failures=%s skipped=%s\n' "$failures" "$skips" >&2
  exit 1
fi
pass "container engine daemon reachable"

if ! runtime_init_agt "$runtime_engine"; then
  fail "AgentTeams access configuration is invalid"
  printf 'RUNTIME_HEALTHCHECK_FAIL failures=%s skipped=%s\n' "$failures" "$skips" >&2
  exit 1
fi

if runtime_agt status > "$temporary_dir/status.txt" 2>&1; then
  pass "AgentTeams manager/controller API reachable through agt status"
else
  fail "agt status failed"
fi

if [ "${AGENTTEAMS_ACCESS_MODE:-}" = "container" ]; then
  if [ -z "${AGENTTEAMS_MANAGER_CONTAINER:-}" ]; then
    fail "AGENTTEAMS_MANAGER_CONTAINER is required"
  else
    manager_running=$("$runtime_engine" inspect -f '{{.State.Running}}' "$AGENTTEAMS_MANAGER_CONTAINER" 2>/dev/null || true)
    if [ "$manager_running" = "true" ]; then
      pass "Manager runtime container is running"
    else
      fail "Manager runtime container is not running"
    fi
  fi
fi

if [ -z "${AGENTTEAMS_API_ENDPOINT:-}" ]; then
  fail "AGENTTEAMS_API_ENDPOINT is not configured"
else
  pass "AgentTeams API endpoint configured (value redacted)"
fi

if [ -z "${MODEL_ENDPOINT:-}" ]; then
  fail "MODEL_ENDPOINT is not configured"
else
  pass "model endpoint configured; no model request was sent"
fi

if [ -z "${MATRIX_ENDPOINT:-}" ]; then
  fail "MATRIX_ENDPOINT is not configured"
elif curl -fsS --connect-timeout 5 --max-time 10 \
  "${MATRIX_ENDPOINT%/}/_matrix/client/versions" >/dev/null; then
  pass "Matrix service reachable through client versions API"
else
  fail "Matrix service is not reachable"
fi

rendered="$project_dir/deploy/archmind-minimal.yaml"
if [ ! -f "$rendered" ]; then
  fail "rendered deployment manifest is missing"
elif grep -q 'PACKAGE_URI_' "$rendered"; then
  fail "rendered deployment manifest contains unresolved package URI"
else
  pass "rendered deployment manifest has no unresolved package URI"
fi

for name in default archmind-review-team chief-engineer review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier; do
  if [ -f "$rendered" ] && grep -q "  name: $name$" "$rendered"; then
    pass "expected identity or team definition present: $name"
  else
    fail "expected identity or team definition missing: $name"
  fi
done

package_files_ok=1
for worker in review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier; do
  if [ ! -f "$project_dir/packages/dist/$worker.zip" ]; then
    package_files_ok=0
    fail "local package file missing: $worker"
  fi
done
if [ "$package_files_ok" -eq 1 ]; then
  pass "five local package files exist"
fi

if runtime_agt get managers default -o json > "$temporary_dir/manager.json" 2>/dev/null; then
  check_json_resource "Manager resource exists and is ready" \
    "$temporary_dir/manager.json" --name default --require-ready || true
else
  fail "Manager resource query failed"
fi

worker_names="review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier"
for worker in $worker_names; do
  case "$worker" in
    review-coordinator)
      uri=$(resolve_uri PACKAGE_URI_REVIEW_COORDINATOR review-coordinator.zip)
      ;;
    hardscape-reviewer)
      uri=$(resolve_uri PACKAGE_URI_HARDSCAPE_REVIEWER hardscape-reviewer.zip)
      ;;
    planting-reviewer)
      uri=$(resolve_uri PACKAGE_URI_PLANTING_REVIEWER planting-reviewer.zip)
      ;;
    stormwater-sponge-reviewer)
      uri=$(resolve_uri PACKAGE_URI_STORMWATER_SPONGE_REVIEWER stormwater-sponge-reviewer.zip)
      ;;
    evidence-verifier)
      uri=$(resolve_uri PACKAGE_URI_EVIDENCE_VERIFIER evidence-verifier.zip)
      ;;
  esac
  if [ -z "$uri" ]; then
    fail "package URI unavailable for $worker"
    worker_failures=$((worker_failures + 1))
    continue
  fi
  if runtime_agt get workers "$worker" -o json > "$temporary_dir/$worker.json" 2>/dev/null; then
    check_json_resource "Worker exists, ready, and references expected package: $worker" \
      "$temporary_dir/$worker.json" --name "$worker" --require-ready \
      --expected-package "$uri"
    code=$?
    case "$code" in
      0) ;;
      3) worker_skips=$((worker_skips + 1)) ;;
      *) worker_failures=$((worker_failures + 1)) ;;
    esac
  else
    fail "Worker resource query failed: $worker"
    worker_failures=$((worker_failures + 1))
  fi
done

if runtime_agt get teams archmind-review-team -o json > "$temporary_dir/team.json" 2>/dev/null; then
  check_json_resource "Team exists with all required worker members" \
    "$temporary_dir/team.json" --name archmind-review-team \
    --members $worker_names
  team_code=$?
  if [ "$team_code" -eq 0 ] && [ "$worker_failures" -eq 0 ] && [ "$worker_skips" -eq 0 ]; then
    pass "Team ready derived from complete membership and five ready Workers"
  elif [ "$team_code" -eq 0 ]; then
    skip "Team readiness cannot pass until every required Worker is confirmed ready"
  fi
else
  fail "Team resource query failed"
fi

if runtime_agt get humans chief-engineer -o json > "$temporary_dir/human.json" 2>/dev/null; then
  check_json_resource "Human identity resource exists: chief-engineer" \
    "$temporary_dir/human.json" --name chief-engineer || true
else
  fail "Human identity resource query failed"
fi

if [ "$failures" -ne 0 ]; then
  printf 'RUNTIME_HEALTHCHECK_FAIL failures=%s skipped=%s model_calls=0\n' "$failures" "$skips" >&2
  exit 1
fi
if [ "$skips" -ne 0 ]; then
  printf 'RUNTIME_HEALTHCHECK_INCOMPLETE failures=0 skipped=%s model_calls=0\n' "$skips" >&2
  exit 2
fi

printf 'RUNTIME_HEALTHCHECK_PASS required_checks=all model_calls=0 business_tasks=0\n'

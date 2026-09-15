#!/bin/sh
set -u

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=runtime-lib.sh
. "$project_dir/scripts/runtime-lib.sh"
runtime_load_env "$project_dir"

phase=pre-build
case "${1:-}" in
  "") ;;
  --pre-build) phase=pre-build ;;
  --post-build) phase=post-build ;;
  *)
    printf 'FAIL unknown argument: %s\n' "$1" >&2
    exit 2
    ;;
esac

failures=0

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  failures=$((failures + 1))
}

skip() {
  printf 'SKIPPED_WITH_REASON %s\n' "$1"
}

require_env() {
  variable=$1
  eval "value=\${$variable-}"
  if [ -n "$value" ]; then
    pass "$variable is configured (value redacted)"
  else
    fail "$variable is required"
  fi
}

printf 'RUNTIME PREFLIGHT phase=%s\n' "$phase"

if runtime_engine=$(runtime_select_engine 2>/dev/null); then
  pass "container engine executable available"
  if "$runtime_engine" info >/dev/null 2>&1; then
    pass "container engine daemon reachable"
  else
    fail "container engine daemon is not reachable"
  fi
else
  fail "docker or podman is required; set CONTAINER_ENGINE when both are installed"
  runtime_engine=
fi

if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'; then
    pass "Python version is 3.9 or newer"
  else
    fail "Python 3.9 or newer is required"
  fi
else
  fail "python3 is required"
fi

for command_name in sh zip unzip curl; do
  if command -v "$command_name" >/dev/null 2>&1; then
    pass "$command_name executable available"
  else
    fail "$command_name executable is required"
  fi
done

if command -v shasum >/dev/null 2>&1 || command -v sha256sum >/dev/null 2>&1; then
  pass "SHA-256 executable available"
else
  fail "shasum or sha256sum is required"
fi

if [ -f "$project_dir/deploy/archmind-minimal.template.yaml" ]; then
  pass "deployment template exists"
else
  fail "deploy/archmind-minimal.template.yaml is missing"
fi

for worker in review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier; do
  if [ -f "$project_dir/packages/$worker/manifest.json" ]; then
    pass "package source manifest exists for $worker"
  else
    fail "package source manifest missing for $worker"
  fi
done

package_files_ready=1
for worker in review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier; do
  [ -f "$project_dir/packages/dist/$worker.zip" ] || package_files_ready=0
done
[ -f "$project_dir/packages/dist/SHA256SUMS" ] || package_files_ready=0

if [ "$package_files_ready" -eq 1 ]; then
  if (cd "$project_dir/packages/dist" && {
    if command -v shasum >/dev/null 2>&1; then
      shasum -a 256 -c SHA256SUMS
    else
      sha256sum -c SHA256SUMS
    fi
  }) >/dev/null 2>&1; then
    pass "five generated package files and checksums are valid"
  else
    fail "generated package checksum verification failed"
  fi
elif [ "$phase" = "post-build" ]; then
  fail "five generated package files are required after BUILD"
else
  skip "package archives are not present; bootstrap BUILD step will generate them"
fi

require_env AGENTTEAMS_ACCESS_MODE
require_env AGENTTEAMS_API_ENDPOINT
require_env MATRIX_ENDPOINT
require_env MODEL_ENDPOINT

case "${AGENTTEAMS_ACCESS_MODE:-}" in
  container)
    require_env AGENTTEAMS_CONTROLLER
    require_env AGENTTEAMS_MANAGER_CONTAINER
    if [ -n "$runtime_engine" ] && [ -n "${AGENTTEAMS_CONTROLLER:-}" ]; then
      controller_running=$("$runtime_engine" inspect -f '{{.State.Running}}' "$AGENTTEAMS_CONTROLLER" 2>/dev/null || true)
      if [ "$controller_running" = "true" ]; then
        pass "AgentTeams Controller container is running"
        if "$runtime_engine" exec "$AGENTTEAMS_CONTROLLER" agt version >/dev/null 2>&1; then
          pass "AgentTeams CLI/API is accessible through Controller"
        else
          fail "agt version failed inside AgentTeams Controller"
        fi
      else
        fail "configured AgentTeams Controller container is not running"
      fi
    fi
    ;;
  host)
    if command -v agt >/dev/null 2>&1 && agt version >/dev/null 2>&1; then
      pass "host AgentTeams CLI/API is accessible"
    else
      fail "host agt CLI is not accessible"
    fi
    ;;
  "")
    ;;
  *)
    fail "AGENTTEAMS_ACCESS_MODE must be container or host"
    ;;
esac

if [ -n "${AGENTTEAMS_LLM_API_KEY:-}" ]; then
  pass "model credential environment variable is present (value redacted)"
elif [ "${MODEL_CREDENTIAL_CONFIGURED:-}" = "true" ] || [ "${MODEL_CREDENTIAL_CONFIGURED:-}" = "1" ]; then
  pass "external AgentTeams model secret is declared configured"
else
  fail "set AGENTTEAMS_LLM_API_KEY or MODEL_CREDENTIAL_CONFIGURED=true"
fi

if python3 "$project_dir/scripts/render-deploy.py" \
  --template "$project_dir/deploy/archmind-minimal.template.yaml" \
  --check-only >/dev/null; then
  pass "all five package URIs resolve from environment configuration"
else
  fail "package URI configuration is incomplete or invalid"
fi

if [ "$failures" -ne 0 ]; then
  printf 'RUNTIME_PREFLIGHT_FAIL failures=%s secrets_printed=0\n' "$failures" >&2
  exit 1
fi

printf 'RUNTIME_PREFLIGHT_PASS phase=%s secrets_printed=0\n' "$phase"

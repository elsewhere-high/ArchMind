#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=runtime-lib.sh
. "$project_dir/scripts/runtime-lib.sh"
runtime_load_env "$project_dir"

run_step() {
  step_name=$1
  shift
  printf '\n[%s] START\n' "$step_name"
  if "$@"; then
    printf '[%s] PASS\n' "$step_name"
  else
    code=$?
    printf '[%s] FAIL exit=%s\n' "$step_name" "$code" >&2
    exit "$code"
  fi
}

template="$project_dir/deploy/archmind-minimal.template.yaml"
rendered="$project_dir/deploy/archmind-minimal.yaml"

run_step PRECHECK sh "$project_dir/scripts/runtime-preflight.sh" --pre-build
run_step BUILD_PACKAGES sh "$project_dir/scripts/build-packages.sh"
run_step POST_BUILD_PACKAGE_CHECK sh "$project_dir/scripts/runtime-preflight.sh" --post-build
run_step RESOLVE_PACKAGE_URI python3 "$project_dir/scripts/render-deploy.py" \
  --template "$template" --check-only
run_step RENDER_DEPLOY_YAML python3 "$project_dir/scripts/render-deploy.py" \
  --template "$template" --output "$rendered"
run_step APPLY_AGENTTEAMS_RESOURCES sh "$project_dir/scripts/apply-resources.sh"
run_step HEALTH_CHECK sh "$project_dir/scripts/runtime-healthcheck.sh"

printf '\n[READY] PASS\n'
printf 'RUNTIME_BOOTSTRAP_READY business_tasks=0 human_decisions=0\n'

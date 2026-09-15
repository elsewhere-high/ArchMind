#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=runtime-lib.sh
. "$project_dir/scripts/runtime-lib.sh"
runtime_load_env "$project_dir"

manifest="$project_dir/deploy/archmind-minimal.yaml"
container_manifest=${AGENTTEAMS_CONTAINER_MANIFEST:-/tmp/archmind-minimal.yaml}

if [ ! -f "$manifest" ]; then
  echo "FAIL rendered deploy/archmind-minimal.yaml is missing" >&2
  exit 1
fi
if grep -q 'PACKAGE_URI_' "$manifest"; then
  echo "FAIL rendered deployment manifest contains unresolved package URI" >&2
  exit 1
fi

runtime_engine=$(runtime_select_engine)
runtime_init_agt "$runtime_engine"

case "$AGENTTEAMS_ACCESS_MODE" in
  container)
    controller_running=$("$runtime_engine" inspect -f '{{.State.Running}}' "$AGENTTEAMS_CONTROLLER" 2>/dev/null || true)
    if [ "$controller_running" != "true" ]; then
      echo "FAIL configured AgentTeams Controller container is not running" >&2
      exit 1
    fi
    "$runtime_engine" cp "$manifest" "$AGENTTEAMS_CONTROLLER:$container_manifest"
    "$runtime_engine" exec "$AGENTTEAMS_CONTROLLER" agt apply -f "$container_manifest"
    ;;
  host)
    agt apply -f "$manifest"
    ;;
esac

echo "APPLY_RESOURCES_PASS resources=8 business_tasks=0"

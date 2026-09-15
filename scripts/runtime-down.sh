#!/bin/sh
set -u

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# shellcheck source=runtime-lib.sh
. "$project_dir/scripts/runtime-lib.sh"
runtime_load_env "$project_dir"

runtime_engine=$(runtime_select_engine) || exit 1
runtime_init_agt "$runtime_engine" || exit 1

failures=0
for worker in review-coordinator hardscape-reviewer planting-reviewer stormwater-sponge-reviewer evidence-verifier; do
  if runtime_agt worker sleep --name "$worker" >/dev/null 2>&1; then
    printf 'PASS Worker sleeping: %s\n' "$worker"
  else
    printf 'FAIL unable to sleep Worker: %s\n' "$worker" >&2
    failures=$((failures + 1))
  fi
done

case "$AGENTTEAMS_ACCESS_MODE" in
  container)
    if [ -z "${AGENTTEAMS_MANAGER_CONTAINER:-}" ]; then
      printf 'FAIL AGENTTEAMS_MANAGER_CONTAINER is required\n' >&2
      failures=$((failures + 1))
    elif [ "$AGENTTEAMS_MANAGER_CONTAINER" = "${AGENTTEAMS_CONTROLLER:-}" ]; then
      printf 'FAIL Manager and Controller container names must differ\n' >&2
      failures=$((failures + 1))
    elif "$runtime_engine" stop "$AGENTTEAMS_MANAGER_CONTAINER" >/dev/null; then
      printf 'PASS Manager runtime stopped\n'
    else
      printf 'FAIL unable to stop Manager runtime\n' >&2
      failures=$((failures + 1))
    fi
    ;;
  host)
    printf 'SKIPPED_WITH_REASON host-mode Manager shutdown is installation-specific\n'
    failures=$((failures + 1))
    ;;
esac

if [ "$failures" -ne 0 ]; then
  printf 'RUNTIME_DOWN_INCOMPLETE failures=%s\n' "$failures" >&2
  exit 1
fi

printf 'RUNTIME_DOWN_PASS workers_sleeping=5 manager_stopped=1 controller_preserved=1 resources_deleted=0\n'

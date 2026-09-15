#!/bin/sh

# Shared helpers for ArchMind runtime scripts. This file never prints secret values.

runtime_project_dir() {
  CDPATH= cd -- "$(dirname -- "$0")/.." && pwd
}

runtime_load_env() {
  : "${CONDA_PREFIX:?Activate the ArchMind Conda environment before running runtime commands}"
  project_dir=$1
  env_file=${ENV_FILE:-"$project_dir/.env"}
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
  fi
}

runtime_select_engine() {
  if [ -n "${CONTAINER_ENGINE:-}" ]; then
    case "$CONTAINER_ENGINE" in
      docker|podman) ;;
      *)
        printf 'FAIL CONTAINER_ENGINE must be docker or podman\n' >&2
        return 1
        ;;
    esac
    command -v "$CONTAINER_ENGINE" >/dev/null 2>&1 || {
      printf 'FAIL configured container engine is not installed\n' >&2
      return 1
    }
    printf '%s\n' "$CONTAINER_ENGINE"
    return 0
  fi

  docker_found=0
  podman_found=0
  command -v docker >/dev/null 2>&1 && docker_found=1
  command -v podman >/dev/null 2>&1 && podman_found=1

  if [ "$docker_found" -eq 1 ] && [ "$podman_found" -eq 0 ]; then
    printf 'docker\n'
    return 0
  fi
  if [ "$podman_found" -eq 1 ] && [ "$docker_found" -eq 0 ]; then
    printf 'podman\n'
    return 0
  fi
  if [ "$docker_found" -eq 1 ] && [ "$podman_found" -eq 1 ]; then
    printf 'FAIL both docker and podman are installed; set CONTAINER_ENGINE explicitly\n' >&2
  else
    printf 'FAIL neither docker nor podman is installed\n' >&2
  fi
  return 1
}

runtime_init_agt() {
  runtime_engine=$1
  case "${AGENTTEAMS_ACCESS_MODE:-}" in
    container)
      if [ -z "${AGENTTEAMS_CONTROLLER:-}" ]; then
        printf 'FAIL AGENTTEAMS_CONTROLLER is required for container access mode\n' >&2
        return 1
      fi
      ;;
    host)
      command -v agt >/dev/null 2>&1 || {
        printf 'FAIL agt is not installed on the host\n' >&2
        return 1
      }
      ;;
    *)
      printf 'FAIL AGENTTEAMS_ACCESS_MODE must be container or host\n' >&2
      return 1
      ;;
  esac
}

runtime_agt() {
  case "$AGENTTEAMS_ACCESS_MODE" in
    container)
      "$runtime_engine" exec "$AGENTTEAMS_CONTROLLER" agt "$@"
      ;;
    host)
      agt "$@"
      ;;
  esac
}

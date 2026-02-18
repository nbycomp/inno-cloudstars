#!/usr/bin/env bash
set -euo pipefail

# repo root = directory above scripts/
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ENV_FILE="${ENV_FILE:-$ROOT_DIR/env.yaml}"
LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/run-${RUN_ID}.log"

# Make ENV_FILE absolute + validate
if command -v realpath >/dev/null 2>&1; then
  ENV_FILE="$(realpath "$ENV_FILE")"
else
  ENV_FILE="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[envctl] ERROR: ENV_FILE not found: $ENV_FILE" >&2
  exit 1
fi

export ROOT_DIR ENV_FILE LOG_FILE

usage() {
  cat <<EOF
==============================================
envctl.sh - multi-cluster env controller
ROOT_DIR=$ROOT_DIR

Usage:
  ENV_FILE=$ROOT_DIR/env.yaml $0 gen <aws|local|vm>
  ENV_FILE=$ROOT_DIR/env.yaml $0 provision
  ENV_FILE=$ROOT_DIR/env.yaml $0 add-single-cluster
  ENV_FILE=$ROOT_DIR/env.yaml $0 kubeconfigs
  ENV_FILE=$ROOT_DIR/env.yaml $0 grafana      # generate datasources + start local grafana
  ENV_FILE=$ROOT_DIR/env.yaml $0 destroy
EOF
}

log_hdr() {
  echo "=============================================="
  echo "[envctl] START $(date '+%F %T')"
  echo "[envctl] ENV_FILE=$ENV_FILE"
  echo "[envctl] LOG_FILE=$LOG_FILE"
  echo "=============================================="
}

log_ftr() {
  echo "=============================================="
  echo "[envctl] DONE $(date '+%F %T')"
  echo "=============================================="
}

cmd="${1:-}"
mode="${2:-}"
if [[ -z "$cmd" ]]; then
  usage
  exit 1
fi

# Always run from repo root
cd "$ROOT_DIR"

log_hdr | tee -a "$LOG_FILE"
{
  case "$cmd" in
    gen)
      if [[ -z "$mode" ]]; then
        echo "[envctl] ERROR: gen requires a mode: aws|local|vm" >&2
        usage
        exit 1
      fi
      bash "$ROOT_DIR/scripts/gen-config.sh" "$mode"
      ;;
    provision)
      bash "$ROOT_DIR/scripts/create-clusters.sh"
      ;;
    add-single-cluster)
      bash "$ROOT_DIR/scripts/add-clusters.sh"
      ;;
    kubeconfigs)
      bash "$ROOT_DIR/scripts/fetch-kubeconfigs.sh"
      ;;
    grafana)
      # Placeholder hook for local Grafana management
      bash "$ROOT_DIR/scripts/gen-grafana-datasources.sh"
      ;;
    destroy)
      bash "$ROOT_DIR/scripts/destroy.sh"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
} 2>&1 | tee -a "$LOG_FILE"

log_ftr | tee -a "$LOG_FILE"

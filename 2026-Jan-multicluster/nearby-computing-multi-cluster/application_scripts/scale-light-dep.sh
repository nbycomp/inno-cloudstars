#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
ANNOTATION_KEY="kwok.x-k8s.io/usage-cpu"
ANNOTATION_PATH="/spec/template/metadata/annotations/kwok.x-k8s.io~1usage-cpu"

usage() {
  cat <<EOF
Set simulated CPU usage for the light workload.

Usage:
  ${SCRIPT_NAME} <cpu>

Arguments:
  <cpu>  CPU quantity, e.g. 5m, 25m, 100m, 1, 2.5

Environment overrides:
  NAMESPACE   (default: nearby-computing-app)
  DEPLOYMENT  (default: simulation-light)

What this script changes:
  - Patches Deployment pod-template annotation:
      ${ANNOTATION_KEY}=<cpu>
  - Triggers a rollout because pod-template metadata changes.
  - New pods report the updated simulated CPU value.
EOF
}

CPU="${1:-}"
if [[ "$CPU" == "-h" || "$CPU" == "--help" ]]; then
  usage
  exit 0
fi
if [[ -z "$CPU" ]]; then
  echo "ERROR: missing required argument <cpu>." >&2
  echo "Run '${SCRIPT_NAME} --help' for usage." >&2
  exit 1
fi

# Basic validation: allow "0", "0m", "5m", "250m", "1", "2.5", etc.
if ! [[ "$CPU" =~ ^[0-9]+([.][0-9]+)?m?$ ]]; then
  echo "ERROR: invalid cpu value '${CPU}'." >&2
  echo "Expected examples: 5m, 100m, 0m, 1, 2.5" >&2
  exit 1
fi

# Defaults (can be overridden via env vars)
NAMESPACE="${NAMESPACE:-nearby-computing-app}"
DEPLOYMENT="${DEPLOYMENT:-simulation-light}"

echo "[info] Target deployment: ${NAMESPACE}/${DEPLOYMENT}"
echo "[info] Applying simulated CPU: ${ANNOTATION_KEY}=${CPU}"

# Ensure target deployment exists before patching.
if ! kubectl -n "${NAMESPACE}" get deployment "${DEPLOYMENT}" >/dev/null 2>&1; then
  echo "ERROR: deployment not found: ${NAMESPACE}/${DEPLOYMENT}" >&2
  exit 1
fi

# Patch pod-template annotation (escaped key path required for JSON patch).
kubectl -n "${NAMESPACE}" patch deployment "${DEPLOYMENT}" --type='json' -p "[
  {\"op\":\"add\",\"path\":\"${ANNOTATION_PATH}\",\"value\":\"${CPU}\"}
]"

echo "[ok] Patch applied successfully."
echo "[info] A rollout is triggered because pod-template metadata changed."
echo "[next] Useful checks:"
echo "  kubectl -n ${NAMESPACE} rollout status deployment/${DEPLOYMENT}"
echo "  kubectl -n ${NAMESPACE} get hpa"
echo "  kubectl -n ${NAMESPACE} top pods -l app=simulation,tier=light"

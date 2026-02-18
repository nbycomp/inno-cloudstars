#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/env.yaml}"

source "${ROOT}/scripts/lib.sh"

need jq

plan_json="${ROOT}/inventory/plan.json"
mode=""
if [[ -f "$plan_json" ]]; then
  mode="$(jq -r '.meta.mode // empty' "$plan_json")"
fi
mode="${mode:-aws}"
case "$mode" in
  aws|local|vm) ;;
  *)
    echo "[destroy] ERROR: invalid mode in inventory/plan.json: ${mode} (expected aws|local|vm)" >&2
    exit 1
    ;;
esac

clusters_json="${ROOT}/inventory/clusters.json"

if [[ "$mode" != "local" ]]; then
  need ssh
  ssh_user="$(yaml_get '.access.ssh_user' "$ENV_FILE")"
  ssh_key="$(yaml_get '.access.ssh_private_key_path' "$ENV_FILE")"
fi

r() {
  local host_ip="$1"; shift
  local cmd="$*"
  set +e
  if [[ "$mode" == "local" ]]; then
    env -u KUBECONFIG bash -lc "$cmd"
  else
    ssh_host "$ssh_key" "$ssh_user" "$host_ip" "bash -lc $(printf '%q' "$cmd")"
  fi
  local rc=$?
  set -e
  return $rc
}

if [[ -f "$clusters_json" ]]; then
  mapfile -t clusters < <(jq -r 'keys[]' "$clusters_json" | sort)
  if [[ "${#clusters[@]}" -gt 0 ]]; then
    echo "[destroy] mode=${mode} clusters=${#clusters[@]}"

    for cluster in "${clusters[@]}"; do
      host_ip="$(jq -r --arg c "$cluster" '.[$c].host_ip' "$clusters_json")"
      echo "[destroy] ${cluster} @ ${host_ip}"
      r "$host_ip" "kwokctl delete cluster --name '${cluster}' >/dev/null 2>&1 || true"
    done
  else
    echo "[destroy] clusters.json is empty; skipping cluster deletion"
  fi
else
  echo "[destroy] no clusters.json found; skipping cluster deletion"
fi

# Local cleanup of generated artifacts
rm -f \
  "${ROOT}/inventory/clusters.json" \
  "${ROOT}/inventory/hosts.json" \
  "${ROOT}/inventory/plan.json" \
  "${ROOT}/inventory/env.effective.yaml" \
  "${ROOT}/inventory/kwok-prometheus.yaml"
rm -rf "${ROOT}/inventory/grafana" 2>/dev/null || true
rm -f "${ROOT}/kubeconfigs/"*.yaml 2>/dev/null || true
rm -f "${ROOT}/grafana/provisioning/datasources/kwok-prometheus.yaml" 2>/dev/null || true

echo "[destroy] done (terraform not touched; inventory/kubeconfigs cleaned)."
echo "[destroy] note: Grafana container is not removed by this script."

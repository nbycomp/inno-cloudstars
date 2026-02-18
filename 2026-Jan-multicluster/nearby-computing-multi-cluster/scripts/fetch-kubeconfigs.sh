#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/env.yaml}"

source "${ROOT}/scripts/lib.sh"

need jq
need yq

plan_json="${ROOT}/inventory/plan.json"
mode=""
if [[ -f "$plan_json" ]]; then
  mode="$(jq -r '.meta.mode // empty' "$plan_json")"
fi
mode="${mode:-aws}"
case "$mode" in
  aws|local|vm) ;;
  *)
    echo "[kubeconfig] ERROR: invalid mode in inventory/plan.json: ${mode} (expected aws|local|vm)" >&2
    exit 1
    ;;
esac

if [[ "$mode" != "local" ]]; then
  need ssh
  ssh_user="$(yaml_get '.access.ssh_user' "$ENV_FILE")"
  ssh_key="$(yaml_get '.access.ssh_private_key_path' "$ENV_FILE")"
else
  if ! command -v kwokctl >/dev/null 2>&1; then
    echo "[kubeconfig] ERROR: kwokctl not found (run: envctl.sh provision)" >&2
    exit 1
  fi
fi

clusters_json="${ROOT}/inventory/clusters.json"
[[ -f "$clusters_json" ]] || { echo "[kubeconfig] ERROR: missing ${clusters_json} (run: envctl.sh provision)"; exit 1; }

mkdir -p "${ROOT}/kubeconfigs"

# Deterministic order (nice for diffs)
mapfile -t clusters < <(jq -r 'keys[]' "$clusters_json" | sort)
echo "[kubeconfig] clusters to fetch: ${#clusters[@]}"

declare -A keep
for cluster in "${clusters[@]}"; do
  keep["$cluster"]=1
done
for f in "${ROOT}/kubeconfigs/"*.yaml; do
  [[ -e "$f" ]] || break
  base="$(basename "$f" .yaml)"
  if [[ -z "${keep[$base]:-}" ]]; then
    rm -f "$f"
  fi
done

for cluster in "${clusters[@]}"; do
  host_ip="$(jq -r --arg c "$cluster" '.[$c].host_ip' "$clusters_json")"
  api_port="$(jq -r --arg c "$cluster" '.[$c].api_port' "$clusters_json")"
  out="${ROOT}/kubeconfigs/${cluster}.yaml"

  echo "[kubeconfig] ${cluster} <- ${host_ip}:${api_port}"

  if [[ "$mode" == "local" ]]; then
    env -u KUBECONFIG kwokctl get kubeconfig --name "${cluster}" --host "${host_ip}:${api_port}" --insecure-skip-tls-verify > "${out}"
  else
    ssh_host "$ssh_key" "$ssh_user" "$host_ip" \
      "kwokctl get kubeconfig --name '${cluster}' --host '${host_ip}:${api_port}' --insecure-skip-tls-verify" \
      > "${out}"
  fi

  # Fix kubeconfig incompatibility: force insecure-skip-tls-verify and drop CA
  yq -y -i '
    .clusters[].cluster |=
      ( .["insecure-skip-tls-verify"]=true
        | del(.["certificate-authority-data"])
        | del(.["certificate-authority"])
      )
  ' "${out}"
done

echo "[kubeconfig] done."
echo "Example:"
echo "  export KUBECONFIG=${ROOT}/kubeconfigs/${clusters[0]}.yaml"
echo "  kubectl get nodes"

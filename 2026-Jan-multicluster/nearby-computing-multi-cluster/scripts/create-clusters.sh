#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/env.yaml}"
source "${ROOT}/scripts/lib.sh"

need jq
need curl
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
    echo "ERROR: invalid mode in inventory/plan.json: ${mode} (expected aws|local|vm)"
    exit 1
    ;;
esac

if [[ "$mode" == "aws" ]]; then
  need terraform
fi

if [[ "$mode" != "local" ]]; then
  need ssh
  ssh_user="$(yaml_get '.access.ssh_user' "$ENV_FILE")"
  ssh_key="$(yaml_get '.access.ssh_private_key_path' "$ENV_FILE")"
fi

runtime="$(yaml_get '.kwok.runtime' "$ENV_FILE")"
enable_prom="$(yaml_get '.kwok.enable_prometheus' "$ENV_FILE")"
enable_dash="$(yaml_get '.kwok.enable_dashboard' "$ENV_FILE")"
enable_ms="$(yaml_get '.kwok.enable_metrics_server' "$ENV_FILE")"
metrics_cfg_url="$(yaml_get '.kwok.metrics_usage_config_url' "$ENV_FILE")"
kwok_version="$(yaml_get '.kwok.version' "$ENV_FILE")"
warn_if_floating_kwok_metrics_url "$metrics_cfg_url" "$kwok_version"

clusters_per_host="$(yaml_get '.kwok.clusters_per_host' "$ENV_FILE")"
if (( clusters_per_host > 100 )); then
  echo "ERROR: kwok.clusters_per_host=${clusters_per_host} exceeds max of 100"
  exit 1
fi
prom_base="$(yaml_get '.kwok.prometheus_port_base' "$ENV_FILE")"
dash_base="$(yaml_get '.kwok.dashboard_port_base' "$ENV_FILE")"
project_prefix="$(yaml_get '.project.name_prefix' "$ENV_FILE")"

mkdir -p "${ROOT}/inventory"

ensure_host_deps() {
  local host_ip="$1"
  local cmd="
    set -e
    if ! command -v curl >/dev/null 2>&1; then
      sudo apt-get update -y
      sudo apt-get install -y curl
    fi
    if ! command -v docker >/dev/null 2>&1; then
      sudo apt-get update -y
      sudo apt-get install -y docker.io
    fi
    sudo systemctl enable --now docker >/dev/null 2>&1 || true
    sudo usermod -aG docker \"\$USER\" >/dev/null 2>&1 || true
    if ! command -v kwokctl >/dev/null 2>&1; then
      tmp=/tmp/kwokctl
      curl -fsSL -o \"\$tmp\" \"https://github.com/kubernetes-sigs/kwok/releases/download/${kwok_version}/kwokctl-linux-amd64\"
      chmod +x \"\$tmp\"
      sudo mv \"\$tmp\" /usr/local/bin/kwokctl
    fi
  "
  r "$host_ip" "$cmd"
}

# Run command safely (no verbose command echo).
# IMPORTANT: do not let a non-zero rc abort the whole script; kwokctl often prints success but ssh may return 1.
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

# "best effort" remote command
r0() {
  local host_ip="$1"; shift
  r "$host_ip" "$@" >/dev/null 2>&1 || true
}

wait_livez() {
  local host_ip="$1" cluster="$2"
  for _ in $(seq 1 25); do
    if r "$host_ip" "kwokctl --name '$cluster' kubectl get --raw /livez >/dev/null 2>&1"; then
      echo "  [ok] api server endpoint is ready"
      return 0
    fi
    sleep 2
  done
  echo "  [warn] api server endpoint timeout (continuing)"
  return 0
}

wait_metrics_api() {
  local host_ip="$1" cluster="$2"
  for _ in $(seq 1 25); do
    if r "$host_ip" "kwokctl --name '$cluster' kubectl get --raw /apis/metrics.k8s.io/v1beta1/nodes >/dev/null 2>&1"; then
      echo "  [ok] metrics endpoint is ready"
      return 0
    fi
    sleep 2
  done
  echo "  [warn] metrics endpoint timeout (continuing)"
  return 0
}

wait_prom_ready() {
  local host_ip="$1" prom_port="$2"
  for _ in $(seq 1 40); do
    if r "$host_ip" "curl -fsS 'http://127.0.0.1:${prom_port}/-/ready' >/dev/null 2>&1"; then
      echo "  [ok] prometheus endpoint is ready"
      return 0
    fi
    sleep 2
  done
  echo "  [warn] prometheus endpoint timeout (continuing)"
  return 0
}

if [[ "$mode" == "aws" ]]; then
  echo "[tf] reading terraform outputs"
  tfout="$(terraform -chdir="${ROOT}/terraform" output -json)"

  hosts_json="$(echo "$tfout" | jq -c '
    (.host_public_ips.value // .public_ips.value // .public_ips // .hosts_public_ips.value // [])
  ')"

  if [[ "$hosts_json" == "[]" ]]; then
    echo "ERROR: no public IPs found in terraform outputs."
    echo "Found outputs:"
    echo "$tfout" | jq -r 'keys[]' | sed 's/^/  - /'
    exit 1
  fi

  mapfile -t hosts < <(echo "$hosts_json" | jq -r '.[]')
  echo "[tf] hosts: ${hosts[*]}"

  echo "$hosts_json" > "${ROOT}/inventory/hosts.json"
else
  hosts_json_file="${ROOT}/inventory/hosts.json"
  [[ -f "$hosts_json_file" ]] || { echo "ERROR: missing ${hosts_json_file} (run: envctl.sh gen)"; exit 1; }
  hosts_json="$(cat "$hosts_json_file")"
  if [[ "$hosts_json" == "[]" || -z "$hosts_json" ]]; then
    echo "ERROR: no hosts found in ${hosts_json_file}"
    exit 1
  fi
  mapfile -t hosts < <(echo "$hosts_json" | jq -r '.[]')
  echo "[hosts] ${mode}: ${hosts[*]}"
fi
clusters_json="${ROOT}/inventory/clusters.json"
echo "{}" > "${clusters_json}"

for host_ip in "${hosts[@]}"; do
  echo "[deps] ensuring kwok dependencies on ${host_ip}"
  ensure_host_deps "$host_ip"
done

cluster_idx=0

for host_idx in "${!hosts[@]}"; do
  host_ip="${hosts[$host_idx]}"

  echo
  echo "[host] ${host_idx}/${#hosts[@]} -> ${host_ip}"

  if ! r "$host_ip" "true"; then
    echo "  [error] SSH failed for ${host_ip}."
    echo "          Check instance readiness, security group port 22, and your IP allowlist."
    exit 1
  fi

  if ! r "$host_ip" "docker version >/dev/null 2>&1"; then
    echo "  [error] docker not accessible for user on ${host_ip}."
    echo "          If you just added the user to the docker group, re-login and retry."
    exit 1
  fi

  for ((i=0; i<clusters_per_host; i++)); do
    cluster_idx=$((cluster_idx + 1))
    cluster="$(cluster_name "$project_prefix" "$host_idx" "$i")"
    api_port=$((30000 + cluster_idx))
    prom_port=$((prom_base + cluster_idx))
    dash_port=$((dash_base + cluster_idx))

    echo
    echo "[cluster] ${cluster}  api=${api_port} prom=${prom_port} dash=${dash_port}"

    # inventory always
    jq --arg c "$cluster" --arg ip "$host_ip" \
       --argjson api "$api_port" --argjson prom "$prom_port" --argjson dash "$dash_port" \
       '. + {($c): {host_ip:$ip, api_port:$api, prometheus_port:$prom, dashboard_port:$dash}}' \
       "$clusters_json" > "${clusters_json}.tmp"
    mv "${clusters_json}.tmp" "$clusters_json"

    # delete (fresh) - no hang
    echo "  [do] delete (fresh)"
    r0 "$host_ip" "kwokctl delete cluster --name '$cluster' >/dev/null 2>&1 || true"
    # short confirm (best effort)
    r0 "$host_ip" "kwokctl get clusters --quiet 2>/dev/null | grep -q '$cluster' && echo 'still-present' || echo 'gone'"

    # metrics config
    remote_cfg="/tmp/metrics-resource-${cluster}.yaml"
    echo "  [do] fetch metrics-resource.yaml"
    if ! r "$host_ip" "curl -fsSL -o '$remote_cfg' '$metrics_cfg_url'"; then
      echo "  [fail] cannot download metrics-resource.yaml on ${host_ip} (skipping cluster)"
      continue
    fi

    # create
    echo "  [do] create"
    create_cmd="kwokctl create cluster --name '$cluster' --runtime '$runtime' --kube-apiserver-port '$api_port' -c '$remote_cfg'"
    [[ "${enable_prom}" == "true" ]] && create_cmd+=" --enable prometheus --prometheus-port '$prom_port'"
    [[ "${enable_dash}" == "true" ]] && create_cmd+=" --enable dashboard --dashboard-port '$dash_port'"
    [[ "${enable_ms}" == "true" ]] && create_cmd+=" --enable metrics-server"

    if ! r "$host_ip" "$create_cmd"; then
      # Even if ssh returns 1, cluster may exist; do a quick probe via /livez
      echo "  [warn] create returned non-zero; probing /livez"
    fi

    # readiness (won't hang)
    wait_livez "$host_ip" "$cluster"
    [[ "${enable_ms}" == "true" ]] && wait_metrics_api "$host_ip" "$cluster"
    [[ "${enable_prom}" == "true" ]] && wait_prom_ready "$host_ip" "$prom_port"

  done
done

echo
echo "[ok] create-clusters done"
echo "[ok] wrote:"
echo "  - ${ROOT}/inventory/hosts.json"
echo "  - ${ROOT}/inventory/clusters.json"
exit 0

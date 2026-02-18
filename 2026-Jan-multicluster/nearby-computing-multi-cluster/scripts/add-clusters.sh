#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/env.yaml}"
source "${ROOT}/scripts/lib.sh"

need jq
need yq

plan_json="${ROOT}/inventory/plan.json"
[[ -f "$plan_json" ]] || { echo "ERROR: missing inventory/plan.json (run envctl.sh gen <local|vm>)" >&2; exit 1; }
mode="$(jq -r '.meta.mode // empty' "$plan_json")"

if [[ "$mode" != "local" && "$mode" != "vm" ]]; then
  echo "ERROR: add-single-cluster supported only for local or vm mode" >&2
  exit 1
fi
if [[ "$mode" != "local" ]]; then
  need ssh
fi

ssh_user="$(yaml_get '.access.ssh_user' "$ENV_FILE")"
ssh_key="$(yaml_get '.access.ssh_private_key_path' "$ENV_FILE")"

runtime="$(yaml_get '.kwok.runtime' "$ENV_FILE")"
enable_prom="$(yaml_get '.kwok.enable_prometheus' "$ENV_FILE")"
enable_dash="$(yaml_get '.kwok.enable_dashboard' "$ENV_FILE")"
enable_ms="$(yaml_get '.kwok.enable_metrics_server' "$ENV_FILE")"
kwok_version="$(yaml_get '.kwok.version' "$ENV_FILE")"
metrics_cfg_url="$(yaml_get '.kwok.metrics_usage_config_url' "$ENV_FILE")"
project_prefix="$(yaml_get '.project.name_prefix' "$ENV_FILE")"
warn_if_floating_kwok_metrics_url "$metrics_cfg_url" "$kwok_version"

port_base="$(yaml_get '.kwok.prometheus_port_base' "$ENV_FILE")"
dash_base="$(yaml_get '.kwok.dashboard_port_base' "$ENV_FILE")"

hosts_json="${ROOT}/inventory/hosts.json"
[[ -f "$hosts_json" ]] || { echo "ERROR: missing inventory/hosts.json (run envctl.sh provision first)"; exit 1; }

host_ip="$(jq -r '.[0]' "$hosts_json")"
[[ -n "$host_ip" && "$host_ip" != "null" ]] || { echo "ERROR: invalid host in inventory/hosts.json"; exit 1; }

clusters_json="${ROOT}/inventory/clusters.json"
mkdir -p "${ROOT}/inventory"
[[ -f "$clusters_json" ]] || echo '{}' > "$clusters_json"

existing_count="$(jq -r 'keys | length' "$clusters_json")"
next_i=$((existing_count + 1))

name="$(cluster_name "$project_prefix" 0 "$existing_count")"

api_port=$((30000 + next_i))
prom_port=$((port_base + next_i))
dash_port=$((dash_base + next_i))

echo "[add] host=${host_ip}"
echo "[add] cluster=${name} api=${api_port} prom=${prom_port} dash=${dash_port}"

if [[ "$mode" == "local" ]]; then
  kwok_check_cmd="env -u KUBECONFIG kwokctl get clusters --quiet 2>/dev/null | grep -qx '${name}'"
else
  kwok_check_cmd="ssh_host \"$ssh_key\" \"$ssh_user\" \"$host_ip\" \"kwokctl get clusters --quiet 2>/dev/null | grep -qx '${name}'\""
fi

if eval "$kwok_check_cmd"; then
  echo "[add] cluster already exists on host -> skipping create"
else
  remote_cfg="/tmp/metrics-resource-${name}.yaml"
  echo "[add] downloading metrics config"
  if [[ "$mode" == "local" ]]; then
    curl -fsSL -o "$remote_cfg" "$metrics_cfg_url"
  else
    ssh_host "$ssh_key" "$ssh_user" "$host_ip" bash -lc "'
      set -euo pipefail
      curl -fsSL -o \"${remote_cfg}\" \"$metrics_cfg_url\"
    '"
  fi

  args=(kwokctl create cluster --name "${name}" --runtime "${runtime}" --kube-apiserver-port "${api_port}" -c "${remote_cfg}")

  if [[ "${enable_prom}" == "true" ]]; then
    args+=(--enable prometheus --prometheus-port "${prom_port}")
  fi

  if [[ "${enable_dash}" == "true" ]]; then
    args+=(--enable dashboard --dashboard-port "${dash_port}")
  fi

  if [[ "${enable_ms}" == "true" ]]; then
    args+=(--enable metrics-server)
  fi

  if [[ "$mode" == "local" ]]; then
    env -u KUBECONFIG "${args[@]}"
  else
    ssh_host "$ssh_key" "$ssh_user" "$host_ip" "${args[*]}"
  fi
fi

# update inventory
jq --arg c "$name" --arg ip "$host_ip" \
   --argjson api "$api_port" --argjson prom "$prom_port" --argjson dash "$dash_port" \
   '. + {($c): {host_ip:$ip, api_port:$api, prometheus_port:$prom, dashboard_port:$dash}}' \
   "$clusters_json" > "${clusters_json}.tmp"
mv "${clusters_json}.tmp" "$clusters_json"

# update plan.json
jq --arg c "$name" \
   --argjson host_index 0 \
   --argjson api "$api_port" --argjson prom "$prom_port" --argjson dash "$dash_port" \
   '.meta.total_clusters += 1
    | .clusters[$c] = {host_index:$host_index, api_port:$api, prometheus_port:$prom, dashboard_port:$dash}' \
   "$plan_json" > "${plan_json}.tmp"
mv "${plan_json}.tmp" "$plan_json"

# fetch kubeconfig immediately
mkdir -p "${ROOT}/kubeconfigs"
out="${ROOT}/kubeconfigs/${name}.yaml"
if [[ "$mode" == "local" ]]; then
  env -u KUBECONFIG kwokctl get kubeconfig --name "${name}" --host "${host_ip}:${api_port}" --insecure-skip-tls-verify > "${out}"
else
  ssh_host "$ssh_key" "$ssh_user" "$host_ip" \
    "kwokctl get kubeconfig --name '${name}' --host '${host_ip}:${api_port}' --insecure-skip-tls-verify" \
    > "${out}"
fi

# Fix kubeconfig incompatibility
yq -y -i '
  .clusters[].cluster |=
    ( .["insecure-skip-tls-verify"]=true
      | del(.["certificate-authority-data"])
      | del(.["certificate-authority"])
    )
' "${out}"

echo "[add] kubeconfig written: ${out}"

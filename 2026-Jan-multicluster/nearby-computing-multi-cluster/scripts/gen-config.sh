#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT}/env.yaml}"
source "${ROOT}/scripts/lib.sh"

mkdir -p "${ROOT}/inventory"

mode="${1:-}"
if [[ -z "$mode" ]]; then
  echo "[gen] ERROR: missing mode (use: aws|local|vm)" >&2
  exit 1
fi
case "$mode" in
  aws|local|vm) ;;
  *)
    echo "[gen] ERROR: invalid mode '${mode}' (use: aws|local|vm)"
    exit 1
    ;;
esac

# snapshot env for traceability (still read live at runtime)
cp -f "${ENV_FILE}" "${ROOT}/inventory/env.effective.yaml"

name_prefix="$(yaml_get '.project.name_prefix' "$ENV_FILE")"

detect_local_ip() {
  local ip=""
  if command -v ip >/dev/null 2>&1; then
    ip="$(ip route get 1.1.1.1 2>/dev/null | awk '/src/ {for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')"
  fi
  if [[ -z "$ip" ]]; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  if [[ -z "$ip" ]]; then
    echo "[gen] ERROR: cannot detect local IP (need non-loopback IP)" >&2
    exit 1
  fi
  echo "$ip"
}

hosts_source="terraform"

if [[ "$mode" == "aws" ]]; then
  region="$(yaml_get '.project.aws_region' "$ENV_FILE")"
  az="$(yaml_get '.project.availability_zone' "$ENV_FILE")"
  my_ip="$(yaml_get '.access.my_ip_cidr' "$ENV_FILE")"
  extra_ips_raw="$(yq -r '.access.extra_ip_cidrs[]?' "$ENV_FILE")"
  if [[ -z "$extra_ips_raw" ]]; then
    extra_ips="[]"
  else
    extra_ips='['
    first=1
    while IFS= read -r cidr; do
      [[ -z "$cidr" ]] && continue
      if [[ $first -eq 0 ]]; then
        extra_ips+=", "
      fi
      first=0
      extra_ips+="\"${cidr}\""
    done <<< "$extra_ips_raw"
    extra_ips+=']'
  fi
  ssh_user="$(yaml_get '.access.ssh_user' "$ENV_FILE")"
  ssh_key="$(yaml_get '.access.ssh_private_key_path' "$ENV_FILE")"
  key_name="$(yaml_get '.access.key_name' "$ENV_FILE")"

  host_count="$(yaml_get '.aws_hosts.count' "$ENV_FILE")"
  instance_type="$(yaml_get '.aws_hosts.instance_type' "$ENV_FILE")"
  root_gb="$(yaml_get '.aws_hosts.root_volume_gb' "$ENV_FILE")"
  vpc_cidr="$(yaml_get '.aws_hosts.vpc_cidr' "$ENV_FILE")"
  subnet_cidr="$(yaml_get '.aws_hosts.public_subnet_cidr' "$ENV_FILE")"

  # Write terraform.tfvars (but do NOT apply)
  cat > "${ROOT}/terraform/terraform.tfvars" <<EOF
aws_region = "${region}"
availability_zone = "${az}"
name_prefix = "${name_prefix}"
my_ip_cidr = "${my_ip}"
extra_ip_cidrs = ${extra_ips}
ssh_user = "${ssh_user}"
key_name = "${key_name}"
ssh_private_key_path = "${ssh_key}"

host_count = ${host_count}
instance_type = "${instance_type}"
root_volume_gb = ${root_gb}
vpc_cidr = "${vpc_cidr}"
public_subnet_cidr = "${subnet_cidr}"
EOF

  echo "[gen] wrote terraform/terraform.tfvars"
else
  host_count=1
  hosts_source="inventory/hosts.json"

  if [[ "$mode" == "local" ]]; then
    local_ip="$(detect_local_ip)"
    echo "[gen] local_ip=${local_ip}"
    echo "[\"${local_ip}\"]" > "${ROOT}/inventory/hosts.json"
    echo "[gen] wrote inventory/hosts.json (local)"
  else
    vm_host="$(yaml_get '.vm_host' "$ENV_FILE")"
    if [[ -z "$vm_host" || "$vm_host" == "null" ]]; then
      echo "[gen] ERROR: vm_host not set in env.yaml" >&2
      exit 1
    fi
    echo "[\"${vm_host}\"]" > "${ROOT}/inventory/hosts.json"
    echo "[gen] wrote inventory/hosts.json (vm)"
  fi
fi

# Generate a plan for clusters/ports/names (AWS host IPs are known after terraform apply)
runtime="$(yaml_get '.kwok.runtime' "$ENV_FILE")"
enable_prom="$(yaml_get '.kwok.enable_prometheus' "$ENV_FILE")"
port_base="$(yaml_get '.kwok.prometheus_port_base' "$ENV_FILE")"
dash_base="$(yaml_get '.kwok.dashboard_port_base' "$ENV_FILE")"
clusters_per_host="$(yaml_get '.kwok.clusters_per_host' "$ENV_FILE")"
if (( clusters_per_host > 100 )); then
  echo "[gen] ERROR: kwok.clusters_per_host=${clusters_per_host} exceeds max of 100"
  exit 1
fi

total_clusters=$((host_count * clusters_per_host))

# Build plan.json with stable IDs and port allocation (global unique)
tmp="${ROOT}/inventory/plan.json.tmp"
{
  echo '{'
  echo '  "meta": {'
    echo "    \"generated_at\": \"$(date -Iseconds)\","
    echo "    \"mode\": \"${mode}\","
    echo "    \"hosts_source\": \"${hosts_source}\","
    echo "    \"hosts\": ${host_count},"
    echo "    \"clusters_per_host\": ${clusters_per_host},"
    echo "    \"total_clusters\": ${total_clusters},"
    echo "    \"runtime\": \"${runtime}\","
    echo "    \"enable_prometheus\": ${enable_prom}"
  echo '  },'
  echo '  "clusters": {'
} > "$tmp"

global_i=0
for host_idx in $(seq 0 $((host_count-1))); do
  for j in $(seq 1 "${clusters_per_host}"); do
    global_i=$((global_i + 1))
    name="$(cluster_name "$name_prefix" "$host_idx" "$((j-1))")"
    api_port=$((30000 + global_i))
    prom_port=$((port_base + global_i))
    dash_port=$((dash_base + global_i))

    comma=","
    if [[ "$global_i" -eq "$total_clusters" ]]; then comma=""; fi

    cat >> "$tmp" <<EOF
    "${name}": {
      "host_index": ${host_idx},
      "api_port": ${api_port},
      "prometheus_port": ${prom_port},
      "dashboard_port": ${dash_port}
    }${comma}
EOF
  done
done

{
  echo '  }'
  echo '}'
} >> "$tmp"

mv "$tmp" "${ROOT}/inventory/plan.json"
echo "[gen] wrote inventory/plan.json"

if [[ "$mode" == "aws" ]]; then
  # placeholder hosts.json until terraform apply
  echo '[]' > "${ROOT}/inventory/hosts.json"
  echo "[gen] wrote inventory/hosts.json (placeholder; filled after terraform apply)"
fi

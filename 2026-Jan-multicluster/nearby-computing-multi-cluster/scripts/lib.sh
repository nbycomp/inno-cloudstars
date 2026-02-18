#!/usr/bin/env bash
set -euo pipefail

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing '$1'"; exit 1; }; }

yaml_get() {
  # Requires mikefarah yq (recommended): https://github.com/mikefarah/yq
  need yq
  yq -r "$1" "$2"
}

ssh_host() {
  local key="$1" user="$2" ip="$3"; shift 3
  echo "[ssh] ${user}@${ip} :: $*" >&2
  ssh \
    -o UserKnownHostsFile=/dev/null \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=10 \
    -i "$key" \
    "${user}@${ip}" "$@"
}

# Canonical cluster naming used across aws/local/vm.
# Example: cluster_name "nbc-cluster" 0 2 -> nbc-cluster-h00-02
cluster_name() {
  local prefix="$1" host_idx="$2" ordinal="$3"
  printf "%s-h%02d-%02d" "$prefix" "$host_idx" "$ordinal"
}

warn_if_floating_kwok_metrics_url() {
  local url="$1" kwok_version="$2"
  if [[ "$url" == *"/refs/heads/main/"* ]]; then
    echo "[warn] kwok.metrics_usage_config_url is floating (refs/heads/main)." >&2
    echo "[warn] for reproducible runs, pin to refs/tags/${kwok_version}." >&2
  fi
}

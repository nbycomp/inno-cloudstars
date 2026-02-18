#!/usr/bin/env bash
set -euo pipefail

KUBECONFIG=""
if [[ "${1:-}" == "--kubeconfig" ]]; then
  KUBECONFIG="$2"; shift 2
fi
[[ -n "${KUBECONFIG}" ]] || { echo "ERROR: provide --kubeconfig <file>" >&2; exit 1; }
[[ -f "${KUBECONFIG}" ]] || { echo "ERROR: kubeconfig not found: ${KUBECONFIG}" >&2; exit 1; }

KUBECTL=(kubectl --kubeconfig "${KUBECONFIG}")
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NODES_DIR="${NODES_DIR:-${ROOT}/scripts/templates/nodes}"
PAD="${KWOK_NODE_PAD:-4}"

# --- KWOK metrics-server integration fix knobs ---
KWOK_FIX_METRICS="${KWOK_FIX_METRICS:-1}"          # 1=on, 0=off
KWOK_KUBELET_PORT="${KWOK_KUBELET_PORT:-10247}"   # kwok-controller metrics port
KWOK_CTRL_HOST="${KWOK_CTRL_HOST:-}"              # optional override

usage() {
  cat <<EOF
Usage:
  $0 --kubeconfig <file> list [type=<template>]
  $0 --kubeconfig <file> add <count> type=<template>
  $0 --kubeconfig <file> rm  <count> type=<template>
  $0 --kubeconfig <file> scale <desired_count> type=<template>
  $0 --kubeconfig <file> wipe type=<template>

Env:
  NODES_DIR=${NODES_DIR}
  KWOK_NODE_PAD=${PAD}

  # Metrics-server fix (recommended for kwokctl/docker clusters):
  KWOK_FIX_METRICS=${KWOK_FIX_METRICS}     (1=on, 0=off)
  KWOK_KUBELET_PORT=${KWOK_KUBELET_PORT}  (default 10247)
  KWOK_CTRL_HOST=${KWOK_CTRL_HOST:-"(auto)"} (override controller host)
EOF
}

die(){ echo "ERROR: $*" >&2; exit 1; }

arg_type() {
  local t=""
  for a in "$@"; do
    case "$a" in
      type=*) t="${a#type=}" ;;
    esac
  done
  [[ -n "$t" ]] || die "missing type=<template> (expects ${NODES_DIR}/<template>.yaml)"
  echo "$t"
}

prefix_for() { echo "kwok-$1-"; }

node_name() {
  local type="$1" idx="$2"
  printf "%s%0*d" "$(prefix_for "$type")" "$PAD" "$idx"
}

template_for() {
  local type="$1"
  local f="${NODES_DIR}/${type}.yaml"
  [[ -f "$f" ]] || die "template not found: $f"
  echo "$f"
}

list_nodes() {
  local type="${1:-}"
  if [[ -n "$type" ]]; then
    local pfx="^$(prefix_for "$type")"
    "${KUBECTL[@]}" get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' \
      | awk -v p="$pfx" '$0 ~ p {print $0}' | sort
  else
    "${KUBECTL[@]}" get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' \
      | awk -v p="^kwok-" '$0 ~ p {print $0}' | sort
  fi
}

count_nodes() { list_nodes "${1:-}" | wc -l | tr -d ' '; }

max_index() {
  local type="$1"
  local pfx
  pfx="$(prefix_for "$type")"
  list_nodes "$type" \
    | sed -E "s/^${pfx}([0-9]+)$/\1/" \
    | awk 'NF==1 && $1 ~ /^[0-9]+$/ {print $1+0}' \
    | sort -n | tail -n 1
}

apply_from_template() {
  local tmpl="$1" name="$2"
  sed "s/__NODE_NAME__/${name}/g" "$tmpl" | "${KUBECTL[@]}" apply -f - >/dev/null
}

# Derive kwok-controller container DNS name for THIS cluster.
# Final form should follow kwokctl container naming:
#   <kubeconfig cluster name>-kwok-controller
# Example:
#   cluster=kwok-nbc-cluster-h00-00   -> kwok-nbc-cluster-h00-00-kwok-controller
#   legacy: kwok-kwok-local-00        -> kwok-kwok-local-00-kwok-controller
compute_ctrl_host() {
  if [[ -n "${KWOK_CTRL_HOST}" ]]; then
    echo "${KWOK_CTRL_HOST}"
    return 0
  fi

  # --minify returns the active kubeconfig entry only, which avoids brittle context filtering.
  local cluster_raw
  cluster_raw="$("${KUBECTL[@]}" config view --minify -o jsonpath='{.clusters[0].name}' 2>/dev/null || true)"
  [[ -n "$cluster_raw" ]] || return 0

  if [[ "${cluster_raw}" == kwok-* ]]; then
    echo "${cluster_raw}-kwok-controller"
  else
    echo "kwok-${cluster_raw}-kwok-controller"
  fi
}

fix_metrics_status_for_nodes() {
  [[ "${KWOK_FIX_METRICS}" == "1" ]] || return 0

  local ctrl_host
  ctrl_host="$(compute_ctrl_host)"
  if [[ -z "$ctrl_host" ]]; then
    return 0
  fi

  echo "  [kwok] metrics fix: Hostname=${ctrl_host} Port=${KWOK_KUBELET_PORT}"

  for n in "$@"; do
    "${KUBECTL[@]}" patch node "$n" --subresource=status --type='merge' -p "{
      \"status\": {
        \"addresses\": [
          {\"type\":\"Hostname\",\"address\":\"${ctrl_host}\"}
        ],
        \"daemonEndpoints\": {\"kubeletEndpoint\": {\"Port\": ${KWOK_KUBELET_PORT}}}
      }
    }" >/dev/null || true
  done
}

cmd_list() {
  local type="${1:-}"
  if [[ -n "$type" ]]; then
    echo "KWOK nodes (type=$type):"
    list_nodes "$type" || true
    echo "Count: $(count_nodes "$type")"
  else
    echo "KWOK nodes (all types):"
    list_nodes "" || true
    echo "Count: $(count_nodes "")"
  fi
}

cmd_add() {
  local count="$1"; shift
  [[ "$count" =~ ^[0-9]+$ ]] || die "add requires integer count"
  local type; type="$(arg_type "$@")"
  local tmpl; tmpl="$(template_for "$type")"

  local start; start="$(max_index "$type" || true)"
  [[ -n "${start}" ]] || start=0

  echo "Adding $count node(s) of type=$type using template=$tmpl (start after $start)"

  local created=()
  for ((i=1; i<=count; i++)); do
    idx=$((start+i))
    name="$(node_name "$type" "$idx")"
    apply_from_template "$tmpl" "$name"
    created+=("$name")
    (( i % 50 == 0 )) && echo "  created $i/$count..."
  done

  fix_metrics_status_for_nodes "${created[@]}"

  echo "Done. Total type=$type nodes: $(count_nodes "$type")"
}

cmd_rm() {
  local count="$1"; shift
  [[ "$count" =~ ^[0-9]+$ ]] || die "rm requires integer count"
  local type; type="$(arg_type "$@")"

  local current; current="$(count_nodes "$type")"
  if (( count > current )); then count="$current"; fi
  echo "Removing $count node(s) of type=$type (highest indexes first)"
  list_nodes "$type" | sort -r | head -n "$count" | while read -r n; do
    "${KUBECTL[@]}" delete node "$n" --ignore-not-found >/dev/null
  done
  echo "Done. Total type=$type nodes: $(count_nodes "$type")"
}

cmd_scale() {
  local desired="$1"; shift
  [[ "$desired" =~ ^[0-9]+$ ]] || die "scale requires integer desired_count"
  local type; type="$(arg_type "$@")"

  local current; current="$(count_nodes "$type")"
  if (( desired > current )); then
    cmd_add $((desired-current)) "type=$type"
  elif (( desired < current )); then
    cmd_rm $((current-desired)) "type=$type"
  else
    echo "Already at desired count ($desired) for type=$type"
  fi
}

cmd_wipe() {
  local type; type="$(arg_type "$@")"
  local current; current="$(count_nodes "$type")"
  echo "Wiping ALL nodes of type=$type (count=$current)"
  list_nodes "$type" | while read -r n; do
    "${KUBECTL[@]}" delete node "$n" --ignore-not-found >/dev/null
  done
  echo "Done. Total type=$type nodes: $(count_nodes "$type")"
}

main() {
  local cmd="${1:-}"; shift || true
  case "$cmd" in
    list)
      if printf "%s\n" "$@" | grep -q '^type='; then cmd_list "$(arg_type "$@")"; else cmd_list ""; fi
      ;;
    add)   cmd_add "${1:-}" "${@:2}" ;;
    rm|remove|del|delete) cmd_rm "${1:-}" "${@:2}" ;;
    scale) cmd_scale "${1:-}" "${@:2}" ;;
    wipe)  cmd_wipe "$@" ;;
    ""|-h|--help|help) usage ;;
    *) die "unknown command: $cmd" ;;
  esac
}

main "$@"

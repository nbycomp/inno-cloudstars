#!/usr/bin/env bash
set -euo pipefail

# --------------------------
# Config (adjust if needed)
# --------------------------
GRAFANA_CONTAINER_NAME="${GRAFANA_CONTAINER_NAME:-grafana}"
GRAFANA_IMAGE="${GRAFANA_IMAGE:-grafana/grafana:9.4.7}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

GF_ADMIN_USER="${GF_ADMIN_USER:-admin}"
GF_ADMIN_PASSWORD="${GF_ADMIN_PASSWORD:-admin}"

# Repo paths
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTERS_JSON="${CLUSTERS_JSON:-$ROOT/inventory/clusters.json}"

GRAPHANA_DASHBORADS_DIR="${GRAPHANA_DASHBORADS_DIR:-$ROOT/grafana/dashboards}"
INVENTORY_GRAFANA_DIR="${INVENTORY_GRAFANA_DIR:-$ROOT/inventory/grafana}"
DASH_PROVISIONING_DIR="${DASH_PROVISIONING_DIR:-$INVENTORY_GRAFANA_DIR/provisioning/dashboards}"
DASHBOARD_OUT_DIR="${DASHBOARD_OUT_DIR:-$INVENTORY_GRAFANA_DIR/dashboards}"
DATASOURCES_OUT_DIR="${DATASOURCES_OUT_DIR:-$INVENTORY_GRAFANA_DIR/datasources}"
OUT_DASH="${OUT_DASH:-$DASH_PROVISIONING_DIR/kwok-dashboards.yaml}"
OUT_DS="${OUT_DS:-$DATASOURCES_OUT_DIR/kwok-prometheus.yaml}"

# --------------------------
# Checks
# --------------------------
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker not found"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found"; exit 1; }
[[ -f "$CLUSTERS_JSON" ]] || { echo "ERROR: missing $CLUSTERS_JSON"; exit 1; }

mkdir -p "$GRAPHANA_DASHBORADS_DIR"
mkdir -p "$DASH_PROVISIONING_DIR"
mkdir -p "$DASHBOARD_OUT_DIR"
mkdir -p "$DATASOURCES_OUT_DIR"

# --------------------------
# Stop + remove old Grafana
# --------------------------
if docker ps -a --format '{{.Names}}' | grep -qx "$GRAFANA_CONTAINER_NAME"; then
  echo "[grafana] removing existing container: $GRAFANA_CONTAINER_NAME"
  docker rm -f "$GRAFANA_CONTAINER_NAME" >/dev/null
fi

# --------------------------
# Generate datasources YAML
# --------------------------
echo "[grafana] generating datasources from: $CLUSTERS_JSON"
{
  echo "apiVersion: 1"
  echo "datasources:"
  jq -r '
    to_entries
    | sort_by(.key)
    | .[]
    | "  - name: \(.key)\n    type: prometheus\n    access: proxy\n    url: http://\(.value.host_ip):\(.value.prometheus_port)\n    isDefault: false\n    editable: true\n"
  ' "$CLUSTERS_JSON"
} > "$OUT_DS"

echo "[grafana] wrote: $OUT_DS"

echo "[grafana] syncing dashboards into: $DASHBOARD_OUT_DIR"
rm -f "$DASHBOARD_OUT_DIR"/* 2>/dev/null || true
shopt -s nullglob
for f in "$GRAPHANA_DASHBORADS_DIR"/*; do
  [[ -f "$f" ]] || continue
  base="$(basename "$f")"
  case "$base" in
    *.yaml|*.yml)
      cp "$f" "$DASHBOARD_OUT_DIR/${base%.*}.json"
      ;;
    *)
      cp "$f" "$DASHBOARD_OUT_DIR/$base"
      ;;
  esac
done
shopt -u nullglob

echo "[grafana] writing dashboard provisioning: $OUT_DASH"
cat > "$OUT_DASH" <<'EOF'
apiVersion: 1
providers:
  - name: "kwok-dashboards"
    orgId: 1
    folder: "nbc"
    folderUid: "nbc"
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
EOF


# Optional: show a quick preview
echo "[grafana] datasource names:"
jq -r 'keys[]' "$CLUSTERS_JSON" | sed 's/^/  - /'

# --------------------------
# Start Grafana
# --------------------------
echo "[grafana] starting container: $GRAFANA_CONTAINER_NAME ($GRAFANA_IMAGE)"
docker run -d --name "$GRAFANA_CONTAINER_NAME" \
  -p "${GRAFANA_PORT}:3000" \
  -e "GF_SECURITY_ADMIN_USER=${GF_ADMIN_USER}" \
  -e "GF_SECURITY_ADMIN_PASSWORD=${GF_ADMIN_PASSWORD}" \
  -e "GF_AUTH_ANONYMOUS_ENABLED=true" \
  -e "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin" \
  -v "$DASHBOARD_OUT_DIR:/var/lib/grafana/dashboards:ro" \
  -v "$OUT_DS:/etc/grafana/provisioning/datasources/kwok-prometheus.yaml:ro" \
  -v "$DASH_PROVISIONING_DIR:/etc/grafana/provisioning/dashboards:ro" \
  "$GRAFANA_IMAGE" >/dev/null

# --------------------------
# Wait for Grafana to be ready
# --------------------------
echo -n "[grafana] waiting for http://localhost:${GRAFANA_PORT}/api/health "
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${GRAFANA_PORT}/api/health" >/dev/null 2>&1; then
    echo "OK"
    echo "[grafana] ready: http://localhost:${GRAFANA_PORT} (user=${GF_ADMIN_USER})"
    exit 0
  fi
  echo -n "."
  sleep 1
done

echo
echo "[grafana] WARNING: Grafana did not become ready in time."
echo "[grafana] check logs: docker logs $GRAFANA_CONTAINER_NAME | tail -n 100"
exit 1

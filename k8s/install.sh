#!/usr/bin/env bash
# Path B: install the OpenTelemetry Demo on the current kubectl context and send traces and metrics to Splunk.
# Usage: ./install.sh          (reads SPLUNK_REALM and SPLUNK_ACCESS_TOKEN from ../.env)
# Optional env: INSTANCE (default northstar-01), LAB_OWNER (default workshop-user, no spaces),
#               LITE (true | false | auto; default auto = lite when the cluster has under 12 GiB of memory)
set -euo pipefail
cd "$(dirname "$0")"

[ -f ../.env ] || { echo "Copy ../.env.example to ../.env and set SPLUNK_ACCESS_TOKEN first."; exit 1; }
set -a; source ../.env; set +a
: "${SPLUNK_REALM:?set SPLUNK_REALM in ../.env}"
[ "${SPLUNK_ACCESS_TOKEN:-REPLACE_ME}" != "REPLACE_ME" ] || { echo "Set SPLUNK_ACCESS_TOKEN in ../.env"; exit 1; }

REALM="$SPLUNK_REALM"; ACCESS_TOKEN="$SPLUNK_ACCESS_TOKEN"
INSTANCE="${INSTANCE:-northstar-01}"
OWNER="${LAB_OWNER:-workshop-user}"
ENVIRONMENT="k8s-workshop-${INSTANCE}"     # the APM environment name; the k8s- prefix keeps it apart from Path A

LITE="${LITE:-auto}"
if [ "$LITE" = "auto" ]; then
  mem_ki="$(kubectl get nodes -o jsonpath='{range .items[*]}{.status.allocatable.memory}{"\n"}{end}' | sed 's/Ki$//' | awk '{s+=$1} END {print s+0}')"
  if [ "$mem_ki" -lt 12582912 ]; then LITE=true; else LITE=false; fi
fi
EXTRA=()
[ "$LITE" = "true" ] && EXTRA=(-f lite-values.yaml)

helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts >/dev/null 2>&1 || true
helm repo update >/dev/null

echo "Context: $(kubectl config current-context)  Realm: $REALM  Environment: $ENVIRONMENT  Lite: $LITE"
helm upgrade --install otel-demo open-telemetry/opentelemetry-demo \
  -n otel-demo --create-namespace \
  -f splunk-values.yaml ${EXTRA[@]+"${EXTRA[@]}"} \
  --set-string "opentelemetry-collector.config.exporters.otlp_http/signalfx.traces_endpoint=https://ingest.${REALM}.signalfx.com/v2/trace/otlp" \
  --set-string "opentelemetry-collector.config.exporters.otlp_http/signalfx.headers.X-SF-Token=${ACCESS_TOKEN}" \
  --set-string "opentelemetry-collector.config.exporters.signalfx.realm=${REALM}" \
  --set-string "opentelemetry-collector.config.exporters.signalfx.access_token=${ACCESS_TOKEN}" \
  --set-string "opentelemetry-collector.config.processors.resource/lab.attributes[0].value=${INSTANCE}" \
  --set-string "opentelemetry-collector.config.processors.resource/lab.attributes[1].value=${OWNER}" \
  --set-string "opentelemetry-collector.config.processors.resource/lab.attributes[2].value=${INSTANCE}-cluster" \
  --set-string "opentelemetry-collector.config.processors.resource/lab.attributes[3].value=${ENVIRONMENT}"
echo "Installed. Watch: kubectl -n otel-demo get pods -w"

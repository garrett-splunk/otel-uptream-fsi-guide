#!/usr/bin/env bash
# No-Docker fallback for SDK-direct mode: runs the seven services as local processes.
# Usage: ./run-local.sh [seconds]   (default 120)
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "Copy .env.example to .env and set SPLUNK_ACCESS_TOKEN first."; exit 1; }
_cli_redact="${REDACT_IN_SDK-}"   # a value passed on the command line wins over .env
set -a; source .env; set +a
[ -z "$_cli_redact" ] || REDACT_IN_SDK="$_cli_redact"
[ "${SPLUNK_ACCESS_TOKEN:-REPLACE_ME}" != "REPLACE_ME" ] || { echo "Set SPLUNK_ACCESS_TOKEN in .env"; exit 1; }

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r app/requirements.txt

# Test hook: LOCAL_INGEST overrides the Splunk endpoint (used to inspect payloads without sending).
INGEST="${LOCAL_INGEST:-https://ingest.${SPLUNK_REALM}.observability.splunkcloud.com}"
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="$INGEST/v2/trace/otlp"
export OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="$INGEST/v2/datapoint/otlp"
export OTEL_EXPORTER_OTLP_HEADERS="X-SF-Token=${SPLUNK_ACCESS_TOKEN}"
export OTEL_RESOURCE_ATTRIBUTES="deployment.environment=${DEPLOY_ENV_PREFIX:-fsi-workshop}-direct,service.version=1.0.0"
export REDACT_IN_SDK="${REDACT_IN_SDK:-false}"

export URL_PAYROLL_API=http://127.0.0.1:8102 URL_TAX_ENGINE=http://127.0.0.1:8103 \
       URL_ACH_GATEWAY=http://127.0.0.1:8104 URL_NOTIFICATION_SVC=http://127.0.0.1:8105 \
       URL_BENEFITS_API=http://127.0.0.1:8106 URL_HR_API=http://127.0.0.1:8107
export PORTAL_URL=http://127.0.0.1:8101

pids=()
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT
port=8101
for role in portal-web payroll-api tax-engine ach-gateway notification-svc benefits-api hr-api; do
  ROLE=$role PORT=$port OTEL_SERVICE_NAME=$role .venv/bin/python app/service.py >"/tmp/fsi-$role.log" 2>&1 &
  pids+=($!)
  port=$((port + 1))
done
sleep 4
echo "Environment: ${DEPLOY_ENV_PREFIX:-fsi-workshop}-direct  Endpoint: $INGEST"
.venv/bin/python app/traffic.py --seconds "${1:-120}"
sleep 6   # let the batch exporters flush

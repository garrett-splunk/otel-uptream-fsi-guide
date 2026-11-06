#!/usr/bin/env bash
# Usage: ./run.sh direct | collector | down direct | down collector
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "Copy .env.example to .env and set SPLUNK_ACCESS_TOKEN first."; exit 1; }
_cli_redact="${REDACT_IN_SDK-}"   # a value passed on the command line wins over .env
set -a; source .env; set +a
[ -z "$_cli_redact" ] || REDACT_IN_SDK="$_cli_redact"
: "${SPLUNK_REALM:?set SPLUNK_REALM in .env}"
[ "${SPLUNK_ACCESS_TOKEN:-REPLACE_ME}" != "REPLACE_ME" ] || { echo "Set SPLUNK_ACCESS_TOKEN in .env"; exit 1; }

INGEST="https://ingest.${SPLUNK_REALM}.observability.splunkcloud.com"
export REDACT_IN_SDK="${REDACT_IN_SDK:-false}"

mode="${1:-}"; action="up"
if [ "$mode" = "down" ]; then action="down"; mode="${2:-}"; fi

case "$mode" in
  direct)
    export DEPLOY_ENV="${DEPLOY_ENV_PREFIX:-fsi-workshop}-direct"
    export TRACES_ENDPOINT="$INGEST/v2/trace/otlp"
    export METRICS_ENDPOINT="$INGEST/v2/datapoint/otlp"
    export OTLP_HEADERS="X-SF-Token=${SPLUNK_ACCESS_TOKEN}"
    profile=()
    ;;
  collector)
    export DEPLOY_ENV="${DEPLOY_ENV_PREFIX:-fsi-workshop}-collector"
    export TRACES_ENDPOINT="http://otel-collector:4318/v1/traces"
    export METRICS_ENDPOINT="http://otel-collector:4318/v1/metrics"
    export OTLP_HEADERS=""
    profile=(--profile collector)
    ;;
  *) echo "Usage: $0 direct|collector | down direct|collector"; exit 1 ;;
esac

if [ "$action" = "down" ]; then
  exec docker compose -p "fsi-$mode" "${profile[@]}" down
fi
echo "Mode: $mode  Environment: $DEPLOY_ENV  Realm: $SPLUNK_REALM"
exec docker compose -p "fsi-$mode" "${profile[@]}" up --build

#!/usr/bin/env bash
# Optional: send a larger volume of synthetic traces to build out the service map (SDK-direct, no Docker).
#
# Usage:  ./simulate.sh <minutes> <workers> <profile>   (all optional; try: ./simulate.sh 10 4 steady)
#   minutes   how long to run                       (default 10)
#   workers   parallel request loops                (default 4)
#   profile   steady | busy | incident              (default steady)
#
#   steady    normal mix: ~20% slow multi-state payroll runs, ~6% ACH timeouts, ~3% QuickBooks failures
#   busy      same mix, requests twice as often
#   incident  bank timeouts jump to ~35% and most payroll runs are multi-state: a bad day to find in the map
#
# Each request starts about one trace. Rough volume: workers x minutes x ~35 traces
# (4 workers x 10 minutes = about 1,500 traces). Uses your .env token and realm. Stop with Ctrl-C.
set -euo pipefail
cd "$(dirname "$0")"

minutes="${1:-10}"
workers="${2:-4}"
profile="${3:-steady}"

case "$profile" in
  steady)   export TRAFFIC_PAUSE_SCALE=1;   export MULTI_STATE_RATE=0.2; export ACH_FAIL_RATE=0.06; export QB_FAIL_RATE=0.03 ;;
  busy)     export TRAFFIC_PAUSE_SCALE=0.5; export MULTI_STATE_RATE=0.2; export ACH_FAIL_RATE=0.06; export QB_FAIL_RATE=0.03 ;;
  incident) export TRAFFIC_PAUSE_SCALE=1;   export MULTI_STATE_RATE=0.7; export ACH_FAIL_RATE=0.35; export QB_FAIL_RATE=0.03 ;;
  *) echo "Unknown profile '$profile' (use steady, busy or incident)"; exit 1 ;;
esac
export TRAFFIC_WORKERS="$workers"

echo "Simulating: ${minutes} min, ${workers} workers, profile ${profile}"
seconds="$(awk -v m="$minutes" 'BEGIN { printf "%d", m * 60 }')"
[ "$seconds" -gt 0 ] || { echo "minutes must be a positive number"; exit 1; }
exec ./run-local.sh "$seconds"

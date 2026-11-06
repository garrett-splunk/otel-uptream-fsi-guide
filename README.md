# Upstream OTel to Splunk Observability Cloud: FSI challenge lab

Hands-on lab: send OpenTelemetry traces and metrics from a synthetic FSI payroll platform (seven services) to Splunk Observability Cloud, first **straight from the SDK**, then **through a Collector**, and compare the two.

**Workshop guide: https://garrett-splunk.github.io/otel-uptream-fsi-guide/**

The guide is served by GitHub Pages from `/docs`:
- `docs/index.html`: Path A, Docker or local Python (SDK direct vs Collector, redaction, find the fault).
- `docs/kubernetes.html`: Path B, the OpenTelemetry Demo on Kubernetes with an in-cluster Collector. Adapted from the OpenTelemetry Kubernetes Demo workshop guide; not run from this repo.

## Quick start

```bash
cp .env.example .env        # then set SPLUNK_REALM and SPLUNK_ACCESS_TOKEN (INGEST scope)
./run.sh direct             # SDK exports straight to ingest        (Docker)
./run.sh collector          # SDK -> Collector -> ingest            (Docker)
./run-local.sh 120          # direct mode without Docker, 120 seconds
./simulate.sh 10 4 steady   # optional: send more traces (minutes workers profile; profile is steady, busy or incident)
./run.sh down direct        # stop
```

- `.env` is git-ignored. This repo is public: never commit a token.
- All data is synthetic. Nothing here refers to a real customer.

## Layout

| Path | What it is |
|---|---|
| `app/` | One Flask codebase that plays all seven services (`ROLE` env), the telemetry setup, and a traffic generator |
| `collector/config.yaml` | Gateway Collector with central redaction |
| `docker-compose.yml`, `run.sh` | Docker run path for both modes |
| `run-local.sh` | No-Docker, direct-mode run path |
| `simulate.sh` | Optional: send a larger volume of traces to fill out the service map (profiles: steady, busy, incident) |
| `docs/` | The workshop guide (GitHub Pages) |

## Status

- SDK direct: run against a real us1 org; services, inferred nodes, latency and error tags confirmed in APM.
- Collector mode: config written to spec, not yet run end to end.
- Enable Pages: Settings → Pages → Deploy from branch → `main` / `/docs`.

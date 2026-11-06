# Upstream OTel to Splunk Observability Cloud: FSI challenge lab

Hands-on lab: send OpenTelemetry traces and metrics from a synthetic FSI payroll platform (seven services) to Splunk Observability Cloud, first **straight from the SDK**, then **through a Collector**, and compare the two.

Guide (GitHub Pages, served from `/docs`): see `docs/index.html`.

## Quick start

```bash
cp .env.example .env        # then set SPLUNK_REALM and SPLUNK_ACCESS_TOKEN (INGEST scope)
./run.sh direct             # SDK exports straight to ingest        (Docker)
./run.sh collector          # SDK -> Collector -> ingest            (Docker)
./run-local.sh 120          # direct mode without Docker, 120 seconds
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
| `docs/` | The workshop guide (GitHub Pages) |

## Status

- SDK direct: run against a real us1 org; services, inferred nodes, latency and error tags confirmed in APM.
- Collector mode: config written to spec, not yet run end to end.
- Enable Pages: Settings → Pages → Deploy from branch → `main` / `/docs`.

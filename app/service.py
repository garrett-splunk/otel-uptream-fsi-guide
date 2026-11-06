"""One codebase, seven services. ROLE selects which service this process plays.

Fictional FSI payroll platform ("Northstar Payroll"). All data is synthetic:
tenant ids are opaque, SSNs use the invalid 900- range, bank numbers are zeros.

  portal-web -> payroll-api  -> tax-engine
                             -> payroll-db            (inferred database)
                             -> ach-gateway -> bank-network (inferred external)
                             -> notification-svc
             -> benefits-api -> benefits-db, carrier-gateway (inferred)
             -> hr-api       -> hr-db, quickbooks-api (inferred, third-party)
"""
import os
import random
import time

import requests
from flask import Flask, jsonify, request
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.trace import SpanKind, Status, StatusCode

import telemetry

ROLE = os.environ["ROLE"]
PORT = int(os.environ.get("PORT", "8080"))

telemetry.init()
tracer = trace.get_tracer("northstar.payroll")
meter = metrics.get_meter("northstar.payroll")
payroll_runs = meter.create_counter("payroll_runs", description="Payroll runs by result")
ach_seconds = meter.create_histogram("ach_settlement_seconds", unit="s", description="ACH submit latency")

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()


ACH_FAIL_RATE = float(os.environ.get("ACH_FAIL_RATE", "0.06"))   # bank-network timeouts
QB_FAIL_RATE = float(os.environ.get("QB_FAIL_RATE", "0.03"))     # quickbooks-api failures


def svc(name):
    return os.environ.get("URL_" + name.upper().replace("-", "_"), f"http://{name}:8080")


def call(name, path, body):
    """Call a downstream service; the requests instrumentation propagates trace context."""
    tenant = request.headers.get("X-Tenant-Id", "")
    r = requests.post(svc(name) + path, json=body, headers={"X-Tenant-Id": tenant}, timeout=15)
    return r


def db_call(db_name, operation, table, lo=8, hi=40):
    """Simulated database client span. Shows up as an inferred database in the service map."""
    with tracer.start_as_current_span(
        f"{operation} {db_name}.{table}",
        kind=SpanKind.CLIENT,
        attributes={
            "db.system": "postgresql",
            "db.name": db_name,
            "db.operation": operation,
            "db.sql.table": table,
            "db.statement": f"{operation} ... FROM {table} WHERE tenant_id = ?",
            "server.address": f"{db_name}.internal.example",
            "server.port": 5432,
        },
    ):
        time.sleep(random.uniform(lo, hi) / 1000)


def external_call(peer, operation, lo, hi, fail_rate=0.0):
    """Simulated call to a system we do not instrument. peer.service makes it an inferred service."""
    with tracer.start_as_current_span(
        f"{operation} {peer}",
        kind=SpanKind.CLIENT,
        attributes={
            "peer.service": peer,
            "http.request.method": "POST",
            "server.address": f"api.{peer}.example",
        },
    ) as span:
        time.sleep(random.uniform(lo, hi) / 1000)
        if random.random() < fail_rate:
            span.set_attribute("http.response.status_code", 504)
            span.set_status(Status(StatusCode.ERROR, f"{peer} timeout"))
            raise TimeoutError(f"{peer} timeout")
        span.set_attribute("http.response.status_code", 200)


@app.before_request
def tag_tenant():
    tenant = request.headers.get("X-Tenant-Id")
    if tenant:
        trace.get_current_span().set_attribute("client.tenant_id", tenant)


@app.get("/healthz")
def healthz():
    return "ok"


if ROLE == "portal-web":

    def forward(name, path, body):
        try:
            r = call(name, path, body)
            return jsonify(r.json()), r.status_code
        except requests.RequestException as exc:
            return jsonify({"error": str(exc)}), 502

    @app.post("/payroll/run")
    def portal_payroll():
        return forward("payroll-api", "/payroll/run", request.get_json(silent=True) or {})

    @app.post("/benefits/enroll")
    def portal_benefits():
        return forward("benefits-api", "/benefits/enroll", request.get_json(silent=True) or {})

    @app.post("/hr/summary")
    def portal_hr():
        return forward("hr-api", "/hr/summary", request.get_json(silent=True) or {})


elif ROLE == "payroll-api":

    @app.post("/payroll/run")
    def run_payroll():
        body = request.get_json(silent=True) or {}
        span = trace.get_current_span()
        span.set_attribute("payroll.employee_count", body.get("employees", 0))
        span.set_attribute("payroll.jurisdiction", body.get("jurisdiction", "single-state"))
        telemetry.tag_sensitive(span, "employee.ssn", "900-00-0001")
        telemetry.tag_sensitive(span, "bank.account_number", "0000012345")
        db_call("payroll-db", "SELECT", "employee_earnings")
        tax = call("tax-engine", "/tax/calc", body)
        if tax.status_code >= 500:
            payroll_runs.add(1, {"result": "error"})
            return jsonify({"error": "tax failure"}), 502
        db_call("payroll-db", "INSERT", "payroll_runs")
        ach = call("ach-gateway", "/ach/submit", body)
        if ach.status_code >= 500:
            payroll_runs.add(1, {"result": "error"})
            return jsonify({"error": "ach failure"}), 502
        call("notification-svc", "/notify", {"kind": "payroll-complete"})
        payroll_runs.add(1, {"result": "ok"})
        return jsonify({"status": "paid"})


elif ROLE == "tax-engine":

    @app.post("/tax/calc")
    def tax_calc():
        body = request.get_json(silent=True) or {}
        multi = body.get("jurisdiction") == "multi-state"
        with tracer.start_as_current_span("compute-withholding") as s:
            s.set_attribute("tax.jurisdiction", body.get("jurisdiction", "single-state"))
            time.sleep(random.uniform(800, 1500) / 1000 if multi else random.uniform(30, 90) / 1000)
        return jsonify({"withheld": True})


elif ROLE == "ach-gateway":

    @app.post("/ach/submit")
    def ach_submit():
        start = time.time()
        span = trace.get_current_span()
        telemetry.tag_sensitive(span, "bank.routing_number", "000000000")
        try:
            external_call("bank-network", "submit-batch", 120, 400, fail_rate=ACH_FAIL_RATE)
        except TimeoutError as exc:
            ach_seconds.record(time.time() - start, {"result": "error"})
            span.record_exception(exc)
            return jsonify({"error": "bank timeout"}), 504
        ach_seconds.record(time.time() - start, {"result": "ok"})
        return jsonify({"submitted": True})


elif ROLE == "notification-svc":

    @app.post("/notify")
    def notify():
        time.sleep(random.uniform(10, 30) / 1000)
        return jsonify({"queued": True})


elif ROLE == "benefits-api":

    @app.post("/benefits/enroll")
    def enroll():
        span = trace.get_current_span()
        telemetry.tag_sensitive(span, "employee.ssn", "900-00-0002")
        db_call("benefits-db", "SELECT", "plans")
        external_call("carrier-gateway", "submit-enrollment", 150, 400)
        db_call("benefits-db", "INSERT", "enrollments")
        return jsonify({"enrolled": True})


elif ROLE == "hr-api":

    @app.post("/hr/summary")
    def hr_summary():
        db_call("hr-db", "SELECT", "employees")
        try:
            external_call("quickbooks-api", "sync-ledger", 200, 600, fail_rate=QB_FAIL_RATE)
        except TimeoutError as exc:
            trace.get_current_span().record_exception(exc)
            return jsonify({"error": "accounting sync failed"}), 502
        return jsonify({"synced": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True)

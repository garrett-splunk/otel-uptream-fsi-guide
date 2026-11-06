"""Synthetic load. Plain requests, no OpenTelemetry: the portal starts every trace."""
import os
import random
import sys
import time

import requests

PORTAL = os.environ.get("PORTAL_URL", "http://portal-web:8080")
TENANTS = [f"tenant-{n:04d}" for n in range(1, 13)]
SCENARIOS = [
    (55, "/payroll/run"),
    (25, "/benefits/enroll"),
    (20, "/hr/summary"),
]


def pick():
    return random.choices([p for _, p in SCENARIOS], weights=[w for w, _ in SCENARIOS])[0]


def main(limit, seconds=None):
    sent = 0
    deadline = time.time() + seconds if seconds else None
    while (limit is None or sent < limit) and (deadline is None or time.time() < deadline):
        path = pick()
        tenant = random.choice(TENANTS)
        body = {
            "employees": random.randint(5, 400),
            "jurisdiction": "multi-state" if random.random() < 0.2 else "single-state",
        }
        try:
            r = requests.post(PORTAL + path, json=body, headers={"X-Tenant-Id": tenant}, timeout=30)
            print(f"{sent:04d} {path} {tenant} -> {r.status_code}", flush=True)
        except requests.RequestException as exc:
            print(f"{sent:04d} {path} {tenant} -> error {exc}", flush=True)
            time.sleep(2)
        sent += 1
        time.sleep(random.uniform(0.3, 1.5))


if __name__ == "__main__":
    # python traffic.py            -> run forever
    # python traffic.py 100        -> 100 requests
    # python traffic.py --seconds 60
    if len(sys.argv) > 2 and sys.argv[1] == "--seconds":
        main(None, float(sys.argv[2]))
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else None)

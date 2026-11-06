"""Synthetic load. Plain requests, no OpenTelemetry: the portal starts every trace.

Knobs (environment variables):
  PORTAL_URL            where portal-web listens
  TRAFFIC_WORKERS       parallel request loops (default 1)
  TRAFFIC_PAUSE_SCALE   0.5 sends requests twice as often (default 1)
  MULTI_STATE_RATE      share of slow multi-state payroll runs (default 0.2)
"""
import os
import random
import sys
import threading
import time

import requests

PORTAL = os.environ.get("PORTAL_URL", "http://portal-web:8080")
WORKERS = int(os.environ.get("TRAFFIC_WORKERS", "1"))
PAUSE_SCALE = float(os.environ.get("TRAFFIC_PAUSE_SCALE", "1"))
MULTI_STATE_RATE = float(os.environ.get("MULTI_STATE_RATE", "0.2"))

TENANTS = [f"tenant-{n:04d}" for n in range(1, 13)]
SCENARIOS = [
    (55, "/payroll/run"),
    (25, "/benefits/enroll"),
    (20, "/hr/summary"),
]


def pick():
    return random.choices([p for _, p in SCENARIOS], weights=[w for w, _ in SCENARIOS])[0]


def worker(wid, limit, deadline, counter, lock):
    while (limit is None or counter[0] < limit) and (deadline is None or time.time() < deadline):
        path = pick()
        tenant = random.choice(TENANTS)
        body = {
            "employees": random.randint(5, 400),
            "jurisdiction": "multi-state" if random.random() < MULTI_STATE_RATE else "single-state",
        }
        try:
            r = requests.post(PORTAL + path, json=body, headers={"X-Tenant-Id": tenant}, timeout=30)
            status = r.status_code
        except requests.RequestException as exc:
            status = f"error {exc}"
            time.sleep(2)
        with lock:
            counter[0] += 1
            n = counter[0]
        if n % 25 == 0 or limit is not None:
            print(f"[w{wid}] {n:05d} {path} {tenant} -> {status}", flush=True)
        time.sleep(random.uniform(0.3, 1.5) * PAUSE_SCALE)


def main(limit, seconds=None):
    deadline = time.time() + seconds if seconds else None
    counter, lock = [0], threading.Lock()
    threads = [threading.Thread(target=worker, args=(i, limit, deadline, counter, lock)) for i in range(WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"done: {counter[0]} requests (about one trace each) with {WORKERS} worker(s)", flush=True)


if __name__ == "__main__":
    # python traffic.py            -> run forever
    # python traffic.py 100        -> 100 requests
    # python traffic.py --seconds 60
    if len(sys.argv) > 2 and sys.argv[1] == "--seconds":
        main(None, float(sys.argv[2]))
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else None)

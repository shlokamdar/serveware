"""Verifies the monitoring stack is actually watching production."""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request


def get_json(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--prometheus", default="http://localhost:9090")
    p.add_argument("--alertmanager", default="http://localhost:9093")
    p.add_argument("--grafana", default="http://localhost:3000")
    p.add_argument("--job", action="append", required=True)
    p.add_argument("--retries", type=int, default=12)
    a = p.parse_args()
    problems = []

    for job in a.job:
        q = urllib.parse.quote(f'up{{job="{job}"}}')
        up = None
        for _ in range(a.retries):
            try:
                res = get_json(f"{a.prometheus}/api/v1/query?query={q}")["data"]["result"]
                up = res[0]["value"][1] if res else None
            except Exception as exc:  # noqa: BLE001
                print(f"waiting for Prometheus: {exc}")
            if up == "1":
                break
            time.sleep(5)
        print(f"{'PASS' if up == '1' else 'FAIL'}  target {job} up={up}")
        if up != "1":
            problems.append(f"{job} not up")

    groups = get_json(f"{a.prometheus}/api/v1/rules")["data"]["groups"]
    rules = [r["name"] for g in groups for r in g["rules"]]
    print(f"{'PASS' if len(rules) >= 3 else 'FAIL'}  alert rules loaded: {rules}")
    if len(rules) < 3:
        problems.append("alert rules missing")

    firing = [al for al in get_json(f"{a.prometheus}/api/v1/alerts")["data"]["alerts"]
              if al["state"] == "firing" and al["labels"].get("severity") == "critical"]
    print(f"{'PASS' if not firing else 'FAIL'}  critical alerts firing: {len(firing)}")
    if firing:
        problems.append("critical alerts firing")

    for name, url in (("alertmanager", f"{a.alertmanager}/-/ready"), ("grafana", f"{a.grafana}/api/health")):
        try:
            urllib.request.urlopen(url, timeout=5)
            print(f"PASS  {name} reachable")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL  {name}: {exc}")
            problems.append(f"{name} unreachable")

    if problems:
        print("MONITORING CHECK FAILED:", "; ".join(problems))
        return 1
    print("Monitoring stack healthy and watching production.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

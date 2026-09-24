"""Post-deploy smoke test: waits for the app, then checks key endpoints."""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def get(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "serveware-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def wait_for_health(base, expect_version, retries, delay):
    for attempt in range(1, retries + 1):
        try:
            status, body = get(f"{base}/healthz/")
            data = json.loads(body)
            if status == 200 and data.get("status") == "ok":
                if expect_version and not str(data.get("version", "")).startswith(expect_version):
                    print(f"[{attempt}] healthy but version={data.get('version')} (waiting for {expect_version})")
                else:
                    print(f"[{attempt}] healthy: {data}")
                    return True
        except (urllib.error.URLError, ConnectionError, ValueError) as exc:
            print(f"[{attempt}/{retries}] not ready: {exc}")
        time.sleep(delay)
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--expect-version", default="")
    p.add_argument("--retries", type=int, default=24)
    p.add_argument("--delay", type=float, default=5)
    a = p.parse_args()
    base = a.base_url.rstrip("/")

    if not wait_for_health(base, a.expect_version, a.retries, a.delay):
        print("SMOKE FAIL: app never became healthy")
        return 1

    checks = [
        ("/", 200, None),
        ("/accounts/customer/signin/", 200, None),
        ("/accounts/restaurant/signin/", 200, None),
        ("/metrics", 200, "django_http"),
    ]
    failed = 0
    for path, code, must_contain in checks:
        try:
            status, body = get(base + path)
            ok = status == code and (must_contain is None or must_contain in body)
        except urllib.error.HTTPError as exc:
            status, ok = exc.code, False
        print(f"{'PASS' if ok else 'FAIL'}  {path}  -> {status}")
        failed += not ok

    print(f"Smoke test: {len(checks) - failed}/{len(checks)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

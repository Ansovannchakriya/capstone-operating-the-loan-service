"""Post-deploy verification. Exits 1 if the live release is not healthy, which triggers the rollback job.

Checks, in order:
  1. /health reports the expected git SHA (polls until the new release is live)
  2. /openapi.json is served and lists the spec paths
  3. the three API-key checks: no key -> 401, wrong key -> 401, right key -> 200
  4. golden applicants: a strong borrower scores low risk, a weak borrower scores high risk

Only the standard library is used so it runs on any runner. The API key is read from the
LIVE_API_KEY environment variable and is never printed.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

SPEC_PATHS = ["/api/v1/applications", "/api/v1/applications/{application_id}",
              "/api/v1/applications/{application_id}/predictions", "/api/v1/borrowers/{borrower_id}/applications"]
# borrower id -> (check, limit) on default probability for a 1,500 USD / 12 month loan
GOLDEN = {1042: ("<", 0.20), 1043: (">", 0.80)}

lines: list[str] = []


def say(msg: str) -> None:
    line = f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} {msg}"
    print(line, flush=True)
    lines.append(line)


def call(base, method, path, key=None, body=None):
    req = urllib.request.Request(base.rstrip("/") + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if key is not None:
        req.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return 0, str(e)


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--sha", required=True)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--merged-at", help="commit/merge time, to report merge -> live")
    ap.add_argument("--rollback-started-at", help="when the failure was detected, to report rollback -> recovered")
    ap.add_argument("--log", default="verify.log")
    args = ap.parse_args()
    key = os.environ.get("LIVE_API_KEY", "")
    failures = []

    say(f"verify {args.base_url} expecting git_sha={args.sha[:7]}")
    deadline = time.time() + args.timeout
    while True:
        status, body = call(args.base_url, "GET", "/health")
        live = (body or {}).get("git_sha", "") if isinstance(body, dict) else ""
        say(f"GET /health -> {status} git_sha={live[:7] or '-'}")
        if status == 200 and live == args.sha:
            break
        if time.time() > deadline:
            failures.append("new release never became live")
            break
        time.sleep(10)
    live_at = datetime.now(timezone.utc)
    merged = parse_time(args.merged_at)
    if merged and not failures:  # reported even if a later check fails: the release did go live
        say(f"TIMING merge -> live: {(live_at - merged).total_seconds():.0f} s")

    if not failures:
        status, spec = call(args.base_url, "GET", "/openapi.json")
        missing = [p for p in SPEC_PATHS if p not in (spec or {}).get("paths", {})]
        say(f"GET /openapi.json -> {status}, missing spec paths: {missing or 'none'}")
        if status != 200 or missing:
            failures.append("openapi")

        for label, k, want in [("no key", None, 401), ("wrong key", "wrong-key", 401), ("right key", key, 200)]:
            status, _ = call(args.base_url, "GET", "/api/v1/applications?limit=1", key=k)
            say(f"API key check [{label}] -> {status} (want {want})")
            if status != want:
                failures.append(f"auth {label}")

        for borrower, (op, limit) in GOLDEN.items():
            status, app = call(args.base_url, "POST", "/api/v1/applications", key,
                               {"borrower_id": borrower, "amount_usd": 1500, "term_months": 12})
            if status != 201:
                failures.append(f"golden {borrower}: create {status}")
                continue
            status, pred = call(args.base_url, "POST", f"/api/v1/applications/{app['id']}/predictions", key)
            p = (pred or {}).get("default_probability", -1)
            ok = status == 201 and (p < limit if op == "<" else p > limit)
            say(f"golden borrower {borrower}: default_probability={p} (want {op} {limit}) -> {'ok' if ok else 'FAIL'}")
            if not ok:
                failures.append(f"golden {borrower}")

    started = parse_time(args.rollback_started_at)
    if started and not failures:
        say(f"TIMING rollback -> recovered: {(datetime.now(timezone.utc) - started).total_seconds():.0f} s")

    say("RESULT " + ("PASS" if not failures else "FAIL: " + ", ".join(failures)))
    with open(args.log, "w") as f:
        f.write("\n".join(lines) + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("```\n" + "\n".join(lines) + "\n```\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

"""Compare the live /openapi.json with the Module 2 spec and print a Markdown table.

usage: python scripts/compare_openapi.py https://<live-host>/openapi.json docs/openapi-module2.yaml
"""
import json
import sys
import urllib.request

import yaml

METHODS = {"get", "post", "put", "patch", "delete"}
PREFIX = "/api/v1"   # the spec's server URL ends in /api/v1, so its paths have no prefix


def operations(spec, strip=""):
    ops = {}
    for path, item in spec.get("paths", {}).items():
        for method, op in item.items():
            if method in METHODS:
                key = (method.upper(), path[len(strip):] if strip and path.startswith(strip) else path)
                codes = sorted(str(c) for c in op.get("responses", {}))
                ops[key] = codes
    return ops


def main():
    live_src, spec_src = sys.argv[1], sys.argv[2]
    if live_src.startswith("http"):
        with urllib.request.urlopen(live_src, timeout=15) as r:
            live = json.loads(r.read())
    else:
        live = json.load(open(live_src))
    spec = yaml.safe_load(open(spec_src))
    lv, sp = operations(live, PREFIX), operations(spec)

    print("| Method | Path (under /api/v1) | Spec codes | Live codes | Result |")
    print("|---|---|---|---|---|")
    for key in sorted(set(lv) | set(sp), key=lambda k: (k[1], k[0])):
        s, l_ = sp.get(key), lv.get(key)
        if s and l_:
            extra = sorted(set(l_) - set(s))
            result = "match" if not set(s) - set(l_) else "codes differ"
            if extra:
                result += f" (live adds {', '.join(extra)})"
        elif l_:
            result = "added on purpose" if key[1] == "/health" else "only live"
        else:
            result = "MISSING in live"
        print(f"| {key[0]} | {key[1]} | {', '.join(s or []) or '-'} | {', '.join(l_ or []) or '-'} | {result} |")
    live_schemes = list(live.get("components", {}).get("securitySchemes", {}))
    print(f"\nSecurity schemes - spec: {list(spec['components']['securitySchemes'])}, live: {live_schemes}")


if __name__ == "__main__":
    main()

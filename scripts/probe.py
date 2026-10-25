#!/usr/bin/env python3
"""Probe Lumi Trades public endpoints once and append one JSON line per endpoint.

Free, unpaid requests only. No payment headers are ever sent, so paid routes
answer with an x402 "402 Payment Required" quote, which counts as UP.
Standard library only.
"""
import json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

UA = "lumi-uptime/1.0 (+https://github.com/lumitrades/lumi-uptime)"
SAMPLE = "https://api.example.com/v1/data"  # harmless placeholder target
ENDPOINTS = [
    # name, url, accepted statuses
    ("health", "https://api.lumitrades.io/health", {200}),
    ("verdict", f"https://api.lumitrades.io/v1/verdict?url={SAMPLE}", {402}),
    ("trust_check", f"https://api.lumitrades.io/v1/trust/check?url={SAMPLE}", {402}),
    ("well_known_x402", "https://lumitrades.io/.well-known/x402", {200}),
]
TIMEOUT = 15

def probe(name, url, ok_codes):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    t0 = time.monotonic()
    status, body, headers, err = None, b"", {}, None
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            status, body, headers = r.status, r.read(65536), dict(r.headers)
    except urllib.error.HTTPError as e:
        status, headers = e.code, dict(e.headers or {})
        try: body = e.read(65536)
        except Exception: body = b""
    except Exception as e:  # DNS, TLS, timeout, connection reset
        err = f"{type(e).__name__}: {e}"[:200]
    ms = round((time.monotonic() - t0) * 1000, 1)
    up = status in ok_codes
    note = None
    if up and status == 402:
        # Must be a real x402 quote, not a generic 402 page.
        hdr = {k.lower() for k in headers}
        has_quote = b'"accepts"' in body or "payment-required" in hdr
        if not has_quote:
            up, note = False, "402 without x402 accepts/PAYMENT-REQUIRED"
    if up and status == 200 and name == "health":
        try:
            if json.loads(body).get("status") != "ok":
                up, note = False, "health status != ok"
        except Exception:
            up, note = False, "health body not JSON"
    rec = {"ts": ts, "endpoint": name, "url": url, "status": status, "ms": ms, "up": up}
    if err: rec["error"] = err
    if note: rec["note"] = note
    if os.environ.get("GITHUB_RUN_ID"):
        rec["run"] = os.environ["GITHUB_RUN_ID"]
    return rec

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else None
    recs = [probe(*e) for e in ENDPOINTS]
    lines = "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in recs)
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "a") as f: f.write(lines)
    sys.stdout.write(lines)

if __name__ == "__main__":
    main()

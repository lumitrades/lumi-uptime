#!/usr/bin/env python3
"""Compute availability per endpoint over trailing windows (default 7 and 30 days).

Reads data/probes-YYYY-MM.jsonl (or files/globs given as arguments).
availability = up probes / total probes in the window, per endpoint.
"All endpoints" = share of probe rounds (one GitHub run) in which every endpoint was up.
Gaps (rounds GitHub skipped or delayed) are reported as coverage, not counted as down.
"""
import glob, json, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

def load(paths):
    for p in paths:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    try: yield json.loads(line)
                    except json.JSONDecodeError: pass

def parse(ts): return datetime.strptime(ts.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S.%f%z")

def main():
    args = sys.argv[1:]
    paths = sorted(sum((glob.glob(a) for a in args), [])) if args else sorted(glob.glob("data/probes-*.jsonl"))
    recs = [r for r in load(paths)]
    if not recs:
        print("no probe data yet"); return
    for r in recs: r["_t"] = parse(r["ts"])
    now = datetime.now(timezone.utc)
    first = min(r["_t"] for r in recs)
    print(f"data: {len(recs)} probes, {first:%Y-%m-%d %H:%M}Z to {max(r['_t'] for r in recs):%Y-%m-%d %H:%M}Z")
    for days in (7, 30):
        since = now - timedelta(days=days)
        win = [r for r in recs if r["_t"] >= since]
        span_h = (now - max(since, first)).total_seconds() / 3600
        print(f"\n== last {days} days ({span_h/24:.1f} days of data) ==")
        per = defaultdict(lambda: [0, 0, []])
        rounds = defaultdict(list)
        for r in win:
            s = per[r["endpoint"]]; s[0] += r["up"]; s[1] += 1; s[2].append(r["ms"])
            rounds[r.get("run") or r["ts"][:16]].append(r["up"])
        print(f"{'endpoint':<18}{'up/total':>12}{'avail %':>10}{'p50 ms':>9}{'p95 ms':>9}")
        for ep, (u, n, ms) in sorted(per.items()):
            ms = sorted(ms)
            p50 = ms[len(ms)//2]; p95 = ms[min(len(ms)-1, int(len(ms)*0.95))]
            print(f"{ep:<18}{f'{u}/{n}':>12}{100*u/n:>10.3f}{p50:>9.0f}{p95:>9.0f}")
        allup = sum(all(v) for v in rounds.values())
        exp = span_h * 12  # one round every 5 minutes
        print(f"{'ALL (per round)':<18}{f'{allup}/{len(rounds)}':>12}{100*allup/max(1,len(rounds)):>10.3f}")
        print(f"coverage: {len(rounds)} rounds vs ~{exp:.0f} expected at 5-min cadence ({min(100, 100*len(rounds)/max(1,exp)):.0f}%)")

if __name__ == "__main__":
    main()

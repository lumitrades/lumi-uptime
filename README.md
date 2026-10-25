# lumi-uptime

Independent, outside uptime log for the [Lumi Trades](https://lumitrades.io) x402 API
(`api.lumitrades.io`, a Cloudflare Worker). It runs on GitHub-hosted runners, not on
Lumi's own infrastructure.

## What is probed

Every 5 minutes (GitHub's scheduler can delay or skip runs; each record carries the
actual UTC time it ran), a GitHub Actions job sends these unpaid requests:

| endpoint | request | counts as up |
|---|---|---|
| `health` | `GET https://api.lumitrades.io/health` | 200 and `"status":"ok"` |
| `verdict` | `GET https://api.lumitrades.io/v1/verdict?url=https://api.example.com/v1/data` | 402 with an x402 `accepts` quote |
| `trust_check` | `GET https://api.lumitrades.io/v1/trust/check?url=https://api.example.com/v1/data` | 402 with an x402 `accepts` quote |
| `well_known_x402` | `GET https://lumitrades.io/.well-known/x402` | 200 |

No payment is ever made: the paid routes are called without a payment header, so a
healthy server answers with its x402 price quote (HTTP 402). Anything else (5xx, timeout,
DNS/TLS failure, wrong status) counts as down. Requests use the User-Agent
`lumi-uptime/1.0`.

## Data

`data/probes-YYYY-MM.jsonl`, one JSON object per endpoint per run:

```json
{"ts":"2026-10-25T21:30:04.123Z","endpoint":"health","url":"...","status":200,"ms":104.5,"up":true,"run":"123"}
```

`ms` is total request time from the GitHub runner (includes DNS/TLS). Every run is also a
commit, so the git history timestamps the log independently.

## Availability

```sh
python3 scripts/availability.py
```

Prints, for the last 7 and 30 days, up/total probes and availability % per endpoint,
p50/p95 latency, the share of rounds where all endpoints were up, and coverage (rounds
actually run vs. the ~12/hour expected). Skipped scheduler runs reduce coverage; they are
not counted as downtime.

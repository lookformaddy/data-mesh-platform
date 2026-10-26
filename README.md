# data-mesh-platform

A federated data mesh platform: domains own versioned data products;
global policy packs and domain-local policies govern them (global wins
on conflict, and the conflict is logged); consumers discover products,
request expiring access, and read SLO health and cross-domain lineage —
and a product version publishes only if it passes its schema and SLO
gate. Built as production-grade Python with synthetic data only.

**Track:** Data Engineering

## The enterprise problem

A central data team cannot scale, but pure decentralization is chaos:

- **"Who owns this dataset?"** — without domain ownership, nobody is
  accountable for freshness or quality.
- **"Can we use it?"** — access rules scattered across teams and tools
  mean slow, unauditable approvals.
- **"Is it any good?"** — a product with no SLO is a promise nobody made.
- **"What breaks if this changes?"** — without cross-domain lineage,
  one domain's breaking change is another domain's outage.
- **"Can a bad version ship?"** — without a publish gate, a schema
  violation reaches consumers before anyone notices.

This repo implements all of it, clean-room, with synthetic data only.

## Architecture overview

```
domains ──▶ own ──▶ data products (versioned schemas, SLOs, ports)
                          │
     ┌────────────────────┼────────────────────┐
     ▼                    ▼                    ▼
governance           discovery            access
(global + domain,    (ranked search)      (request → grant,
 global wins)                            expiring, audited)
     │                    │                    │
     └──────────┬─────────┴──────────┬─────────┘
                ▼                    ▼
          publish gate          health + lineage
          (schema + SLO;         (SLO scores, BFS
           blocked = no ship)     impact with hops)
```

See [docs/architecture.md](docs/architecture.md) for the full component
map, data flow, and design trade-offs.

## How to run it

```bash
python -m venv /tmp/venv && source /tmp/venv/bin/activate
pip install -r requirements.txt
pip install -e .

# run the tests (API tests auto-skip without FastAPI)
pytest -q

# end-to-end demo: build a mesh, publish, search, grant access, score health
python examples/run_demo.py
# or: python -m datamesh demo

# optional API service (requires FastAPI + uvicorn)
python -m datamesh serve   # http://127.0.0.1:8000
```

## Key design decisions and trade-offs

- **Federated ownership, central guardrails.** Domains decide their
  products; global policy packs set the floor. A domain policy can
  narrow a global allow, never widen a global deny.
- **Global wins, logged.** On conflict the global policy wins and the
  conflict is recorded in the audit log — decisions are explainable,
  not just enforced.
- **Fail-closed publish gate.** A version that violates its schema or
  SLO thresholds does not ship, and the last good version stays live.
- **Deterministic discovery.** Name > tag > description scoring with an
  owner boost and product_id tie-breaks — reproducible, debuggable,
  no embeddings required.
- **Expiring, auditable access.** Grants expire, can be revoked, and
  every transition is appended to an audit log. Denied requests never
  create grants; expired grants never revive.
- **Health as a blend, breaches listed.** A weighted score stops one
  perfect signal hiding a stale feed, while each SLO breach is still
  reported individually.

## What it demonstrates

Domain-driven data ownership at enterprise scale: a registry of
versioned, SLO-backed data products; federated governance with
auditable conflict resolution; ranked mesh-wide discovery; an
expiring, audited access workflow; SLO health scoring; cross-domain
lineage impact analysis; and a fail-closed publish gate — the control
plane a real data mesh runs on.

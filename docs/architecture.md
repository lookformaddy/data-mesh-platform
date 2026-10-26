# Architecture

## The enterprise problem

A central data team cannot scale: every new dataset queues behind one
team, ownership is unclear, and "who can use what, and is it any good?"
has no single answer. A data mesh fixes this by federating ownership —
domains own their data products — while keeping mesh-wide governance,
discovery, and quality guarantees central. This repo implements that
control plane: not a query engine, but the registry, governance,
discovery, access, health, lineage, and publishing rules a mesh needs
before any data moves.

## Component map

```
MeshPlatform (src/datamesh/platform.py) — facade over all subsystems
├── registry.py      domains own products; products carry versioned
│                    schemas, SLOs, input/output ports
├── governance.py    global policy packs + domain-local policies;
│                    global deny wins over domain allow, logged
├── discovery.py     deterministic ranked search (name > tag >
│                    description, owner boost, stable tie-break)
├── access.py        request → approve/deny → expiring grant →
│                    revoke; append-only audit log
├── health.py        SLO-based health score (freshness/completeness/
│                    availability/quality), grades + breaches
├── lineage.py       directed product graph; BFS upstream/downstream
│                    with hop counts; cycle detection
├── publish.py       publish gate: schema check + SLO check;
│                    blocked publish never moves published_version
└── service.py       optional FastAPI read/decision surface
```

## Data flow

```
register domain ──▶ register product ──▶ add schema + ports
                                              │
publish_version ──▶ governance decision ──▶ schema check ──▶ SLO check
     │                                                        │
     ▼ (all pass)                                    (any fail)
published_version = new version              published_version unchanged
                                              + violations returned
consumers ──▶ discovery ──▶ access request ──▶ grant ──▶ health + lineage
```

## Key design decisions and trade-offs

- **In-memory, stdlib core.** The platform is a library first; persistence
  (a real store behind the registry) is a deployment choice, not baked
  into the domain logic. Tests and the demo run with zero services.
- **Fail-closed everywhere.** Unknown products, undecided requests, and
  failed gates are errors/denials, never defaults. A blocked publish
  leaves the last good version live — consumers never see a broken one.
- **Global wins, logged.** Conflict resolution is one sentence, not a
  priority-number maze — and every conflict lands in the audit log, so a
  domain team can see exactly which global rule overrode them and why.
- **Deterministic ranking, no embeddings.** Discovery scores are
  explainable (name/tag/description/owner) with product_id tie-breaks, so
  search results are reproducible and debuggable.
- **Health is a blend, not a minimum.** A weighted score means a stale
  feed cannot hide behind perfect completeness, while SLO breaches are
  still listed individually for operators.
- **No execution engine.** This repo governs products; it does not move
  bytes. Pair it with a pipeline platform (e.g. an ELT/CDC platform) for
  the actual data movement, and point lineage edges at its outputs.
```


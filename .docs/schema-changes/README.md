# Schema changes (per development cycle)

**Purpose:** Give architecture (and implementers) **one document** that lists every database change for a feature cycle—without reading requirements, tech sketch, reviews, and open questions end-to-end.

This is **not** a second product process. It is a **cycle-specific schema delta** that the rest of the packet **points to**.

## When required

| Change type | Schema-changes doc? |
|-------------|---------------------|
| New/altered tables, columns, constraints, indexes, enums | **Yes** (full pipeline) |
| RLS policy changes | **Yes** (call out explicitly) |
| Data backfill / dual-write | **Yes** |
| App-only (no migration) | No — omit file |

Tiny/small work that still needs a migration: short schema-changes file is enough (can skip full idea/reviews if process allows).

## Naming

Same stem as the feature packet:

```
requirements/data-parsers-lims-runs.md
tech-sketch/data-parsers-lims-runs.md
schema-changes/data-parsers-lims-runs.md   ← this folder
architecture-review/data-parsers-lims-runs.md
```

Optional: Alembic revision ids filled in at implement time (`0054_…`).

## What goes here (only)

1. **Scope** — which phase(s) of the feature this migration set covers  
2. **Delta table** — ADD / ALTER / DROP (tables, columns, FKs, checks, indexes, enums)  
3. **RLS** — new or changed policies  
4. **Backfill / dual-write** — if any  
5. **Rollback** — how to reverse or why forward-only  
6. **Out of scope** — schema explicitly **not** changing this cycle  
7. **Links** — requirements + tech sketch (context only; do not duplicate product prose)

## What does **not** go here

- Full product rationale (→ requirements)  
- API/UI flows (→ tech sketch / UI review)  
- Open product debates (→ open questions); only **schema decisions** and open **schema** blockers  

## Lifecycle

```
Tech sketch (may draft model)
    ↓
schema-changes/<stem>.md   ← freeze candidate for architecture review
    ↓
Architecture review verifies THIS file
    ↓
Implementation: Alembic migrations match this doc (update revision ids)
    ↓
After ship: keep file as historical record; do not delete
```

If schema changes during review, **update this file** and re-check architecture conditions—not scatter updates across seven docs.

## Template

Copy [\_TEMPLATE.md](./_TEMPLATE.md) to `<stem>.md`.

## Related

- [development-process](../development-process/README.md)  
- Long-form field-management / schema **product** design (platform): [design/schema-evolution.md](../design/schema-evolution.md) — different from per-cycle deltas  

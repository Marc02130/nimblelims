# P0 Atomic Receive — Test Data & Scenario Catalog

This pack is **test data + a scenario catalog only**. It does not implement
`POST /api/samples/receive`, does not change product feature code, and does
not insert parent/child samples.

Seeded BioTech entities come from migration **0058** (clients, users, projects,
lists, analyses, analytes, container types). Migration **0059** seeds lifecycle
samples **with aliquots / `parent_sample_id`** — those rows are **not** receive
fixtures. P0 receive uses **payloads only**.

Implement gate: **CLOSED**. Live `POST /api/samples/receive` is not on main.
UAT of the receive API itself cannot pass until the feature PR lands. Schema
invariants (this pack's pytest) and list seeds (migration 0060) can run now.

---

## How to load

Docker Compose applies Alembic on backend startup (0058 + 0059 + **0060** when
this pack is merged):

```bash
sudo docker compose up -d --build
```

Re-run migrations against an already-running stack:

```bash
sudo docker exec lims-backend python run_migrations.py
```

Verify 0058 users/projects exist (do **not** expect AR-* samples — they are
created only by a future receive API):

```sql
SELECT username FROM users
 WHERE username IN ('alice-tech', 'bob-tech', 'carol-manager', 'david-cro');

SELECT id, name FROM projects
 WHERE name IN ('mAb-2301 PK Study', 'CAR-T In-Process Testing');

SELECT le.name
  FROM list_entries le
  JOIN lists l ON l.id = le.list_id
 WHERE l.name = 'Test Status'
   AND le.name = 'Assigned/Pending';

SELECT le.name
  FROM list_entries le
  JOIN lists l ON l.id = le.list_id
 WHERE l.name = 'Result Qualifiers'
   AND le.name IN ('<LOD', 'ND');
```

Data source for actors/projects/lists: **migration 0058**, not 0059 samples.
0060 only adds missing **Test Status** (`Assigned/Pending`) and **Result Qualifiers**
(`<LOD`, `ND`) list entries. It does not seed samples.

---

## Implement gate (CLOSED)

| Surface | Status |
|---------|--------|
| `POST /api/samples/receive` | **Not implemented.** Expect 404/405 until the feature PR. |
| Receive UAT (AR-HV-*, AR-DUP-*, AR-ID-*, AR-ST-*) | Blocked on the gate. Use `payloads.json` as the contract. |
| Follow-up test/result APIs (`POST /tests/`, `POST /tests/assign`, `DELETE /tests/{id}`, `POST /results/`, `PATCH /tests/{id}/review`) | Exist today; P0 expected codes (DELETE → 400 when results exist; result unit from `analytes.units_default` → 422 if missing) may still be unimplemented. Catalog documents **target** behavior. |
| Schema invariants | Runnable now: `pytest backend/tests/test_atomic_receive_p0_invariants.py` (needs `migrated_engine` / testcontainers). |

Do **not** treat 0059 samples (`mAb-2301-PK-T0`, `CAR-T-Batch-001`, aliquots)
as receive fixtures. Do **not** POST `parent_sample_id`.

---

## How Tobias binds UAT to AR-* IDs

Stable IDs in this pack are the **only** IDs Tobias should write in the
execution log. Do not remap them to legacy `TC-ACC-*` numbers.

| Bind | Where |
|------|--------|
| Scenario ID | Exact string: `AR-HV-01`, `AR-DUP-01`, … (keep hyphens and zero-padding) |
| Catalog | `UAT_Scripts/atomic-receive/scenarios.md` — one `## AR-…` section per ID |
| Payloads | `UAT_Scripts/atomic-receive/payloads.json` — top-level keys by the same ID |
| Pytest | Comments / test names in `backend/tests/test_atomic_receive_p0_invariants.py` (schema only; no receive HTTP) |

**Execution rules**

1. Copy the AR-* ID into the UAT log "Test Case ID" column verbatim.
2. High-volume `AR-HV-01` … `AR-HV-04` is **one 24-tube receive wave**. POST the
   combined bodies under `AR-HV-01.receives`. Treat HV-02/03/04 as
   overlay checklists against those same POSTs (do not replay barcodes).
3. After a successful receive, resolve the sample/test by
   **`containers.name` = scanned barcode** (e.g. `NBIO-AR-0001`).
   `samples.name` is the name-template ID (`{PROJECT}-{SEQ}` from migration
   0021) and is a **different** unique string. Never use `samples.name` as the
   barcode collision key.
4. Follow-ups (`AR-TST-*`, `AR-RES-*`, `AR-DUP-01`) use runtime placeholders
   in payloads (`<resolved:container_barcode=…>`). Substitute the UUID returned
   by receive / list-by-barcode before sending.
5. Record HTTP status against `expected_status_code` in `payloads.json`, then
   the DB checks in `scenarios.md`.

---

## Users / passwords (0058)

| Username | Password | Role | Client | Projects (0058 `project_users`) |
|----------|----------|------|--------|----------------------------------|
| `alice-tech` | `alice123` | Lab Technician | NovaBio Therapeutics | **mAb-2301 PK Study**, Project Alpha |
| `bob-tech` | `bob123` | Lab Technician | NovaBio Therapeutics | **CAR-T In-Process Testing**, Project Beta |
| `carol-manager` | `carol123` | Lab Manager | NovaBio Therapeutics | All NovaBio projects (mAb PK, CAR-T, Plasmid Lot Release Testing, Alpha, Beta) |
| `david-cro` | `david123` | Client | PharmaTest CRO | Sponsor XYZ — Bioanalytical Services (read-only) |
| `admin` | `admin123` | Administrator | System | Global (not an AR-* actor) |

P0 receive actors: **alice-tech** (NBIO-AR-\*) and **bob-tech** (CART-AR-\*).
**carol-manager** is the reviewer in `AR-MU-02` (must be ≠ enterer).

Alice must not POST `project_id` for CAR-T. Bob must not POST `project_id`
for mAb PK.

---

## Default tube

Expected P0 default container type: **Cryovial (2mL)** (`ctype-001-cryovial`
in 0058).

The current accessioning form (`frontend/src/pages/AccessioningForm.tsx`) does
**not** preselect a default-tube (`container_type_id` starts empty). No other
default-tube constant was found in code. Receive UAT should still assume
Cryovial (2mL) unless the receive UI/API later documents a different default.

Container identity on receive: `containers.name` = scanned barcode
(`NBIO-AR-0001`, …). Do not apply the container name template (`{YYMM}-{SEQ}`).

---

## Two identities (sketch)

| Entity | `name` meaning | Uniqueness |
|--------|----------------|------------|
| `containers` | Scanned barcode | `BaseModel.name` UNIQUE → replay barcode **409** |
| `samples` | Name template `{PROJECT}-{SEQ}` (0021, `seq_padding_digits=2`) | `BaseModel.name` UNIQUE, **different string** from the barcode |
| `samples.client_sample_id` | Optional external ID | Globally UNIQUE (NULL allowed; first four HV tubes use `EXT-PK-001`…`004`) |

Receive body (required): `container_barcode`, `sample_type`, `matrix`,
`project_id`. Optional: `analysis_ids`, `temperature`, `client_sample_id`.
Payloads contain **no** `name` / `lab_id` / `parent_sample_id`.

On commit: sample status **Available for Testing** (no Received hop),
`received_date` set. Optional tests land **Assigned/Pending**.
Result persist lock: typed value in `results.reported_result`; `qualifiers` is the
`<LOD` / `ND` list-entry FK; `raw_result` copies the same string. **No `unit_id`.**
Unit from `analytes.units_default`; if NULL → **422** and no row.

---

## Files

| Path | Role |
|------|------|
| `UAT_Scripts/atomic-receive/scenarios.md` | Per-ID actor, sticky fields, HTTP+DB, not-in-P0 |
| `UAT_Scripts/atomic-receive/payloads.json` | Machine-readable bodies keyed by AR-* ID (top-level) |
| `backend/tests/fixtures/atomic_receive.py` | 0058 resolvers + barcode constants (no sample inserts) |
| `backend/tests/test_atomic_receive_p0_invariants.py` | Schema invariants via `migrated_engine` |
| `backend/db/migrations/versions/0060_atomic_receive_p0_lists.py` | Idempotent Assigned/Pending + Qualifiers |

---

## Not in P0

- No aliquot UI; no `parent_sample_id` on receive payloads
- No US-31 receipt events
- No US-38 quantity
- No 0059 lifecycle samples as receive fixtures

# P0 / CORE Atomic Receive — Test Data & Scenario Catalog

Catalog + seed notes for atomic receive UAT and pytest.

**Product code (Phases 1–4):** `POST /api/samples/receive` + UI `/receive` (wizard at `/accessioning` removed; that route redirects to `/receive`).  
**Human UAT SoT:** [`../uat-atomic-receive.md`](../uat-atomic-receive.md)  
**Manual:** [manuals/HOWTO.md](../../manuals/HOWTO.md) §2 (receive). Local `.docs/manuals/atomic-receive.md` if present.

**Receive freeze:** CORE receive does **not** mint Tests. OOB UI has no analysis picker. Omit `analysis_ids` or send `[]`. Non-empty → **422**. After receive: zero Tests, zero Results. Extra barcodes = more tubes of that sample. **Asked-for** (requested analysis) is P1 on `/asked-for`, not on receive — see `uat-post-receive-work-spine.md`.

Seeded BioTech entities come from migration **0058** (clients, users, projects, lists, analyses, analytes, container types). Migration **0059** seeds lifecycle samples **with aliquots / `parent_sample_id`** — those rows are **not** receive fixtures. CORE receive uses **payloads + live receive API**.

Migration **0060** adds missing **Test Status** (`Assigned/Pending`) and **Result Qualifiers** (`<LOD`, `ND`) when needed. Assigned/Pending is for **later explicit add-test**, not for receive.

---

## How to load

Docker Compose applies Alembic on backend startup:

```bash
sudo docker compose up -d --build
```

Re-run migrations against an already-running stack:

```bash
sudo docker exec lims-backend python run_migrations.py
```

Verify actors/projects/lists:

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
```

---

## Smoke (after CORE deploy)

```bash
# UI: log in as alice-tech → sidebar Receive → /receive
# Confirm: no analysis picker. Never send analysis_ids.
# API (example shape; fill UUIDs from seed):
curl -X POST "$API/samples/receive" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "container_barcode": "NBIO-AR-SMOKE-1",
    "additional_container_barcodes": ["NBIO-AR-SMOKE-1B"],
    "sample_type": "<uuid>",
    "matrix": "<uuid>",
    "project_id": "<mAb-2301 uuid>"
  }'
```

Expect **201**, one sample, two containers, status Available for Testing, `tests: []`, **zero Test rows**, **zero Result rows**.

Non-empty `analysis_ids` must **422** and must not create a sample.

Pytest: `backend/tests/test_atomic_receive_phase1.py` … `phase3.py` (non-empty `analysis_ids` → 422; empty/omitted → 201 with `tests: []`).

See also [scenarios.md](scenarios.md) and [payloads.json](payloads.json).

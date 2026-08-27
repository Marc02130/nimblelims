# P0 / CORE Atomic Receive — Test Data & Scenario Catalog

Catalog + seed notes for atomic receive UAT and pytest.

**Product code (Phases 1–4):** `POST /api/samples/receive` + UI `/receive` on branch `feat/atomic-receive-core`.  
**Human UAT SoT:** [`../uat-atomic-receive.md`](../uat-atomic-receive.md)  
**Manual:** `.docs/review/manuals/atomic-receive.md`

Seeded BioTech entities come from migration **0058** (clients, users, projects, lists, analyses, analytes, container types). Migration **0059** seeds lifecycle samples **with aliquots / `parent_sample_id`** — those rows are **not** receive fixtures. CORE receive uses **payloads + live receive API**.

Migration **0060** adds missing **Test Status** (`Assigned/Pending`) and **Result Qualifiers** (`<LOD`, `ND`) when needed.

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
# API (example shape; fill UUIDs from seed):
curl -X POST "$API/samples/receive" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "container_barcode": "NBIO-AR-SMOKE-1",
    "additional_container_barcodes": ["NBIO-AR-SMOKE-1B"],
    "sample_type": "<uuid>",
    "matrix": "<uuid>",
    "project_id": "<mAb-2301 uuid>",
    "analysis_ids": []
  }'
```

Expect **201**, one sample, two containers, status Available for Testing.

Pytest: `backend/tests/test_atomic_receive_phase1.py` … `phase3.py`.

See also [scenarios.md](scenarios.md) and [payloads.json](payloads.json).

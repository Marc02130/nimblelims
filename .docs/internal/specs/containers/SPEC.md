# Spec: Containers

**Domain:** Containers  
**PRD:** [../../prd/containers/PRD.md](../../prd/containers/PRD.md)  
**Date:** 2026-08-26 (framework-first)  
**Framework:** [../../../decision-logs/framework-stamps-2026-08-26.md](../../../decision-logs/framework-stamps-2026-08-26.md)

---

## 0. Framework vs fixed spine

| Configurable (`config:edit`) | Fixed at runtime |
|------------------------------|------------------|
| `container_types` catalog (shape, material, capacity) | Option A amount semantics |
| Units lists | 1×1-only Contents; nesting rules |
| Active type packs in sidebar (FW-1b) | Empty-dest rule on aliquot mint; RLS |

Do not express inventory physics as an intake “profile.”

## 1. Scope

Technical contracts for container types, container instances, contents, inventory semantics, RLS, and create paths used by accessioning and aliquot execute.

## 2. Data model

### 2.1 Tables (shipped)

| Table | Role |
|-------|------|
| `container_types` | Catalog: name, capacity, material, preservative, **dimensions** (legacy free-text) |
| `containers` | Instance: type, parent, row/column, amount + unit, concentration + unit, BaseModel audit |
| `contents` | `(container_id, sample_id)` PK; optional amount/conc + units |
| `batch_containers` | Batch linkage |

**Code:** `backend/models/container.py`, `backend/models/base.py`

### 2.2 Target type shape (decided — implement lag)

| Column | Rule |
|--------|------|
| `rows`, `columns` | Integers ≥ 1 |
| `dimensions` | Remove as grid SoT |
| Single-element | `rows=1 AND columns=1` → may have Contents |
| Multi-element | Structure only → child containers, **no** Contents |

Instance `Container.row` / `Container.column` = position in parent (1-based), constrained by parent type.

### 2.3 Inventory (Option A — decided)

| Field | Meaning |
|-------|---------|
| `Contents.amount` | Solute mass or count for **that** sample in the vessel |
| `Container.amount` (1×1) | Compatible-unit sum of contents (same txn or derived) |
| `Container.concentration` (1×1) | Vessel inventory concentration |
| `Contents.concentration` | Legacy — **not** inventory SoT for new behavior |
| Volume | **Never stored**; \(V = m/C\) |

Diluent changes concentration, not solute amount.

## 3. Identity

| Field | Meaning |
|-------|---------|
| `samples.name` | System lab ID |
| `containers.name` | Scanned barcode (unique) |

Never treat them as interchangeable.

## 4. APIs (shipped)

| Method | Path | Notes |
|--------|------|-------|
| GET/POST/PATCH | `/containers/types` | Write: `config:edit` |
| GET | `/containers` | Filters: type, parent, project_ids |
| GET/POST/PATCH | `/containers/{id}` | |
| GET/POST | `/containers/{id}/contents` | |
| PATCH/DELETE | `/containers/{id}/contents/{sample_id}` | |

Permissions: `sample:create|update|read` for instances.

## 5. RLS

Migrations `0062`, `0064`:

| Command | Containers |
|---------|------------|
| INSERT | `is_admin() OR created_by = current_user_id()` |
| SELECT | admin OR creator OR contents→sample→`has_project_access` |
| UPDATE | USING project/admin; WITH CHECK allows creator |
| DELETE | admin or project via contents |

**Contents:** FORCE RLS; admin or sample project access.

App must set `created_by` on insert. Aliquot dest: container + contents in one transaction.

## 6. Create-path contracts

### 6.1 Atomic receive (target)

- Default tube type resolved server-side  
- `containers.name` = barcode → 409 on conflict  
- Contents row links sample ↔ container  
- Same DB transaction as sample (+ tests)

### 6.2 Aliquot / pool execute (shipped)

```text
INSERT dest container (created_by = actor)
INSERT contents (dest sample)
UPDATE source contents amount
COMMIT — or full rollback (no empty dest)
```

### 6.3 Empty-container product rule

Never **commit** barren tube/plate/box as an outcome. Multi-element empty wells as structure OK.

## 7. UI surfaces

| Surface | Path |
|---------|------|
| Container management | `/containers` |
| Types admin | `/admin/container-types` |
| Accessioning / receive | Intake forms |
| Batch grid | Batch container UI |
| Aliquot plan | Experiment entry editor |

## 8. Tests / UAT

- `backend/tests/test_containers_rls_sec9.py`  
- `UAT_Scripts/uat-container-management.md`  
- Security UAT TC-S11 (empty dest / FORCE)

## 9. Implement backlog (from decided locks)

1. Migrate types to `rows`/`columns`; stop using dimensions as grid  
2. Enforce Contents-only-on-1×1 in API  
3. Align Container Management with empty-container rule  
4. Decide auto-spawn children (open)  
5. Sync admin forms and manuals  

## 10. Code index

| Area | Path |
|------|------|
| Model | `backend/models/container.py` |
| Router | `backend/app/routers/containers.py` |
| Schema | `backend/app/schemas/container.py` |
| Aliquot mint | `backend/app/services/aliquot_plan_service.py` |
| RLS | `backend/db/migrations/versions/0062_*.py`, `0064_*.py` |
| UI | `frontend/src/pages/ContainerManagement.tsx`, `components/containers/*` |

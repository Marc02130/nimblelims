# UAT: UI-driven schema DDL (`ui-schema-ddl`)

**Stem:** `ui-schema-ddl`  
**Brief:** `.docs/review/requirements/ui-schema-ddl-brief.md`  
**Status:** Tobias **Pass** on product `b6d1920` (alembic **0081**). Rolf Confirm **Met**. Merge = Marc’s call.  
**Evidence:** `/workspace/uat-ui-schema-ddl-b6d1920/RESULT.md` (room stamps if the file is not on the VM).  
**Prior Fail (history):** `8c14a84` — see section below. Evidence `/workspace/uat-ui-schema-ddl-8c14a84/`.  
**Not IC50.** Do **not** merge an empty Pass/Fail table.

## Fail bars (Tobias, locked)

1. No-privilege write → **403/422**, not silent drop; not-on-layout ≠ API allow.  
2. Privilege-denied read → **refuse**, not empty-as-layout.  
3. **`schema:edit`** only for CREATE/ALTER; lab role without it cannot DDL.  
4. CREATE/ALTER proves real Postgres (`information_schema`), not JSONB-as-config.  
5. Config path writing JSONB instead of DDL/catalog rows → **Fail**.

## Logins

- Admin: `admin` / `admin123` (has `schema:edit` + `layout:edit`)
- Lab tech: `lab-tech` / `labtech123` (no `schema:edit`)

## 1. Surfaces

1. Admin → Schema: **Tables**, **Columns**, **Layouts**, **Privileges** are four distinct tabs.  
2. Asked-for and Routing map are **unchanged** (not schema-config screens).  
**Pass / Fail:** **Pass** — carried from `8c14a84` (stands).

## 2. CREATE TABLE (AC2 / Fail bar 4)

1. As Admin, Tables → Add table → display name `Lot Notes` → Create real table.  
2. Physical name starts with `x_`. Platform columns shown as fixed.  
3. Prove in DB: table exists, `client_id` column, FORCE RLS.  
**Pass / Fail:** **Pass** — restamp on `b6d1920` (blocker A cleared: `UiSchemaDdlLog.seq` IDENTITY). Fail bar (4) **Met**.

## 3. ADD COLUMN on Samples (AC1)

1. Columns → table Samples → Add field `Lab note`, type Text.  
2. Preview copy says real field, not custom-attribute JSON.  
3. Prove `information_schema` has `lab_note` on `samples`.  
**Pass / Fail:** **Pass** — restamp on `b6d1920` (blocker B cleared: `schema_apply` ALTER `samples`). Fail bar (4) **Met**.

## 4. schema:edit gate (S-UI-1 / Fail bar 3)

1. As lab-tech, open `/admin/schema/tables` (or call POST `/v1/schema/tables`).  
2. CREATE is **403**. `config:edit` alone is not enough.  
**Pass / Fail:** **Pass** — carried from `8c14a84` (stands). Fail bar (3) **Met**.

## 5. Layout membership (OQ-2)

1. Layouts → pick Lab Technician + Samples list.  
2. Add/remove fields by membership. **No hide toggle.**  
3. Save does **not** CREATE/ALTER.  
**Pass / Fail:** **Pass** — carried from `8c14a84` (stands).

## 6. Privileges default-deny (S-UI-3 / Fail bar 1)

1. Privileges → a role with access **none** on Samples extra field.  
2. API write of that extra field → **403** with readable copy, not silent drop.  
3. Saving privileges does **not** grant `schema:edit`.  
**Pass / Fail:** **Pass** — restamp on `b6d1920`. Fail bars (1) and (2) **Met**.

## 7. Deprecate vs DROP (OQ-9 / S-UI-6)

1. Deprecate the extra field — data retained.  
2. DROP without confirm → refused. DROP with confirm → audited.  
**Pass / Fail:** **Pass** — restamp on `b6d1920`.

## 8. JSONB-as-config (OQ-16 / Fail bar 5)

1. Type picker has no “JSONB config field”. List/Text/Number/etc. only.  
**Pass / Fail:** **Pass** — carried from `8c14a84` (stands). Fail bar (5) **Met**.

## Sign-off

| Role | Result | SHA |
|------|--------|-----|
| Tobias | **Pass** | `b6d1920` |
| Rolf Confirm | **Met** | `b6d1920` |
| Merge | Marc’s call | — |

### Section stamps (overall Pass on `b6d1920`)

| § | Result | Tip |
|---|--------|-----|
| 1 Surfaces | **Pass** | `8c14a84` (stands) |
| 2 CREATE TABLE | **Pass** | `b6d1920` |
| 3 ADD COLUMN | **Pass** | `b6d1920` |
| 4 schema:edit | **Pass** | `8c14a84` (stands) |
| 5 Layout membership | **Pass** | `8c14a84` (stands) |
| 6 Privileges | **Pass** | `b6d1920` |
| 7 Deprecate/DROP | **Pass** | `b6d1920` |
| 8 JSONB-as-config | **Pass** | `8c14a84` (stands) |

### Fail bars

| Bar | Result |
|-----|--------|
| (1) privilege refuse write | **Met** (`b6d1920`) |
| (2) privilege refuse read | **Met** (`b6d1920`) |
| (3) schema:edit only for DDL | **Met** (`8c14a84`) |
| (4) real Postgres proof | **Met** (`b6d1920`) |
| (5) JSONB-as-config | **Met** (`8c14a84`) |

## Tobias UAT Fail on 8c14a84 (history — superseded by re-UAT Pass on b6d1920)

| Item | Cite |
|------|------|
| Product tip UAT’d | `8c14a84` on `feat/ui-schema-ddl` |
| UAT script | `UAT_Scripts/uat-ui-schema-ddl.md` |
| Evidence | `/workspace/uat-ui-schema-ddl-8c14a84/` |
| Overall | **Fail** — no invent Pass |

### Section stamps (Tobias, history)

| § | Result |
|---|--------|
| 1 Surfaces | **Pass** |
| 2 CREATE TABLE | **Fail** — 500 `UiSchemaDdlLog.seq` NotNullViolation |
| 3 ADD COLUMN | **Fail** — 422 `schema_apply` ≠ samples owner |
| 4 schema:edit | **Pass** (lab-tech 403) |
| 5 Layout membership | **Pass** |
| 6 Privileges | **Fail** (403 not proven; blocked by §3) |
| 7 Deprecate/DROP | **Fail** |
| 8 JSONB-as-config | **Pass** |

### Fail bars (history)

| Bar | Result |
|-----|--------|
| (1) privilege refuse write | **not scored** |
| (2) privilege refuse read | **not scored** |
| (3) schema:edit only for DDL | **Met** |
| (4) real Postgres proof | **Fail** on API |
| (5) JSONB-as-config | **Met** |

### Blockers (cleared on `b6d1920`)

| ID | Blocker |
|----|---------|
| **A** | `UiSchemaDdlLog.seq` ORM NULL → CREATE TABLE **500** |
| **B** | `schema_apply` cannot ALTER `samples` → ADD COLUMN **422** |

**Status:** Grok Build fixed A+B on `b6d1920`; re-UAT Pass — see sign-off above. Compose down. Not IC50.

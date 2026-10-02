# Requirements: Schema Tables cleanup + kill Custom Fields

**Date:** 2026-10-01  
**Status:** Packet **OPEN** — Leadership locks below. UX sketch tip **`564fe6f`** (pending Accept). Implement gate **CLOSED** until Brief + Design UX Accept + Marc green-light. No product code until then (Grok Build).  
**Stem:** `ui-schema-tables-cleanup`  
**Prior packet:** `ui-schema-ddl` merged main @ `180f0c1` / cite `2074f9e` — CREATE TABLE / ADD COLUMN / layout / privileges stand.  
**Open questions:** [`.docs/review/open-questions/ui-schema-tables-cleanup.md`](../open-questions/ui-schema-tables-cleanup.md)  
**UI owner:** Mathilda (Custom Fields chrome removal; Schema Tables list).  
**Not IC50. No product code in this PR.**

## 1. Purpose

After `ui-schema-ddl`, Schema Tables only shows **samples** plus UI-created tables (e.g. Lot Notes), while **Custom Fields** still appears in the UI. This packet:

1. **Removes Custom Fields completely** — no Custom Fields UI; no JSONB / `custom_attributes` path as a substitute for real schema columns.
2. **Expands the Schema Tables list** to real **allow-listed** Postgres tables (not only samples + UI-created). **`project` is in for P1.**
3. **Relations in scope** — real Postgres FKs / junction tables (CRM/ERP/MES pattern), **not** JSONB “related ids.”

## 2. Leadership locks (cite)

| Lock | Source |
|------|--------|
| Kill custom fields completely — no Custom Fields UI; no JSONB/`custom_attributes` as schema substitute | Marc + **Rolf Confirm** 2026-10-01 |
| Schema Tables list = real allow-listed tables — not just samples + Lot Notes | Marc + **Rolf Confirm** 2026-10-01 |
| **`project` is in** for P1 Schema Tables list | Rolf 2026-10-01 |
| **Relations in scope:** 1:N = FK on many; 1:1 = unique FK on dependent; M:N = junction (two FKs + row identity) | Marc + **Rolf Confirm** 2026-10-01 |
| **M:N junctions behind the scenes** — product creates/maintains junction; operators **link/unlink** only; no junction as lab data-entry table | Marc + **Rolf Confirm** 2026-10-01 |
| Junction visibility default: **`schema:edit` only**, never operator layouts (Marc may overwrite — OQ-5e) | Rolf 2026-10-01 |
| No fake M:N arrays / JSONB related-ids | Rolf 2026-10-01 |
| No product code until Brief + Design path + Marc green-light | Rolf 2026-10-01 |
| Prior OQ-16: JSONB-as-**config** forbidden; JSONB payload/instrument **data** still allowed | `ui-schema-ddl` |
| Not IC50 | Standing |

## 3. Goals

- Remove every **Custom Fields** admin/lab surface (nav, screens, entry points) so operators cannot create or edit `custom_attributes`-style fields as schema.
- Stop treating `custom_attributes` / Custom Fields as a configuration path for samples or other entities (Fail if UI still offers it).
- Schema → **Tables** lists **allow-listed** real tables, including at minimum: **`samples`**, **`project`**, and **any UI-created** tables (existing CREATE TABLE path).
- Columns / Layouts / Privileges for newly listed tables follow existing `ui-schema-ddl` rules (`schema:edit`, membership layout, privilege R/W).
- Admin with **`schema:edit`** defines FK / 1:1 unique FK / M:N junction; operators **link records** (not redefine schema).
- Migration / cutover path for any existing Custom Fields / `custom_attributes` data is **decided in Brief** (park, migrate-to-column, or refuse) — do not invent silent JSONB-as-schema.

## 4. Non-goals (this packet)

- Reopening CREATE TABLE / Hybrid apply / FORCE RLS / privilege model from `ui-schema-ddl` (stands).
- AI proposing schema (still later).
- Arbitrary DBA console or listing every Postgres relation without allow-list.
- Indexes/FKs catalog expansion beyond prior packet.
- Product coding before Brief + Design + Marc green-light.

## 5. Acceptance criteria (draft — Brief will firm)

| ID | Criterion |
|----|-----------|
| AC1 | No Custom Fields chrome in Admin (or lab) UI — nav, pages, deep links gone or 404/redirect with no edit path. |
| AC2 | No API that creates/updates schema-like config via `custom_attributes` JSONB for allow-listed entities; such writes **403/422** (not silent accept). |
| AC3 | Schema Tables list includes **`samples`**, **`project`**, and UI-created tables; display names lab-admin friendly (Mathilda). |
| AC4 | Selecting `project` (and other P1 allow-listed tables once Decided) exercises Columns / Layout / Privileges per existing packet locks. |
| AC5 | **Tobias Fail bars (provisional until OQ-1 freezes allow-list):** (1) Custom Fields chrome/path → Fail; (2) `custom_attributes`/JSONB-as-fields → Fail; (3) Tables missing `project` (or other P1 once Decided) while in Postgres → Fail; (4) UI-created in Postgres but absent from Tables → Fail; (5) relation only in JSONB/`custom_attributes` → Fail; (6) operator junction data-entry / spreadsheet / non–`schema:edit` layout → Fail (link/unlink only). Prior privilege/`schema:edit`/DDL bars hold. |
| AC6 | Relation stored only in JSONB / `custom_attributes` (no real FK or junction) → **Fail** (Tobias bar 5). |
| AC7 | Cutover for existing Custom Fields data per Brief (no invented silent migrate). |
| AC8 | Admin can define 1:N / 1:1 / M:N per Leadership lock; operators link records; Brief decides cascade/delete + Related-list UX (OQ-5). |
| AC9 | CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (Tobias bar 7; provisional until OQ-5b freezes). |

## 6. Open questions

See living OQ doc. **OQ-1** (allow-list) waits on Marc. **OQ-5** (relations cardinality + UI + on-delete) open. Tobias will restamp Fail bars when OQ-1 closes.

## 7. Sign-off

| Review | Verdict |
|--------|---------|
| Leadership / CEO | Packet **OPEN** — locks above. Allow-list P1 beyond project pending Marc. |
| Spec (Wilhelmina) | Living fold (this doc). Implement **CLOSED**. |
| UI (Mathilda) | UX sketch tip **`564fe6f`** — **pending Accept**. Custom Fields kill + Tables (project P1) + Relations tab. |
| QA (Tobias) | Fail bars draft AC5 — script after Brief. |
| Architecture / Lab Ops / Security / Science | Await Brief + punches. |

**Implement gate:** **CLOSED** until Brief + Design UX + Marc green-light.

## Tobias Fail bars + relations fold (2026-10-01)

| Item | Cite |
|------|------|
| Fail (1) | Custom Fields chrome or create/edit path still reachable → **Fail** |
| Fail (2) | Write/read via `custom_attributes` / JSONB-as-fields → **Fail** |
| Fail (3) | Schema Tables missing `project` (or other P1 once Marc answers) while in Postgres → **Fail** |
| Fail (4) | UI-created table in Postgres but absent from Schema Tables → **Fail** |
| Fail (relations / 5) | Relation only in JSONB/`custom_attributes` → **Fail** |
| Fail (6) | Operator opens junction as lab data-entry table, creates/edits link rows as spreadsheet, or puts junction on non–`schema:edit` layout → **Fail**; link/unlink only; junction rows still real Postgres |
| Fail (7) | CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (provisional until OQ-5b freezes) |
| Research | Odoo / SAP / LIMSbase cite under OQ-5 — locks match; no reopen |
| Relations lock | 1:N FK on many; 1:1 unique FK on dependent; M:N junction (two FKs + identity); junction is a Schema Tables row; operators link; Admin `schema:edit` defines |
| Restamp | Tobias restamps when OQ-1 closes |

## M:N behind-the-scenes fold (2026-10-01; Rolf)

| Item | Cite |
|------|------|
| Lock | M:N junctions **behind the scenes**; Admin defines relation; product maintains junction table/rows |
| Operators | **Link / unlink** only — no junction lab data-entry / spreadsheet of link rows |
| Visibility default | Visible to **`schema:edit` only** (read-only metadata in Schema Tables); **never** in operator layouts — Marc may overwrite (OQ-5e) |

## Fail bar (6) + research cite fold (2026-10-01)

| Item | Cite |
|------|------|
| Fail (6) | Operator junction as lab data-entry / link-row spreadsheet / non–`schema:edit` layout → **Fail** |
| Mathilda UX | Operators link/unlink via Related list/pickers; Admin defines FK/1:1/M:N; junction metadata `schema:edit` only |
| Katinka SOP | Container/vessel + parent→aliquot = 1:N FK on child; OQ-5b lean RESTRICT on identity links |
| Research | Odoo / SAP / LIMSbase — same pattern; Leadership: keep locks; no Spec reopen |

## Fail bar (7) RESTRICT-on-identity (2026-10-01)

| Item | Cite |
|------|------|
| Fail (7) | CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → **Fail** (provisional until OQ-5b freezes) |
| Anton | Relation fixtures = real FK / real junction rows when Brief opens; seed hold until OQ-1/OQ-5 freeze |

## UX sketch cite (2026-10-01; Mathilda / Rolf Confirm Met)

| Item | Cite |
|------|------|
| UX sketch tip | `564fe6f` on `docs/ui-schema-tables-cleanup` ([PR 139](https://github.com/Marc02130/nimblelims/pull/139)) |
| Spec base | `07ccd59` (PR 138 merged) |
| File | [`.docs/review/ui-review/ui-schema-tables-cleanup.md`](../ui-review/ui-schema-tables-cleanup.md) |
| Sketch status | **Pending Accept** — no invent |
| Encoded | Custom Fields chrome kill (nav + `/admin/custom-fields` redirect; Custom Attributes blocks; results custom cols; experiment JSON dump; `custom.*` filters); Tables = Samples + Project + UI-created (OQ-1 open); Relations tab under Schema (`schema:edit`); operators Related list / link-unlink; junction metadata `schema:edit` only (OQ-5e A) |
| Still open | OQ-1 (Marc allow-list); OQ-5b (on-delete freeze) |
| Implement | **CLOSED** |

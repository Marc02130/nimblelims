# P0 Atomic Receive — Scenario Catalog

Stable IDs below are exact. Tobias binds UAT log rows and `payloads.json`
keys to these strings. High-volume `AR-HV-01`…`AR-HV-04` is **one 24-tube
wave** (no `analysis_ids` on those bodies); `AR-HV-02` is a separate **422** refuse of non-empty `analysis_ids`; `AR-HV-05` is a separate typed barcode.

**WO-7 / CORE contract:** receive does **not** mint Tests. Happy-path bodies omit
`analysis_ids` (empty `[]` also OK). Non-empty `analysis_ids` → **422**. After
success: zero Tests, zero Results. Extra barcodes = more tubes of that sample.
OOB UI has no analysis picker. Asked-for (requested analysis) is **not** on receive; see `uat-post-receive-work-spine.md`.

Live `POST /api/samples/receive` is on `feat/atomic-receive-core` (PR 71 draft).
Expected HTTP codes below are the **contract**. Hold merge until UAT + dogfood.

Lookups (0058, resolve by name at runtime — list names are slugs after 0007):

| Field | Lookup | List / table |
|-------|--------|----------------|
| sample_type | `Plasma` | `sample_types` (`lists.id` `55555555-5555-5555-5555-555555555555`) |
| matrix (alice) | `Plasma (K2EDTA)` | `matrix_types` (`66666666-…`) |
| matrix (bob) | `Cell Supernatant` | `matrix_types` |
| sample_type (bob) | `PBMC` | `sample_types` |
| project (alice) | `mAb-2301 PK Study` | `projects` (`proj-mab-pk-001` advertised) |
| project (bob) | `CAR-T In-Process Testing` | `projects` (`proj-cell-therapy-002`) |
| analysis ELISA | `ELISA (Human IgG)` | `analyses` (`analysis-elisa-001`) — **not** on CORE receive body |
| analysis viability | `Cell Viability (Trypan Blue)` | `analyses` (`analysis-viability-001`) — **not** on CORE receive body |
| analyte IgG | `IgG Concentration` | `analytes` (`analyte-igg-conc`, `units_default` = µg/mL) |
| analyte cell count | `Total Cell Count` | `analytes` (`analyte-cell-count`, `units_default` NULL) |
| sample status | `Available for Testing` | `sample_status` (`11111111-…`) |
| test status | `Assigned/Pending` | `test_status` (`22222222-…`, seeded by **0060**) — used only after explicit add-test |
| qualifiers | `<LOD`, `ND` | `Result Qualifiers` (seeded by **0060**) |
| default tube | `Cryovial (2mL)` | `container_types` (`ctype-001-cryovial`) |

Default tube: Cryovial (2mL). Receive UI does not preselect a tube and does not offer analyses.

---

## AR-HV-01

**Title:** High-volume receive — 24 unique barcodes

| | |
|--|--|
| **Actor** | `alice-tech` / `alice123` |
| **Project** | `mAb-2301 PK Study` only (not CAR-T, not Bob's `project_id`) |
| **Sticky fields** | `sample_type` = Plasma; `matrix` = Plasma (K2EDTA); `project_id` = mAb-2301 PK Study |
| **Barcodes** | `NBIO-AR-0001` … `NBIO-AR-0024` (24 unique). Payload refs: `payloads.json` → `scenarios.AR-HV-01.requests` (combined wave including HV-03/04 overlays). **Omit `analysis_ids`.** |
| **Expected HTTP** | `201` per barcode |
| **Expected DB** | 24 `containers` rows with `name` = barcode, type Cryovial (2mL); 24 `samples` linked via `contents`; `samples.name` from template `{PROJECT}-{SEQ}` and **≠** barcode; `parent_sample_id` NULL; `status` = Available for Testing; `received_date` NOT NULL; **zero `tests` rows; zero `results` rows**. |
| **Not in P0** | No aliquot UI; no US-31 receipt events; no US-38 qty. Do not insert 0059 samples. Do not send non-empty `analysis_ids`. |

---

## AR-HV-02

**Title:** Non-empty `analysis_ids` → 422 (WO-7 refuse; do not mint Tests)

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same as AR-HV-01 |
| **Barcodes / payload refs** | Dedicated barcode `NBIO-AR-REFUSE-0001`. Body includes `analysis_ids` = `[analysis-elisa-001]` (`payloads.json` → `AR-HV-02`). Do **not** overlay this on the HV-01 wave. Empty/`[]` path is AR-HV-01. UI never sends `analysis_ids`. |
| **Expected HTTP** | **422**. Do not ignore. Do not mint Tests. |
| **Expected DB** | Zero sample, container, contents, tests, and results for `NBIO-AR-REFUSE-0001`. |
| **Not in P0** | Asked-for is **not** on receive. Do not auto-assign batteries. |

---

## AR-HV-03

**Title:** Temperature omitted on even barcodes; 4.0 on odd

| | |
|--|--|
| **Actor** | `alice-tech` (same wave) |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same as AR-HV-01 |
| **Barcodes / payload refs** | Odd (`NBIO-AR-0001`, `0003`, … `0023`): `"temperature": 4.0`. Even (`0002`, `0004`, … `0024`): **omit** `temperature` (do not send null unless the schema treats omit/null the same). Overlay on AR-HV-01. |
| **Expected HTTP** | `201` |
| **Expected DB** | Odd samples: `samples.temperature` = 4.0. Even: `samples.temperature` IS NULL. Still zero Tests. |
| **Not in P0** | No required-temperature gate. No US-38 qty. |

---

## AR-HV-04

**Title:** `client_sample_id` on first four tubes only

| | |
|--|--|
| **Actor** | `alice-tech` (same wave) |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same as AR-HV-01 |
| **Barcodes / payload refs** | `NBIO-AR-0001`→`EXT-PK-001`, `0002`→`EXT-PK-002`, `0003`→`EXT-PK-003`, `0004`→`EXT-PK-004`. Omit `client_sample_id` on `0005`–`0024`. IDs are **globally unique** (`samples.client_sample_id` UNIQUE). Overlay on AR-HV-01. |
| **Expected HTTP** | `201`. Replaying an `EXT-PK-*` on another tube → unique-violation / 409 (not a separate AR-* ID). |
| **Expected DB** | Four rows with those `client_sample_id` values; remaining 20 have NULL. Zero Tests. |
| **Not in P0** | No per-project uniqueness (constraint is global). |

---


## AR-HV-05

**Title:** Keyboard fallback — type barcode (no scanner)

| | |
|--|--|
| **Actor** | `alice-tech` / `alice123` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same as AR-HV-01 (Plasma / Plasma (K2EDTA) / mAb-2301 PK Study) |
| **Barcodes / payload refs** | `NBIO-AR-KB-0001` — typed into `container_barcode`. Same POST as a scan. Must not collide with `NBIO-AR-0001`…`0024`. Omit `analysis_ids`. |
| **Expected HTTP** | `201` |
| **Expected DB** | Same as first HV tube: `containers.name` = typed barcode, `samples.name` from template, Available for Testing, `parent_sample_id` NULL, zero Tests. |
| **Not in P0** | No separate keyboard API. HID scan vs typing is UI-only; body is identical. |

---


## AR-VAL-01

**Title:** Missing required barcode / type / matrix / project → 422

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | n/a (each request omits one required field) |
| **Barcodes / payload refs** | `payloads.json` → `scenarios.AR-VAL-01.requests` (four bodies) |
| **Expected HTTP** | `422` for each. No partial create. |
| **Expected DB** | Zero new `samples`, `containers`, `contents`, `tests`. |
| **Not in P0** | Do not implement the endpoint in this pack. |

---

## AR-DUP-01

**Title:** Replay barcode `NBIO-AR-0001` → 409 on `containers.name`

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same receive body as `NBIO-AR-0001` in the HV wave (Plasma / Plasma (K2EDTA) / temp 4.0 / `EXT-PK-001`). **No `analysis_ids`.** |
| **Barcodes / payload refs** | Replay `NBIO-AR-0001`. `payloads.json` → `AR-DUP-01`. |
| **Expected HTTP** | **409**. Collision key is **`containers.name`** (scanned barcode). |
| **Expected DB** | Still exactly one container `NBIO-AR-0001`. **`samples.name` is not the collision key** — the template ID is a different unique string (`{PROJECT}-{SEQ}`), so a unique violation on `samples.name` would mean the implementation wrote the barcode into `samples.name` (fail). No second sample row. |
| **Not in P0** | No merge-into-existing-container. No barcode reuse across projects. |

---

## AR-ID-01

**Title:** Receive payloads have no sample name / lab_id; `samples.name` comes from the template

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same as HV wave |
| **Barcodes / payload refs** | Any successful HV tube (use `NBIO-AR-0001`). Body must **not** contain `name`, `sample_name`, `lab_id`, or non-empty `analysis_ids`. |
| **Expected HTTP** | `201` on first receive of that barcode |
| **Expected DB** | `samples.name` is generated from active sample template `{PROJECT}-{SEQ}` (0021, padding 2) using project name `mAb-2301 PK Study` → e.g. `mAb-2301 PK Study-01` (project name is substituted raw, not slugified). **`samples.name` ≠ `containers.name`** ≠ barcode. |
| **Not in P0** | Client-supplied sample name is rejected/ignored; do not add a name field to the receive body. |

---

## AR-ST-01

**Title:** After success, sample status is Available for Testing; `received_date` not null

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Same as HV wave |
| **Barcodes / payload refs** | Any successful HV tube. `payloads.json` → `AR-ST-01` (DB assertions; no extra POST). |
| **Expected HTTP** | `201` on receive |
| **Expected DB** | `samples.status` → list_entry **Available for Testing** (`sample_status`). `received_date` IS NOT NULL. **No Received hop** — do not write status Received then transition. Zero Tests. |
| **Not in P0** | No US-31 receipt event row. Status list still contains `Received` (0004) for legacy accessioning; P0 receive must not use it. |

---

## AR-TST-01

**Title:** Add ELISA to a sample received with no tests (`NBIO-AR-0009`)

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Sample already received in HV wave with omitted/`[]` `analysis_ids` (zero Tests at receive) |
| **Barcodes / payload refs** | `NBIO-AR-0009`. Resolve `sample_id` via `containers.name`. POST `/tests/` or `/tests/assign` with ELISA (`analysis-elisa-001`). `payloads.json` → `AR-TST-01`. |
| **Expected HTTP** | `201` |
| **Expected DB** | Immediately after receive: **zero tests**. After this POST: one new `tests` row, `analysis` = ELISA (Human IgG), status **Assigned** or **Pending**, `sample_id` = the NBIO-AR-0009 sample. No results until a later results POST. |
| **Not in P0** | Do not use 0059 samples. Do not set `parent_sample_id`. Do not mint this test at receive. |

---

## AR-TST-02

**Title:** Remove the AR-TST-01 test while it has no results

| | |
|--|--|
| **Actor** | `alice-tech` |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | Test from AR-TST-01 (ELISA on `NBIO-AR-0009`, zero results) |
| **Barcodes / payload refs** | DELETE `/tests/{id}` for that test. `payloads.json` → `AR-TST-02`. |
| **Expected HTTP** | `200` (current delete) or `204`. Must **not** be 400 (no results yet). |
| **Expected DB** | Test gone or `active = false`. Sample remains Available for Testing. Container `NBIO-AR-0009` unchanged. |
| **Not in P0** | No cascade delete of the sample. |

---

## AR-TST-03

**Title:** After a result exists on `NBIO-AR-0001` ELISA, DELETE must 400

| | |
|--|--|
| **Actor** | `alice-tech` (enter result); DELETE as same tech is enough |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | After HV receive of `NBIO-AR-0001` (zero Tests), **explicitly add** ELISA, then enter a result |
| **Barcodes / payload refs** | 1) POST `/tests/` ELISA on `NBIO-AR-0001`. 2) POST `/results/` on that ELISA test (IgG Concentration). 3) DELETE `/tests/{id}`. `payloads.json` → `AR-TST-03`. |
| **Expected HTTP** | Test create `201`. Result create `201`. DELETE **`400`** (test has results). |
| **Expected DB** | Test still active; result still present. Current main DELETE soft-deletes even with results — **P0 contract is 400**; treat a 200 delete as a product gap, not a pass. |
| **Not in P0** | No force-delete flag. ELISA was not created at receive. |

---

## AR-RES-01

**Title:** Enter raw + qualifier `<LOD` on IgG Concentration (has `units_default`)

| | |
|--|--|
| **Actor** | `alice-tech` (`result:enter`) |
| **Project** | mAb-2301 PK Study |
| **Sticky fields** | ELISA test **explicitly added** on `NBIO-AR-0001` after receive; analyte `IgG Concentration` (`analyte-igg-conc`) |
| **Barcodes / payload refs** | POST `/results/` with `raw_result` plus qualifier `<LOD` (0060 `qualifiers` list). Do **not** send a unit — unit comes from `analytes.units_default` (µg/mL). `payloads.json` → `AR-RES-01`. May share the result row with AR-TST-03; run RES-01 before TST-03 DELETE, or use a distinct replicate. |
| **Expected HTTP** | `201` |
| **Expected DB** | `results.raw_result` set; `results.qualifiers` → list_entry `<LOD`; unit applied from `units_default` (µg/mL), not from the payload. `entered_by` = alice. |
| **Not in P0** | No client-supplied unit override. Not a CORE receive blocker. |

---

## AR-RES-02

**Title:** Result for Cell Viability / Total Cell Count (`units_default` NULL) → 422

| | |
|--|--|
| **Actor** | `bob-tech` (CAR-T project) |
| **Project** | `CAR-T In-Process Testing` |
| **Sticky fields** | Sample type PBMC; matrix Cell Supernatant. Analysis Cell Viability (Trypan Blue) is **added after receive**. Analyte **Total Cell Count** (`analyte-cell-count`, `units_default` NULL). Identity-pass and A260/280 also have NULL units — this scenario is specifically Total Cell Count. |
| **Barcodes / payload refs** | Receive `CART-AR-0001` **without** `analysis_ids` (or `[]`). Then POST `/tests/` with `analysis-viability-001`. Then POST `/results/` for Total Cell Count. `payloads.json` → `AR-RES-02`. |
| **Expected HTTP** | Receive `201` with zero Tests. Test add `201`. Result **422**. Result unit is required from `analytes.units_default`; missing → 422. Do not invent a unit in the payload to bypass. |
| **Expected DB** | After receive: zero tests/results. After add-test: one viability test. After result POST: no `results` row for that analyte. Test remains Assigned/Pending. |
| **Not in P0** | No per-result unit picker. Do not use 0059 `CAR-T-Batch-001` / blank QC (those are parent/QC fixtures, not receive). Not a CORE receive blocker. |

---


## AR-RBAC-01

**Title:** Client cannot receive

| | |
|--|--|
| **Actor** | `david-cro` / `david123` (Client, PharmaTest CRO) |
| **Project** | n/a — client must not reach receive |
| **Sticky fields** | Body uses alice sticky fields only to prove the POST is refused |
| **Barcodes / payload refs** | `NBIO-AR-CLIENT-0001` in `AR-RBAC-01` |
| **Expected HTTP** | **403** (401 fail-closed also acceptable). No receive UI for client. |
| **Expected DB** | No sample or container row. |
| **Not in P0** | Do not grant client a receive role to make the case pass. AuthZ remains PR 68. |

---

## AR-MU-01

**Title:** Alice and Bob isolated by project_id

| | |
|--|--|
| **Actor** | `alice-tech` AND `bob-tech` |
| **Project** | Alice: **mAb-2301 PK Study** only. Bob: **CAR-T In-Process Testing** only. |
| **Sticky fields** | Alice: Plasma + Plasma (K2EDTA), barcodes `NBIO-AR-*` (HV wave). Bob: **PBMC** + **Cell Supernatant**, barcodes `CART-AR-0001`…`CART-AR-0008`. Omit `analysis_ids`. |
| **Barcodes / payload refs** | Alice bodies = AR-HV-01 wave. Bob bodies = `AR-MU-01` CART requests. Negative: Alice POST with Bob's `project_id` / Bob POST with Alice's `project_id`. |
| **Expected HTTP** | Happy path `201` for each actor on their own project. Cross-project `403` (or 404 under RLS). Each actor **must not** send the other's `project_id`. |
| **Expected DB** | `project_users`: alice has `proj-mab-pk-001` (+ Alpha alias), **not** `proj-cell-therapy-002`. Bob has CAR-T (+ Beta alias), **not** mAb PK. CART containers named `CART-AR-0001`…`0008`. No cross-project `contents`. Zero Tests at receive. |
| **Not in P0** | No tenant flag beyond `project_users` + RLS. Keep PR 68 AuthZ locks. |

---

## AR-MU-02

**Title:** (PARKED — not P0 must-pass) carol-manager reviews a result entered by alice-tech

| | |
|--|--|
| **Actor** | Enterer: `alice-tech`. Reviewer: `carol-manager` / `carol123`. |
| **Project** | mAb-2301 PK Study (Carol has all NovaBio projects) |
| **Sticky fields** | Result on `NBIO-AR-0001` ELISA / IgG from AR-RES-01 (or AR-TST-03 setup). |
| **Barcodes / payload refs** | PATCH `/tests/{id}/review` as carol (existing review endpoint). `payloads.json` → `AR-MU-02`. |
| **Expected HTTP** | `200`. Reviewer identity ≠ `results.entered_by`. |
| **Expected DB** | `tests.review_date` set; `modified_by` = carol. `results.entered_by` remains alice. **No tenant flag for second-person review exists in schema yet** — there is no `clients.require_second_person_review`, `projects.require_second_review`, or similar column. Enforcement is UAT/procedural only (Carol must not be the enterer). Do not fail the schema invariant pytest for a missing flag; document the gap. |
| **Not in P0** | No workflow engine for review. No reject-own-result API unless already present. |

---

## Not in P0

Out of scope for this pack and for the atomic-receive feature PR:

- **No aliquot UI** and **no `parent_sample_id`** on receive payloads or P0 fixtures. Migration 0059 already seeds parent/child samples (`mAb-2301-PK-T0` → `mAb-2301-PK-T0-Aliq`); do not reuse them as receive tubes.
- **No US-31 receipt events** (no event table write on receive).
- **No US-38 quantity** (no required amount/concentration on the receive body).
- No Received status hop.
- **No Tests at receive** / no analysis picker. Requested analysis is `/asked-for` (P1 lake), not receive and not a Test.
- **AR-MU-02** (US-10 second-person review) is out of P0 receive must-pass. Q1 parallel. Distinct enterer/reviewer users remain in 0058 seed.
- No second-person-review tenant flag.
- IC50 / dose-response / parsers / ELN.

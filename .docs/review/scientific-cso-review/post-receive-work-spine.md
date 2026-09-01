# Scientific CSO Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** Accept with conditions  
**Reviewer persona:** Chief Scientific Officer  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Packet:**  
- Requirements: [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
- Schema: [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
- PRD: [`.docs/internal/prd/post-receive-work-spine/PRD.md`](../../internal/prd/post-receive-work-spine/PRD.md)  
- Spec: [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
- Open questions: [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
**Related Lab Ops:** [lab-ops-review/post-receive-work-spine.md](../lab-ops-review/post-receive-work-spine.md) — ordered-route L2/L4 locked; dest-follow Met; P2 on `main` `5040f2d` with **OQ-WO-7 OPEN**
**Related:**  
- Framework stamps WO-1…WO-7, FW-0/FW-2: [`.docs/decision-logs/framework-stamps-2026-08-26.md`](../../decision-logs/framework-stamps-2026-08-26.md)  
- Promote-on-publish: [open-questions/run-results.md](../open-questions/run-results.md) (Decision #2 `raw_result`; Decision #7 ensure-on-publish **superseded by WO-7**)  
- Dest-type Hold: [open-questions/sop-ai-to-process.md](../open-questions/sop-ai-to-process.md) · [extract-then-qubit testdata gap](../open-questions/extract-then-qubit-testdata-gap.md)

---

## 1. Executive summary

This packet is the scientific middle of the LIMS: **what was asked**, **what the lab must run**, **what number is official**. Receive already registers identity + vessels and correctly mints **zero Tests**. That is accessioning, not an assay.

The spine is scientifically right and must not collapse:

| Layer | Scientific object | Must not become |
|-------|-------------------|-----------------|
| Asked-for (P1) | Request: analysis + TAT + assay params | A Test, a result, or a work plan |
| Routing + `work_order` (P2) | Analysis + TAT → ordered `process_definition[]`; first-process type gate | A Test row, an unordered bag, an admin-authored type, or a chain-wide gate |
| Test (WO-7) | Assay **instance** at LimsRun start, with frozen params | Minted at receive / asked-for / WO save / publish |
| Result (P3) | Reportable analyte value + unit + optional qualifier + replicate | A unit picker, a JSON blob in `qualifiers`, or a number typed into asked-for |
| SOP Apply (P4) | Process definition with typed experiment / LimsRun steps | Blood → DNA → Qubit E2E (still Hold) |

**OQ-RES-1 is Decided here.** The proposal to store `qualifiers` as JSON `{"entered_as": "<string>"}` is scientifically wrong and would break the live column. `results.qualifiers` is already a UUID FK to **Result Qualifiers** (`<LOD`, `ND`). That list is the controlled vocabulary for censored / special results. The typed token belongs in `reported_result`. See §3 SC1 and §6.

**Qubit-on-blood must refuse.** If Qubit is the first Experiment/LimsRun in the first process, Route refuses blood before mint. If Qubit is in a later process/step, that later start refuses until dest-type execute actually minted or selected DNA. Map save does not chain-AND the ordered route. Extract-first and Qubit-first for the same TAT may both exist. Do not invent testdata IDs.

**Params must travel and freeze (L3).** Cell line / dilution / assay params that die at the bench are a side process. Snapshot onto the Test at LimsRun start. Schema currently says `tests: none` — that is not enough (SC5).

**Units stay on the analyte.** `analytes.units_default` required for numeric quantity persist; missing → **422**; no `results.unit_id`. A scientist reinterpreting “12.3” later must not guess ng/mL vs µg/mL.

**Verdict: Accept with conditions.** P1 is scientifically implementable (empty param defs OOB is honest). P3 coding is **closed** until SC1–SC4 are folded into RQ-RES-1 / AC-P3-1 / the sketch (OQ-RES-1 no longer Open). P2 carries SC5 with Lab Ops L2–L4. P4/P5 do not reopen dest-type or IC50.

---

## 2. Scientific fit assessment

| Dimension | Score (0–10) | Notes |
|-----------|--------------|--------|
| **Scientific completeness** | **7** | Asked-for + param defs + WO-7 Test + persist lock is the minimum ELISA/plasma story. Qubit/dsDNA HS is named but correctly Hold. Empty OOB param defs is acceptable for P1; ELISA `cell_line` as list-backed example is the right shape. Schema omits where frozen params land on Test (SC5). |
| **Result integrity** | **5 → 8 if SC1–SC4 land** | Today: `reported_result`/`raw_result` are strings; `qualifiers` is a list FK; **no unit on the result row**; create_result does **not** enforce `units_default`; promote writes **`raw_result` only** (Decision #2), leaving `reported_result` null after publish. Packet RQ-RES-1 (“typed number lands in reported_result **and** qualifiers”) collides with the FK. JSON `entered_as` would destroy LOD/ND. Fix is the persist lock in SC1–SC4, not a new column `unit_id`. |
| **QC support** | **4** | Out of P3 scope (persist lock, not a QC product). `analysis_analytes` already has high/low/sig-figs; `result:review` exists. No controls, acceptance criteria, or CoA freeze in this packet — acceptable for a persist lock if we do not pretend otherwise. |
| **Metadata sufficiency** | **6** | Params catalog + snapshot is the reproducibility joint (FW-0 “params travel”). Without a frozen Test payload, “IgG 12.3 µg/mL” has no cell line / dilution. Replicate column exists (Decision #14). `entered_by` / `entry_date` exist. Instrument SoT remains `lims_run_data` for promote. |
| **Data-integrity habits** | **7** | Two writers → 409; publish refuses missing Test (WO-7); cancel-before-reroute; map-save 409 only on TAT **and** first-step allow-list overlap; human SOP Apply. Persist must not float-roundtrip the typed token (sig figs). Review-lock of final results is **not** this slice. |
| **Practicality for startups/CROs** | **8** | No enterprise result-amendment workflow. Classic type-a-number stays (WO-4). Empty param defs OOB. One persist function. No unit picker. Do not invent a second qualifier JSON overlay. |
| **Alignment with Lab Ops** | **8** | L1 keeps asked-for distinct from work. L2 derives the first-step Route gate and keeps later gates at step start. L3 params travel is the CSO bar. L4 ordered process steps are the work plan. L5 dest-type Hold is unchanged. |

**Overall scientific readiness:** **7/10** for the spine with conditions. **P1 is implementable.** **P3 is not**, until OQ-RES-1 / RQ-RES-1 / AC-P3-1 match the live result columns.

---

## 3. Conditions (must land with the named phase)

| ID | Phase | Condition | Why |
|----|-------|-----------|-----|
| **SC1** | **P3** | **`qualifiers` stay list-backed. Typed number does not land in `qualifiers`.** Keep `results.qualifiers` as nullable UUID FK → Result Qualifiers (`<LOD`, `ND`, …). Do **not** migrate it to JSON. Do **not** store `{"entered_as": …}` there. Persist lock: typed token → `reported_result`; `raw_result` **may** copy the same token on the manual path; `qualifiers` = optional list entry (**NULL** for a clean number such as `12.3`). No `results.unit_id`. Restate **RQ-RES-1** and **AC-P3-1** before P3 coding: AC-P3-1 must **not** require qualifiers to be “set” for `12.3`. AR-RES-01 already has the right shape (`reported_result="<0.05"`, `qualifiers=<LOD` UUID, no `unit_id`). | Qualifier means LOD/ND/BQL in every regulated lab. JSON in that column 500s the FK, breaks 0060 seed, and makes CoA flags unqueryable. `reported_result` **is** entered-as. |
| **SC2** | **P3** | **Persist the typed token as-is.** `persist_typed_result` stores the trimmed string the operator typed. Validate numeric parse **without** writing `str(float(value))` (that drops trailing zeros / changes `12.30`). Censored forms (`<0.05`, `>100`, `ND`) are **valid** when a Result Qualifier is present — do not 422 them because `float()` failed. Clean numeric with no qualifier must parse as a number for `data_type=numeric`. Replicate identity is preserved (default 1). | Significant figures and censoring are the result. Float roundtrip is a silent scientific mutation. Batch entry today already `float()`-rejects `<0.05`; persist lock must not copy that bug. |
| **SC3** | **P3** | **`units_default` 422 is for numeric quantities, not every analyte.** If `analyte.data_type` (or analysis_analyte `data_type`) is **numeric** and `units_default` is null → **422**, no row. **Text / boolean** analytes (Identity Result) may have null units. **Dimensionless numeric** (A260/A280) must get a catalog unit (`ratio` / `AU` / dimensionless) — do not 422-loop a valid assay, and do not leave a null hole. Total Cell Count remaining NULL is a **catalog defect**; 422 until `cells/mL` (or equivalent) is set is correct. No unit picker; no silent conversion. | “12.3” without a unit is not a result. Pass/Fail is not a concentration. Ratios need an explicit dimensionless unit so reports do not invent µg/mL. |
| **SC4** | **P3** | **The reportable ledger is `reported_result`.** Manual persist writes it (SC1). Promote-on-publish must also leave `reported_result` populated: copy `raw_result` → `reported_result` unless a later censoring rule applies. Instrument SoT remains `lims_run_data` (Decision #5). Two writers on the same Test (classic vs LimsRun publish) → **409**. Promote still must **not** ensure-on-publish a missing Test (WO-7). | Decision #2 filled `raw_result` only; published ELISA/Qubit rows then show an empty reported value. Lab Ops bench bar: the number typed or promoted is what review/publish shows. |
| **SC5** | **P2** | **Frozen params on the Test.** At LimsRun start, snapshot asked-for `params` onto the Test and **freeze**. Storage is a dedicated payload (preferred: `tests.asked_for_params` JSONB, nullable), **not** merged into editable Field Management `tests.custom_attributes`. Later asked-for edits do not mutate a started Test. Empty defs remain `{}` only (OQ-AF-3). Schema “`tests: none`” is insufficient — P2 schema delta must name this column. Aligns Lab Ops **L3**. | Assay params are scientific context for the result. Cell line on the order that never reaches the Test cannot be reconstructed at review. |

Already normative (restated so P3 does not drop them): no `results.unit_id`; missing numeric `units_default` → 422; results persist only on an existing Test; P3 does not mint Tests at asked-for or receive; client cannot write results they cannot see; P4 does not close dest-type Hold (**L5**); Qubit started while current type is blood refuses (**L2**) — Qubit dsDNA HS is not a whole-blood assay.

---

## 4. Risks / watch items (non-blocking)

1. **`(sample_id, analysis_id)` uniqueness vs real param defs.** Two ELISA requests with different cell lines cannot coexist. Fine for P1 empty-params. When required param defs ship, either uniqueness includes param identity or the product rule is “one open asked-for; PATCH params while `requested`; cancel to change condition.” Do not silently overwrite params on a `routed` row.
2. **Qualifier catalog is thin.** 0060 has `<LOD` and `ND` only. Pharma/CRO CoAs commonly need `<LOQ`, `>ULOQ`, BQL/BLOQ. Do not block P3; seed when a named assay needs them. Do not free-text those flags.
3. **P3 is not QC.** No controls, Westgard, or acceptance criteria in this packet. `analysis_analytes` high/low/sig-figs stay unused by persist lock. A later QC slice; do not type numbers into asked-for in the meantime.
4. **Promote vs WO-7.** Run-results Decision #7 (ensure Test on publish) is **superseded** by WO-7. P2/P3 must remove find-or-create on publish. CSO agrees: a result without a Test instance is not an assay instance.
5. **Classic Tests page still mints Tests** (Lab Ops risk 1). Scientific SoT for the number is still the Result row; the order path must be Asked-for. Do not delete classic type-a-number (WO-4).
6. **Catalog gap for NCI 23113 → 22975 remains.** No whole-blood intake, no DNA daughter, no Qubit analysis in 0058/0059. Do not invent those IDs. Dest-type Hold is a different packet.
7. **Parser expected-output tests (P5).** Dry-run should assert analyte identity + value (unit implied by analyte), not merely “rows parsed.” Not a P1/P3 gate.
8. **Duplicate qualifier lists.** 0046 seeded `result_qualifiers`; 0060 seeded `Result Qualifiers`. P3 must bind persist to the list AR-RES-01 uses (`<LOD`, `ND`). Arch/BA cleanup, not a scientific redesign.

---

## 5. Stance on open questions

| ID | Stance |
|----|--------|
| **OQ-RES-1** (qualifiers shape) | **Decided.** See §6. Typed token → `reported_result`; `qualifiers` remains Result Qualifiers list FK; no JSON overlay; no `entered_as` in that column. |
| **OQ-AF-3** (empty param defs) | Agree provisional. Table ships; OOB may be empty; unknown keys 422. Empty `{}` is not scientific context — it is an honest empty catalog. |
| **OQ-WO-1** | Decided: explicit Route with zero→422 / multiple→409. |
| **OQ-WO-3** | Decided: ordered process instances carry WO route position. |
| **OQ-SOP-2** (inactive parser draft) | Accept inactive, unbound. Never auto-bind to production runs (would silently remap analytes). |

---

## 6. OQ-RES-1 decision (qualifiers shape)

**Status:** **Decided**  
**Date:** 2026-08-28  
**Owner:** Scientific CSO  
**Blocks:** P3 (now unblocked on the question; SC1–SC4 still must fold into reqs/sketch)

### Live columns (do not reinvent)

| Column | Type today | Scientific role |
|--------------------|-----------------|
| `reported_result` | `String(255)` | **Reportable value** — the token review / publish / CoA shows |
| `raw_result` | `String(255)` | Instrument / typed raw; promote fills this today (Decision #2); manual path **may** copy the typed token |
| `qualifiers` | UUID FK → `list_entries` (Result Qualifiers: `<LOD`, `ND`) | Controlled **flag** for censored / special results. Nullable. |
| Unit | `analytes.units_default` only | No `results.unit_id` |

### Persist lock (normative)

1. Operator types a value on an **existing** Test (WO-7 / classic Test).  
2. Trimmed token → `reported_result`.  
3. `raw_result` may copy the same token on the manual path.  
4. If the operator selects (or the token maps to) `<LOD` / `ND` / later catalog flags → set `qualifiers` to that list_entry. Clean number → `qualifiers` **NULL**.  
5. Resolve unit from `analytes.units_default` (SC3). Missing on a numeric quantity → **422**, no row.  
6. Do **not** add `results.unit_id`. Do **not** change `qualifiers` to JSONB.  
7. `entered_as` is **redundant**: `reported_result` is the entered token. If a later phase needs parse metadata (locale, original bytes), use `custom_attributes` or a new column — **never** overwrite the qualifier list.

### Rejected proposal

`qualifiers: {"entered_as": "<string>"}` — type collision with the UUID FK; destroys LOD/ND; contradicts AR-RES-01; makes flags unqueryable.

### Requirements fold (P3, same phase as persist lock)

- **RQ-RES-1** → Typed numeric (or censored) token lands in `results.reported_result`. `results.qualifiers` is the optional Result Qualifiers list FK. `raw_result` may copy the token.  
- **AC-P3-1** → Type `12.3` with `units_default` set → `reported_result='12.3'`, `qualifiers` NULL, unit from analyte.  
- **AC-P3-2** unchanged in spirit: missing numeric `units_default` → 422, no row (subject to SC3 exemptions).

---

## 7. Locked for this packet (do not reopen)

- Asked-for ≠ Test ≠ work_order ≠ Result. No numbers on asked-for.  
- Test at **LimsRun start** only (WO-7). Publish refuses if missing.  
- Params snapshot at LimsRun start and freeze (L3 / SC5).  
- Qubit-first on blood refuses at Route; later Qubit on unchanged blood refuses at step start (L2). Map authoring has no sample-type picker. Extract-first vs Qubit-first for the same TAT may both exist. Dest-type Hold is a **different** packet.
- No `results.unit_id`. Unit from analyte default.  
- `qualifiers` remain list-backed. No JSON overlay.  
- Two writers on the same Test → 409.  
- SOP Apply: process definition; never silent auto-activate; not IC50; no SOP PDF bodies in git.  
- Parser production import: no LLM.  
- Named NCI extract → Qubit E2E remains Hold.

---

## 8. Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (SC1–SC5) |
| **Date** | 2026-08-28 |
| **Implement relevance** | **OPEN for P1 only** (scientific gate) |
| **P1** | **OPEN** — empty param defs OOB is scientifically honest; no result rows; L1 copy is the WO-7 guard |
| **P2** | **CLOSED** until Lab Ops L2–L4 **and SC5** are in the sketch/schema (type eligibility; params freeze column; dest mint ≠ `sample_type_transitions`) |
| **P3** | **CLOSED** until SC1–SC4 are folded into RQ-RES-1 / AC-P3-1 / tech sketch §5. **OQ-RES-1 is Decided** (no longer the open gate). Not licensed as “type results on asked-for.” |
| **P4** | Apply → process definition **may** proceed with Lab Ops **L5**. Dest-type Hold **unchanged**. Not IC50. |
| **P5** | **OPEN** (admin UX). Parser tests should assert analyte + value (watch item 7). |
| **Not licensed by this stamp** | Extract-hold dest type · blood → DNA → Qubit E2E · Qubit/blood testdata IDs · `results.unit_id` · JSON `qualifiers` · QC/acceptance product · compound/lots · IC50 / dose-response |

```
SCIENTIFIC CSO REVIEW: Accept with conditions (SC1–SC5)
IMPLEMENT RELEVANCE: OPEN (P1 only)
OQ-RES-1: Decided
```

---

## 9. Science fold — P2 merge with OQ-WO-7 OPEN — 2026-09-01

**Not a restamp of the 2026-08-28 Accept.** Does **not** rewrite SC1–SC5, OQ-RES-1, or Tobias Results on `bf51b19`. Not IC50.

**Science:** Per-AC on `bf51b19` **Pass**. **Overall P2 stayed unsigned.** We merged (`5040f2d`, feat tip `4b8c41f`) with **OQ-WO-7 OPEN**: **WGS params on the DNA Test from the WO after C3**. **That click never landed.** Leftover `9f86d14` is not a UAT click and is not on `main`.

Clarifying the issue made the product better. Assay params are scientific context for the result (SC5). After Blood→DNA, the WGS Test on the DNA tube must freeze the **work order’s** WGS params (`{library_kit: …}`), **not** `{}`, **not** Qubit / process-QC params. Lookup by dest `sample_id` is the wrong cohort.

Land OQ-WO-7 as **Brief → code → UAT with Pass/Fail and not-a-Fail → stamp → merge**. Do not close the OQ from leftover unmerged code. Do not invent overall P2 Pass.

| Field | Value |
|-------|--------|
| **OQ-WO-7** | **OPEN** |
| **Grain** | WGS params on the DNA Test from the WO after C3 |
| **Merge** | `5040f2d` with this OPEN. Click never landed |
| **Process** | Brief → code → UAT (Pass/Fail and not-a-Fail) → stamp → merge |

```
SCIENTIFIC CSO: OQ-WO-7 OPEN
P2 MERGE: 5040f2d with OQ-WO-7 OPEN
CLICK: never landed
```

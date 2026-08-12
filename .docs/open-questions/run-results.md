# Open Questions — LimsRun → Results

**Status:** Living decision log  
**Idea:** [`.docs/ideas/run-results.md`](../ideas/run-results.md)  
**Reviews:** [CEO](../ceo-review/run-results.md) · [UI](../ui-review/run-results.md) · [Tech](../design/run-results.md) · [Security](../security-review/run-results.md)  
**Branch:** `run-results`

## Gate rule

Do not implement a phase until questions that block it are **Decided** (or provisional with written default).

| Status | Meaning |
|--------|---------|
| **Open** | Blocks related work |
| **Decided (provisional)** | Ship temporary rule |
| **Decided** | Locked |
| **Deferred** | Out of scope for named phase |

---

## Questions

| # | Question | Status | Blocks | Decision | Date | Owner | Rationale |
|---|----------|--------|--------|----------|------|-------|-----------|
| 1 | When are structured results written from run data? | **Decided** | Whole feature | **On run publish** (`→ published`) | 2026-07-11 | Product | Official moment; matches publish permission |
| 2 | What value field is filled in v1? | **Decided** | Mapping | **`raw_result`** from JSONB value; calculated deferred | 2026-07-11 | Product | No general run calc engine |
| 3 | How do JSONB columns resolve to analytes? | **Decided** | Mapping | Name match + **aliases on analyte** (+ optional template map if needed later) | 2026-07-11 | Product | Multi-CRO column names |
| 4 | Cardinality: multi-analyte columns? | **Decided** | Promote service | **One column → one result row** per sample/test; multi-analyte = multi-row | 2026-07-11 | Product | Matches results model |
| 5 | Instrument vs results SoT? | **Decided** | Integrity | Run JSONB remains instrument SoT; results = published projection | 2026-07-11 | Product | Align Decision #1g |
| 6 | Always promote on publish, or opt-in? | **Decided** | Publish hook | See **Decision #6**. Promote when run has **`analysis_id` set** and status → **published**. | 2026-07-11 | Product | Analysis association is the opt-in |
| 7 | Missing tests on sample: block vs auto-create? | **Decided** | Promote readiness | See **Decision #7**. Analysis/analyte = catalog objects; test/result = instances. If analysis is on the run, tests are **ensured** (find-or-create)—there is no “missing test” failure mode for a defined analysis. | 2026-07-11 | Product | Objects vs instances |
| 8 | Existing results conflict policy? | **Decided** | Idempotency | See **Decision #8**. Same run re-publish/edit → **update**. Different run promoting same sample/analyte/replicate → **fail + notify**. | 2026-07-11 | Product | Lineage distinguishes runs |
| 9 | Alias storage / matching? | **Decided** | P0 aliases | **Maintained list on analyte** (no pattern matching). AI assist for misses = **later idea** ([ai-analyte-resolution](../ideas/ai-analyte-resolution.md)) | 2026-07-11 | Product | EtOH / C2H5OH / ethanol have no pattern |
| 15 | Replicate number when JSONB has none? | **Decided** | Promote | Use **row order** (1..n) among rows for that sample+analyte | 2026-07-11 | Product | Deterministic without instrument replicate column |
| 16 | Promote batch size? | **Decided** | Ops | **Configurable** (admin Lims Runs settings); **default 200** | 2026-07-11 | Product | Large imports |
| 10 | Permissions: publish alone vs + result:enter? | **Decided** | AuthZ | **Publish alone is enough** to write tests/results on promote | 2026-07-11 | Product | Publish is the official gate |
| 11 | Lineage on results? | **Decided** | Schema / #8 | **`lims_run_id` FK on results** (required for conflict rules). Optional data-row FK later. | 2026-07-11 | Product | Distinguishes same-run update vs other-run fail |
| 12 | Unmapped JSONB keys → custom_attributes? | **Decided** | Scope | **No** by default | 2026-07-11 | Product | Prefer Field Management for meta |
| 13 | Dose-response integration? | **Deferred** | — | Separate tables; not classic promote v1 | 2026-07-11 | | |
| 14 | Replicates: multiple data rows same sample+analyte? | **Decided** | Schema | **`results.replicate` INT** (nullable or default 1). Multiple data rows map to multiple result rows distinguished by replicate. | 2026-07-11 | Product | Structured replicates for query/report |
| 17 | Does `results` need BaseModel `name` (global unique)? | **Decided** | Schema | **Remove `name` (and name uniqueness) from results** — does not make product sense. Identity = id + test/analyte/replicate/lims_run_id. | 2026-07-11 | Product | Results are values, not named entities |

---

## Phase gate

| Phase | Scope | Status |
|-------|--------|--------|
| **P0** | Analyte aliases (on analyte) | **Shipped** |
| **P1** | `analysis_id` on run + UI; start-run warning | **Shipped** |
| **P2** | Schema: `lims_run_id`, `replicate`; drop `results.name` | **Shipped** |
| **P3** | Promote service + publish hook | **Shipped** |
| **P4** | Preview UX, conflict notifications | **Shipped** |
| **P5** | Optional JSONB → result custom fields | Deferred |

**v1 product policy + implementation complete.** Follow-ons: [ai-analyte-resolution](../ideas/ai-analyte-resolution.md), [ai-data-import](../ideas/ai-data-import.md), [ai-data-analysis](../ideas/ai-data-analysis.md).

---

## Decision #1 — Write on publish

**Status:** Decided · **Date:** 2026-07-11

Structured `results` rows are created/updated when the LimsRun transitions to **`published`**, not on import and not on complete alone.

---

## Decision #2 — raw_result v1

**Status:** Decided · **Date:** 2026-07-11

Promotion fills **`raw_result`**. `calculated_result` is out of scope until a calc product exists.

---

## Decision #4 — Multi-row multi-analyte

**Status:** Decided · **Date:** 2026-07-11

Each mapped analyte column produces its own result row (infinite rows per test allowed by the model).

---

## Decision #5 — Dual SoT roles

**Status:** Decided · **Date:** 2026-07-11

- **Instrument truth:** `lims_run_data`  
- **Reportable structured truth:** `results` after publish  

No write-back from results to JSONB in v1.

---

## Decision #12 — No JSONB dump to custom_attributes

**Status:** Decided · **Date:** 2026-07-11

Do not auto-copy unmapped keys into `results.custom_attributes`. Use result Field Management / custom fields for defined meta.

---

## Decision #6 — Runs are always tied to an Analysis

**Status:** Decided · **Date:** 2026-07-11 · **Superseded UX:** 2026-07-19  
**Also:** [data-parsers Decision #6](data-parsers-lims-runs.md) (no non-reportable path)

### Product rule (current)

| Rule | Behavior |
|------|----------|
| **Every LimsRun has an `analysis_id`** | Required from create/edit — **not** optional |
| **No non-reportable runs** | Cannot create, start, import, or publish a run without analysis |
| **On publish** | Always promote run data → **tests** + **results** for samples on data rows (subject to map/conflicts) |

There is no separate “promote_on_publish” boolean and **no** “continue without analysis” path.

### Implications

1. **Schema (target):** `lims_runs.analysis_id` **NOT NULL** FK → `analyses.id` (migrate nullable column when implementation aligns).  
2. **UI:** Analysis selection **required** on create/edit run; no “None (non-reportable)” option.  
3. **Start / import / publish:** Reject if `analysis_id` missing — no ack flag.  
4. **Test target:** For each distinct `sample_id` in `lims_run_data`, **ensure** a **test** instance for that sample + analysis (see **#7**).  
5. **Analyte scope:** Prefer analytes on that analysis (via `analysis_analytes`); aliases on analyte.  
6. **Template default:** Optional default `analysis_id` from template for convenience; run can override to another analysis.  
7. **Method-dev / scratch:** Deferred to [lab projects](../ideas/orders-and-projects.md) — still use a real analysis (e.g. draft), not null.

### Superseded (do not reintroduce)

- Start-run warn + **Continue without analysis** / `acknowledge_no_analysis`  
- Publish without promote when analysis null  
- “Non-reportable” as a first-class run mode  

### Rationale

- Analysis is the LIMS assay unit linking samples → tests → analytes.  
- “This run is for this assay” is always explicit (multi-CRO / multi-analyte panels).  
- Parsers are analysis × instrument/CRO; null analysis has no valid import model.

---

## Decision #7 — Tests are instances of Analysis (no “missing test”)

**Status:** Decided · **Date:** 2026-07-11

### Model

| Layer | Role |
|-------|------|
| **Analysis** / **Analyte** | Catalog **objects** (definitions) |
| **Test** / **Result** | **Instances** of analysis / analyte for a sample (and run lineage) |

### Rule

If the run has an **`analysis_id`**, promote **always ensures** a test for each sample involved:

- Find existing test for `(sample_id, analysis_id)`, or  
- **Create** that test instance  

There is **no** failure mode “analysis defined but test missing”—that would contradict objects vs instances.  
(Still fail if `sample_id` missing on data rows, or analyte cannot be resolved.)

**Yes — that makes sense for #7.**

---

## Decision #8 — Conflict policy (update vs fail)

**Status:** Decided · **Date:** 2026-07-11

| Situation | Behavior |
|-----------|----------|
| **Same LimsRun** re-published / data edited then published again | **Update** existing results that belong to this run (via lineage) |
| **Different LimsRun** would write the same sample + analyte (+ replicate) | **Fail promote** and **notify** user (do not overwrite the other run’s results) |

Requires **`results.lims_run_id`** (Decision #11) to tell “ours” from “another run’s.”

---

## Decision #9 — Aliases: maintained list on analyte

**Status:** Decided · **Date:** 2026-07-11

Store CRO/instrument alternate names as a **maintained list on the analyte** (array or `analyte_aliases` table).  

Matching is **list membership** (after light normalize: trim, casefold)—**not** chemical heuristics or regex patterns. Names like `ethanol` / `EtOH` / `C2H5OH` have no discoverable pattern; labs already maintain synonym lists for this reason.

**v1:** unresolved column → surface in preview/errors (skip or block per policy).  
**Later:** AI-assisted resolution / suggest alias — [ideas/ai-analyte-resolution.md](../ideas/ai-analyte-resolution.md).

---

## Decision #15 — Replicate from order if absent

**Status:** Decided · **Date:** 2026-07-11

If the JSONB / import does not supply a replicate number, assign **`replicate` by stable order** of `lims_run_data` rows for that sample (and analyte mapping), starting at **1**.

If instrument provides a replicate field later, prefer that when present.

---

## Decision #16 — Configurable promote batch size

**Status:** Decided · **Date:** 2026-07-11

Promote processes result writes in batches. Size is **admin-configurable** on a **Lims Runs** admin/settings page. **Default: 200**.

---

## Decision #10 — Publish permission is enough

**Status:** Decided · **Date:** 2026-07-11

Users who can **publish** the run may create/update tests and results as part of promote. No separate `result:enter` required for this path.

---

## Decision #11 — Lineage: `lims_run_id` on results

**Status:** Decided · **Date:** 2026-07-11

Add **`results.lims_run_id`** FK → `lims_runs` (nullable for manually entered results; set on promote).  
Needed for Decision **#8** (update vs fail across runs). Optional later: `lims_run_data_id` for row-level trace.

---

## Decision #14 — Replicate column on results

**Status:** Decided · **Date:** 2026-07-11

Add **`results.replicate`** as **integer** (default `1` or null meaning 1).  

Multiple `lims_run_data` rows for the same sample+analyte become multiple result rows distinguished by **replicate**.  
Conflict key for #8 includes replicate: `(sample’s test, analyte_id, replicate)` + ownership by `lims_run_id`.

If import has no replicate field: assign **1..n by row order** (#15).

---

## Decision #17 — Drop `name` on results

**Status:** Decided · **Date:** 2026-07-11

**Remove** the BaseModel-style **`name`** column (and global unique constraint) from **`results`**.

Results are not named lab objects (unlike samples, batches, runs). Natural identity is:

- `id`
- `test_id` + `analyte_id` + `replicate` (+ `lims_run_id` when from promote)

### Eng implications

- Stop inheriting name-required BaseModel for Result, or drop/null `name` via migration and adjust model.
- API schemas already omit `name` on create in places—align ORM/DB with that.
- UI should show analyte + sample + value, never a synthetic result name.

---

## Related

- LimsRun lifecycle: [../manuals/lims-runs.md](../manuals/lims-runs.md)  
- Experiments #9 lab-only data: [experiments.md](experiments.md)  

# Tech sketch: Configurable-entry framework

**Date:** 2026-08-24  
**Status:** **Design Group + CEO Agree (locked)**  
**Audience:** Design Group — Heidi (Architecture), Hans (Scientific CSO), Deiter (Lab Ops); CEO Rolf  
**Stem:** `configurable-entries-framework`  
**This PR:** docs only. No application/product code. **Not IC50.**  
**Coding:** stays Grok Build / paused unless Marc instructs.

**Related (do not duplicate; fold locks):**

| Doc | Role |
|-----|------|
| [`.docs/tech-sketch/experiment-template-entries.md`](experiment-template-entries.md) | Two base kinds, storage, grid contract, v1 predefined wrappers (§0.8 / §0.9) |
| [`.docs/tech-sketch/extract-hold-dest-type.md`](extract-hold-dest-type.md) | Aliquot/pool atomic pair, METHOD_CATALOG dual-map, dest type, execute/mint |
| [`.docs/requirements/extract-hold-dest-type.md`](../requirements/extract-hold-dest-type.md) | Acceptance criteria and leadership locks for dest type + pair |
| [`.docs/open-questions/sop-ai-to-process.md`](../open-questions/sop-ai-to-process.md) | PR 51 / SOP→AI Apply Hold |

---

## 0. Why this sketch exists

Aliquot/pool is the **first preconfigured proof** of a **configurable-entry framework**, not a one-off special type.

Design Group + CEO need one place that states:

1. What the framework **is** (two kinds + predefined wrappers + product execute).
2. How aliquot/pool **proves** it (atomic pair + METHOD_CATALOG dual-map + mint integrity).
3. How we **differ from Sapio** on purpose.
4. What the **north star** is, and what we **bounce** until the proof works.

This document **does not invent** beyond locks already in the related docs. It folds them so the framework is visible.

---

## 1. Problem

Without a named framework, aliquot/pool looks like a special-case pair of entries. That invites:

- A third base type (“aliquot entry”) or a new experiment-plan object.
- Dest rows that are identifiers, not `sample_id` FKs.
- Customer Python / webhooks as the mint path.
- Method and dest sample type collapsed into one control.
- Plan-only or dest-only add.
- Later “custom entries” and SOP→AI that bypass catalog, `sample_id`, and L1.

Those paths break sample-centric integrity and make every later preconfigured entry a new one-off.

**Ask of this review:** agree that aliquot/pool is **wrapper + catalogs + product execute** on the **same two kinds** every future minting entry must reuse.

---

## 2. Goals and non-goals

### Goals (this agree)

- Name the framework: two base kinds only; predefined wrappers; catalogs that attach columns/FieldDefinitions; product execute for mint.
- Treat aliquot/pool as the first proof of that pattern (atomic pair).
- Keep dest rows `sample_id`-linked; mint via product execute; lineage + L1 join non-optional for any minting entry.
- Record north star (more wrappers → lab-authored behavior → SOP→AI as a **later consumer**) without opening those slices now.
- Stamp Design Group + CEO Accept (locked 2026-08-24).

### Non-goals

- Implementing aliquot/pool or METHOD_CATALOG in this PR (docs only).
- Duplicating full METHOD_CATALOG method tables (see extract-hold sketch).
- Reopening IC50.
- Shipping lab-authored entry behavior or customer Python.
- SOP+AI Apply writing a live process / parser (PR 51 Hold stands).
- Experiment Header pin-to-top as the subject of this agree (related UX lock only).

---

## 3. Two base entry kinds only

Legacy API strings `sample_data` / `experiment_detail` **normalize** to these names on read/write. There is **no third base type**.

| Kind | Meaning | Rows |
|------|---------|------|
| **`experiment_sample_data`** | Per-sample process capture for one purpose on the experiment | Rows are **`sample_id`-linked**. Table: cohort (or minted dests after execute). Many such entries per experiment, each with its own columns. |
| **`experiment_data`** | Experiment-level / plan tables (plans, Experiment Header, operation lines) | **Table only.** Multi-row via **`row_key`**. User/code adds rows. Optional `sample_id` is secondary to free multi-row. |

**Multiplicity:** one experiment can have **many** entries of each kind.

Storage, grid (`GET /v1/entries/{id}/grid`), save/submit, and export stay as locked in [experiment-template-entries.md](experiment-template-entries.md) §0.2–§0.4. This framework sketch does not reopen those contracts.

**No new physical tables** named `experiment_sample_data` / `experiment_data` — those are **entry types** (logical). Columns are FieldDefinitions on the entry (`entity_type` ∈ those two kinds), not Custom Fields on Sample.

### 3.1 Entries are not copies of Sample (Marc CEO lock 2026-08-24)

`experiment_data` and `experiment_sample_data` are **not copies of Sample**. They capture **processing data** during the experiment. They must not be treated as a duplicate Sample record.

Sample **read-only projections** on grids may display identity for the tech (type, parent, barcode / container). **Writable** entry FieldDefinitions are **process values only** (e.g. dest amount / vol / conc on `aliquots_pools`).

---

## 4. Predefined wrappers (not a third kind)

A predefined wrapper is **functionality + catalogs + (when minting) execute**, keyed by `predefined_entry_key`. It is still one of the two kinds.

### 4.1 First proof: aliquot/pool (atomic pair)

| Role | `predefined_entry_key` | Kind | When | Owns |
|------|------------------------|------|------|------|
| **Plan** | `aliquot_pool_plan` | `experiment_data` | Before / at execute | Entry config + plan lines (METHOD_CATALOG plan-line columns) |
| **Dest** | `aliquots_pools` | `experiment_sample_data` | Created at add (**empty**); populated **after execute only** | Lists minted daughters. Dest FieldDefinitions live **on this entry**, not Sample columns. **No** method/type picker. |

**Atomic pair (locked):** one **“Add aliquot/pool”** action (template or ad hoc) creates **both** entries together. UI must **not** offer plan-only or dest-only. Dest stays empty until after execute. **No** new experiment-plan object.

Flow: Add → both entries exist (dest empty) → operator selects **method** → METHOD_CATALOG attaches **both maps immediately** → Execute reads plan → mints dests → L1 join → dest entry lists them. No dest-type re-prompt at execute.

### 4.2 Related UX lock (not this agree’s focus)

**Experiment Header** = `experiment_data` + `predefined_entry_key = experiment_header`. When added, it **pins to the top** of the entry list (no drag below). Parked as a separate entries-docs fold; mentioned so it is not mistaken for a third kind.

Other v1 wrappers (Samples cohort display, generic plating/LH as `experiment_data`, LIMS Run for instrument primary data) remain as in experiment-template-entries §0.9. Instrument primary data is **not** an ELN instrument entry.

---

## 5. METHOD_CATALOG dual-map

**Do not copy the full method tables here.** Canonical IN/CUT list, plan-line columns, dest FieldDefinitions, normalization, and Hans equimolar-by-size gate: [extract-hold-dest-type.md](extract-hold-dest-type.md) §4.

**Framework rule (locked):** a **concrete method id** implies **exactly one** `mint_op` ∈ {aliquot, pool} — aliquot **XOR** pool, never both — **and** two attachment maps:

1. **Plan-line columns** on the plan entry (`aliquot_pool_plan` / `experiment_data`).
2. **Dest FieldDefinitions** on the dest entry (`aliquots_pools` / `experiment_sample_data`).

**Method select attaches both maps immediately.** Not optional later wiring.

**Method ≠ dest sample type.** Separate controls. Method drives columns + mint op + dest FieldDefinitions. Dest type is an independent catalog control (`sample_type_transitions`).

### 5.1 Field picker / FieldDefinitions (Marc lock 2026-08-24)

When authoring an entry, **Add existing field** is populated only with existing FieldDefinitions for the **selected entry kind** (`experiment_data` **OR** `experiment_sample_data`).

Aliquot/pool METHOD_CATALOG predefined fields must be **existing fields for their source kind**:

| Surface | Kind / `entity_type` |
|---------|----------------------|
| Plan-line / plan-side fields | `experiment_data` |
| Dest FieldDefinitions on `aliquots_pools` | `experiment_sample_data` |

They are **not** Sample Custom Fields and **not** fields of the other kind. METHOD_CATALOG attaches those existing kind-scoped FieldDefinitions; it does not invent fields outside that kind’s catalog.

**Dest FieldDefinitions must not duplicate Sample identity** (Heidi Architecture Accept, PR 63): do not attach `sample_type`, `parent_sample_id`, barcode, or container identity as dest FieldDefinitions. Those come from **execute** (and accessioning), not from entry FieldDefinitions. Grids may **project** Sample identity read-only; writable dest fields stay process values (§3.1).

**Mid-flight method change:** not warn/wipe and not silent reshape. **Cancel the experiment.** Cancel does **not** un-mint already-minted daughters.

Transition catalog rows still key off `mint_op` (aliquot|pool), not concrete method id. Concrete methods (Deiter IN list) live in METHOD_CATALOG; CUT methods (fraction, contribution ratio, plate map, serial dilution) stay out of this proof.

---

## 6. Mint / integrity (non-optional)

These rules apply to **any minting entry**, including future custom wrappers. They are product integrity, not aliquot-only extras.

| Rule | Detail |
|------|--------|
| Dest rows | Stay **`sample_id`-linked** (`experiment_sample_data`). No working-table identifier that is not an FK to Sample. |
| Execute | **Product behavior** in NimbleLIMS. Not customer Python webhooks on entry/experiment events. |
| Lineage | Dest has **`parent_sample_id`**. |
| Process join | Dest joins **`eln_process_samples` (L1)** when the parent is under process. |
| Dest type | From plan: **line override → entry default → parent**. Catalog: **`sample_type_transitions`** (many-to-many), mutate with **`config:edit`**. |
| Pool sources | Must share **one** `sample_type` or refuse; then catalog lookup for that `mint_op`. |
| Dest amount / vol / conc | **FieldDefinitions on the dest entry**, not new Sample columns. Process values only — **not** Sample identity (`sample_type`, `parent_sample_id`, barcode / container). |

Execute resolve (same as extract-hold; not a new rule):

```text
mint_op = METHOD_CATALOG[entry.method].mint_op   # exactly one
type_id =
  line.dest_sample_type if set
  else entry.default_dest_sample_type if set
  else source.sample_type   # Same as parent
if type_id != source.sample_type and no catalog_row(source, mint_op, type_id): refuse
```

Seeds already locked for the proof: Blood × aliquot → DNA; DNA × pool → pooled DNA.

---

## 7. Framework vs Sapio

| Sapio (typical) | NimbleLIMS (this framework) |
|-----------------|-----------------------------|
| OOB ≈ Sample Details / Experiment Details | Same idea as our **two kinds**: `experiment_sample_data` / `experiment_data`. |
| Working tables with identifiers **not** FK-linked to Sample | Dest (and cohort) rows stay **`sample_id`-linked**. |
| Python webhooks on entry/experiment events to mint / reshape | **Product execute** for mint. **Bounce customer Python as v1 path.** |
| Labs often wire one-off tables + scripts per protocol | We ship **preconfigured wrappers** on the two kinds; catalogs attach maps; later authoring is a **later slice**. |

We keep sample-centric FKs and product mint **on purpose**. That is the competitive and integrity choice, not an implementation shortcut.

---

## 8. North star (later slices — not this proof)

Order is intentional. Later slices **consume** this framework; they do not replace it.

1. **Now / next proof:** aliquot/pool atomic pair + METHOD_CATALOG dual-map + dest type + L1 mint (extract-hold packet). Coding paused unless Marc instructs.
2. **More preconfigured entries** reuse the same pattern (wrapper key + kind + catalogs + product behavior). No new base type per workflow.
3. **Later:** labs may **author entry behavior on this substrate** (still two kinds, still `sample_id` / execute / catalogs for mint).
4. **Ultimately:** AI reads an SOP and **configures** entries / experiments / LIMS runs so the tech **executes and captures**.

**SOP→AI is a later consumer of this framework.** It is not a bypass.

**PR 51 / sop-ai-to-process Apply Hold stands:** the frame can hold Extract-then-Qubit (process + LIMS run + parser catalog). Apply must **not** write a live process definition or parser. A perfect parse does not fix dest type / L1 until mint integrity ships. See [sop-ai-to-process.md](../open-questions/sop-ai-to-process.md).

**Bounce until aliquot/pool proof works:**

- Lab-authored entry behavior (beyond the preconfigured pair).
- Customer Python / webhook-required mint.

---

## 9. Bounce bars

Do not reopen without a new product decision. **Design Group bounce bars (2026-08-24)** folded here with the prior spine — one row per bar, sources in the last column. **Not IC50.**

**Design Group (this fold):** Heidi (Architecture) · Hans (CSO) · Deiter (Lab Ops). Overlaps are merged (e.g. customer Python v1 is Heidi **and** Deiter).

| Bounce | Why | Source |
|--------|-----|--------|
| **Third base kind** | Wrappers sit on the two kinds only. | Heidi; spine |
| **Sample / `material_class` column for dest fields** | Dest amount / vol / conc are **FieldDefinitions on the dest entry**, not Sample schema and not a Sample/`material_class` column. | Heidi |
| **Customer Python as v1** | Mint is **product execute**, not customer Python / Sapio-style webhooks on entry or experiment events. | Heidi; Deiter |
| **Unlinked working tables** | Dest (and cohort) rows stay **`sample_id`-linked**. No identifier-only working table. | Hans |
| **Mint without transition catalog / `sample_id` / L1** | Every mint (including future custom) requires `sample_type_transitions`, `sample_id` dest rows, and L1 `eln_process_samples` join when under process. | Hans |
| **SOP→AI that bypasses catalog / `sample_id` / L1** | SOP→AI is a later **consumer** of this framework; it does not skip those integrity bars. PR 51 Apply Hold stands. | Hans |
| **Fill dest before execute** | Dest entry (`aliquots_pools`) is created at add but stays **empty until after execute**. | Deiter |
| **Dest type at execute** | Dest type stays on the **plan** (line override → entry default → parent). Execute does not prompt or set type. | Deiter |
| **Mid-flight method change / silent reshape** | After lines exist, changing method is **not** warn/wipe and not silent reshape — **cancel the experiment**. Cancel does not un-mint. | Deiter; spine |
| **Dual mint on one entry** | One method → exactly one `mint_op`. | Spine |
| **Un-mint on cancel** | Already-minted daughters stay minted. | Spine |
| **Collapsing method + dest type** | Separate controls. | Spine |
| **Method picker on dest entry** | Method lives on the plan entry. | Spine |
| **New experiment-plan object** | Plan is `experiment_data` + `aliquot_pool_plan`. | Spine |
| **Adding only one of the pair** | Atomic pair; no plan-only or dest-only UI. | Spine |
| **Optional later wiring of METHOD_CATALOG maps** | Both maps attach **immediately** on method select. | Spine |
| **Add existing field showing the wrong kind / Sample fields** | Dropdown lists only existing FieldDefinitions for the **selected entry kind**. Not Sample Custom Fields and not the other kind. | Marc 2026-08-24 |
| **METHOD_CATALOG inventing fields outside the kind’s FieldDefinition catalog** | Predefined plan fields are existing `entity_type = experiment_data`; dest fields on `aliquots_pools` are existing `entity_type = experiment_sample_data`. | Marc 2026-08-24 |
| **Dest FieldDefinitions that duplicate Sample identity** | Do not put `sample_type`, `parent_sample_id`, barcode, or container identity on the dest entry as FieldDefinitions. Those come from **execute** (and accessioning). Grids may show Sample identity as **read-only projections**. | Heidi PR 63 |
| **Treating `experiment_data` / `experiment_sample_data` as a duplicate Sample record** | Those kinds capture **processing data** during the experiment, not a copy of Sample. Writable FieldDefinitions are process values only. | Marc CEO 2026-08-24 |

Also still bounced in the extract-hold packet (not reopened here): CUT methods; free type-in parent concentration on normalization; equimolar-by-size without size/bp path; matrix drop; receive/mid-entry type gate; if-blood-then; transitions on `template_definition`. Sample/`material_class` for dest fields is in the table above (Heidi), not only this footnote.

---

## 10. How later wrappers reuse this (without inventing them)

Any future minting or plan/dest pair should answer the same questions:

1. Which of the **two kinds** is each surface?
2. What is the **`predefined_entry_key`** (or keys, if an atomic pair)?
3. If minting: which **catalog** supplies plan columns and dest FieldDefinitions, and when do they attach?
4. Does **product execute** mint `sample_id`-linked dests with `parent_sample_id` and L1 join?
5. Are dest quantitative fields **entry FieldDefinitions**, not Sample schema?
6. Does **Add existing field** list only FieldDefinitions for that entry’s kind (Marc lock §5.1)?
7. Are writable FieldDefinitions **process values only** (not a duplicate Sample record; not Sample identity — Heidi / Marc CEO)?

If a proposed entry cannot answer those without a third kind, a webhook mint, unlinked identifiers, Sample-identity dest fields, or fields from Sample / the other kind, it is **out of framework**.

---

## 11. Relationship to existing packets

| Packet | This framework |
|--------|----------------|
| Experiment template entries | Substrate: kinds, storage, grid, Header as wrapper, aliquot/pool named as v1 predefined. |
| Extract-hold dest type | **Proof slice:** dest type, METHOD_CATALOG dual-map, atomic pair, execute. Implement gate OPEN (docs); coding Grok Build unless Marc/Rolf asks. |
| SOP→AI / PR 51 | Later **consumer**. Apply Hold: Frame can hold Extract-then-Qubit; Apply must not write live process/parser. |

This sketch does **not** replace extract-hold requirements or METHOD_CATALOG tables. Those remain the implement packet when coding is unpaused.

---

## 12. Status and coding gate

| Item | Value |
|------|--------|
| Status | **Design Group + CEO Agree (locked)** |
| Status line | **Design Group + CEO Agree (locked)** |
| IC50 | **Not IC50** |
| Code in this PR | **None** (docs only) |
| Application coding | **Grok Build / paused** unless Marc instructs |

---

## 13. Reviews

Stamped 2026-08-24. Framework agree is **locked**. **Not IC50.** Docs only. Coding stays paused unless Marc instructs.

| Review | Reviewer | Verdict | Date | Notes |
|--------|----------|---------|------|-------|
| **CEO** | Rolf | **Accept** | 2026-08-24 | Framework agree; aliquot/pool as first proof |
| **CEO (Marc lock)** | Marc | **Accept** | 2026-08-24 | Entries are not copies of Sample; writable FieldDefinitions = process values; Sample identity may be RO grid projections |
| **Architecture** | Heidi | **Accept** | 2026-08-24 | Two kinds; no Sample/`material_class` dest columns; no customer Python v1 |
| **Architecture (PR 63)** | Heidi | **Accept** | 2026-08-24 | Field-picker fold; bounce dest FieldDefinitions that duplicate Sample identity (`sample_type`, `parent_sample_id`, barcode / container) |
| **Lab Ops** | Deiter | **Accept** | 2026-08-24 | Dest empty until execute; dest type on plan; no mid-flight method change; no customer Python v1 |
| **CSO** | Hans | **Accept** | 2026-08-24 | `sample_id` linkage; mint requires transition catalog / `sample_id` / L1; SOP→AI must not bypass |

**Implement gate for this framework agree:** **open (docs lock)**. Extract-hold implement gate remains as documented on that packet. This PR does not unpause coding.

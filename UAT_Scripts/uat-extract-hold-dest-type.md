# UAT: Aliquot / pool destination sample type

**Stem:** `extract-hold-dest-type`  
**Scope:** Plan-entry destination-type UX (Lab Ops L2)

## Prerequisites

1. Apply migrations through `0077` (process assignment is sample-in-a-container).
2. Log in as Administrator, Lab Manager, or Lab Technician with
   `experiment:manage`.
3. Create or open an experiment with an **Aliquot / pool plan** entry and at
   least:
   - one Blood source sample;
   - one source sample of a different sample type;
   - tracked source container amounts sufficient for execute.
4. Confirm the seeded catalog includes `Blood × aliquot → DNA` and
   `DNA × pool → Pooled DNA`.

## 1. Aliquot destination choice

| Step | Action | Expected result |
|------|--------|-----------------|
| 1.1 | Open the Aliquot / pool plan entry. | Separate entry controls appear for concrete **Method** and **Default dest sample type**. Only the eight Deiter IN methods are offered; no CUT or equimolar method appears. |
| 1.2 | Choose `Aliquot — by volume`, then select a Blood source. | The entry has one aliquot mint operation. Default and line destination controls offer **Same as parent.** and **DNA**; there is no free-text type input. |
| 1.3 | Set entry default to DNA and leave the line at **Use entry default**. Complete required inputs and save. | Entry config stores `method=aliquot_by_volume` and `default_dest_sample_type=DNA`; the line inherits the default. |
| 1.4 | Set the line to **Same as parent.** and save. | The explicit line clear overrides entry DNA and resolves to the parent type. |
| 1.5 | Select **DNA** as a line override and save. | Plan line stores `dest_sample_type` as the DNA list-entry UUID. |
| 1.6 | Reload the entry. | Method, default, and line override remain selected. Method is locked because lines exist; the UI directs the operator to cancel the experiment to change it. |
| 1.7 | Leave dest type **DNA**. Execute. Same click as spine **AC-P2-C3**. | Dest exists **only after execute**. Plan dest type is catalog intent, **not** a Sample. **New Sample** in a **new container**, `parent_sample_id` = Blood source. Dest type DNA. Parent Sample stays Blood. Dest sample + container on the process; inbound source `removed`. **Fail C3** if dest tube lands on the blood Sample, parent `container_id` is retargeted, or later Start follows blood. Do **not** score this as AC-P2-C2. **Result:** unsigned until Tobias (numbered on `570bbc0`; execute `1572071`). |

## 2. Catalog filtering

| Step | Action | Expected result |
|------|--------|-----------------|
| 2.1 | Select a source whose type has no aliquot transition rows. | Only **Same as parent.** is offered. |
| 2.2 | Inspect the network request after selecting a source. | `GET /v1/entries/dest-sample-types` sends `source_sample_id` and the mint operation implied by the entry method; the response contains only catalog destinations for that source type and client. |
| 2.3 | Attempt to save or execute an off-catalog `dest_sample_type` through an API client. | Request is refused with `dest_sample_type_not_allowed`; no destination is created. |

## 3. Pool source-type gate

| Step | Action | Expected result |
|------|--------|-----------------|
| 3.1 | Create a separate plan entry with `Pool — equal volume from each`; put two DNA sources in one pool group. | The entry has one pool mint operation. Destination choices use DNA `pool` transitions and include **Pooled DNA** plus **Same as parent.** |
| 3.2 | Change one source to a different sample type while retaining the pool group. | A lab-readable warning identifies the mixed pool; destination selectors for that pool are disabled and do not offer destination types. |
| 3.3 | Try Save plan, Dry-run, and Execute while the pool is mixed. | Each action refuses the mixed pool; no destination is created. |
| 3.4 | Restore one shared source type. | Warning clears and destination selection is enabled. |

## 4. Method and normalization locks

| Step | Action | Expected result |
|------|--------|-----------------|
| 4.1 | Attempt to submit pool groups under an aliquot method, or omit pool groups under a pool method. | API refuses the dual/mismatched mint shape. |
| 4.2 | Save at least one line, then attempt to change the concrete method through UI and API. | UI locks Method; API returns `method_change_requires_cancel`. No lines are reshaped. |
| 4.3 | Select `Aliquot — by target concentration` for a source with no concentration result. | Save is refused with `prior_concentration_required`. |
| 4.4 | Add a prior numeric concentration result for the source and enter target concentration plus target volume or amount. | Plan saves and dry-run resolves. There is no source-concentration input. |
| 4.5 | Attempt to send line `concentration` through an API client. | Request is refused with `free_text_concentration_not_allowed`. |

## 5. Bounce-bar checks

Verify the plan and execute flows contain none of the following:

- receive-time or mid-entry sample-type gate;
- execute-time destination-type picker or dest-container-type picker;
- free-text destination type;
- destination sample-ID box;
- wizard or forced navigation to Sample detail;
- `material_class` field or matrix removal;
- transition rules stored on `template_definition`.
- method or destination controls on the post-execute `aliquots_pools` entry;
- CUT methods, fake equimolar, or one entry that mints both aliquots and pools.

## 6. Dest container type (plan control; dest init does not prompt)

Distinct from dest **sample** type (sections 1–2) and from Method. 1×1 vessels only. E-9 lock 2026-09-10.

**Result: Pass** (Tobias QA) · **Rolf Confirm** 2026-09-10 · SHA `008baf2705beb4238e434f893e3a06b53cac1145` (`008baf2`) · `feat/dest-container-type` · Alembic `0079` · Compose down.

Combined from two Tobias stamps on the same SHA:

1. **Browser 6.1 Pass** — Tobias, 2026-09-10 21:59 ET. Three controls: Method, Default dest sample type, Default dest container type. Dropdown: **Same as source.** plus 1×1 vessels; **no** 96-well / plates. Did **not** re-score 6.2–6.8. Screens (cite; do not commit): `/workspace/uat-dest-container-type-008baf2-ui61/three-controls.png`, `/workspace/uat-dest-container-type-008baf2-ui61/open-dest-container-dropdown.png`.
2. **API Pass 6.2–6.8** plus sections **1–5 smoke** — Tobias, 2026-09-10 21:53 ET. Live API execute. Evidence (cite; do not commit): `/workspace/uat-dest-container-type-008baf2/{RESULT.md,tobias-stamp.json,acs.md}`.

**Locks held:** dest container type is a **plan** control; dest init does **not** prompt; **1×1 only**; Method ≠ dest sample type ≠ dest container type.

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 6.1 | Open the Aliquot / pool plan. | Third control: **Default dest container type**, separate from Method and Default dest sample type. Options: **Same as source.** plus 1×1 container types (tube, vial, well). 96-well / multi-position types are **not** listed. | **Pass** (browser, Tobias, 2026-09-10 21:59 ET, `008baf2`). FE unit is supporting only — **not** the UI stamp. |
| 6.2 | Leave default at **Same as source.** Leave the line at **Use entry default**. Save and execute. | Dest container is the **same type** as the source tube. No dest-init prompt for container type. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |
| 6.3 | Set entry default to a different 1×1 type (e.g. Cryovial). Leave the line at **Use entry default**. Save and execute. | Dest container uses the **entry default** type. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |
| 6.4 | Set the line to **Same as source.** (override) and execute. | Line clear overrides entry default; dest type is the source vessel type. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |
| 6.5 | Set the line to a specific 1×1 type and execute. | Dest container uses the **line override**. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |
| 6.6 | Template: Aliquot/pool plan entry → Default dest container type. Save template, start an experiment from it. | Runtime plan loads that default. Dest init still does not prompt. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |
| 6.7 | API: save/execute with no dest container type, inherit false, and no source container. | **422** `dest_container_type_required`. No dest minted. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |
| 6.8 | API: line `dest_container_type_id` = a plate (rows×columns ≠ 1×1). | **422** `dest_container_type_not_1x1`. No dest minted. | **Pass** (live API, 2026-09-10, `008baf2`; not re-scored in the 21:59 browser run) |

**Fail:** dest init asks for container type; method/sample-type/container-type collapsed into one picker; plate offered as dest mint vessel; silent execute fallback that was not a plan choice.

## 7. Atomic pair (E-10) — one Add creates plan + dest

**Result: Pass** (Tobias QA) · 2026-09-14 22:28 ET · SHA `dc7ee92c086558420c16edffe301773975f17234` (`dc7ee92`) · overall **closed** · **Rolf Confirm: Hold merge lifted** · **E-10 Met** · product on `main` @ `e56a89fe01656b416cfcae885b6ade605e8cf38e` (`e56a89f`, PR **129**).

Living honesty: numbered **7.1–7.8 Pass** on `e5a8fdd` (not rescored) **plus** Deiter Lab Ops EXTRA **double-Add Pass** on `dc7ee92` (**409** `wrapper_at_capacity`). **Lab Ops: Deiter Met** on double-Add 2026-09-14. That split **closes** the prior overall §7 **Fail** on `e5a8fdd`. Do **not** teach overall §7 Fail or **Hold merge** as current. Uniqueness is enforced: second instance while the wrapper exists is **409** `wrapper_at_capacity`. **Tobias dogfood Ready=Yes** on **`dc7ee92`** (`/workspace/dogfood-e10-dc7ee92/READY.md`; clean FE Docker/CRA; paths **1–5 Pass**). Ready=Yes on **`e5a8fdd`** and Ready=No on **`9312c54`** stay dogfood history. **Deiter Lab Ops Confirm** of Marc’s fold (2026-09-14) is not the double-Add Met. One **Add aliquot/pool** creates `aliquot_pool_plan` **and** `aliquots_pools` (`WRAPPER_CATALOG` `aliquot_pool`, cardinality **1**). Dest stays empty until dest init. Do not offer separate plan-only or dest-only presets. Steps **7.9 / 7.9b** stamped **Pass** from uniqueness restamp honesty on `dc7ee92` (sequential second plan POST **409**, second dest POST **409**, GET still 1+1; concurrent double POST statuses **201 + 409**, after counts **1 plan + 1 dest**). §§1–6 stay `008baf2` (not restamped). Not IC50.

**Evidence (cite only; binaries not committed):**
- `/workspace/uat-e10-section7-overall-dc7ee92/RESULT.md`
- `/workspace/uat-e10-section7-overall-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`
- `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`
- `/workspace/dogfood-e10-dc7ee92/READY.md`

**Prior Fail (history only):** `/workspace/uat-e10-section7-e5a8fdd/`

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 7.1 | New template → Tables & forms. Confirm presets. | **+ Aliquot/pool** is present. **+ Aliquot/pool plan** and **+ Aliquots/pools results** are **absent**. | **Pass** (Tobias, 2026-09-14 21:31 ET, `e5a8fdd`) |
| 7.2 | Click **+ Aliquot/pool**. | Two entries appear: Aliquot / pool plan and Aliquots / pools. Add **disables while the pair exists** (not forever — see 7.8). | **Pass** |
| 7.3 | Delete the **plan** entry. | **Both** disappear. | **Pass** |
| 7.3b | Add the pair again. Delete the **dest** entry. | **Both** disappear. Same as 7.3; either half is the pair. | **Pass** |
| 7.4 | Save template, create experiment from it. | Experiment has both entries. Dest table empty (no minted rows) before execute. | **Pass** |
| 7.5 | Ad hoc experiment (no template). Entries → **Add aliquot/pool**. | Same pair created. Add hidden/disabled while the pair exists. | **Pass** |
| 7.6 | API: POST only `aliquot_pool_plan`. | **201**; GET entries includes `aliquots_pools`. | **Pass** |
| 7.6b | API: POST only `aliquots_pools` on a fresh experiment. | **201**; GET entries includes `aliquot_pool_plan`. | **Pass** |
| 7.7 | API: DELETE the plan entry. | Both inactive. | **Pass** |
| 7.7b | API: DELETE the dest entry (fresh pair). | Both inactive. | **Pass** |
| 7.8 | After 7.3 / 7.3b (pair gone). | **+ Aliquot/pool** / **Add aliquot/pool** is enabled again. One wrapper instance at a time per template or experiment — not a lifetime lock. | **Pass** |
| 7.9 | API: POST `aliquot_pool_plan` again while the pair exists. | **409** `wrapper_at_capacity` (`wrapper_id`: `aliquot_pool`). GET still one plan + one dest. | **Pass** (Tobias / Deiter double-Add, 2026-09-14 ~22:27 ET, `dc7ee92`; sequential second plan POST) |
| 7.9b | API: create template with two `aliquot_pool_plan` decls. | **409** `wrapper_at_capacity`. | **Pass** (stamped from double-Add Pass honesty on `dc7ee92`; cardinality 1 / `wrapper_at_capacity`) |

**Deiter Lab Ops EXTRA bars** (double-Add restamp on `dc7ee92`; overall §7 closed / Pass):

| Bar | Result |
|-----|--------|
| Double-click Add → two pairs / half | **Pass** on `dc7ee92` — sequential second plan POST → **409** `wrapper_at_capacity`; second dest POST → **409**; GET still **1 plan + 1 dest** (no half). Concurrent double POST → statuses **201 + 409**; after counts **1 plan + 1 dest** (not two pairs). Prior **Fail** on `e5a8fdd` (concurrent 2+2 / sequential 2 plans + 1 dest) is **history**. Uniqueness enforced: **409** `wrapper_at_capacity`. |
| Reload/refresh orphan | Pass (not rescored; prior Pass on `e5a8fdd` stands) |
| Mint-early before execute | Pass (not rescored; prior Pass on `e5a8fdd` stands) |

**Fail (what still fails if broken):** operator can add dest-only or plan-only from presets; delete leaves a half-pair; add stays disabled after the pair is gone; second instance returns **201** instead of **409** `wrapper_at_capacity`. Living uniqueness: **409** `wrapper_at_capacity` (not a current blocker). Prior Fail “API second plan POST while pair/half exists” on `e5a8fdd` is **history**.

## 8. Template default dest sample type (E-12)

**Unsigned.** Do not invent Pass. Do not restamp §§1–7. Method ≠ dest sample type ≠ dest container type.

| Step | Action | Expected result |
|------|--------|-----------------|
| 8.1 | Experiment Templates → aliquot/pool plan entry. | Three plan controls: **Plan method**, **Default dest sample type**, **Default dest container type**. Dest sample type includes **Same as parent.** |
| 8.2 | Set dest sample type to a catalog dest (e.g. DNA) for an aliquot method. Save template. Start an experiment from it. | Runtime plan loads that `default_dest_sample_type`. Lines inherit **Use entry default** until overridden. |
| 8.3 | Clear dest sample type to Same as parent. Save. Start. | Runtime default is blank / Same as parent. |

## 9. Dest-type transition catalog admin (E-14 / S3)

**Unsigned.** Mutate is **config:edit** only. Do not invent Pass. Do not restamp §§1–7.

| Step | Action | Expected result |
|------|--------|-----------------|
| 9.1 | Admin → Dest-type transitions (`/admin/sample-type-transitions`). | Grid of source × operation × dest. Seeded Blood×aliquot→DNA and DNA×pool→Pooled DNA appear when present. |
| 9.2 | Add a transition (config:edit). | **201**. Row listed. Execute dest picker offers the new dest for that source × op. |
| 9.3 | Add the same source × op × dest again. | **409** `transition_exists`. |
| 9.4 | Lab tech without config:edit POST. | **403**. |
| 9.5 | Deactivate a row. | Row inactive. Execute dest picker no longer offers it (Same as parent. remains). |

## Pass criteria

- **This packet (E-10):** Steps **7.1–7.9b**. Formal **§7 Result: Pass** (Tobias QA, 2026-09-14 22:28 ET, `dc7ee92`). Packet **7.1–7.8 Pass** on `e5a8fdd` (not rescored). Deiter EXTRA **double-Add Pass** on `dc7ee92` (sequential **409** / concurrent **201 + 409** → **1 plan + 1 dest**). **Lab Ops: Deiter Met** on double-Add 2026-09-14. **7.9 / 7.9b Pass** from uniqueness restamp honesty. Prior overall **Fail** on `e5a8fdd` is **history**. **Rolf Confirm: Hold merge lifted** — E-10 **Met**; product on `main` @ `e56a89f` (PR **129**). **Tobias dogfood Ready=Yes** on `dc7ee92`. Ready=Yes on `e5a8fdd` and Ready=No on **`9312c54`** stay history. Do **not** restamp §6. Evidence: `/workspace/uat-e10-section7-overall-dc7ee92/RESULT.md`, `/workspace/uat-e10-section7-overall-dc7ee92/stamp.json`, `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`, `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`, `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`, `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`, `/workspace/dogfood-e10-dc7ee92/READY.md`. Prior Fail evidence: `/workspace/uat-e10-section7-e5a8fdd/`.
- Steps 1–6 remain the dest-container-type stamp on `008baf2` (Pass). They are not this packet.
- Blank dest **sample** type always means **Same as parent.** Blank dest **container** type always means **Same as source.**
- Catalog choices are many-to-many and client/source/operation filtered.
- Mixed-type pools are refused in both UI and API.
- Execute resolves dest **sample** type line override → entry default → parent without re-prompting. Dest **container** type resolves line override → entry default → source vessel without re-prompting. Dest type on the plan is catalog intent, **not** a Sample; dest exists **only after execute**. Route / Start / map-save / asked-for mint **zero** daughters. Receive still mints identity + first vessel — that is **not** dest mint.
- **1.7 / AC-P2-C3 execute click:** dest type DNA mints a new Sample + container; parent stays Blood; dest pair continues the process. **Fail C3** if dest tube lands on the blood Sample, parent `container_id` is retargeted, or later Start follows blood. Unsigned until Tobias. Numbered on `570bbc0`; execute is `1572071`. Do not score 1.7 as C2. `570bbc0` does **not** inherit `1572071` C2 Pass or Fail.
- **C2 execute click** (spine): extra container, same sample; dest joins; inbound assignment off; later Start follows dest. Leftover on the inbound tube is whatever was not transferred — emptying is not required. Unsigned until Tobias.
- Assign to process: no vessel, or two vessels with no pick → **422**. No silent pick.
- PATCH of process assignment is not a path.
- Normalization consumes a prior concentration result, never free-typed source concentration.
- **Section 6 stamp status:** **Pass** (Tobias QA) on `008baf2`. Browser 6.1 (21:59 ET) plus live API 6.2–6.8 (21:53 ET). Not a Pass for 1.7 / AC-P2-C3 / AC-P2-C2.

## Stamp log

### 2026-09-10 · `008baf2` · `feat/dest-container-type` · Tobias

**Result: Pass** (Tobias QA) for section 6. **Rolf Confirm** 2026-09-10: full fold on tip `008baf2` — API **6.2–6.8** + UI **6.1** browser Pass (three controls; Same as source. + 1×1; no plates) + sections **1–5 smoke**. Do **not** invent 6.1 from FE unit alone. SHA `008baf2705beb4238e434f893e3a06b53cac1145`. Alembic `0079`. Local compose, **down** after the run.

- **6.1 Pass (browser)** — 2026-09-10 21:59 ET. Method, Default dest sample type, and Default dest container type are three separate controls. Dest container dropdown lists **Same as source.** plus 1×1 vessels; **no** 96-well / plates. Did not re-score 6.2–6.8. FE unit (`isSinglePositionType`; `AliquotPlanEditor.test.tsx` 4/4) is supporting only and is **not** the UI stamp.
- **6.2–6.8 Pass (live API)** — 2026-09-10 21:53 ET. Same as source; entry default different 1×1; line Same as source overrides entry; line specific 1×1; template default survives experiment create; missing → 422 `dest_container_type_required`; plate → 422 `dest_container_type_not_1x1`.
- **Sections 1–5 smoke: Pass** — methods, DNA dest execute, catalog refuse, mixed pool, method lock, free-text conc refuse, no execute-time dest-container prompt. Smoke only. It does **not** sign **1.7 / AC-P2-C3**, and it does not touch **AC-P2-C2**. Both stay **unsigned until Tobias**.

**Locks held:** dest container type is a **plan** control; dest init does **not** prompt; **1×1 only**; Method ≠ dest sample type ≠ dest container type.

**pytest `pytest_dest_container`: Skip** — Docker-in-Docker unavailable in the API run environment. 6.2–6.5 / 6.7 / 6.8 were mirrored live against the API. The skip is **not** a Fail.

**Evidence (cite only; binaries not committed):** `/workspace/uat-dest-container-type-008baf2-ui61/` (6.1 screens) and `/workspace/uat-dest-container-type-008baf2/{RESULT.md,tobias-stamp.json,acs.md}` (API 6.2–6.8 + 1–5 smoke).

**Not touched by this run:** 1.7 / AC-P2-C3, AC-P2-C2, named-slot / OQ-WO-7, Leadership overall P2, receive first vessel. Their existing stamps stand as written. Not IC50.

### 2026-09-14 · WRAPPER_CATALOG cardinality 1 · `feat/e10-aliquot-atomic-pair`

**Not a UAT Pass at the time of this entry.** Aliquot/pool is wrapper id `aliquot_pool` in `WRAPPER_CATALOG` (cardinality **1**). API **409** `wrapper_at_capacity` on a second instance. UAT rows **7.9 / 7.9b** added then. Living §7 is **Pass** (2026-09-14 22:28 ET, `dc7ee92`). Do **not** restamp §6 (`008baf2`). n-pairs remain parked in `.docs/internal/ideas/aliquot-pool-multiple-pairs.md`. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

### 2026-09-14 · Marc E-10 punch (Rolf) · `feat/e10-aliquot-atomic-pair`

Marc’s rows **7.3b** (delete dest → both gone), **7.6b** (POST dest-only `aliquots_pools` → **201**; GET includes plan), **7.7b** (DELETE dest → both inactive), and **7.8** (Add re-enables after the pair is gone; one pair at a time, not a lifetime lock) are live in §7. **Unsigned at the time of this entry** — §7 was later stamped **Fail** on `e5a8fdd` (2026-09-14 21:31 ET), then **Pass** overall on `dc7ee92` (2026-09-14 22:28 ET). Read this row as punch history, not the current §7 state. Steps **1–6** remain the dest-container-type stamp on `008baf2` (Pass). Do **not** restamp §6. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

### 2026-09-14 · Deiter Lab Ops Confirm of Marc’s fold · product `9312c54`

**Deiter Lab Ops Confirm** of Marc’s E-10 punch (7.3b / 7.6b / 7.7b / 7.8). **Unsigned at the time of this entry** — later overall §7 **Fail** on `e5a8fdd`, then **Pass** on `dc7ee92`. This Confirm of Marc’s fold is **not** the 2026-09-14 **Deiter Met** on double-Add. Dogfood first on product SHA **`9312c54`** (`9312c54ddd3999963abd3070c76b0057b62e5d4c`). §§1–6 stay `008baf2`. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

### 2026-09-14 20:26 ET · Tobias dogfood Ready=No · product `9312c54` · docs tip `50b878a`

**Ready for UAT section 7?** **No** on **`feat/e10-aliquot-atomic-pair`**. Paths **1–5 Pass** on product **`9312c54`**. Blocker: clean FE **Docker** build **TS2345** `hasAliquotPair` nullability. Local one-line patch was used for the walk **only** — **not landed**. Formal **§7 Unsigned**. **Rolf Hold §7 UAT** until the fix is on the tip. Do **not** invent Ready=Yes or Pass/Fail for §7. Do **not** invent Pass from §6 / `008baf2`. Product owns TS2345 (docs-only fold; no product code fix here). §§1–6 stay `008baf2`. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

**History.** Superseded by Ready=Yes on **`e5a8fdd`**. Do not treat this Ready=No as current.

Verbatim Tobias READY.md (`/workspace/dogfood-e10-9312c54/READY.md`; artifacts `/workspace/dogfood-e10-9312c54/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 20:26 ET
**Who:** Tobias (dogfood)
**SHA:** product `9312c54ddd3999963abd3070c76b0057b62e5d4c` (9312c54); HEAD `50b878a9f0e182e4ebb84375b87330bf6fd26dfc` (50b878a). 9312c54 is ancestor of 50b878a (docs tip only).

**Ready for UAT section 7?** No — paths 1–5 Pass (API + source/bundle: single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). But clean frontend image build from this SHA fails TS2345 on `hasAliquotPair` nullability; dogfood UI image needed a local uncommitted one-line patch. Land that fix on the branch (or confirm CRA build green) before formal §7. Do **not** invent Pass from §6 / 008baf2.

Artifacts: `/workspace/dogfood-e10-9312c54/`
```

### 2026-09-14 21:23 ET · Tobias dogfood Ready=Yes · product `e5a8fdd` · dogfood history

**Ready for UAT section 7?** **Yes** on **`feat/e10-aliquot-atomic-pair`**. SHA **`e5a8fdd`** (`e5a8fdd50538e23e67c1425dadb3e505171b987f`; includes `hasAliquotPair` nullability fix). Paths **1–5 Pass**. Clean FE **Docker**/CRA build green; no local patch; working tree clean. Ready=Yes is **not** §7 Pass. Do **not** invent §7 Pass from dogfood or from §6 / `008baf2`. Prior Ready=No on **`9312c54`** stays history. §§1–6 stay `008baf2`. Not named-slot / OQ-WO-7 / C2/C3. Not IC50.

**History.** Ready=Yes on `e5a8fdd` is dogfood history. Living Ready=Yes is on **`dc7ee92`**. Formal §7 **Fail** at 21:31 ET (below) is also history; living §7 is **Pass** at 22:28 ET.

Verbatim Tobias READY.md (`/workspace/dogfood-e10-e5a8fdd/READY.md`; artifacts `/workspace/dogfood-e10-e5a8fdd/`):

```
# Dogfood Ready — E-10 aliquot/pool atomic pair

**Date:** 2026-09-14 21:23 ET
**Who:** Tobias (dogfood restamp)
**SHA:** `e5a8fdd50538e23e67c1425dadb3e505171b987f` (e5a8fdd) tip of `feat/e10-aliquot-atomic-pair` (includes hasAliquotPair nullability fix).

**Clean FE build:** Yes — `docker build --no-cache` frontend from this SHA; CRA Compiled successfully; no local patch; working tree clean.

**Ready for UAT section 7?** Yes — clean FE Docker/CRA build green on tip `e5a8fdd`, and dogfood paths 1–5 Pass (single **+ Aliquot/pool** preset, pair create, delete-plan and delete-dest both clear both halves, template→experiment instantiate with dest `minted_sample_ids: []` / `populated_after_execute: false`, ad hoc pair). Not formal §7. Do **not** invent Pass from §6 / 008baf2. Not IC50.

Artifacts: `/workspace/dogfood-e10-e5a8fdd/`
```

### 2026-09-14 · Rolf Confirm: No Hold on starting §7 · product `e5a8fdd` · history

**Rolf Confirm: No Hold** — that Confirm lifted the Hold on **starting** formal §7 after Ready=Yes on **`e5a8fdd`**. Evidence: `/workspace/dogfood-e10-e5a8fdd/READY.md`.

**History.** That Confirm lifted the Hold on **starting** §7. Later 21:31 ET overall **Fail** brought **Hold merge**; living gate is **Hold merge lifted** (product on `main` @ `e56a89f`, PR **129**). This Confirm was never a UAT Pass.

### 2026-09-14 21:31 ET · Tobias formal §7 Fail · product `e5a8fdd` · history

**Result: Fail** (Tobias QA) · SHA `e5a8fdd50538e23e67c1425dadb3e505171b987f` · `feat/e10-aliquot-atomic-pair` · Compose down. §§1–6 stay `008baf2` (not restamped). Not IC50.

- **7.1–7.8:** all **Pass** (packet rows; not rescored later).
- **Deiter Lab Ops EXTRA:** Double-click Add → two pairs / half **Fail** on this SHA — concurrent double POST → 2 plans + 2 dests; sequential 2nd POST → 2 plans + 1 dest. FE guards present; API lacked single-pair uniqueness **on `e5a8fdd`**. Reload/refresh orphan **Pass**. Mint-early before execute **Pass**.
- **Then-blocking (history):** API second plan POST while pair/half exists. Closed by uniqueness **409** `wrapper_at_capacity` on `dc7ee92`.
- **Honesty at 21:31 ET:** overall Result was **Fail** because of the Deiter double-Add bar. That Fail is **closed** by the 22:28 ET overall **Pass**.

**Rolf Confirm of this Fail was Hold merge.** Lifted after uniqueness restamp + overall Pass; product merged to `main` via PR **129** at `e56a89f`.

**Evidence (cite only; binaries not committed):**
- `/workspace/uat-e10-section7-e5a8fdd/RESULT.md`
- `/workspace/uat-e10-section7-e5a8fdd/acs.md`
- `/workspace/uat-e10-section7-e5a8fdd/stamp.json`

### 2026-09-14 ~22:27 ET · Tobias dogfood Ready=Yes · product `dc7ee92` · current dogfood

**Ready for UAT section 7?** **Yes** on **`dc7ee92`**. Clean FE **Docker**/CRA; paths **1–5 Pass**. Ready=Yes is dogfood, not a substitute for the formal overall stamp (22:28 ET Pass below). Prior Ready=Yes on **`e5a8fdd`** and Ready=No on **`9312c54`** stay history. §§1–6 stay `008baf2`. Not IC50.

Evidence: `/workspace/dogfood-e10-dc7ee92/READY.md`

### 2026-09-14 ~22:27 ET · Deiter double-Add Pass · product `dc7ee92`

**Deiter Lab Ops EXTRA double-Add: Pass** on `dc7ee92`. Sequential second plan POST → **409** `wrapper_at_capacity`; second dest POST → **409**; GET still **1 plan + 1 dest** (no half). Concurrent double POST → statuses **201 + 409**; after counts **1 plan + 1 dest**. **Lab Ops: Deiter Met** on double-Add 2026-09-14. Prior Fail on `e5a8fdd` is history. **7.9 / 7.9b Pass** from this uniqueness honesty. §§1–6 stay `008baf2`. Not IC50.

Evidence:
- `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`
- `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`

### 2026-09-14 22:28 ET · Tobias overall §7 Pass · product `dc7ee92` · current

**Result: Pass** (Tobias QA) · SHA `dc7ee92c086558420c16edffe301773975f17234` (`dc7ee92`). Packet **7.1–7.8 Pass** on `e5a8fdd` (not rescored) + Deiter **double-Add Pass** on `dc7ee92` (**409** `wrapper_at_capacity`) **closes** prior overall Fail on `e5a8fdd`. **Rolf Confirm: Hold merge lifted**. **E-10 Met**. Product on `main` @ `e56a89f` (PR **129**). Living uniqueness: **409** `wrapper_at_capacity` (not a blocker). §§1–6 stay `008baf2`. Not IC50.

Evidence:
- `/workspace/uat-e10-section7-overall-dc7ee92/RESULT.md`
- `/workspace/uat-e10-section7-overall-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/RESULT.md`
- `/workspace/uat-e10-doubleadd-dc7ee92/stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/tobias-stamp.json`
- `/workspace/uat-e10-doubleadd-dc7ee92/doubleadd.json`
- `/workspace/dogfood-e10-dc7ee92/READY.md`

### 2026-09-14 · Rolf Confirm: Hold merge lifted · E-10 Met · `main` `e56a89f` (PR 129)

**Rolf Confirm:** Hold merge **lifted**. E-10 **Met**. Product already on `main` at `e56a89fe01656b416cfcae885b6ade605e8cf38e` (PR **129**). Fold overall §7 **Pass** honesty onto `main`. Do **not** teach Hold merge as current. Not IC50.

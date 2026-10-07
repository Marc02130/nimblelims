# Spec: Experiment entries and event rules

**PRD:** [../../prd/experiment-entries/PRD.md](../../prd/experiment-entries/PRD.md)  
**Design:** [../../design/experiment-entries.md](../../design/experiment-entries.md)  
**Date:** 2026-10-07  
**Status:** **Provisional.** Spec freeze waits on Marc. **Implement CLOSED.**  
**Separate packet:** [configuring agent spec](../configuring-agent/SPEC.md). This spec does not open that work.

No Accept, Confirm, or UAT Pass. Tobias bars in §8 are provisional review bars. They are not a UAT stamp. Aliquot/Pool E-10 Met is cited, not restamped.

Not IC50. No chat. No lab-analysis assistant.

---

## 1. P1 entry catalog

Mathilda’s picker shows only these types. FB-E1 fails any other type in the P1 picker.

| Picker label | P1 role | Sample or inventory touch |
|--------------|---------|---------------------------|
| Notes | Documentation around a run (Katinka) | None |
| Attachments | Documentation. Image is this type, not a Static Image entry | File bytes on the attachment. Not a second sample store |
| Table | Documentation around a run | None, unless a column is specified later to call an existing API |
| Form | Documentation around a run | None, unless a field is specified later to call an existing API |
| Samples | Cohort / sample step | Existing sample APIs only (FB-E6) |
| Aliquot/Pool | Shipped bench step. Already Met | Existing execute API. No new ceremony (§3) |
| Material Tracking | Named bench step (Katinka, Rolf) | Existing APIs only (FB-E6). No lot store is invented here |

Out of the drawer, and therefore not Spec’d P1 types:

- Link Experiments (FB-E5 dropped from P1 UAT; see §8)
- Receive Samples / Receive-as-entry
- DNA / RNA / cloning
- Gold+ instrument loaders
- OnlyOffice Document, Sheet, or Slides as an out-of-the-box entry
- A separate Static Image entry

Shipped wrappers today (`backend/models/wrappers.py`) are `experiment_header`, `samples`, and `aliquot_pool` (`aliquot_pool_plan` + `aliquots_pools`). Mathilda’s P1 list does not add Header and does not remove the shipped Header key. Where new types sit relative to `template_definition.entries[]` is Marc’s open question 1. This spec does not add a JSONB config bag for them.

Two entry kinds remain the shipped substrate (`experiment_sample_data`, `experiment_data`; experiments Decision #23). A new P1 label is not a license to add a third kind before Marc freezes the track.

---

## 2. Existing APIs a sample-touching entry may call

Samples and Material Tracking use these routes or they stop. No second sample store. No second material store. No JSONB-as-config field. Lists stay off Schema. OQ-1 and OQ-5b are not frozen.

Mounted in `backend/app/main.py`.

| Method | Path | Use under this spec |
|--------|------|---------------------|
| GET, POST, PATCH | `/samples`, `/samples/{sample_id}` | Read or update a sample through the sample API |
| PATCH | `/samples/{sample_id}/status` | Status change (FB-E7, Katinka) |
| GET | `/v1/samples/{id}/journey` | Read journey. Sample-scoped |
| PATCH | `/containers/{container_id}/contents/{sample_id}` | Set contents amount, including amount → 0 |
| POST | `/v1/entries/{entry_id}/execute` | Aliquot/Pool execute. Already Met (§3) |
| PUT | `/v1/entries/{entry_id}/aliquot-plan` | Aliquot/Pool plan save. Already Met |

`POST /samples/receive` is accession (identity + first vessel, zero Tests). It is not an entry action and not a rule action (§4).

`DELETE /samples/{sample_id}` sets `active=False` in current code. `DELETE /containers/{container_id}/contents/{sample_id}` removes a contents row. `DELETE /v1/entries/{entry_id}` removes an entry row. Those routes exist. P1 entries and P1 rules do not use them as the retire path. The retire path is status change or amount → 0 (FB-E7, FB-R6, Katinka). This spec does not restamp the existing delete routes.

No materials or lot router exists. `container_types.material` is vessel composition, not lot tracking. The placeholder [materials-and-lot-tracking](../../ideas/materials-and-lot-tracking.md) described an inventory that is not shipped. Rolf puts Material Tracking in the P1 picker. FB-E6: the entry calls an API from the table above, or it stops and says the change cannot be expressed. It does not create a lot table, a JSONB config field, or a list-as-schema.

Entry read and value routes that already exist (`/v1/entries/...`, including values, grid, submit) stay the capture substrate. Submit/lock behavior beyond what is shipped waits on Marc’s track freeze and on experiments open question 20. This spec does not close that question.

---

## 3. Aliquot/Pool — cite only

Already Met. This spec asks for no regression and records no new Pass.

| Fact | Record |
|------|--------|
| Wrapper | `aliquot_pool`, cardinality 1, atomic pair, mint. Second instance **409** `wrapper_at_capacity` |
| Keys | `aliquot_pool_plan` (`experiment_data`), `aliquots_pools` (`experiment_sample_data`) |
| Execute | `POST /v1/entries/{entry_id}/execute` debits source `Contents.amount` and mints destination Sample, Container, and Contents |
| Met | [E-10 dogfood](../../../review/development-process/dogfood/e10-aliquot-atomic-pair.md). §7 Pass 2026-09-14. Deiter double-Add Met. Rolf hold-merge lifted. PR 129 on `main` |

Picker may still show Aliquot/Pool so the shipped action remains reachable (Mathilda). Showing it is not a new UAT and not a re-ceremony. A regression is in scope only when a later Spec asks for one.

---

## 4. Receive stays out of the entry drawer

Accession stays as built. Asked-for and routing stay as built. This spec does not reopen those locks.

| Rule | Contract |
|------|----------|
| Drawer | No Receive Samples entry. No Receive-as-entry control (Mathilda, Katinka, Rolf) |
| Receive means | Identity plus first vessel. `POST /samples/receive`. Status Available for Testing. Zero Tests |
| Tests | Created at LimsRun start (WO-7), not at receive, not by an entry, not by a rule |
| Rules | On-receive → create Tests is refused (Katinka). That refusal stays on FB-R3 |

---

## 5. Event rules P1

A P1 rule has a name, one named trigger (FB-R1), and one or more actions from the built-in catalog (FB-R3, FB-R9). It fires once per triggering event unless a later revision of this Spec writes a different count (FB-R2). This revision writes **once per event**.

Built-in actions for P1:

| Built-in | Allowed | Refused |
|----------|---------|---------|
| Set status | Yes, through `PATCH /samples/{sample_id}/status` or another existing status API the action names | Hard delete |
| Set amount to 0 | Yes, through `PATCH /containers/{container_id}/contents/{sample_id}` | Hard delete of the contents row or the sample row |
| Create Tests on receive | No | Fail FB-R3 (Katinka) |
| Script or code | No | Fail FB-R3 and FB-R9 |
| Link Experiments | No | Not a P1 action. FB-E5 is not a P1 bar |
| Any action with no existing API | Stop. Write nothing for that firing | Silent partial apply fails FB-R4 |

The catalog is a gallery in the UI (Mathilda). There is no script IDE chrome in P1.

One firing applies all of its actions or it leaves none of that firing’s writes behind (FB-R4, Rolf). Every attempt is logged (FB-R5), including a refused attempt. Disable keeps that history (FB-R8). Create and edit of a rule are privileged (FB-R7). A caller without the privilege sees a refusal and no write (FB-E8). The permission name is not frozen. The actor stored on the log (user or system) is not frozen (§9). Sync versus async execution is not frozen, and the log is still required either way.

Rules do not mint Process, Experiment, or LimsRun rows and do not become a second workflow engine. Instrument loaders and IC50 stay out.

---

## 6. Privilege and audit

| Bar | Contract |
|-----|----------|
| FB-E8 | A missing privilege is a visible refusal. The entry or rule write does not happen. A silent skip fails |
| FB-E9 | Entry audit records an actor. Which identity (user or system) is open (§9). An audit row with no actor fails |
| FB-R5 | Every rule action attempt is logged, success or refusal |
| FB-R7 | Creating or editing a rule requires a privilege the caller already holds. This spec does not mint a permission |

---

## 7. Attachment integrity

FB-E4. An attachment saved on an entry is the same bytes after reload (FB-E2). An image uses this attachment path. A second Static Image type fails FB-E1. Type isolation (FB-E3): a Notes body is not readable as an Attachment payload, and an Attachment is not readable as a Table or Form.

---

## 8. Fail bars (Tobias, 2026-10-07)

Provisional review bars. Not a UAT. Not a Pass. Implement CLOSED, so these bars are not executed by this fold.

### Entries

| Bar | Pass | Fail |
|-----|------|------|
| **FB-E1 Spec’d type in the picker** | Picker offers only Notes, Attachments (including image), Table, Form, Samples, Aliquot/Pool, Material Tracking | Link Experiments, Receive-as-entry, molecular, Gold+, OnlyOffice, or a separate Static Image type appears as a P1 choice |
| **FB-E2 Survives reload** | Saved entry content is still there after reload | Loss on reload |
| **FB-E3 Type isolation** | One type’s payload is not served as another type | Cross-type read or write |
| **FB-E4 Attachment integrity** | Stored bytes match the bytes uploaded, including an image stored as an attachment | Truncation, swap, or a parallel image store |
| **FB-E5** | **Dropped from P1 UAT entirely.** Link Experiments is out of P1 (Rolf, Mathilda). There is no P1 bar and no deferred P1 bar under this id | — |
| **FB-E6 Existing APIs** | Samples and Material Tracking touch samples or inventory only through existing sample and container APIs (§2) | A second sample store, a second material store, JSONB-as-config, lists on Schema, or a Receive Samples entry used as the touch path |
| **FB-E7 No hard delete** | Retire is status change or amount → 0 (Katinka) | Hard delete from an entry |
| **FB-E8 Privilege** | Refusal is visible. No write | Silent drop on a missing privilege |
| **FB-E9 Audit** | Entry audit has an actor | Audit missing, or actor empty |

Aliquot/Pool does not add an entry bar. It is already Met (§3). This spec does not ask for a regression.

Receive stays out of the drawer. A Receive entry fails FB-E1. It is not given a new bar id.

### Event rules

| Bar | Pass | Fail |
|-----|------|------|
| **FB-R1 Named trigger** | The rule names its trigger | A rule with no trigger |
| **FB-R2 Once per event** | The firing happens once per triggering event (this Spec). A different count fails unless a later Spec writes it | A second firing for the same event, or an unspec’d count |
| **FB-R3 Built-in catalog only** | Actions are built-ins that call existing APIs. **Locked for P1** | Any script or code action path in this packet. On-receive → create Tests (Katinka), including when the action is labeled a built-in |
| **FB-R4 No silent partial apply** | A firing that cannot finish leaves none of that firing’s writes | A partial apply, a silent skip, or a continue after a gap |
| **FB-R5 Attempt log** | Every action attempt is logged | An attempt with no log row |
| **FB-R6 No hard delete** | Rules may set status or set amount to 0 (Katinka). History of the rule remains | A rule hard-deletes a sample, contents row, entry, or rule history |
| **FB-R7 Privileged create/edit** | Create and edit require privilege | An unprivileged create or edit that writes |
| **FB-R8 Disable keeps history** | Disable stops firing and keeps prior log rows | Disable deletes history |
| **FB-R9 Built-in path** | P1 has a built-in-only path. **Locked with FB-R3** | A script or code action path offered in this packet, including “for later” chrome |

FB-R4, FB-R5, and FB-R6 stay. Katinka’s hard-delete refuse stays on FB-E7 and FB-R6. Her on-receive → create Tests refuse stays on FB-R3.

---

## 9. Open (do not freeze)

| Item | Owner | State |
|------|-------|--------|
| Entries inside current `entries[]` versus a separate ELN track | Marc | Open |
| Built-ins versus scripts as a product freeze | Marc | Open. P1 bar is already fail-on-script (FB-R3, FB-R9) |
| Plates in or out of P1 | Marc | Open. Not in the picker |
| Priority versus schema-cleanup and configuring-agent | Marc | Open |
| Sync versus async execution with a guaranteed log | BA | Open. FB-R5 still requires the log |
| Audit actor is user or system | BA | Open. FB-E9 still requires an actor |
| OQ-1 Schema allow-list | Marc (other packet) | Not frozen here |
| OQ-5b on-delete | Marc (other packet) | Not frozen here |
| Submit / lock / unlock reason (experiments Q20) | Lab Ops + Security | Open. Lab path after track freeze (Mathilda). Not closed here |
| Permission that gates rule create/edit | — | Not named. FB-R7 still requires a privilege |

---

## 10. Out of this spec

Link Experiments as P1 work. Receive Samples entry. DNA/RNA/cloning builders. Gold+ loaders. OnlyOffice entries. Script IDE. Code actions. IC50 and dose-response. Chat and lab-analysis assistant. CRM. ERP. A workflow engine beside Process / Experiment / LimsRun. Second sample store. Materials lot schema. JSONB-as-config. Lists on Schema. Freezing OQ-1 or OQ-5b. Reopening asked-for or routing. A new Aliquot/Pool UAT. Any Accept, Confirm, or UAT Pass.

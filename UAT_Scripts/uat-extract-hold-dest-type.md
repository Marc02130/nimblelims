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
| 1.7 **(OOB execute — not the P2 Contents click)** | Execute without changing the plan. | There is no execute-time type prompt. Dest **container-with-sample** joins the process; inbound source assignment is **removed**. Dest appears on **Aliquots / pools**. Matrix remains inherited. This is **not** dest-type Hold closed. This is **not** P2 extract minting a DNA daughter. Start extract still leaves the tube Blood. Do **not** say the dest is DNA, a DNA daughter, or that blood became DNA. This step is **OOB entry execute**; it is **not** AC-P2-C1/C2, which stay **unsigned** at `4671ba8` / `02fe95f`. |

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
- execute-time destination-type picker;
- free-text destination type;
- destination sample-ID box;
- wizard or forced navigation to Sample detail;
- `material_class` field or matrix removal;
- transition rules stored on `template_definition`.
- method or destination controls on the post-execute `aliquots_pools` entry;
- CUT methods, fake equimolar, or one entry that mints both aliquots and pools.

## Pass criteria

- Steps 1–5 pass.
- Blank always means **Same as parent.**
- Catalog choices are many-to-many and client/source/operation filtered.
- Mixed-type pools are refused in both UI and API.
- Execute resolves line override → entry default → parent without re-prompting.
- Execute-minted dest **container-with-sample** continues the process; inbound source assignment is removed.
- Assign to process is the **tube in hand**: no vessel, or two vessels with no `container_id` pick → **422**, lab-readable, **no silent pick**.
- A sample may have many containers; only one container-with-sample is on the process.
- Later Start follows the dest **container**, not a dest **type**.
- An **equivalent aliquot** is the **same sample in a new container** — no new identity, no `sample_type` rewrite. **Dest mint** (a new Sample row carrying `dest_sample_type`, via `_execute_transfer`) is a different motion and stays **Hold**.
- Do **not** score 1.7 as a DNA daughter or as dest-type Hold closed. Step 1.7 is **OOB entry execute**, **not** the P2 Contents click; AC-P2-C1/C2 stay **unsigned** at `4671ba8` / `02fe95f`. Catalog fixture `Blood × aliquot → DNA` is catalog language, not “execute produced a DNA daughter as the P2 extract story.”
- Normalization consumes a prior concentration result, never free-typed source concentration.

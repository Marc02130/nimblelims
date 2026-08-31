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
| 1.7 **(OOB execute — not the P2 Contents click)** | Execute without changing the plan. | This remains OOB; it has no Result stamp. **Different dest type = new derivative sample in a new container (`parent_sample_id`). Parent stays.** It must not retarget the parent assignment’s `container_id` or imply DNA on the parent. The dest is the new sample+container. Deiter’s separate `02fe95f` C2 **Fail** and dest mint Hold **Pass** remain signed history; the Hold Pass records Start extract still Blood with **0 DNA**, not a ban on type-changing execute minting a derivative. Live C2 on `1572071` is same-type dest-follow only and remains **unsigned** until Tobias. |

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
- **Same dest type = same sample, additional container.** Live C2 on `1572071` covers only this same-type dest-follow path and remains **unsigned** until Tobias.
- Assign to process is the **tube in hand**: no vessel, or two vessels with no `container_id` pick → **422**, lab-readable, **no silent pick**.
- A sample may have many containers; only one container-with-sample is on the process.
- Do not teach Later Start dest-follows as shipped, and do not teach PATCH as that path.
- `_follow_destination_in_process` retarget is the **same-sample additional-container** path. Do not use parent `container_id` retarget for a type-changing destination.
- **Different dest type = new derivative sample** in a new container with `parent_sample_id`; the parent assignment stays and the dest is the new sample+container. Dest mint Hold is lifted only for type-changing execute.
- Do **not** score step 1.7. It is **OOB entry execute**, not the P2 Contents click. Deiter C1 **Pass**, C2 **Fail**, and dest mint Hold **Pass** remain signed history at `4671ba8` / `02fe95f`; that Hold Pass is Start extract still Blood / **0 DNA** history. Live C2 on `1572071` remains unsigned.
- Normalization consumes a prior concentration result, never free-typed source concentration.

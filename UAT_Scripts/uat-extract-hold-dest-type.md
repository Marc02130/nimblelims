# UAT: Aliquot / pool destination sample type

**Stem:** `extract-hold-dest-type`  
**Scope:** Plan-entry destination-type UX (Lab Ops L2)

## Prerequisites

1. Apply migrations through `0068`.
2. Log in as Administrator, Lab Manager, or Lab Technician with
   `experiment:manage`.
3. Create or open an experiment with an **Aliquot / pool plan** entry and at
   least:
   - one Blood source sample;
   - one source sample of a different sample type;
   - tracked source container amounts sufficient for execute.
4. Confirm the seeded catalog includes `Blood × aliquot → DNA`.

## 1. Aliquot destination choice

| Step | Action | Expected result |
|------|--------|-----------------|
| 1.1 | Open the Aliquot / pool plan entry. | **Dest sample type** appears immediately beside **Method** on each line. |
| 1.2 | Select a Blood source sample and leave pool group blank. Open Dest sample type. | **Same as parent.** and **DNA** are available. There is no free-text type input. |
| 1.3 | Choose **Same as parent.**, complete required transfer inputs, and save. | Plan saves with a blank `dest_sample_type`. |
| 1.4 | Choose **DNA** and save. | Plan saves `dest_sample_type` as the DNA list-entry UUID. |
| 1.5 | Reload the entry. | The saved DNA choice remains selected. |
| 1.6 | Execute without changing the plan. | There is no execute-time type prompt. The new child sample has sample type DNA and the parent link; matrix remains inherited. |

## 2. Catalog filtering

| Step | Action | Expected result |
|------|--------|-----------------|
| 2.1 | Select a source whose type has no aliquot transition rows. | Only **Same as parent.** is offered. |
| 2.2 | Inspect the network request after selecting a source. | `GET /v1/entries/dest-sample-types` sends `source_sample_id` and `operation=aliquot`; the response contains only catalog destinations for that source type and client. |
| 2.3 | Attempt to save or execute an off-catalog `dest_sample_type` through an API client. | Request is refused with `dest_sample_type_not_allowed`; no destination is created. |

## 3. Pool source-type gate

| Step | Action | Expected result |
|------|--------|-----------------|
| 3.1 | Put two same-type source samples in one pool group. | Dest sample type becomes available after source metadata loads; options use that type's `pool` transitions plus **Same as parent.** |
| 3.2 | Change one source to a different sample type while retaining the pool group. | A lab-readable warning identifies the mixed pool; destination selectors for that pool are disabled and do not offer destination types. |
| 3.3 | Try Save plan, Dry-run, and Execute while the pool is mixed. | Each action refuses the mixed pool; no destination is created. |
| 3.4 | Restore one shared source type. | Warning clears and destination selection is enabled. |

## 4. Bounce-bar checks

Verify the plan and execute flows contain none of the following:

- receive-time or mid-entry sample-type gate;
- execute-time destination-type picker;
- free-text destination type;
- destination sample-ID box;
- wizard or forced navigation to Sample detail;
- `material_class` field or matrix removal;
- transition rules stored on `template_definition`.

## Pass criteria

- Steps 1–4 pass.
- Blank always means **Same as parent.**
- Catalog choices are many-to-many and client/source/operation filtered.
- Mixed-type pools are refused in both UI and API.
- Execute consumes the saved plan-line `dest_sample_type` without re-prompting.

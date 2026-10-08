# Design: Experiment entries and event rules

**Date:** 2026-10-07  
**Status:** **Provisional.** Spec freeze waits on Marc (model track, plates, priority versus schema-cleanup and configuring-agent). **Implement CLOSED.** Sketch waits on that freeze. No review Accept. No UAT Pass. Not IC50.  
**PRD:** [../prd/experiment-entries/PRD.md](../prd/experiment-entries/PRD.md)  
**Spec:** [../specs/experiment-entries/SPEC.md](../specs/experiment-entries/SPEC.md)

## Status / stamps

Core stamps below cite provisional Spec tip `4612e60` ([PR 146](https://github.com/Marc02130/nimblelims/pull/146)). They leave the Spec provisional. They do not open Implement. They do not record a UAT Pass.

- **Rolf Confirm Met** on provisional Spec tip `4612e60` (PR 146): P1 entry catalog and Tobias bars as folded.
- **Tobias:** bars as folded on `4612e60` stand. No UAT stamp on the docs packet. UAT waits Marc freeze and a product tip.
- **Mathilda UI Confirm Met** on `4612e60` for the P1 picker/drawer (§1) and the built-in rules gallery (§3). Sketch waits Marc freeze.
- **Katinka SOP Confirm Met** on `4612e60`: receive stays out of the entry drawer; refuse hard-delete and on-receive→create-Tests.

**Mathilda UI Confirm Met** covers the screen below. She does not Accept the packet. The screen is the contract a later sketch must follow after Marc freezes the Spec. This note does not draw that sketch.

No chat. No lab-analysis assistant. No script IDE.

---

## 1. Entry picker

One add control on the experiment. The menu lists only:

| Label | What the operator gets |
|-------|------------------------|
| Notes | A note on the run |
| Attachments | A file. An image is attached here. The menu has no Static Image row |
| Table | A table of documentation on the run |
| Form | A form of documentation on the run |
| Samples | Sample work through the existing sample screens and APIs |
| Aliquot/Pool | The shipped add. One action, the existing pair. Already Met. This menu does not start a new test script |
| Material Tracking | The material step. It can run only through an API the product already has. If none can express the step, the screen says so and writes nothing |

Katinka: Aliquot/Pool and Material Tracking are bench steps. Notes, Attachments, Table, and Form are documentation around the run.

The menu does not include:

- Link Experiments
- Receive Samples
- DNA, RNA, or cloning
- Gold+ instrument loaders
- OnlyOffice Document, Sheet, or Slides

Receive stays on accession, outside this drawer. Accession already creates identity and the first vessel and does not create Tests.

Plates are absent because Marc has not put them in or out of P1. The menu does not grow a Plates row in this note.

---

## 2. After add

FB-E1 through FB-E4 and FB-E6 through FB-E9 are the review bars ([spec §8](../specs/experiment-entries/SPEC.md)). FB-E5 is not a P1 bar.

Reload shows the same entry (FB-E2). A Notes entry does not open as an Attachment, and an Attachment does not open as a Table or Form (FB-E3). The file the operator attached is the file that comes back, including an image (FB-E4).

A sample or material change that the current API cannot express stops on that entry with the gap in plain words. Nothing is written for that change (FB-E6, FB-R4).

Retire on a sample-touching entry is a status change or amount set to 0. The control does not offer hard delete (FB-E7).

A caller who lacks privilege sees a refusal. The screen does not clear the field and continue (FB-E8).

---

## 3. Event rules

Place: with experiment administration, gated by privilege (FB-R7). The permission name is not frozen.

The screen is a gallery of built-in actions:

- Set status
- Set amount to 0

Each rule has a name and a named trigger (FB-R1). Saving a rule with an empty trigger is refused.

The gallery has no code box, no script editor, and no “add custom action” control. A script or code path on this screen fails FB-R3 and FB-R9.

The gallery does not offer:

- Create Tests when a sample is received
- Hard delete
- Link Experiments
- IC50 or a curve fit

On-receive → create Tests is refused in the gallery even if someone later labels it a built-in (Katinka, FB-R3).

Disable is a status on the rule. Prior attempts stay in the log (FB-R8). The log lists every attempt (FB-R5). Whether the actor column shows the user or a system identity waits on the open BA question. The column is not left blank (FB-E9 for entry audit; the rule log still records the attempt).

If a firing cannot finish, the screen shows the failed action and does not leave the earlier actions of that firing applied (FB-R4). Sync versus async is open. The screen still shows one result for the firing and a log row per attempt.

---

## 4. Submit, lock, unlock

Mathilda: submit, lock, and the unlock challenge stay the lab path after Marc freezes the track. Experiments open question 20 is still open. This note does not design the unlock dialog and does not close the question.

Shipped entry submit stays as it is until that freeze.

---

## 5. What this screen does not contain

A second workflow board beside Process, Experiment, and LimsRun. A Receive button. A molecular cloning canvas. A Gold+ loader. An OnlyOffice frame. A chat thread. A dose-response plot. A script IDE. A Schema editor. A materials catalog that the API does not already have.

Configuring agent screens stay on the [configuring-agent design](configuring-agent.md). This note does not add a rules tab there.

---

## 6. Sketch

Sketch waits on Marc freeze. Implement stays **CLOSED**. No Accept is claimed by this layout. No UAT Pass.

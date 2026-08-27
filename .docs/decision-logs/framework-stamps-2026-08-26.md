# Framework discussion stamps

**Date:** 2026-08-26  
**Status:** Decided (discussion)  
**Sources:**  
- [framework-driven-lims-accessioning](../discussions/2026-08-25-framework-driven-lims-accessioning.md)  
- [work-orders-assay-params-compounds](../discussions/2026-08-25-work-orders-assay-params-compounds.md)  
- [what-is-a-good-framework](../discussions/2026-08-25-what-is-a-good-framework.md)  
- [AR CORE leadership](../discussions/2026-08-26-ar-core-plan-leadership.md)  

---

## Stamps

| ID | Decision |
|----|----------|
| **FW-0** | **Accept** “good framework” definition as product SoT (fixed spine, DB joints, clear layers, maps, OOB defaults, one execute substrate, config:edit, params travel). |
| **FW-1** | **OOB intake = atomic receive only.** Labs/admins configure their own intake configs. Sidebar shows **active** configurations; only admin activates. |
| **FW-1b** | Activate/publish active configs to sidebar = **`config:edit` only** (not a separate lab-manager activate perm). |
| **FW-2** | Intake/work **profiles separate from Workflow Templates**. Profiles/routing = SoT for what procedure applies; templates = optional automation only. |
| **WO-1** | Entity = **`work_order`**. |
| **WO-3** | Work order **embeds an ordered chain** of process definitions (not first-only + route-next). |
| **WO-2** | Routing keys v1: **analysis + sample_type + TAT**. TAT as **range in days** (not a class enum). TAT can be derived as `due_date − order_date` (calendar days) when ordered. |
| **WO-4** | Non-instrument analysis: **LimsRun with analysis required**; manual entry OK; **no parser/instrument required** unless importing. |
| **WO-5** | Compound/gene/protein **registration deferred**, but **will be required**. Uniqueness validation (e.g. SMILES) is known-hard — separate packet. |
| **WO-6 / 6b** | Lot model **deferred**. Intent: **one compound = one Sample** so all testing rolls up; lots captured for provenance/troubleshooting. **Prefer lot as child Sample** when designed. |
| **WO-7** | Test row created or attached at **LimsRun start** — not at accession, not on a bare order, **not at publish**. Publish **refuses** if the Test is missing (no find-or-create / no ensure-on-publish). Hans/Heidi/Günter punch 2026-08-26. |

---

## WO-7 conditions

- `work_order` feeds Process / Experiment / LimsRun — not a second home / AuthZ path.
- Routing must not order a step on a sample type that does not exist yet (e.g. Qubit on blood).
- Empty routing map mints nothing.
- Overlapping TAT refuse (TAT matching algorithm still open).
- Params snapshot at LimsRun start and freeze.
- Classic type-a-number Result on a Test still lands (WO-4); two writers on same Test = 409.
- Instantiating from `work_order` uses existing process AuthZ — no client expand.
- **AR CORE hole closed:** `_create_asked_for_tests` is a **fail**. Empty `analysis_ids` as happy path is **not** enough. CORE **refuses** `analysis_ids` — **no Test mint at receive**. **Refuse (sketch pick):** if `analysis_ids` is present and non-empty → **422** (do not mint Tests, do not persist asked-for analyses). Empty or omitted is the only accepted path. Do **not** ignore. Do not add `work_order` or a new asked-for store in the AR packet. Classic Test+Result with no LimsRun still exists — do not silently kill it in stories. Test row at LimsRun start is this stamp, a later packet.
- AR CORE = identity + **1..N** vessels (not first vessel). Processing waits on CORE identity. Hold merge on PR 71 until UAT + dogfood.

---

## Sequencing (unchanged order; CORE vessel count corrected)

1. Atomic receive CORE — identity + **1..N** vessels; **refuse `analysis_ids`** (when Marc green-lights code; PR 71 stays draft pending UAT + dogfood).  
2. Work-order + routing map + order params packet. Test at **LimsRun start** (WO-7).  
3. Registration / lots packet (compound, gene, protein).  
4. Intake-profile engine beyond AR OOB when a second real profile is needed.

---

## Still open (not asked / deferred detail)

- Exact intake-profile **schema** columns (only AR OOB for now).  
- Work_order field list / status model.  
- How TAT range matching works when multiple map rows overlap (overlap **refuses**; algorithm still open).  
- Registration uniqueness strategies (SMILES, sequences, …).

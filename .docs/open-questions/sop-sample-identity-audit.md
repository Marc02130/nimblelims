# Open Questions: Sample Identity, Dispositions, Audit, Review/Amendment

Decision log for SOP-derived requirements (Issues #22–#26). Tracks questions that must be resolved before implementation or UAT cutover.

**Related Stories**: US-2, US-10, US-30 through US-38  
**Related Issues**: #22 (status mixing), #23 (dispositions), #24 (immutable ID), #25 (audit trail), #26 (review/amendment)

---

## Q1: When can UAT stop using Reviewed/Reported as Sample.status?

**Status**: Decided (provisional)  
**Blocks**: UAT cutover (not blocking this packet)  
**Owner**: Tobias  
**Context**: Current product has Sample.status with five values including `Reviewed` and `Reported`. Product direction shifts review/release to result-level controls (US-10, US-36), but UAT currently relies on the sample-status approach.

**Question**: When can UAT transition from setting Sample.status = Reviewed/Reported to using result-level review/release states instead?

**Decision (2026-08-20, Tobias):** **Parallel operation** for this cycle.

- Atomic-receive UAT (`UAT_Scripts/uat-atomic-receive.md`) uses Sample.status = **Available for Testing** only. It does **not** set Reviewed or Reported on the sample.
- The five existing sample status names remain valid list values so old scripts do not break overnight.
- **Cutover trigger:** first recorded **pass** of result-level review UAT (US-10; successor to / companion of `uat-results-entry-review.md`). Then retire Reviewed/Reported *sample* cases from `uat-sample-status-editing.md`.
- No calendar date now. Indefinite dual-path is **not** the product goal.

---

## Q2: Tenant configuration grain for second-person review gate

**Status**: Open  
**Blocks**: Implementation of US-10 (review configurability). **Does not block atomic-receive P0.**  
**Owner**: Product / Wilhelmina  
**Context**: Second-person review gate (reviewer ≠ enterer) should be tenant-configurable: default OFF for pure R&D, default ON for GxP/CRO-release. SOP sources do not specify configuration granularity.

**Atomic-receive packet:** Heidi locked **no new columns** on that stem. There is no schema flag for this gate in P0. Anton seeds distinct enterer vs reviewer users; AR-MU-02 stays catalog-only until this question has a home.

**Question**: At what level is the second-person review gate configured?

**Options**:
1. **Organization/Tenant-level**: One setting for entire organization (simplest; covers "we are a GxP lab" vs "we are a research core").
2. **Project-level**: Per-project configuration (allows mixed R&D and GxP projects in same org).
3. **GxP flag on project**: Binary flag (gxp_project boolean) that enables/disables gate (lighter than full per-project config).
4. **Analysis/Test-level**: Per-analysis configuration (most granular; allows "this assay requires review, that one doesn't").

**Recommendation (provisional)**: Start with **GxP flag on project**. Not part of atomic-receive; do not add the column on that packet.

**Next Steps**:
- Confirm with product/stakeholders if project-level GxP flag is sufficient for MVP.
- AR-MU-02 executes only after the setting exists.

---

## Q3: Lab ID format and generation algorithm

**Status**: **Closed 2026-08-20** (identity model locked on atomic-receive PR 30)  
**Blocks**: —  
**Owner**: Product / Deiter (Lab Ops)  
**Decision**: Two identities. Do **not** treat lab ID as the barcode.

- `samples.name` = lab sample ID, **system-assigned** from the existing name template/sequence. Tech does not type it. Receive screen has no sample-ID field.
- `containers.name` = scanned (or typed) tube barcode. Duplicate scan → 409 on the container only.
- `samples.name` 409 only if the generated sample ID itself collides.
- External ID stays in existing `client_sample_id` (optional; unique if present).
- Receipt datetime stays in existing `received_date`.

User-entered lab_id (old provisional Q3) is **retracted** with Lab Ops L1.

---

## Q4: Cancel-order SOP (after reported result)

**Status**: Open (unverified practice)  
**Blocks**: US-37 (retest) and order cancellation behavior  
**Owner**: Product  
**Recommendation (provisional)**: **Block** cancel after Reported; direct user to amendment workflow.

---

## Q5: Deiter Lab Ops gate on immutable lab ID (Issue #24)

**Status**: **Closed 2026-08-20** (identity model)  
**Blocks**: — Implement gate OPEN for atomic-receive packet (CEO Accept, PR 30 merged).  
**Owner**: Deiter (Lab Ops)  
**Decision**: L1 retracted. Two IDs is correct lab identity. Mix-up is unacceptable only if receive or lookup makes techs hunt or type the sample ID. Lookup is scan the tube. Receive screen does not show a sample-ID field.

Aliquot later = another container on the same sample. Derivative later = new sample with `parent_sample_id`. No aliquot UI on atomic-receive.

---

## Summary: What Blocks What

| Open Question | Blocks | Owner | Status |
|---------------|--------|-------|--------|
| Q1: UAT cutover for Reviewed/Reported | UAT cutover (not this packet) | Tobias | **Provisional: parallel.** AR UAT only sets Available for Testing |
| Q2: Second-person review config grain | US-10. Not atomic-receive P0. | Product | Open (no column on receive packet) |
| Q3: Lab ID format | — | Product + Deiter | **Closed**: system sample ID + container barcode |
| Q4: Cancel after report | Order management | Product | Open (provisional: block) |
| Q5: Deiter Lab Ops gate | — | Deiter | **Closed**. CEO Accept. Gate OPEN for this packet |

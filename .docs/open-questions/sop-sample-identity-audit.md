# Open Questions: Sample Identity, Dispositions, Audit, Review/Amendment

Decision log for SOP-derived requirements (Issues #22–#26). Tracks questions that must be resolved before implementation or UAT cutover.

**Related Stories**: US-2, US-10, US-30 through US-38  
**Related Issues**: #22 (status mixing), #23 (dispositions), #24 (immutable ID), #25 (audit trail), #26 (review/amendment)

---

## Q1: When can UAT stop using Reviewed/Reported as Sample.status?

**Status**: Decided (provisional)  
**Blocks**: UAT cutover (not blocking MVP implementation)  
**Owner**: Tobias  
**Context**: Current product has Sample.status with five values including `Reviewed` and `Reported`. Product direction shifts review/release to result-level controls (US-10, US-36), but UAT currently relies on the sample-status approach.

**Question**: When can UAT transition from setting Sample.status = Reviewed/Reported to using result-level review/release states instead?

**Decision (2026-08-20, Tobias):** **Parallel operation** for this cycle.

- Atomic-receive UAT (`UAT_Scripts/uat-atomic-receive.md`) uses Sample.status = **Available for Testing** only. It does **not** set Reviewed or Reported on the sample.
- The five existing sample status names remain valid list values so old scripts do not break overnight.
- **Cutover trigger:** first recorded **pass** of result-level review UAT (US-10; successor to / companion of `uat-results-entry-review.md`). Then retire Reviewed/Reported *sample* cases from `uat-sample-status-editing.md`.
- No calendar date now. Indefinite dual-path is **not** the product goal.

**Options** (historical):
1. **Parallel operation**: Implement result-level review/release; keep sample status values working; UAT decides when to cut over (no forced migration).
2. **Guided migration**: Provide migration tool/documentation; set cutover date with UAT.
3. **Indefinite compatibility**: Support both approaches permanently (product direction favors result-level, but sample status remains valid).

**Constraints**:
- Must not break existing UAT workflows without notice.
- Product direction is clear (result-level review), but forcing immediate cutover risks UAT disruption.
- Existing five status names remain valid list values during transition.

---

## Q2: Tenant configuration grain for second-person review gate

**Status**: Open  
**Blocks**: Implementation of US-10 (review configurability)  
**Owner**: Product / Wilhelmina  
**Context**: Second-person review gate (reviewer ≠ enterer) should be tenant-configurable: default OFF for pure R&D, default ON for GxP/CRO-release. SOP sources do not specify configuration granularity.

**Question**: At what level is the second-person review gate configured?

**Options**:
1. **Organization/Tenant-level**: One setting for entire organization (simplest; covers "we are a GxP lab" vs "we are a research core").
2. **Project-level**: Per-project configuration (allows mixed R&D and GxP projects in same org).
3. **GxP flag on project**: Binary flag (gxp_project boolean) that enables/disables gate (lighter than full per-project config).
4. **Analysis/Test-level**: Per-analysis configuration (most granular; allows "this assay requires review, that one doesn't").

**Trade-offs**:
- Org-level: Simple, covers common cases, less flexible for mixed orgs.
- Project-level or GxP flag: More flexible, common pattern (clinical trials project vs R&D project in same org).
- Analysis-level: Maximum flexibility, but adds complexity to catalog management.

**Recommendation (provisional)**: Start with **GxP flag on project** (simplest step beyond org-level that covers common "this project ships to FDA" use case). Can enhance to analysis-level later if customer requests.

**Next Steps**:
- Confirm with product/stakeholders if project-level GxP flag is sufficient for MVP.
- Document as "project.gxp_mode boolean; when true, result review requires reviewer ≠ enterer."

---

## Q3: Lab ID format and generation algorithm

**Status**: Open (uniqueness decided; format open)  
**Blocks**: Implementation of US-30 (immutable lab ID)  
**Owner**: Product / Deiter (Lab Ops review)  
**Context**: SOP sources require unique, immutable lab ID per container. Must not encode location or PHI. No public SOP specifies format (no "must be Code 128" or "must be 10 alphanumeric").

**Question**: What is the format and generation algorithm for `lab_id`?

**Options**:
1. **Sequential integer with prefix**: e.g., `NL-000001`, `NL-000002`. Simple, human-readable, easy to implement. Risk: predictable (minor; research lab, not a security token).
2. **UUID or ULID**: Globally unique, sortable (ULID), but less human-friendly (long strings).
3. **User-entered**: Technician types barcode from pre-printed labels. Product validates uniqueness but does not generate. Common in cores with existing label stock.
4. **Hybrid**: User can enter or system can generate (flexibility for labs with/without label stock).

**Trade-offs**:
- Sequential: Easy to read/say over phone; sufficient for startup with <10k samples/year.
- UUID/ULID: Handles distributed/offline entry; overkill for single-site startup.
- User-entered: Matches existing lab label workflow; requires validation only (no generation logic).

**Recommendation (provisional)**: Start with **user-entered** (simplest; matches existing accessioning workflow where techs scan/type pre-printed barcodes). System enforces uniqueness via database constraint. Add optional auto-generation (sequential with prefix) as enhancement if requested.

**UAT note (Tobias, 2026-08-20):** Atomic-receive treats the **user-entered/scanned** value as `containers.name` and the **system-assigned** value as `samples.name`. Q3 should be rewritten against that two-ID model (see QA review BA gap on US-30).

**Next Steps**:
- Deiter to confirm user-entered with uniqueness check covers Lab Ops workflow.
- Document as "lab_id: unique string, technician-entered (scan or type), validated at accession."

---

## Q4: Cancel-order SOP (after reported result)

**Status**: Open (unverified practice)  
**Blocks**: US-37 (retest) and order cancellation behavior  
**Owner**: Product  
**Context**: No public SOP found for cancelling a test order after a result is reported. CLIA documents add-ons (additional testing), not cancellations. Common unverified practice: cancel before result entry; after results exist, void/amend with reason; never silent-delete.

**Question**: What happens when user tries to cancel an order after result is reported?

**Options**:
1. **Block**: Cannot cancel after Reported; use amendment (US-36) if result is incorrect.
2. **Allow with reason**: Cancel marks order as "cancelled" with reason; result remains visible but flagged as "order cancelled post-report."
3. **Convert to amendment**: Cancelling a reported result automatically triggers amendment workflow (reason required; original remains).

**Recommendation (provisional)**: **Block** cancel after Reported; direct user to amendment workflow. Rationale: No SOP supports cancelling reported results; amendment keeps original and is the sourced pattern.

**Label**: Document as "unverified practice; product blocks cancel after report; use amendment for corrections."

**Next Steps**:
- Implement block in US-37 / order management.
- Add UI message: "Cannot cancel reported result. Use Amend Result instead."

---

## Q5: Deiter Lab Ops gate on immutable lab ID (Issue #24)

**Status**: Open (blocking implement-ready, not blocking requirements)  
**Blocks**: US-30 marked as implement-ready  
**Owner**: Deiter (Lab Ops)  
**Context**: Issue #24 requires stopping barcode timestamp-suffix mutation and implementing immutable lab ID. This is a mix-up risk mitigation; Deiter must review before implementation begins.

**Question**: Does the proposed approach (user-entered unique lab_id + separate external_id + no timestamp suffix) adequately mitigate mix-up risk?

**Review scope for Deiter**:
- External ID stored separately from lab ID (no mutation).
- Duplicate lab barcode rejected (no collision resolution algorithm).
- Receipt timestamp is a field, not encoded in the identifier.
- Each aliquot gets a new lab ID.
- Typed entry acceptable; scan supported.

**Next Steps**:
- Schedule Lab Ops review with Deiter before marking US-30 as implement-ready.
- Deiter provides sign-off or requests changes to mitigate mix-up risk.
- Document review outcome as "Deiter Lab Ops gate: [Approved / Revisions Requested]."

---

## Parked (Out of MVP Scope)

The following are **not open questions**; they are confirmed out-of-scope and should not pull requirements into MVP:

- **Forensic chain-of-custody every-handoff forms**: Who signed, who received, every internal transfer. MVP: receipt event, current location/custodian. Forensic depth is post-MVP.
- **Live freezer probe integration**: Real-time temp monitoring, alarms. MVP: temp class as a field; excursion flag. Live probes are infrastructure, not LIMS core.
- **Numeric freeze-thaw limits**: "Max 3 cycles" is common practice but no public SOP found. MVP: count freeze-thaw cycles. Numeric limit enforcement is optional/later.
- **After-hours accessioning SOP**: No public procedure found. MVP: receipt datetime captures when it happened; policy is external.
- **Duplicate-barcode collision algorithm**: Product refuses duplicates; no resolution algorithm sourced. UC Davis: bill for rework. MVP: reject duplicate; manual resolution by admin.
- **NCI SOP 22002 field list**: Referenced in SOP pack but PDF not retrieved. Do not invent its required fields. MVP uses sourced minimum (sample ID, test, requester, dates).
- **Consent-withdrawal handling**: GTEx CoC includes return-on-withdrawal; ISO 20387 7.7.8 mentions it. Relevant for human biobanks; **not MVP** unless customer is human-subject biobank.
- **CLIA retention clocks**: Slides 10 years, blocks 2 years (pathology). Hospital-only; **not for research aliquots**. MVP: configurable retain-until date, not hardcoded clocks.
- **21 CFR 58.195 retention math**: GLP retention formula (2 years after approval or 5 after submission, whichever is later). Do not hardcode; make retain-until configurable.
- **CGT chain of identity / ISBT 128**: Autologous cell therapy (CAR-T, FDA 1271, FACT-JACIE). Out of MVP even if seed data includes CAR-T as sample types. COI is post-MVP.
- **E-signatures with meaning and re-auth**: Part 11 11.50, 11.200, 11.70 (signature bound to record). Post-MVP. Do not fake it on day 1.
- **Part 11 compliance claim**: FDA does not certify software. Audit trail is GxP-ready, not "certified." Marketing claim is post-MVP with validation evidence.

---

## Summary: What Blocks What

| Open Question | Blocks | Owner | Status |
|---------------|--------|-------|--------|
| Q1: UAT cutover for Reviewed/Reported | UAT cutover (not MVP implementation) | Tobias | Decided (provisional): parallel until US-10 result-level review UAT passes |
| Q2: Second-person review config grain | US-10 implementation | Product | Open (provisional: project-level GxP flag) |
| Q3: Lab ID format | US-30 implementation | Product + Deiter | Open (provisional: user-entered). UAT maps that to containers.name |
| Q4: Cancel after report | Order management behavior | Product | Open (provisional: block, direct to amendment) |
| Q5: Deiter Lab Ops gate | US-30 implement-ready | Deiter | Open (review pending) |

**Gate rule**: Q1 does not block MVP implementation (compatibility path allows both approaches). Q2–Q4 need decisions before implementation; provisional answers provided for velocity. Q5 must complete before US-30 is marked implement-ready.

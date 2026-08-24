# SOP mapping onto NimbleLIMS (as of 20 Aug 2026)

Public SOP findings applied to the current product, not a second copy of the SOP packs. Companion files: `sample-management-mvp.md`, `test-ordering-results-qc-lims-mvp.md`.

**Product facts used here:** MVP = accession/track + order tests + enter results. Status list is configurable and free-form: `Received → Available for Testing → Testing Complete → Reviewed → Reported`. Accessioning still mutates typed barcodes with a timestamp suffix. Audit today is `created_at/by` + `modified_at/by` (no confirmed audit-event table). BioTech seed in draft PR #21 (mAb PK, CAR-T, plasmids). ELN / LimsRuns / dose-response / parsers are parked.

---

## 1. Status model — the list mixes two lifecycles

No public SOP defines a coded state machine, so **free-form is not a compliance failure**. ISO 20387 + GTEx require reconstructing *history*, not a named enum.

The current five names mix **sample** states with **result** states:

| Current Sample.status | SOP object it actually belongs to | Closest sourced language |
|---|---|---|
| Received | Sample | GTEx ‘received’; WHO register |
| Available for Testing | Sample (accepted, not quarantined) | WHO/CLIA accept; Decision #24 cohort eligibility |
| Testing Complete | Order / work, not the specimen | No SOP name. NCI “distribution” / in testing is custody, not a sample status |
| Reviewed | Result | 211.194(a)(8) second-person; ISO 17025 7.8.1.1 authorize |
| Reported | Result | ISO release; CLIA report |

**Recommendation (synthesis, not a fake SOP):** keep Sample.status as sample-only. Add **Quarantined**, **Rejected**, **Discarded** (sources actually name these). Keep result review/release on the **result/report**, not by overwriting Sample.status to Reviewed/Reported.

Do **not** hard-block techs into a state machine on day 1. Do **not** drop the existing five names without Wilhelmina/Tobias. Flag for UAT: today’s product allows any `sample:update` user to set status freely — that does **not** satisfy 211.194 second-person review even if someone types “Reviewed”.

Minimum extras vs current list:

| Add? | Why | MVP? |
|---|---|---|
| Quarantined | GTEx / ISO 20387 segregate until ID/quality checks complete | **Yes** if you accession shipments |
| Rejected | WHO / CDC / BioSEND / TJU | **Yes** |
| Discarded | ISBER M3; WHO disposal | **Yes** (or a disposal event with qty=0) |
| Cancelled | Order-level, not sample | On the **order** |
| On hold | **No public SOP found** for this name | Optional comment/flag |

---

## 2. Accessioning IDs and the timestamp-suffix barcode

Sources (NCI B.6.2, ISBER, 21 CFR 58.130): unique **immutable** lab ID per container; human-readable + barcode; must **not** encode location or PHI; each aliquot gets a **new** ID.

**Mutating a typed barcode with a timestamp suffix at accession is not in any public SOP.** It is the opposite of immutability and is a real mix-up risk (Lab Ops L8). Unique IDs are assigned *in addition to* the submitter’s ID, not by rewriting it.

SOP-backed rule for MVP:

1. Submitter/external ID stored as-is.
2. Lab assigns a new unique `lab_id` / barcode that never changes.
3. Duplicate lab barcode is rejected (no public collision *algorithm*; cores just refuse duplicates).
4. Timestamp belongs on the **receipt event**, not inside the identifier.

Typed entry is acceptable (Annex 11: manual entry + second check for critical data). Scan is better; it is not a sourced mandate for a research LIMS.

---

## 3. CoC, storage, aliquots — minimum vs later

| Practice | Sourced minimum for a startup/CRO | Park |
|---|---|---|
| Chain of custody | Who received, when, from whom, current location (event log, not a status) | Forensic every-handoff forms; 10-year CoC default; CGT chain of **identity** |
| Storage | A location string (freezer/box if they have it); temp class if known | Live probes, mapping, LN2 auto-fill |
| Aliquots | Parent–child ID + remaining quantity if they split | Robotic worklists, SPREC in the ID |
| Freeze–thaw | Count if they freeze | Numeric “max 3” (no public SOP) |

PR #21 CAR-T *samples* do **not** pull in FDA 1271 / FACT-JACIE chain of identity. COI stays parked even if the seed data includes CAR-T.

Decision #24 (process assign must not change Sample.status) matches SOP: custody/testing is an event, not a specimen identity change.

---

## 4. Test ordering

- Who: an identifiable requester (CLIA “authorized person” is clinical; research analog is PI/submitter). Not a shared lab login.
- Which sample statuses: only **accepted / available** — not quarantined or rejected. “Available for Testing” is the right gate if you keep that name.
- Panel vs single: catalog of named assays; optional panel = list of assays. Do not build clinical CMP/BMP.
- Retest: linked new order on the same sample, reason required, original result kept. Reflex engine is clinical/overkill.
- Cancel: **no public SOP**. Unverified practice: cancel before entry; after results, amend/void with reason.

---

## 5. Results + QC + review

Required to enter a result (sourced): value (numeric or qualitative), unit where applicable, analyst, system timestamp. Spec pass/fail is GMP-path useful, not R&D-required.

QC: first-class QC samples + optional block-on-fail. Full OOS module is not MVP (NCI SOP 22004 / FDA 2022 are real — they belong in a QMS later).

Who reviews: a **second person** for GxP (211.194(a)(8)). For a five-person startup R&D lab, make the gate **tenant-configurable, default off for pure R&D, on for GxP/CRO-release**. Typing Sample.status = Reviewed is not review.

Can results change after Reviewed/Reported? After **issue**, only via amendment that keeps the original (CLIA 493.1291(k); ISO 17025 7.8.8). Silent overwrite is the thing the sources forbid.

---

## 6. Audit — the real gap

`created_at/by` + `modified_at/by` is last-write metadata. It is **not** an audit trail.

Part 11 11.10(e), OECD 22, WHO, Annex 11: computer-generated, time-stamped, **old and new value**, who, when (time zone), reason on GxP change; must not obscure prior values; users cannot disable it.

For MVP GxP-ready (so you do not paint the data model into a corner): append-only events on sample, order, result, spec, user. Reason required once a result is reviewed/reported. Admin cannot edit the log.

Do not claim Part 11 compliance. FDA does not certify software. E-signatures with meaning + re-auth are post-MVP.

---

## 7. API `PATCH /samples/{id}/status` vs `PATCH /samples/{id}`

Not an SOP issue. UAT should treat both as product bugs if they disagree. SOP only cares that a status change is an attributable event with old→new.

---

## 8. Stay out of the release pack

ELN process-assign, cohort start / `StartCohortPanel`, LimsRuns, dose-response, workflow templates, parsers, EPA/soil leftovers, hospital two-patient-ID, verbal orders, CGT COI / ISBT 128, live environmental monitoring.

UAT data: use PR #21 BioTech types (mAb PK, plasmids, CAR-T as *samples*), not Project Alpha / Method 8080.

---

## What to hand whom

- **Wilhelmina:** three-pillar stories only. New AC candidates: immutable lab ID (external ID stored separately); reject/quarantine as dispositions; result amendment keeps original; audit old/new; Reviewed/Reported live on the result. Park CoC/storage/aliquot *depth* as non-blocking unless already in supporting config.
- **Tobias:** scenarios for free-form status (anyone with `sample:update` can type Reviewed — that is not second-person review); reject and quarantine paths; amendment vs overwrite; duplicate barcode; barcode suffix changing identity; QA seat packet on sample/results/audit/security. Do not use the 2026-02-24 64/65 run as baseline.
- **Deiter:** timestamp-suffix barcode fails the “will a tech do this without mix-ups” test. External ID ≠ lab ID. Quarantine is a bin, not a comment. Volume remaining on aliquot.
- **Hans:** capture assay identity, units, QC pass/fail, who entered, who reviewed. CAR-T seed ≠ COI module. No dose-response in MVP.
- **Marc:** this stays inside the BioTech/Pharma wedge. No environmental/clinical drift.

---

## Honest gaps (still)

- No public SOP for the product’s five-name list.
- No public SOP for barcode timestamp suffixes (against the grain of NCI/ISBER).
- No public cancel-order SOP.
- No public numeric freeze–thaw limit.
- NCI SOP 22002 (test request form) PDF was not retrieved; do not invent its field list.

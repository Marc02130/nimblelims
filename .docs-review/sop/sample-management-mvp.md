# NimbleLIMS SOP pack: sample management (MVP)

Compiled 20 Aug 2026. Public/standard sources only. Clinical (CLIA/CAP/WHO hospital) identity rules are cited as **do not copy**, not as the default.

**Model this product on:** NCI Best Practices (2016), ISBER Best Practices, ISO 20387 biobanking clauses, NCI GTEx OP-0011 Chain of Custody. Keep 21 CFR 58.130 / OECD GLP 19 as the GLP-shaped *record*, not as hardcoded retention clocks.

**Do not model MVP on:** hospital two-patient identifiers, verbal orders, unlabeled-tube “collector comes to lab,” CGT chain of identity / ISBT 128, live freezer mapping.

---

## 1. Sample receipt / accessioning

### Concrete process (research/biotech)

1. Inspect the package for tampering (GTEx OP-0011).
2. Open and verify contents against the shipping manifest (GTEx OP-0011; VCU CR-CO-570 2025).
3. Record receipt **date and time** and who received it (CLIA 493.1242(b) requires time; OECD GLP 19 records date and condition; use time even for research).
4. Record condition: intact / leaking / damaged / tampered; temperature or “sufficient dry ice remaining” (GTEx; CDC accessioning; OECD 19).
5. Assign the lab unique ID and introduce the sample into the register (WHO LQSI reception SOP, transferable).
6. Disposition: **accept**, **reject**, or **quarantine**. Quarantine until ID/label discrepancies are resolved (GTEx: resolve within 24 hours; ISO 20387: segregate from final storage until legal/ethical/quality checks complete).
7. Notify the sender of count or identity discrepancies (VCU 2025; GTEx).

### Edge cases named in the sources

| Edge case | Required handling | Source |
|---|---|---|
| Count shipped ≠ count received | Notify; quarantine until IDs resolved (24 h in GTEx) | GTEx OP-0011 8.10 |
| Unlabeled, leak, undocumented custody, RT too long | May reject | TJU HBB SOP; BioSEND 2025; PPMI |
| Form vs label mismatch | IDs on form must match IDs on label | CDC; UNMC |
| Weekend / holiday delivery | Treat as nonconformance if unexpected; some reference labs refuse | PPMI; CDC Mycotic |
| After-hours unmanned facility | Publish hours and emergency contacts; **no public after-hours accessioning SOP found** | ISBER 4th A3.4 |
| Precious unlabeled specimen (CSF, tissue) | Hospital labs may process with senior auth + disclaimer. **Do not copy.** Research: quarantine / reject, do not relabel from memory | UK BCPS 2025 vs GTEx |
| Verbal request | Clinical-only (CLIA 493.1241). **Not in research SOPs found** | WHO; CLIA |

### LIMS fields at receipt

Submitter/study, external ID(s), lab unique ID, sample type, container type, quantity+unit, collection datetime, receipt datetime, acceptor, requested tests, condition, manifest match, accept/reject/quarantine + reason, shipper/tracking, whether the lab collected it or received it (ISO 20387 7.3.2.6).

### UAT notes

- Reject path leaves a durable record (do not delete the sample).
- Quarantine is a real status, not a comment.
- Receipt time is recorded, not date-only.
- Manifest mismatch can still create a receipt event.

---

## 2. Identification / labeling

### Concrete process

- Every container gets a **unique** lab ID that is machine-readable **and** human-readable (NCI B.6.2; ISBER).
- Each aliquot/extract is a **new** biospecimen with a **new** ID; origin recorded (NCI).
- ID **must not** encode storage location, clinical data, or patient/donor identifiers (NCI; ISBER). No PHI on the research label.
- GLP minimum on or with the container: test system, study, specimen nature, collection date (21 CFR 58.130(c)). If the vial is too small, a unique reference traceable to fuller info (OECD 19).
- Labels must survive the storage condition (ISBER: validate at actual storage temps).

**Do not** default to CAP GEN.40491 / two *patient* identifiers (name + DOB/MRN). That is hospital/clinical.

### Edge cases

- Duplicate submitter names (UC Davis core: billed rework). **No public SOP for a collision algorithm** — product must still refuse or warn on duplicate lab barcodes.
- PHI printed on a research label is an ISBER/NCI anti-requirement.
- Barcode placement must not make the vial unusable (GTEx cassette note).

### UAT notes

- Print/scan unique barcode per aliquot, not shared parent barcode.
- Label text has no donor name/MRN/SSN.
- Parent ID is recorded on children.

---

## 3. Chain of custody

CoC is an **event log**, not a status enum. GTEx OP-0011: chronological movement from collection through shipment, receipt, possession, handling, processing, analysis, and final storage (including return on consent withdrawal).

### Concrete process

- At transfer: who, from, to, datetime, remaining quantity (21 CFR 58.107; OECD 19).
- Custody exists if: physical possession, secured against tampering, **or** restricted-access storage (GTEx).
- Shipping: manifest in the package + electronic copy; recipient verifies labels vs packing list (NCI B.2.8.2).
- Deviations on the CoC (ISO 20387 7.4.2: duration/temp/humidity/light if they can alter quality).
- Paper fallback only if the electronic system is down; enter electronically when it returns (GTEx).

### MVP vs overkill

- **MVP:** who received it, when, from whom, current location/custodian, condition.
- **Not MVP:** forensic every-internal-handoff paper form; 10-year CoC retention as a hardcoded default (GTEx 10 years is project-specific).

**Chain of identity (COI)** is not CoC. COI appears in FDA CAR-T 2024, 21 CFR 1271.290, FACT-JACIE 2025. It is autologous CGT. **Out of MVP.**

---

## 4. Storage and freeze–thaw

### Concrete process

- Map unique ID to unit → box → position (NCI: must identify each position).
- Record storage-temp class. When in doubt for research biospecimens: −80 °C or LN2 vapor (NCI).
- **Count freeze–thaw cycles.** WHO 5-5: “must be monitored.” BRISQ: freeze–thaw count is a Tier 2 data element. ISBER 5th: if you cannot say how many times an aliquot was thawed, that is a data gap.
- Avoid unnecessary freeze–thaw by sizing aliquots in advance (NCI; CAP). Sources say **avoid and count**, not “max N cycles.” **No public SOP found with a numeric limit.**
- Restricted access, authorized personnel only (21 CFR 58.51 / 58.190; OECD 1 §10.3; ISO 20387).
- Inventory verification at planned intervals (ISO 20387; WHO).

### Edge cases

- Freezer failure / excursion: record the deviation (NCI). Live probe integration is **overkill for MVP**; an excursion flag is enough.
- Frost-free auto-defrost can thaw specimens (CAP).
- After-hours unmanned monitoring: ISBER wants alarms/contacts, not a LIMS SOP.

### UAT notes

- Moving a vial updates location without changing identity.
- Aliquoting a frozen parent increments freeze–thaw (or child starts at 0 after a thaw, but the thaw is recorded). Product should not silently lose the count.
- Checked-out vs in-storage is visible.

---

## 5. Aliquoting / splitting

### Concrete process (NCI + WHO + UB Biobank)

1. Decide aliquot size/number in advance so the parent is not repeatedly thawed.
2. Record personnel, date, **time**, volumes taken and remaining (NCI B.3.3.1 / B.6.2.1).
3. Each child gets a new unique ID linked to parent (genealogy).
4. Restocking unused returned aliquots is **not recommended**; if done, track possible compromise (NCI).

**No public SOP found** that mandates a specific aliquot volume or a status named “aliquoted.” Remaining quantity is the real signal of depletion.

### UAT notes

- Parent remaining quantity decreases; children are independently locatable.
- Deleting a child does not delete the parent history.
- Cannot aliquot more than remaining quantity.

---

## 6. Status lifecycle (synthesis, not a fake SOP)

**No public SOP defines** `{received, in storage, in testing, depleted, discarded}`. Closest real language:

| Suggested status | Closest source language | MVP |
|---|---|---|
| Received | GTEx logged ‘received’; WHO register | yes |
| Quarantined | GTEx; ISO 20387 segregated until checks complete | yes |
| Accepted / rejected | WHO; CLIA 493.1242; CDC | yes |
| In storage | ISO 7.7; NCI B.2.6 | yes |
| Checked out / in testing | NCI “distribution”; CoC possession | yes |
| Depleted | quantity remaining → 0 (NCI, OECD) | yes (quantity-driven) |
| Discarded / destroyed | ISBER M3; WHO disposal; OECD 19 §73 | yes |
| Expected / in transit | GTEx shipment in progress | later |
| Recalled / consent withdrawn | GTEx CoC scope; ISO 7.7.8 | later unless human-subject biobank |

Keep **event history** (CoC + processing). ISO 20387 and NCI require reconstructing history, not only current state.

---

## 7. Disposal / retention

### Concrete process

- Disposal is documented: who, when, method, remaining qty = 0 (WHO 5-5; OECD 19 §73; ISBER M3).
- Records **survive** specimen destruction (ISO 20387 4.1.8).
- GLP retention math (21 CFR 58.195: 2 years after approval or 5 after submission, etc.) is **not** a startup default. Make retain-until configurable; do not hardcode 58.195.
- CLIA pathology clocks (slides 10 y, blocks 2 y) are **hospital-only. Do not use for research aliquots.**

### UAT notes

- Discarded samples still searchable by ID.
- Early disposal can carry a justification field (GLP/OECD).
- Consent-withdrawal is a later flag, not an MVP blocker unless the lab is a human biobank.

---

## 8. Sample-record integrity (not a handling SOP)

21 CFR 58.130(e) / MHRA ALCOA+ applied to sample records:

- Attributable user on every receipt, move, aliquot, dispose.
- Contemporaneous (receipt **time**).
- Corrections do not obscure the original; reason + who + when.
- Rejected/discarded samples are not hard-deleted.
- Timestamps consistent (ship before receive).

MVP: unique users, timestamps, audit of corrections. Do not claim 21 CFR Part 11 compliance without validation evidence. Do not allow shared logins or silent overwrites (paints the data model into a corner).

---

## 9. What not to invent

Common lab habits **with no public SOP found**:

- A universal status vocabulary matching the product enum above.
- Numeric freeze–thaw limit (e.g. max 3).
- After-hours accessioning step-by-step.
- Duplicate-barcode collision algorithm.
- Required barcode symbology (Code 128 vs DataMatrix). ISBER says barcode/RFID, not which. 2D on cryovials is common practice.
- GDP for laboratory samples (GDP is medicinal-product distribution).
- EMA accessioning SOP.

---

## 10. Minimum data shape implied by the sources

```
Sample: lab_id (immutable), barcode, external_ids[], study_id, type,
        collection_datetime, parent_id, quantity + remaining,
        storage_temp_class, location (unit/rack/box/position),
        freeze_thaw_count, status, quarantine_flag + reason

ReceiptEvent: received_at, received_by, condition, temp_or_dry_ice,
              manifest_match, accept|reject|quarantine

CustodyEvent: from, to, at, by, remaining_qty

AliquotEvent: parent, children[], volumes, by, at

DisposalEvent: at, by, method, justification
```

---

## Primary sources

- NCI Best Practices for Biospecimen Resources (2016): https://dctd.cancer.gov/data-tools-biospecimens/biospecimens-biobanks/resources/best-practices/best-practices-2016.pdf
- NCI GTEx BBRB-OP-0011 Chain of Custody: https://dctd.cancer.gov/data-tools-biospecimens/biospecimens-biobanks/resources/sops/gtex/bbrb-op-0011.pdf
- ISO 20387:2018 (clause-level via NATA worksheet): https://nata.com.au/files/2021/12/ISO-20387-Assessment-Worksheet.pdf
- ISBER Best Practices 4th ed. (2018 public PDF) / 5th ed. 2023 (current, download)
- WHO LQMS Ch. 5 Sample Management: https://extranet.who.int/lqsi/sites/default/files/attachedfiles/LQMS%205-4%20Sample%20Processing.pdf
- 21 CFR 58.130 / 58.107 / 58.190 / 58.195
- OECD GLP Advisory Document 19 (2018): test-item receipt/label/quantity/disposal
- BioSEND PSP Manual of Procedures (April 2025); PPMI Biologics MOP V12 (nonconformance lists)
- VCU CR-CO-570 (July 2025); UNMC CRC SOP CO03

# Decision log: Extract-hold dual-map kick-back

**Date:** 2026-08-24; **Decided** 2026-09-10  
**Status:** **Decided** (Marc, 2026-09-10). Implement may proceed against this log.  
**Domain:** Sample processing (aliquot/pool)  
**Related:** [prd/sample-processing/PRD.md](../prd/sample-processing/PRD.md) · [specs/sample-processing/SPEC.md](../specs/sample-processing/SPEC.md) · `.docs/review/tech-sketch/extract-hold-dest-type.md` · [mass-concentration-contents.md](../review/tech-sketch/mass-concentration-contents.md)

Do **not** recode dest-follow (C2/C3). Do **not** put mass/conc on Sample. Not IC50.

---

## Stamps from OQ walk (2026-08-23) — still stand, now answered

| ID | Stamp | 2026-09-10 |
|----|--------|------------|
| OQ-1 | Dest vol/amount/conc on **entry FieldDefinitions** until a gate; then inventory | **Plan** holds working qty. Dest FDs are dest-entry **shape**, not the working ledger. |
| OQ-2 | **No** entry-level sample-type gate; gate on **experiment / LimsRun** | **Decided.** Entry gates cost too much config for too little benefit. |
| OQ-3 | S3 catalog = API + thin admin UI, `config:edit` | Unchanged (E-14). |
| OQ-4 | Atomic pair on **template and ad hoc** | Unchanged (E-10). |
| OQ-5 | Kick-back — fields are not Sample fields during capture | **Decided.** Capture = plan. Inventory + new sample = **dest init**, one transaction. |

## Questions for Heidi + Mathilda (± Lab Ops) — answered

| # | Question | Decision |
|---|---------|----------|
| 1 | Which entry holds working qty before inventory updates? | **Plan** (`aliquot_pool_plan`). Tech types source/dest vol, target amount, N, etc. there. Dest entry does not hold working qty before dest init. |
| 2 | What unlocks Contents/Container write? | **Dest init.** Requires **destination container type** known (else **422**). Dest init does not prompt dest sample type (that stays on the plan: line → default → parent). |
| 3 | Exact write-back map? | **One transaction:** source depleted **and** dest vol / conc / amount written to Contents / 1×1 Container. No half-mint. |
| 4 | Attach immediately = FD columns on the entry only? | **Yes.** See below. |
| 5 | Rewrite AC12 / type gate? | Type gate is on **experiment and LimsRun**, not entry. |

**Mint is not a sixth question on this list.** Minting a new sample (derivative **or** pool) happens **at dest init**, in that same transaction as inventory. Q1–Q5 are capture vs inventory vs gates. Dest init is the mint gate.

---

## Question 4 — what “attach immediately” is (and is not)

METHOD_CATALOG dual map, on **method select**:

| Map | Attached onto | Meaning |
|-----|---------------|---------|
| Plan columns | `aliquot_pool_plan` | Working-qty fields the tech fills (Q1). |
| Dest FieldDefinitions | `aliquots_pools` | Column **shape** of the dest entry after mint (volume / amount / concentration per method). |

**Is:** linking FieldDefinitions / columns onto those **entries**. The dest table knows what it will show. The plan knows what to type. No later optional wiring.

**Is not:** touching Sample, Contents, or Container. Not depleting source. Not minting a daughter. Not copying plan numbers into inventory.

Method-select is schema. **Dest init** is the write. Dest FD cells after dest init are RO projections (or same-transaction write-through) of Contents / 1×1 Container — not a second ledger, not Sample columns.

---

## Dest init (one transaction)

Must already know:

- Method → exactly one `mint_op`
- Dest **sample type** (plan resolve: line → entry default → parent; catalog)
- Dest **container type** (required; missing → **422**)
- Plan working qty

Then in **one** transaction:

1. Mint dest **sample** (derivative or pool) + dest **container** of that type + **contents**
2. Deplete source contents
3. Write dest vol / conc / amount onto Contents / 1×1 Container
4. Fill dest entry rows (`sample_id`-linked); dest FD cells project those owners
5. Process join: dest continues; inbound source assignment **removed** (already Pass — do not recode)

Save still persists the plan only. Generic entry submit still must **not** mint.

Dest **sample type** ≠ dest **container type**. Method ≠ either. Do not collapse those three controls.

---

## Bounce

- Working qty on Sample or on dest entry before dest init
- Inventory write at method-select, plan save, or generic submit
- Source deplete without dest inventory (or the reverse) — not one transaction
- Dest init without dest container type
- New Sample columns for vol / amount / conc
- Sample-type gate on the entry
- Treating Q1–Q5 as the mint design — mint **is** dest init

---

## Dest container type control (2026-09-10)

Same pattern as dest sample type. Distinct from method and dest sample type. Dest init does **not** prompt.

| Layer | Control |
|-------|---------|
| Entry / template | `default_dest_container_type` — optional. Empty = Same as source vessel. |
| Line | Use entry default · Same as source · pick a **1×1** container type |
| Existing dest vessel | `dest_container_id` set → type not used for mint |

Resolve: line override → entry default → source container type. Missing after that → **422** `dest_container_type_required`. Non-1×1 (plate as dest mint) → **422** `dest_container_type_not_1x1`.

## Left after this stamp (not a reopen of Q1–Q5)

- E-10 atomic-pair UI; E-14 transition admin; E-12 dest **sample** type on template.
- E-11 dest FD attach implements this dual map (now unblocked for coding against this log).

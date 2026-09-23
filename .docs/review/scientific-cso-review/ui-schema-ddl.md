# Scientific CSO review: UI-driven schema DDL

**Date:** 2026-09-22  
**Reviewer:** Hans (Scientific CSO)  
**Stem:** `ui-schema-ddl`  
**Packet tip cited:** `c6f0854` (`docs/ui-schema-ddl`)  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**OQs:** [`.docs/review/open-questions/ui-schema-ddl.md`](../open-questions/ui-schema-ddl.md)  
**Not IC50. No product code.**

## Verdict

**Science Accept with conditions** (2026-09-22).

## Conditions (punches)

1. **SOP hint grains** — public SOP field-name hints on the column registry only; no house SOP text in git. **Marc overwrite:** **matrix removed** — use **sample type**; **vessel = container** synonym; keep barcode ≠ sample ID; container ≠ sample type; parent = `parent_sample_id`.  
2. **OQ-9 deprecate** — deprecate/archive path before destructive DROP of data-bearing scientific fields.  
3. **OQ-6 identity protect** — UI allow-list must not casually overwrite identity / lineage fields.  
4. **Classic Results first-class** — **Confirm stands** (Marc overwrite): structured Results remain first-class; JSONB payloads are **data** (OQ-16), not a config or Results substitute.  
5. **No quantity+unit** compound column type in this packet.

## Aligns

- OQ-16 JSONB = instrument/payload data only; bounce JSONB-as-config.  
- Layout vs privilege separation (bench vs review) stays intact.

## Out of scope / bounce

- Replacing Results with opaque JSONB bags for configuration.  
- Shipping quantity+unit as one primitive before a later science lock.

## Gate

Implement remains **CLOSED**. Original punches stand (this note is not a Science restamp).

**Fold note 2026-09-22:** [Brief](../requirements/ui-schema-ddl-brief.md) written — punches baked (SOP hint grains; OQ-9 deprecate; OQ-6 identity protect; classic Results first-class; no quantity+unit). Lab Ops + Günter Accept-with-conditions already on packet. Still waiting **Design Group UX Accept** and **Günter restamp**.

**Fold note 2026-09-23 (Marc Leadership overwrite; Rolf Confirm):** SOP hints — matrix out / sample type in; vessel=container; classic Results Confirm stands.

**Confirm 2026-09-23 (Hans; Rolf):** Marc Leadership overwrite Confirmed — SOP hints (matrix→sample type; vessel=container) + classic Results Confirm stands. Implement CLOSED.

## Marc Leadership overwrite — layout visibility (2026-09-23; Rolf Confirm)

**No “hidden” on layout.** Visibility = **membership** on the layout only. Do **not** add a hide / Visible toggle that keeps the field on the layout as hidden.

| Case | Rule |
|------|------|
| **Show** | Field is on the role × screen layout. |
| **Not shown** | Field is **not added** to the layout (absent = not shown — Deiter stands). |
| Neither read nor write | Not displayed; layout editor **must not offer** that field. |
| Read yes / Write no | May appear on layout as **read-only** — from **privileges**, not a layout hide. |

Retract any remaining copy that implies a hide mode or three-mode Hide / Read-only / Deny. Dated Confirm lines above that say CLOSED are history.

## Implement gate OPEN (2026-09-23; Rolf)

Design Group UX Accept **Met** @ `f79e2a0`. Günter Brief restamp **Met**. Implement **OPEN**. Next: Marc green-light. This note is not a Science restamp of the original Accept.


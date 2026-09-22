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

1. **SOP hint grains** — public SOP field-name hints on the column registry only; no house SOP text in git.  
2. **OQ-9 deprecate** — deprecate/archive path before destructive DROP of data-bearing scientific fields.  
3. **OQ-6 identity protect** — UI allow-list must not casually overwrite identity / lineage fields.  
4. **Classic Results first-class** — structured Results remain first-class; JSONB payloads are **data** (OQ-16), not a config or Results substitute.  
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

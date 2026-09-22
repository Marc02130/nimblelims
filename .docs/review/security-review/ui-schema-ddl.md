# Security / CSO review: UI-driven schema DDL

**Date:** 2026-09-22  
**Reviewer:** Günter (Security / CSO)  
**Stem:** `ui-schema-ddl`  
**Packet tip cited:** `c6f0854` (`docs/ui-schema-ddl`)  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**OQs:** [`.docs/review/open-questions/ui-schema-ddl.md`](../open-questions/ui-schema-ddl.md)  
**Not IC50. No product code.**

## Verdict

**CSO Accept with conditions** (2026-09-22).

## Conditions — S-UI-1…6

| ID | Condition |
|----|-----------|
| **S-UI-1** | **schema-admin** only for CREATE/ALTER and schema-registry mutate |
| **S-UI-2** | **FORCE RLS** on UI-created / UI-extended relations |
| **S-UI-3** | Privileges **default-deny** enforced in the **API** (not layout/UI alone) |
| **S-UI-4** | **layout-admin ≠ DDL** |
| **S-UI-5** | No **`lims_app` bypass** of RLS or privilege checks |
| **S-UI-6** | Destructive **DROP**/remove requires confirm + audit |

## Aligns

- OQ-3 privileges ≠ OQ-2 layout
- OQ-16 JSONB = payload data only; bounce JSONB-as-config
- Tobias Fail bars (1)–(5)

## Gate

Implement remains **CLOSED**. Original S-UI-1…6 stand (this note is not a CSO restamp).

**Fold note 2026-09-22:** [Brief](../requirements/ui-schema-ddl-brief.md) written — S-UI-1…6 baked in (schema-admin only; FORCE RLS; default-deny API; layout-admin ≠ DDL; revoke `lims_app` CREATE on `public`; DROP confirm+audit). Still waiting **Design Group UX Accept** and **Günter restamp** that S-UI-1…6 still hold under the Brief.

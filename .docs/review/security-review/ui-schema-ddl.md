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
| **S-UI-1** | Permission **`schema:edit`** only for CREATE/ALTER and schema-registry mutate — not a new role; admin-assignable |
| **S-UI-2** | **FORCE RLS** on UI-created / UI-extended relations |
| **S-UI-3** | Privileges **default-deny** enforced in the **API** (not layout/UI alone) |
| **S-UI-4** | Permission **`layout:edit`** ≠ DDL; privilege Write never mints **`schema:edit`** |
| **S-UI-5** | No **`lims_app` bypass** of RLS or privilege checks |
| **S-UI-6** | Destructive **DROP**/remove requires confirm + audit |

## Aligns

- OQ-3 privileges ≠ OQ-2 layout
- OQ-16 JSONB = payload data only; bounce JSONB-as-config
- Tobias Fail bars (1)–(5)

## Gate

Implement remains **CLOSED**. Original S-UI-1…6 stand (this note is not a CSO restamp).

**Fold note 2026-09-22:** [Brief](../requirements/ui-schema-ddl-brief.md) written — S-UI-1…6 baked in (schema-admin only; FORCE RLS; default-deny API; layout-admin ≠ DDL; revoke `lims_app` CREATE on `public`; DROP confirm+audit). Still waiting **Design Group UX Accept** and **Günter restamp** that S-UI-1…6 still hold under the Brief.

**Fold note 2026-09-23 (Marc Leadership overwrite; Rolf Confirm):** S-UI-1 = permission `schema:edit` (not a new role). S-UI-4 = permission `layout:edit`; cannot DDL; privilege write never mints `schema:edit`. Günter restamp still pending under Brief (Brief-level S-UI hold).

**Confirm 2026-09-23 (Günter; Rolf):** Marc Leadership overwrite Confirmed — S-UI-1=`schema:edit`; S-UI-4=`layout:edit`. Implement CLOSED. Brief-level Günter restamp still separate / pending.

**Günter Confirm follow-on (2026-09-23; Rolf):** Admin role **defaults** to permission **`schema:edit`** + privilege admin (small-startup / no full-time IT) — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later. Optional separate schema role later. Permission **`layout:edit`** still no DDL. **S-UI-2 / S-UI-3 / S-UI-5 / S-UI-6** unchanged.

**Marc Confirm (2026-09-23; Rolf):** Default **`schema:edit`** + privilege admin = **Admin only** (not lab manager). **Closed.** Optional re-assign later. Implement CLOSED.

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

Design Group UX Accept **Met** @ `f79e2a0`. Günter Brief restamp **Met**. Implement **OPEN**. Next: Marc green-light. This note is not a CSO restamp of the original Accept.


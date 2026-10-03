# Brief stub: ui-schema-tables-cleanup

**Status:** P1 **implemented** 2026-10-03 under Marc's product locks (OQ-1 = B allow-list, OQ-2 = A park, OQ-3 = B lazy register; M:N deferred until ids are globally unique). Delta: `.docs/review/schema-changes/ui-schema-tables-cleanup.md` (alembic 0082). UAT: `UAT_Scripts/uat-ui-schema-tables-cleanup.md` (pass pending). Manual: `manuals/ui-schema.md`. The stub text below is history.

**Locks in:** Kill Custom Fields completely; Schema Tables allow-list includes **`project`** + **`samples`** + UI-created; **relations** 1:N/1:1/M:N as real FKs/junctions; implement CLOSED until Brief + Design + Marc green-light.

**Blocked on:** OQ-1 Marc; OQ-2 cutover; OQ-3 registry seed; OQ-5a–e (relation UI / on-delete / Related-list / junction visibility — default schema:edit only).

**M:N:** junctions behind the scenes; operators link/unlink only.

**Fail bars:** Tobias (1)–(6) provisional until OQ-1 freeze. **(7)** CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → Fail (provisional until OQ-5b freezes).

**Research cite:** Odoo / SAP / LIMSbase under OQ-5 — locks stand.

**UX sketch:** tip `564fe6f` pending Accept (PR 139). Spec base `07ccd59`. Encoded: Custom Fields kill; Tables = Samples + Project + UI-created; Relations tab; link/unlink; junction `schema:edit` only. OQ-1 / OQ-5b still open. Implement **CLOSED**.

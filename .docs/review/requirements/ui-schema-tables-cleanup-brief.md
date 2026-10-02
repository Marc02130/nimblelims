# Brief stub: ui-schema-tables-cleanup

**Status:** Stub only — full Brief after Marc decides OQ-1 (allow-list) and Spec folds OQ-2/3 with Heidi/Mathilda.

**Locks in:** Kill Custom Fields completely; Schema Tables allow-list includes **`project`** + **`samples`** + UI-created; **relations** 1:N/1:1/M:N as real FKs/junctions; implement CLOSED until Brief + Design + Marc green-light.

**Blocked on:** OQ-1 Marc; OQ-2 cutover; OQ-3 registry seed; OQ-5a–e (relation UI / on-delete / Related-list / junction visibility — default schema:edit only).

**M:N:** junctions behind the scenes; operators link/unlink only.

**Fail bars:** Tobias (1)–(6) provisional until OQ-1 freeze. **(7)** CASCADE or silent wipe on identity links (sample/barcode vessel) where Spec says RESTRICT → Fail (provisional until OQ-5b freezes).

**Research cite:** Odoo / SAP / LIMSbase under OQ-5 — locks stand.

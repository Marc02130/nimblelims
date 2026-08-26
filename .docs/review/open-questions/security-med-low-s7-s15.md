# Open questions: security-med-low-s7-s15

**Status:** Living decision log — **decisions stamped 2026-08-21**  
**Requirements:** [`.docs-review/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)

| ID | Question | Status | Blocks | Answer / notes | Date | Owner |
|----|----------|--------|--------|----------------|------|-------|
| OQ-S9 | Who may call `/results/validate` after AuthN? | **Decided** | P1 | **`result:enter` OR `result:review` only** (not read-only). | 2026-08-21 | Product + Security |
| OQ-S10 | httpOnly cookie JWT / BFF this cycle? | **Decided** | P4 → expands | **Yes — design httpOnly cookies / BFF this cycle** (not docs-only). Scope expansion: see requirements § FR-S10. | 2026-08-21 | CEO + Security |
| OQ-S11a | Containers `created_by` / empty containers | **Decided** | P3 (+ aliquot path) | **Atomic dest create:** one transaction; RLS allows **INSERT** when `created_by = current_user_id()`; SELECT/UPDATE/DELETE via admin or contents→sample→project (tighten off FOR ALL). **Never commit** a container without contents. Product rule: no empty tube/plate/box as an outcome—empty wells on a plate are fine; creating a barren container is not. | 2026-08-21 | Product + Arch |
| OQ-S11b | Enable RLS on `contents`? | **Decided** | P3 | **Enable + policy in P3** mirroring sample/project access; aliquot INSERT contents must still work for labtech. | 2026-08-21 | Arch + Security |
| OQ-S12 | Prod DB port exposure | **Decided** | P3 | **`docker-compose.prod.yml` overlay**; no host `:5432`. Local compose may keep published port. | 2026-08-21 | Eng |
| OQ-S14 | biotype / temperature dual role | **Decided** | P1 | **Drop from `SAMPLE_WRITE_BACK_COLUMNS`**; keep as sample system display (RO in grids). | 2026-08-21 | Product |
| OQ-S15 | Login lockout storage | **Decided** | P2 | **Postgres table** (no Redis). Survives restarts/workers. | 2026-08-21 | Eng |
| OQ-S7-retest | Unassigned same-client lab access | **Decided** | UAT hold fix | **Lab Technician / Lab Manager** (non-System): **`project_users` only** — no same-client / `client_projects` short-circuit. **Client** role keeps same-client. Admin + System client unchanged. Migration `0065`. | 2026-08-21 | Product + Security |
| OQ-S10-denylist | Logout revoke JWT | **Decided** | UAT residual | **Postgres `revoked_tokens` (jti)** on logout (+ password change). No Redis. Migration `0066`. | 2026-08-21 | Security |

## Gate rule

- **P1:** Unblocked (S8, S9, S13, S14 decided).  
- **P2:** Unblocked (S7, S15 decided — lockout table in schema).  
- **P3:** Unblocked (S11a/b, S12 decided).  
- **P4:** Now includes **httpOnly cookie / BFF design + implement** (larger than original docs-only S10).

## Decision detail — OQ-S11a (empty containers)

**Product:** Do not create empty containers as a LIMS outcome. Plates/boxes may have empty wells/slots as structure; a new tube/plate/box with no contents should not be committed.

**Eng:** Aliquot dest create stays one DB transaction: INSERT container (WITH CHECK via `created_by`) → INSERT contents → INSERT/link sample. If contents step fails → full rollback (already S5). Policy tighten: `created_by` for INSERT path only; ongoing visibility via project/contents.

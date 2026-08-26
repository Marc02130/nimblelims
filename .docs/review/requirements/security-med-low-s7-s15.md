# Requirements: Med/Low security remediation (S7–S15)

**Date:** 2026-08-21  
**Status:** **Implemented on branch** (P1–P4) — live UAT / merge pending  
**Branch:** `security/med-low-s7-s15`  
**Source audit:** [`.docs-review/security-review/codebase.md`](../security-review/codebase.md)  
**Idea:** local `.docs-internal/ideas/security-med-low-s7-s15.md` (not committed)  
**Tech sketch:** [`.docs-review/tech-sketch/security-med-low-s7-s15.md`](../tech-sketch/security-med-low-s7-s15.md)  
**Schema changes:** [`.docs-review/schema-changes/security-med-low-s7-s15.md`](../schema-changes/security-med-low-s7-s15.md)  
**Open questions:** [`.docs-review/open-questions/security-med-low-s7-s15.md`](../open-questions/security-med-low-s7-s15.md)  
**Checklist:** [`.docs-review/checklist/security-med-low-s7-s15.md`](../checklist/security-med-low-s7-s15.md)  
**Prerequisite:** High S1–S6 **Met** ([security-high-s1-s6](security-high-s1-s6.md))

## Review packet

| Review | Doc | Gate |
|--------|-----|------|
| CEO / product | [ceo-review/security-med-low-s7-s15.md](../ceo-review/security-med-low-s7-s15.md) | Required |
| Architecture | [architecture-review/security-med-low-s7-s15.md](../architecture-review/security-med-low-s7-s15.md) | Required |
| Security (CSO) | [security-review/security-med-low-s7-s15.md](../security-review/security-med-low-s7-s15.md) | Required |
| QA / Testing | [qa-review/security-med-low-s7-s15.md](../qa-review/security-med-low-s7-s15.md) | Required |
| Lab Ops / UI | — | **Skipped** unless S7/S14 change bench-visible copy (then thin pass) |

---

## 1. Problem

High findings are closed. Remaining risks:

- Cohort start may accept samples the caller should not touch across client/project boundaries (S7).  
- Unbounded SOP / run import uploads enable DoS (S8).  
- Unauthenticated result validation endpoint (S9).  
- UI AuthZ theater if docs/claim RLS incorrectly (S10).  
- Incomplete FORCE RLS / GUC story on remaining tables; containers `created_by` FOR ALL residual (S11).  
- Default compose publishes Postgres `:5432` with known password (S12).  
- Loose verify-email / catalog GETs (S13).  
- Conflicting FieldDefinition semantics for biotype/temperature (S14).  
- No login brute-force control (S15).

## 2. Goals

| ID | Goal |
|----|------|
| G1 | Start/link paths enforce caller client/project access in addition to sample existence and Decision #24 gates |
| G2 | Upload endpoints hard-cap at **10 MB** (SOP + run import-file; align parser setup if not already) |
| G3 | `/results/validate` requires authentication (and sensible permission) |
| G4 | Docs/comments state clearly: server RBAC/RLS is AuthZ; frontend `hasPermission` / `localStorage` are UX only |
| G5 | Expand FORCE RLS where policies exist but FORCE is off; keep GUC bind correct; decide containers `created_by` scope |
| G6 | Prod compose profile does not publish DB port with default password |
| G7 | verify-email and role/permission list endpoints least-privilege |
| G8 | Write-back allowlist and system-RO sample fields are mutually exclusive |
| G9 | Login rate limit / temporary lockout |

## 3. Non-goals

- Full WAF / CDN rate limiting (app-level + optional reverse-proxy notes)  
- Rewriting all RLS policy expressions beyond FORCE + documented residuals  
- Changing High S1–S6 behavior  
- Opaque server-side session store (JWT-in-cookie is sufficient for this cycle)  

---

## 4. Functional requirements by finding

### FR-S7 — Start experiment / run: client & project enforcement

| ID | Requirement |
|----|-------------|
| FR-S7.1 | On experiment start / sample link (and LIMS run start cohort where applicable), system shall reject samples the caller cannot access via the same rules as sample read (RLS / `has_project_access` / client scope)—not only “sample row exists.” |
| FR-S7.2 | Cross-client samples shall fail closed with **403/404** (no existence oracle preferred: 404). |
| FR-S7.3 | Decision #24 eligibility (Available for Testing, process membership) remains; S7 is an **additional** gate. |
| FR-S7.4 | Negative tests: user A cannot start experiment with user B’s inaccessible sample ID. |

### FR-S8 — Upload size caps

| ID | Requirement |
|----|-------------|
| FR-S8.1 | `POST /v1/lims-runs/{id}/import-file` shall reject bodies/files **> 10 MB** with **413** or **400** and clear code. |
| FR-S8.2 | SOP parse upload(s) shall enforce the same **10 MB** per file. |
| FR-S8.3 | Parser setup/test endpoints already capped shall remain capped; document parity. |
| FR-S8.4 | Cap enforced server-side (not only nginx client_max_body_size), though nginx alignment is required for Docker. |

### FR-S9 — Authenticate results validate

| ID | Requirement |
|----|-------------|
| FR-S9.1 | `POST /results/validate` shall require authenticated user (`get_current_user`). |
| FR-S9.2 | Permission: **`result:enter` OR `result:review`** only (OQ-S9). Not `result:read` alone. |
| FR-S9.3 | Unauthenticated call → **401**; insufficient permission → **403**. |

### FR-S10 — httpOnly cookie AuthN + AuthZ honesty (OQ-S10 expanded)

| ID | Requirement |
|----|-------------|
| FR-S10.1 | Replace (or dual-run then cut over) `localStorage` JWT with **httpOnly, Secure, SameSite** cookie session (or BFF pattern) so XSS cannot read the token. |
| FR-S10.2 | Frontend `hasPermission` remains UX only; manuals state server RBAC/RLS is AuthZ. |
| FR-S10.3 | CORS / CSRF: cookie auth shall include CSRF defense appropriate to SameSite choice (e.g. SameSite=Lax + state-changing POST checks, or double-submit token). |
| FR-S10.4 | Login/logout set/clear cookie; `/auth/me` works with cookie credentials (`credentials: include`). |
| FR-S10.5 | Tech sketch shall detail cookie name, TTL alignment with JWT exp, and migration from localStorage (no silent dual-auth forever). |

### FR-S11 — FORCE RLS + GUC + containers/contents

| ID | Requirement |
|----|-------------|
| FR-S11.1 | For tables that already have RLS policies but `relforcerowsecurity = false` among tenant data tables (samples, tests, results, projects, batches, containers, …), enable **FORCE ROW LEVEL SECURITY** where safe for `lims_app` (not migrator). |
| FR-S11.2 | Confirm request path continues to bind `app.current_user_id` / `app.client_id` via `set_config` (already P0d); fix any code paths that skip bind. |
| FR-S11.3 | **Containers (OQ-S11a):** Tighten 0062 so `created_by = current_user_id()` applies to **INSERT WITH CHECK** only; SELECT/UPDATE/DELETE via admin OR contents→sample→project. Aliquot dest create remains **one transaction**; **never commit** a container without contents (product: no empty tube/plate/box outcome). |
| FR-S11.4 | **`contents` RLS (OQ-S11b):** ENABLE (+ FORCE as appropriate) with policy mirroring sample/project access; aliquot INSERT contents must succeed for eligible labtech. |

### FR-S12 — Postgres publish / defaults

| ID | Requirement |
|----|-------------|
| FR-S12.1 | Default **production** compose overlay/profile shall **not** map host `5432:5432`, or shall require override and non-default password. |
| FR-S12.2 | Dev compose may keep published port for local tools; document risk. |
| FR-S12.3 | `start.sh` / docs use `DATABASE_URL` / `MIGRATE_DATABASE_URL` only (no hardcoded prod passwords). |

### FR-S13 — verify-email & roles/permissions GET

| ID | Requirement |
|----|-------------|
| FR-S13.1 | `POST /auth/verify-email`: do not leak user existence; require token semantics or disable stub in production; rate-limit. |
| FR-S13.2 | `GET /roles` and `GET /permissions`: require `user:manage` or `config:edit` (not any authenticated user). |
| FR-S13.3 | Mutating role/permission endpoints remain permission-gated (already). |

### FR-S14 — Write-back vs system-RO fields

| ID | Requirement |
|----|-------------|
| FR-S14.1 | `specimen_biotype_id` and `temperature` shall be **removed from `SAMPLE_WRITE_BACK_COLUMNS`** (OQ-S14). |
| FR-S14.2 | They remain in sample system display fields for RO grids. |
| FR-S14.3 | Tests: write-back / link targeting those columns fails closed. |

### FR-S15 — Login rate limit / lockout

| ID | Requirement |
|----|-------------|
| FR-S15.1 | After **N** consecutive failed logins per username (default **5**) within window **W** (default **15 min**), further attempts return **429** (preferred) with lock message until unlock time. |
| FR-S15.2 | Persistence: **Postgres table** (OQ-S15)—no Redis. Survives restarts and multiple workers. |
| FR-S15.3 | Successful login clears failure counter for that username. |
| FR-S15.4 | Does not log passwords (S4 remains). Optional IP bucket can share the same table. |

---

## 5. Phasing (implementation plan for review)

| Phase | Findings | Exit |
|-------|----------|------|
| **P1 — Quick harden** | S8, S9, S13, S14 | Caps live; validate auth’d (enter\|review); GETs tightened; write-back allowlist consistent |
| **P2 — Access & abuse** | S7, S15 | Start gates + DB-backed login lockout; tests |
| **P3 — Platform** | S11, S12 | FORCE RLS; contents RLS; containers INSERT-only `created_by`; prod compose overlay |
| **P4 — Cookie AuthN** | S10 | httpOnly cookie (or BFF) cutover + CSRF + docs honesty |

**Recommended implement order:** P1 → P2 → P3 → P4.  
**Note:** P4 is a **scope expansion** vs original docs-only S10 (OQ-S10 Decided Yes).

---

## 6. Acceptance

1. codebase.md S7–S15 updated per phase Met/Deferred.  
2. Pytest + `UAT_Scripts/uat-security-med-low-s7-s15.md`.  
3. No regression of S1–S6 UAT spine.  
4. Reviews Accept (with conditions OK).  

## 7. Risks

| Risk | Mitigation |
|------|------------|
| FORCE RLS breaks background jobs | Jobs use migrator URL or explicit SET ROLE + GUC |
| Lockout DoS against admin username | Longer unlock + admin unlock endpoint later; alert |
| Tightening GET /roles breaks UI | Grant config users permission; smoke admin Users page |
| S14 product conflict | **Decided** — drop write-back |
| P4 cookie AuthN complexity | CSRF + SameSite design in tech sketch before code; phased dual-run if needed |

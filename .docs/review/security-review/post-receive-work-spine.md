# Security Review: Post-receive work spine

**Date:** 2026-08-28  
**Status:** **Accept with conditions**  
**Stem:** `post-receive-work-spine`  
**Tech sketch:** [`.docs/review/tech-sketch/post-receive-work-spine.md`](../tech-sketch/post-receive-work-spine.md)  
**Requirements:** [`.docs/review/requirements/post-receive-work-spine.md`](../requirements/post-receive-work-spine.md)  
**Schema:** [`.docs/review/schema-changes/post-receive-work-spine.md`](../schema-changes/post-receive-work-spine.md)  
**Spec:** [`.docs/internal/specs/post-receive-work-spine/SPEC.md`](../../internal/specs/post-receive-work-spine/SPEC.md)  
**Related reviews:** [Lab Ops](../lab-ops-review/post-receive-work-spine.md) (Accept with conditions L1–L5)  
**Open questions:** [`.docs/review/open-questions/post-receive-work-spine.md`](../open-questions/post-receive-work-spine.md)  
**Stamps:** WO-1…WO-7, FW-0/FW-2, Decision #9 (lab writes; client reads own)  
**Scope:** Feature packet (STRIDE). **DEEP CSO:** skipped (not requested).

---

## Executive summary

The spine is the right AuthZ shape: **asked-for is a request log**, **routing_map is config**, **work_order start reuses process AuthZ**, **execute is already shipped**. No second permission world. No client expand. That matches WO-7 and Decision #9.

| Surface | AuthZ (locked) |
|---------|----------------|
| Asked-for write | `test:assign` + sample → project RLS |
| Asked-for read | `sample:read` + same RLS |
| Routing map mutate | `config:edit` only |
| Work-order start | Existing process AuthZ (`experiment:manage`) |
| Client | Read-only on own samples; no asked-for / routing / parser / WO-start write |
| SOP Apply | Human save; never silent auto-activate |
| Production import | No LLM |

**Real exploit paths this packet must close:**

1. **Client leftover `test:assign`.** Migration `0013_seed_client_role` falls back to `test:assign` because **`test:read` was never seeded**. Permission-name-only gating would let a Client POST asked-for (and today, POST `/tests`). Deny **Client role** on write, not only the permission string.
2. **Cross-project `sample_id` IDOR** on create / cancel / route / start if the service does not load the sample (or WO) under RLS and return **403** (not 404) when hidden.
3. **`ensure_test` on publish** (`ResultPromotionService.ensure_test`, called from `lims_run_service.publish_run`) is find-or-create. That is WO-7 elevation: a Test appears without LimsRun-start AuthZ. P2 must **refuse** if missing — no ensure-on-publish.
4. **SOP Apply auto-activate or auto-bind parser** would put untrusted LLM output on the live process / import path. Human save; draft `active=false`; parser draft inactive and unbound.

**Verdict: Accept with conditions.** P1 may implement if **S1–S4** land in the P1 PR. **S5–S8** land with P2, **S9** with P3, **S10–S11** with P4, **S12** with P5. Not IC50. Does not reopen CORE receive.

---

## AuthZ matrix (normative)

| Action | Admin | Lab Manager | Lab Tech | Client |
|--------|-------|-------------|----------|--------|
| GET asked-for (own project samples) | Yes | Yes | Yes | **Yes if sample:read + RLS** |
| POST / cancel asked-for | Yes (`test:assign`) | Yes | Yes | **No — 403** |
| PUT analysis param-defs | Yes (`config:edit`) | No | No | **No** |
| Mutate routing_map | Yes (`config:edit`) | No | No | **No** |
| POST asked-for/{id}/route (mint WO) | Yes (lab write + RLS) | Yes | Yes | **No** |
| POST work-orders/{id}/start | Yes (`experiment:manage`) | Yes | Yes | **No** |
| Persist result on existing Test | existing `result:enter` / publish | same | same | **No** |
| SOP Apply | `experiment:manage` | Yes | Yes | **No** |
| Activate process def / parser | `config:edit` (FW-1b) | No | No | **No** |
| Day-to-day file import | existing import AuthZ | same | same | **No** |

UI `hasPermission` is UX only. Server RBAC + Postgres RLS are AuthZ.

---

## Surface delta

| Surface | Risk |
|---------|------|
| `POST/GET /api/v1/asked-for`, `POST …/cancel` | IDOR write/read across projects; Client write via leftover `test:assign` |
| Multi-sample asked-for (L1) | Mixed-project set writes unauthorized `sample_id`s if AuthZ is first-row-only |
| `PUT /api/v1/analyses/{id}/param-defs` | Config elevation; `params` JSONB dumping identity fields |
| `GET/POST/PATCH/DELETE /api/v1/routing-map` | Elevation if writable without `config:edit` |
| `POST /api/v1/asked-for/{id}/route` | Mint WO for another client; zero-hit mint; ambiguous silent first-row choice |
| `GET /api/v1/work-orders`, `POST …/start` | Hijack another client’s WO; client expand into Process |
| LimsRun start → Test (WO-7) | Silent Test create at asked-for / WO save / **publish ensure** |
| `persist_typed_result` (P3) | Two-writer overwrite; Client enter; persist without a Test |
| `POST /v1/sop-parse/{id}/apply` (P4) | Auto-activate live process; auto-bind LLM parser_config |
| Parser / instrument CRUD + activate (P5) | Client config; LLM on import; executable parser RCE |

No new execute runtime. Receive stays 422 on `analysis_ids` (existing bounce, not a new AuthZ door).

---

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| **Spoofing** | Existing JWT / cookie session. Same AuthN as tests / processes. No new token world. |
| **Tampering** | Params allowlist. Routing zero-hit 422 / ambiguity 409. Ordered process-definition snapshot at mint. Results two-writer 409. |
| **Repudiation** | Audit create/cancel asked-for, map save, route/mint, WO start, LimsRun Test mint, SOP Apply, parser activate (S4, S8, S10, S12). |
| **Info disclosure** | Sample → project RLS + FORCE on new tables; hidden → **403** not 404 (S1, S3, S6). Client does not need lab-wide routing packs (S8). |
| **DoS** | Out of scope (no new public flood surface; parser upload caps already S3 on the parsers packet). |
| **Elevation** | No new permission this phase (OQ-AF-2). Client write denied by **role** (S2). Map mutate `config:edit` only (S5). WO start = existing `experiment:manage` (S6). No ensure-on-publish (S7). Apply never auto-activates / auto-binds (S10–S11). Import never calls LLM (S12). |

---

## Findings / conditions

| ID | Severity | Phase | Condition |
|----|----------|-------|-----------|
| **S1** | High | **P1** | Asked-for **write** = `test:assign` **and** load sample under project RLS (`has_project_access` / `lims_app`) **inside** the service. Hidden or cross-project `sample_id` → **403** (not 404). No new `order:create` permission (OQ-AF-2). UI is not the AuthZ gate. Receive still **422** on non-empty `analysis_ids`; asked-for does **not** call `_create_tests` / `_create_asked_for_tests`. |
| **S2** | High | **P1** | **Client role cannot write asked-for** (create / cancel). GET/list only if `sample:read` + RLS on that sample. **Do not treat leftover Client `test:assign` as write license.** `0013_seed_client_role` falls back to `test:assign` because `test:read` does not exist — permission-name-only checks fail this. Pytest: Client POST/cancel → 403; lab tech without project access → 403; other-client sample → 403. |
| **S3** | High | **P1** | **FORCE ROW LEVEL SECURITY** on `asked_for` and `analysis_param_defs`. `asked_for` USING **and WITH CHECK** via sample → project (mirror `tests`). Param-defs: authenticated read; **write `config:edit` / admin**. Multi-sample (L1): **each** `sample_id` independently RLS-checked; fail closed — no write of unauthorized ids (no first-row-only bulk). |
| **S4** | Med | **P1** | `params` keys must match `analysis_param_defs` for that analysis; unknown or missing required → **422**. Empty defs = `{}` only. Do **not** persist `params` onto Sample identity (`client_sample_id`, subject, container metrics). Audit asked-for create/cancel (actor, sample_id, analysis_id, status). |
| **S5** | High | **P2** | Map mutate = `config:edit`; intake type is match data only. Route matches analysis × type × TAT and checks only the first step. Map save does no chain-wide type validation. |
| **S6** | High | **P2** | Work orders snapshot one `process_definition_id`. Start under `experiment:manage` instantiates it once; typed steps retain order. |
| **S7** | High | **P2** | **WO-7:** Test minted **only** at LimsRun start under process AuthZ. Asked-for create, WO save, and route mint **zero** Tests. Publish **422** if Test missing. **Remove** find-or-create / `ensure_test` on publish (`ResultPromotionService.ensure_test` is called today from `publish_run` — “may create tests via ensure”). Asked-for `params` snapshot onto the Test at LimsRun start and **freeze**; no write-back to Sample identity. |
| **S8** | Med | **P2** | Snapshot ordered definition IDs at mint so map edits cannot retarget work. Preserve process/step order. Audit candidate count, Route refusal/ambiguity, chosen map, each route-position start, and later type refusal. |
| **S9** | High | **P3** | Persist typed results on an **existing** Test only. AuthZ = existing `result:enter` (classic) or existing publish path (lab-only). RLS via test → sample → project. Two writers on the same Test → **409**. Client cannot enter. No `results.unit_id`. Do not persist from asked-for. P3 does not mint Tests. |
| **S10** | High | **P4** | SOP Apply is a **human** POST (`experiment:manage`; Client **403**). Creates/updates a **draft** process definition (`active=false`) until explicit activate (`config:edit` / existing process-def activation). **Never silent auto-activate.** Treat model output as untrusted: typed steps only; no eval/exec. Apply does **not** call LLM. No SOP PDF bodies in git. |
| **S11** | High | **P4** | Optional parser draft from Apply: **inactive and unbound**. Never auto-bind to production runs or day-to-day import. **OQ-SOP-2 locked this way for security.** Production import stays the deterministic engine. |
| **S12** | High | **P5** | Instrument types / instruments / CRO sources / `data_parsers` mutate **and activate** = **`config:edit`**. Client **403**. Production import **never** calls LLM (pytest assert; no call site). No user-uploaded executable parsers. AI draft = setup-only; validate as untrusted JSON (parsers packet S1/S6/S7 still hold). |

Already normative in the packet (restated so they are not dropped): uniqueness 409; status checks; no Tests at asked-for; bounce Client write on routing/parsers; L2 Qubit-on-blood is lab integrity (Lab Ops), not a new AuthZ path.

---

## Open questions (security stance)

| ID | Stance |
|----|--------|
| **OQ-AF-2** | **Locked.** Reuse `test:assign`. Do not add `order:create`. Client write still denied by **role** (S2). |
| **OQ-WO-1** | Explicit Route is a lab write under RLS; no map returns `no_route`; Client cannot route. |
| **OQ-WO-3** | One process instance links to the work order. RLS follows the sample. |
| **OQ-SOP-2** | **Locked for security:** inactive, **unbound**. Never auto-bind (S11). |

---

## Not in scope this review

- Deep gstack `/cso` infra / repo audit (Layer B skipped)
- Extract-hold dest type / blood → DNA → Qubit E2E (different packet)
- IC50 / dose-response
- Reopening CORE receive AuthZ (S-AR-1..5 already stamped)
- Stripping historical Client `project:manage` / `result:review` leftovers from 0013 (watch; not this stem except asked-for write)
- Classic `POST /tests` muscle-memory (Lab Ops watch; P1 must not become that path)

---

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (S1–S12) |
| **Date** | 2026-08-28 |
| **Implement gate** | **OPEN for P1 only** — S1–S4 land in the P1 PR |
| **P1** | **OPEN** if S1–S4 (RLS, Client role deny, FORCE+WITH CHECK, params allowlist) |
| **P2** | S5–S8 with P2 code (map `config:edit`, process AuthZ start, no client expand, **remove ensure-on-publish**) |
| **P3** | S9 with persist lock |
| **P4** | S10–S11 with Apply → process definition |
| **P5** | S12 with parser setup UX (may parallel P1) |
| **Deep `/cso`** | skipped |
| **Not licensed** | Client write · LLM on import · SOP auto-activate · Test at asked-for / WO save / publish-ensure · second AuthZ spine |

```
SECURITY REVIEW: Accept with conditions
DEEP CSO: skipped
```

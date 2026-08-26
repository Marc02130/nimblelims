# NimbleLIMS review documentation

This tree is **review + manuals + process** only. It holds review stamps, tech sketches, cycle requirements, schema deltas, open-question logs, checklists, development-process notes, and operator manuals.

Umbrella product PRD, long-form design, ideas, SOP packs, user stories, and private materials live under **local** `.docs-internal/` (**not committed**). Hand-offs must never add `.docs-internal/` to git.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`development-process/`](development-process/) | **How we build** — ideation → production (includes dogfood/UAT) |
| [`manuals/`](manuals/) | Day-to-day reference: setup, API, navigation, domain handbooks |
| [`requirements/`](requirements/) | Cycle feature requirements (not the umbrella PRD) |
| [`tech-sketch/`](tech-sketch/) | Lightweight *how* before architecture/UI review |
| [`schema-changes/`](schema-changes/) | **Per-cycle DB delta** (architecture schema checklist) |
| [`checklist/`](checklist/) | Implementation checklists (task tracking) |
| [`open-questions/`](open-questions/) | **Decision logs** — gate phases until blockers are Decided |
| [`ceo-review/`](ceo-review/) | CEO / product strategy reviews |
| [`ui-review/`](ui-review/) | UI / UX reviews |
| [`architecture-review/`](architecture-review/) | Architecture design reviews |
| [`security-review/`](security-review/) | Security reviews |
| [`lab-ops-review/`](lab-ops-review/) | **SVP Lab Ops** — target-customer lab workflows (required for ELN/experiments) |
| [`qa-review/`](qa-review/) | **Testing / QA Lead** — testability, UAT readiness, acceptance criteria quality |

**Local only (not in this repo):** `.docs-internal/prd/`, `.docs-internal/design/`, `.docs-internal/ideas/`, `.docs-internal/sop/`, `.docs-internal/user-stories/`, `.docs-internal/private/`, plus specs and decision-logs.

**Formal review skills (Grok):** [`.grok/skills/nimble-reviews/README.md`](../.grok/skills/nimble-reviews/README.md) — Lab Ops, CEO, UI, Arch, Security CSO, Scientific CSO, BA, QA packet + orchestrator (`/nimble-*-review`, `/nimble-review-packet`). Shared rules: [PACKET.md](../.grok/skills/nimble-reviews/PACKET.md).

**Index rule:** do not leave new docs at `.docs-review/` root. Put them in the folder that matches their role. Do not commit `.docs-internal/`.

## Start here

Umbrella PRD and long-form design live under local `.docs-internal/` (not committed).

| Need | Doc |
|------|-----|
| **How we develop features** | [development-process/README.md](development-process/README.md) |
| Run the app | [manuals/dev-setup.md](manuals/dev-setup.md), root [README.md](../README.md) |
| Admin password / first login | [manuals/admin-setup.md](manuals/admin-setup.md) |
| API reference | [manuals/api-endpoints.md](manuals/api-endpoints.md) |
| Navigation / sidebar | [manuals/navigation.md](manuals/navigation.md) |
| ELN processes / experiments work | [checklist/experiment-checklist.md](checklist/experiment-checklist.md), [open-questions/experiments.md](open-questions/experiments.md) |
| CLI snippets | [manuals/useful-command-line.md](manuals/useful-command-line.md) |
| **SOP + AI → process (locked)** | [open-questions/sop-ai-to-process.md](open-questions/sop-ai-to-process.md) |
| **Extract-hold dest type** | [requirements/extract-hold-dest-type.md](requirements/extract-hold-dest-type.md) · [tech-sketch/extract-hold-dest-type.md](tech-sketch/extract-hold-dest-type.md) |

## Manuals (domain + ops)

| Doc | Topic |
|-----|--------|
| [accessioning-workflow.md](manuals/accessioning-workflow.md) | Sample accessioning |
| [workflow-accessioning-to-reporting.md](manuals/workflow-accessioning-to-reporting.md) | Full sample → report path + workflows |
| [batches.md](manuals/batches.md) | Batches, QC, prioritization |
| [containers.md](manuals/containers.md) | Containers |
| [lists.md](manuals/lists.md) | Configurable lists |
| [ids-and-configuration.md](manuals/ids-and-configuration.md) | Name templates, IDs, config storage |
| [experiments.md](manuals/experiments.md) | ELN experiments |
| [processes.md](manuals/processes.md) | ELN process definitions & instances |
| [lims-runs.md](manuals/lims-runs.md) | LIMS runs boundary |
| [backend-auth.md](manuals/backend-auth.md) | Auth / JWT / RBAC notes |

## Cycle requirements

Feature-cycle requirements remain here. The umbrella PRD is local `.docs-internal/prd/nimblelims-prd.md` (not committed).

| Doc | Topic |
|-----|--------|
| [experiment-processes-entries.md](requirements/experiment-processes-entries.md) | Processes, entries, experiments requirements |
| [schema-evolution.md](requirements/schema-evolution.md) | FieldDefinitions / schema evolution requirements |
| [data-parsers-lims-runs.md](requirements/data-parsers-lims-runs.md) | Parsers (analysis×instrument/CRO), run lineage, optional AI setup — **in review** |
| [extract-hold-dest-type.md](requirements/extract-hold-dest-type.md) | Optional dest sample_type on aliquot/pool; process-sample on execute — **in review** |
| [security-high-s1-s6.md](requirements/security-high-s1-s6.md) | High security remediation (S1–S6) — **Accept / Met** |
| [security-med-low-s7-s15.md](requirements/security-med-low-s7-s15.md) | Med/Low security remediation (S7–S15) — **In review** |

## Tech sketches

Lightweight *how* (see [tech-sketch/README.md](tech-sketch/README.md)). Feature sketches land here after requirements, before architecture review.

| Cycle | Doc | Status |
|-------|-----|--------|
| atomic-receive | [tech-sketch/atomic-receive.md](tech-sketch/atomic-receive.md) | Design: CEO Accept (PR 30). AuthZ docs gate **satisfied** (Heidi/Günter Accept with conditions, PR 68). **Product code waits on Marc** |
| data-parsers-lims-runs | [tech-sketch/data-parsers-lims-runs.md](tech-sketch/data-parsers-lims-runs.md) | Accepted |
| experiment-template-entries | [tech-sketch/experiment-template-entries.md](tech-sketch/experiment-template-entries.md) | **Hold** — Lab Ops revise (2026-07-29) |
| extract-hold-dest-type | [tech-sketch/extract-hold-dest-type.md](tech-sketch/extract-hold-dest-type.md) | **In review** — Leadership before implement |
| security-high-s1-s6 | [tech-sketch/security-high-s1-s6.md](tech-sketch/security-high-s1-s6.md) | Implemented / Accept |
| security-med-low-s7-s15 | [tech-sketch/security-med-low-s7-s15.md](tech-sketch/security-med-low-s7-s15.md) | **In review** — Med/Low S7–S15 |

## Schema changes (per cycle)

**Single place** for “what migrations does this feature need?” — [schema-changes/README.md](schema-changes/README.md).  
Do not confuse with the platform Field Management design (local `.docs-internal/design/schema-evolution.md`, not committed).

| Cycle | Doc |
|-------|-----|
| data-parsers-lims-runs | [schema-changes/data-parsers-lims-runs.md](schema-changes/data-parsers-lims-runs.md) |
| experiment-template-entries | [schema-changes/experiment-template-entries.md](schema-changes/experiment-template-entries.md) |
| security-high-s1-s6 | [schema-changes/security-high-s1-s6.md](schema-changes/security-high-s1-s6.md) |
| security-med-low-s7-s15 | [schema-changes/security-med-low-s7-s15.md](schema-changes/security-med-low-s7-s15.md) |

## Checklists & decisions

| Doc | Topic |
|-----|--------|
| [checklist/experiment-checklist.md](checklist/experiment-checklist.md) | Experiments / processes / entries phases |
| [checklist/experiment-rework-prerequisites.md](checklist/experiment-rework-prerequisites.md) | Pre-rework issues (historical checklist) |
| [open-questions/experiments.md](open-questions/experiments.md) | Experiments decision log |
| [open-questions/run-results.md](open-questions/run-results.md) | Run→results decisions (shipped) |
| [open-questions/data-parsers-lims-runs.md](open-questions/data-parsers-lims-runs.md) | Parsers + run lineage (in review) |
| [open-questions/sop-ai-to-process.md](open-questions/sop-ai-to-process.md) | SOP + AI → process: frame can hold, Apply cannot; extract-then-Qubit Hold |
| [open-questions/README.md](open-questions/README.md) | Gate rule |

## Reviews

| Track | Folder |
|-------|--------|
| **Lab Ops** | [lab-ops-review/](lab-ops-review/) |
| **CEO / product** | [ceo-review/](ceo-review/) |
| **UI / UX** | [ui-review/](ui-review/) |
| **Architecture** | [architecture-review/](architecture-review/) |
| **Security** | [security-review/](security-review/) |
| **QA / Testing** | [qa-review/](qa-review/) |

Long-form tech designs live under local `.docs-internal/design/` (not committed).

## Reviews (run-results) — complete

- [ceo-review/run-results.md](ceo-review/run-results.md)
- [ui-review/run-results.md](ui-review/run-results.md)
- [security-review/run-results.md](security-review/run-results.md)
- [open-questions/run-results.md](open-questions/run-results.md)

Tech design for this cycle: local `.docs-internal/design/run-results.md` (not committed).

## Reviews (atomic-receive) — AuthZ docs gate satisfied; product code gated on Marc

- **Tech sketch:** [tech-sketch/atomic-receive.md](tech-sketch/atomic-receive.md) — §4b AuthZ spine (Heidi/Günter **Accept with conditions**, PR 68)
- **Security stamp:** [security-review/atomic-receive.md](security-review/atomic-receive.md) — S-AR-1..5 (same as sample create; project RLS; one path/one txn; refuse orphan multi-call; no client bypass)
- [lab-ops-review/atomic-receive.md](lab-ops-review/atomic-receive.md)
- [qa-review/atomic-receive.md](qa-review/atomic-receive.md)

Packet **design** still CEO Accept (PR 30). AuthZ **docs** gate **satisfied**. Product **implement waits on Marc** green-light for the accessioning P0 refactor. Not IC50.

## Reviews (data parsers / LimsRun import) — **CEO Accept; other reviews open**

- **Requirements:** [requirements/data-parsers-lims-runs.md](requirements/data-parsers-lims-runs.md)
- **Tech sketch:** [tech-sketch/data-parsers-lims-runs.md](tech-sketch/data-parsers-lims-runs.md)
- **Open questions:** [open-questions/data-parsers-lims-runs.md](open-questions/data-parsers-lims-runs.md)
- [ceo-review/data-parsers-lims-runs.md](ceo-review/data-parsers-lims-runs.md) — **Accept** (high priority, P0+P1 MVP)
- [security-review/data-parsers-lims-runs.md](security-review/data-parsers-lims-runs.md)
- [architecture-review/data-parsers-lims-runs.md](architecture-review/data-parsers-lims-runs.md)
- [ui-review/data-parsers-lims-runs.md](ui-review/data-parsers-lims-runs.md)

## Agent / contributor rules

See root [`AGENTS.md`](../AGENTS.md): open questions live in `open-questions/`; checklists track tasks; do not start a major feature while related open questions block it.

## What does *not* belong here

- Product PRD, long-form design, ideas, SOP packs, user stories, private notes → local `.docs-internal/` (not committed).
- Ephemeral logs, DB dumps, one-off debug writeups → keep out of git (use `/tmp` or local ignored paths).
- Product decisions → `open-questions/` (or promote into manuals/cycle requirements after Decided).
- Formal reviews → the matching `*-review/` folder, not root.

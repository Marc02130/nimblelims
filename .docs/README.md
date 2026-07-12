# NimbleLIMS documentation

All product and engineering docs live under this directory, organized by purpose.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`development-process/`](development-process/) | **How we build** — ideation → production (includes dogfood/UAT) |
| [`manuals/`](manuals/) | Day-to-day reference: setup, API, navigation, domain handbooks |
| [`requirements/`](requirements/) | PRD and feature requirements |
| [`tech-sketch/`](tech-sketch/) | Lightweight *how* before architecture/UI review |
| [`schema-changes/`](schema-changes/) | **Per-cycle DB delta** (architecture schema checklist) |
| [`design/`](design/) | Longer-form architecture / tech specs |
| [`user-stories/`](user-stories/) | User stories and acceptance criteria |
| [`checklist/`](checklist/) | Implementation checklists (task tracking) |
| [`open-questions/`](open-questions/) | **Decision logs** — gate phases until blockers are Decided |
| [`ceo-review/`](ceo-review/) | CEO / product strategy reviews |
| [`ui-review/`](ui-review/) | UI / UX reviews |
| [`architecture-review/`](architecture-review/) | Architecture design reviews |
| [`security-review/`](security-review/) | Security reviews |
| [`ideas/`](ideas/) | Exploratory notes — not commitments |
| `private/` | Local-only materials (gitignored) |

**Index rule:** do not leave new docs at `.docs/` root. Put them in the folder that matches their role.

## Start here

| Need | Doc |
|------|-----|
| **How we develop features** | [development-process/README.md](development-process/README.md) |
| Run the app | [manuals/dev-setup.md](manuals/dev-setup.md), root [README.md](../README.md) |
| Admin password / first login | [manuals/admin-setup.md](manuals/admin-setup.md) |
| API reference | [manuals/api-endpoints.md](manuals/api-endpoints.md) |
| Navigation / sidebar | [manuals/navigation.md](manuals/navigation.md) |
| Product requirements | [requirements/nimblelims-prd.md](requirements/nimblelims-prd.md) |
| Technical blueprint | [design/nimblelims-tech.md](design/nimblelims-tech.md) |
| User stories | [user-stories/nimblelims-user.md](user-stories/nimblelims-user.md) |
| ELN processes / experiments work | [checklist/experiment-checklist.md](checklist/experiment-checklist.md), [open-questions/experiments.md](open-questions/experiments.md) |
| CLI snippets | [manuals/useful-command-line.md](manuals/useful-command-line.md) |

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

## Requirements

| Doc | Topic |
|-----|--------|
| [nimblelims-prd.md](requirements/nimblelims-prd.md) | Product requirements (MVP+) |
| [experiment-processes-entries.md](requirements/experiment-processes-entries.md) | Processes, entries, experiments requirements |
| [schema-evolution.md](requirements/schema-evolution.md) | FieldDefinitions / schema evolution requirements |
| [data-parsers-lims-runs.md](requirements/data-parsers-lims-runs.md) | Parsers (analysis×instrument/CRO), run lineage, optional AI setup — **in review** |

## Tech sketches

Lightweight *how* (see [tech-sketch/README.md](tech-sketch/README.md)). Feature sketches land here after requirements, before architecture review.

## Schema changes (per cycle)

**Single place** for “what migrations does this feature need?” — [schema-changes/README.md](schema-changes/README.md).  
Do not confuse with the platform Field Management design ([design/schema-evolution.md](design/schema-evolution.md)).

| Cycle | Doc |
|-------|-----|
| data-parsers-lims-runs | [schema-changes/data-parsers-lims-runs.md](schema-changes/data-parsers-lims-runs.md) |

## Design (long-form)

| Doc | Topic |
|-----|--------|
| [nimblelims-tech.md](design/nimblelims-tech.md) | Technical document |
| [schema-evolution.md](design/schema-evolution.md) | Schema evolution design |
| [field-management-oob-harmonization.md](design/field-management-oob-harmonization.md) | Field management design |
| [migration-strategy-schema-evolution.md](design/migration-strategy-schema-evolution.md) | Migration strategy |
| [jsonb-usage-analysis.md](design/jsonb-usage-analysis.md) | JSONB usage analysis |
| [gap-analysis-process-and-experiment.md](design/gap-analysis-process-and-experiment.md) | Process/experiment gaps |
| [experiment-planning.md](design/experiment-planning.md) | Chunk 1–2 planning history |
| [technical-accessioning-to-reporting.md](design/technical-accessioning-to-reporting.md) | Accessioning→report technical design |
| [ui-accessioning-to-reporting.md](design/ui-accessioning-to-reporting.md) | Accessioning→report UI design |

## Checklists & decisions

| Doc | Topic |
|-----|--------|
| [checklist/experiment-checklist.md](checklist/experiment-checklist.md) | Experiments / processes / entries phases |
| [checklist/experiment-rework-prerequisites.md](checklist/experiment-rework-prerequisites.md) | Pre-rework issues (historical checklist) |
| [open-questions/experiments.md](open-questions/experiments.md) | Experiments decision log |
| [open-questions/run-results.md](open-questions/run-results.md) | Run→results decisions (shipped) |
| [open-questions/data-parsers-lims-runs.md](open-questions/data-parsers-lims-runs.md) | Parsers + run lineage (in review) |
| [open-questions/README.md](open-questions/README.md) | Gate rule |

## Reviews

| Track | Folder |
|-------|--------|
| **CEO / product** | [ceo-review/](ceo-review/) |
| **UI / UX** | [ui-review/](ui-review/) |
| **Architecture** | [architecture-review/](architecture-review/) |
| **Security** | [security-review/](security-review/) |

Long-form tech designs stay in [design/](design/). UI review was previously `ui-review/`.

## Ideas

| Doc | Topic | Status |
|-----|--------|--------|
| [ideas/run-results.md](ideas/run-results.md) | LimsRun JSONB → Results on **publish** | **Shipped v1** (P0–P4); see reviews + [manuals/lims-runs.md](manuals/lims-runs.md) |
| [ideas/ai-analyte-resolution.md](ideas/ai-analyte-resolution.md) | AI help when analyte alias list misses | Exploratory follow-on |
| [ideas/ai-data-import.md](ideas/ai-data-import.md) | Deterministic parsers (analysis+instrument/CRO); AI only for setup | **Requirements in review** |
| [ideas/ai-data-analysis.md](ideas/ai-data-analysis.md) | AI-assisted query / anomaly / summary of run+result data | **Placeholder** |
| [ideas/model-fine-tune.md](ideas/model-fine-tune.md) | Model fine-tune notes | See `sop-rag` for related SOP/RAG work |

## Reviews (run-results) — complete

- [ceo-review/run-results.md](ceo-review/run-results.md)
- [ui-review/run-results.md](ui-review/run-results.md)
- [design/run-results.md](design/run-results.md) (tech design)
- [security-review/run-results.md](security-review/run-results.md)
- [open-questions/run-results.md](open-questions/run-results.md)

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

- Ephemeral logs, DB dumps, one-off debug writeups → keep out of git (use `/tmp` or local ignored paths).
- Product decisions → `open-questions/` (or promote into manuals/requirements after Decided).
- Formal reviews → the matching `*-review/` folder, not root.

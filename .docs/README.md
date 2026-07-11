# NimbleLIMS documentation

All product and engineering docs live under this directory, organized by purpose.

## Layout

| Directory | Purpose |
|-----------|---------|
| [`manuals/`](manuals/) | Day-to-day reference: setup, API, navigation, domain handbooks |
| [`requirements/`](requirements/) | PRD and feature requirements |
| [`design/`](design/) | Architecture, tech specs, gap analysis, migration strategy |
| [`user-stories/`](user-stories/) | User stories and acceptance criteria |
| [`checklist/`](checklist/) | Implementation checklists (task tracking) |
| [`open-questions/`](open-questions/) | **Decision logs** — gate new phases/features until blockers are Decided |
| [`ceo-review/`](ceo-review/) | CEO / product strategy reviews |
| [`design-review/`](design-review/) | UX / design reviews |
| [`security-review/`](security-review/) | Security reviews |
| [`ideas/`](ideas/) | Exploratory notes — not commitments |
| `private/` | Local-only materials (gitignored) |

**Index rule:** do not leave new docs at `.docs/` root. Put them in the folder above that matches their role.

## Start here

| Need | Doc |
|------|-----|
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

## Design

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
| [open-questions/README.md](open-questions/README.md) | Gate rule |

## Reviews

- **CEO:** [ceo-review/](ceo-review/) — process/experiment, schema evolution, field management, [SOP RAG config](ceo-review/docker-model-sop-pipeline.md)  
- **Design:** [design-review/](design-review/) — includes [SOP RAG config](design-review/docker-model-sop-pipeline.md)  
- **Security:** [security-review/](security-review/) — includes [SOP RAG config](security-review/docker-model-sop-pipeline.md)  
- **Tech (design/):** architecture specs, including [SOP RAG config](design/docker-model-sop-pipeline.md)

## Ideas

Exploratory only:

- [ideas/sop-rag-config.md](ideas/sop-rag-config.md) — SOP → LIMS config via **RAG** (design docs + vectors + catalog; see reviews above)
- [ideas/multi-tenancy.md](ideas/multi-tenancy.md) — lab–client isolation vs multi-lab SaaS
- [ideas/model-fine-tune.md](ideas/model-fine-tune.md) — stub redirect (superseded by sop-rag-config)

## Agent / contributor rules

See root [`AGENTS.md`](../AGENTS.md): open questions live in `open-questions/`; checklists track tasks; do not start a major feature while related open questions block it.

## What does *not* belong here

- Ephemeral logs, DB dumps, one-off debug writeups → keep out of git (use `/tmp` or local ignored paths).
- Product decisions → `open-questions/` (or promote into manuals/requirements after Decided).
- Formal reviews → the matching `*-review/` folder, not root.

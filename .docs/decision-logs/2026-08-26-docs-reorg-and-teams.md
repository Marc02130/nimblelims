# Docs reorg + Grok teams + domain PRD sync

**Date:** 2026-08-26  
**Status:** Done (working tree)

## Docs reorg (Marc)

| Former | Current |
|--------|---------|
| `.docs-review/` | `.docs/review/` |
| `.docs-internal/` | `.docs/internal/` |
| (discussions / decision-logs) | `.docs/discussions/`, `.docs/decision-logs/` |

Index: [`.docs/README.md`](../README.md). Updated: `Agents.md`, `.grok/skills/nimble-reviews/PACKET.md` + README.

## Teams

Created [`.grok/teams/`](../../.grok/teams/): **Leadership · Dev · QA · Docs** with skill recommendations.

## Leadership → domain PRDs/specs

Framework-first (FW/WO stamps) folded into:

- `.docs/internal/prd/containers/PRD.md` + `specs/containers/SPEC.md`
- `.docs/internal/prd/sample-accessioning/PRD.md` + `specs/sample-accessioning/SPEC.md`
- `.docs/internal/prd/sample-processing/PRD.md` + `specs/sample-processing/SPEC.md`
- Umbrella `.docs/internal/prd/nimblelims-prd.md` v1.8

Leadership intent: fixed spine + DB joints; AR OOB; work_order + routing as missing middle; Process/Exp/LimsRun remain execute SoT.

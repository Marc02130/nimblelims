# Security Review: Experiment template entries

**Date:** 2026-08-10  
**Status:** **Accept with conditions**  
**Tech sketch:** [§0](../tech-sketch/experiment-template-entries.md)  
**Lab Ops / Arch:** Accept with conditions  

## Surface delta

| Surface | Risk |
|---------|------|
| `GET …/grid`, `GET …/export` | Information disclosure if sample set not scoped |
| `PUT …/values` | Tampering process data |
| `POST …/submit` + write-back | Unauthorized Sample mutation |
| `POST …/execute` (aliquot) | Inventory integrity / create samples |
| Template write-back map config | Privilege to map fields to Sample |

## STRIDE (scoped)

| Threat | Control |
|--------|---------|
| Spoofing | Existing auth; experiment:manage (or refined lab write) |
| Tampering | Submit-only write-back; allowlist/config eligible targets; no write to accessioning identity |
| Tampering | Aliquot execute transactional; authz on experiment |
| Info disclosure | Grid/export only samples on experiment; RLS on samples/containers |
| Elevation | Clients must not edit entries (Decision #9) |
| Repudiation | Audit: write_back_previous, entry submit actor, execute actor |

## Findings / conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **S1** | High | Grid/export: samples only from experiment membership; no arbitrary sample_id expansion |
| **S2** | High | Write-back: only config-eligible Sample fields; never client_sample_id/client/subject; type match |
| **S3** | High | Write-back runs **only** on submit path, not save |
| **S4** | High | Aliquot execute: authorize; no partial commit; validate source amount ≥ move |
| **S5** | Med | Export may contain client/sample identifiers — same ACL as experiment view |
| **S6** | Med | Template edit of write-back map requires experiment:manage (or admin) |
| **S7** | Low | Log submit/execute with actor + experiment/entry ids |

## Not in scope this review

- Full /cso infra audit  
- Accessioning workflow security (separate idea)  

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** (S1–S7) |
| **Date** | 2026-08-10 |
| **Block implement?** | No if S1–S4 enforced in same phase as write-back/execute |

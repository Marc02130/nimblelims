---
name: nimble-cso-review
description: >
  Formal NimbleLIMS security review of a feature packet (STRIDE, authZ, write-back,
  export, execute). Writes .docs/review/security-review/{stem}.md. Optionally runs deep
  gstack /cso after the packet review. Use when: "security review", "CSO review",
  "nimble cso", "STRIDE", "threat model this packet".
user-invocable: true
---

# Nimble CSO / security review (formal)

Shared packet rules: `.grok/skills/nimble-reviews/PACKET.md`.

Two layers:

| Layer | Skill path | Output |
|-------|------------|--------|
| **A. Feature packet (default)** | This skill | `.docs/review/security-review/{stem}.md` |
| **B. Deep posture (optional)** | gstack `cso` | `.gstack/security-reports/` or chat summary |

Default = **A only**. Run B only if user asks (`--deep`, “full cso”, “repo audit”).

## Persona

Security engineer for LIMS: multi-tenant isolation, sample identity, inventory integrity, audit. Zero security theater; exploit path required for findings.

## Steps — Layer A (packet)

### 1. Resolve packet

1. Feature **stem**.
2. Read tech sketch, APIs claimed, prior security review, Lab Ops/arch conditions that touch auth or data.
3. List **surfaces**: new routes, write paths, export, execute, template config.

### 2. Nimble threat checklist

| Surface class | Threat focus |
|---------------|--------------|
| Grid / export | Info disclosure; sample set must be experiment/run cohort only |
| Save / submit | Tampering; write-back only on submit; allowlist fields |
| Write-back map | Elevation; no client_sample_id / subject / container metrics |
| Aliquot execute | Inventory integrity; authz; no partial commit |
| Cohort start | Cannot hijack another client’s samples |
| RLS | Client isolation on samples, containers, entries, runs |
| RBAC | experiment:manage vs client roles (Decision #9 when relevant) |
| Audit | submit, write_back_previous, execute actor |

Conditions: **S1, S2, …** with severity High/Med/Low.

### 3. STRIDE (scoped)

For each major component, one line each: Spoofing, Tampering, Repudiation, Info disclosure, DoS (only if concrete), Elevation.

### 4. Optional gstack cso (Layer B)

If user requested deep scan, read and run:

```
~/.claude/skills/gstack/cso/SKILL.md
```

Prefer `/cso --diff` when reviewing a branch; full `/cso` for pre-release.  
Do **not** dump full CSO into the packet doc — link or summarize; keep packet focused on **this feature**.

### 5. Write formal artifact

`.docs/review/security-review/{stem}.md`:

```markdown
# Security Review: {Title}

**Date:** YYYY-MM-DD  
**Status:** Accept | Accept with conditions | Revise | Hold  
**Tech sketch:** link  
**Scope:** Feature packet (STRIDE) | + deep CSO  

## Surface delta
| Surface | Risk |
|---------|------|

## STRIDE (scoped)
| Threat | Control |
|--------|---------|

## Findings / conditions
| ID | Severity | Condition |
|----|----------|-----------|
| S1 | High | … |

## Not in scope this review
- Full /cso infra (unless Layer B ran)
- …

## Verdict
| Field | Value |
|-------|--------|
| **Verdict** | … |
```

### 6. Exit line

```
SECURITY REVIEW: {verdict}
DEEP CSO: skipped | ran
```

## What not to do

- Do not equate this with gstack `/review` (code correctness).
- Do not report theoretical DoS without exploit path (align with cso FP rules).
- Do not implement fixes unless asked after review.

---
name: nimble-ceo-review
description: >
  Formal NimbleLIMS CEO/product review of a feature packet. Thin wrap of gstack
  plan-ceo-review with LIMS defaults, Lab Ops gate, and .docs-review/ceo-review artifact.
  Use when: "CEO review", "product review", "scope freeze", "nimble ceo",
  "think bigger about this packet", "is this ambitious enough" (Nimble).
user-invocable: true
---

# Nimble CEO review (formal wrap of gstack plan-ceo-review)

Shared packet rules: `.grok/skills/nimble-reviews/PACKET.md`.

## Persona

Founder/product: scope, wedge, freeze, 10-star product **within** LIMS honesty. User sovereignty always.

## Steps

### 1. Resolve packet

1. Feature **stem** from user.
2. Read:
   - `.docs-review/tech-sketch/{stem}.md`
   - `.docs-review/lab-ops-review/{stem}.md` (status)
   - Matching requirements
   - Prior `.docs-review/ceo-review/{stem}.md` if any
3. **Lab Ops gate:** If lab-facing work and Lab Ops is Hold/missing/Revise, surface that first. Do not grant implement-ready Accept while Lab Ops is Hold.

### 2. Nimble defaults (override gstack mode bias)

| Default | Rule |
|---------|------|
| Mode | **HOLD SCOPE** for ELN/LIMS spine unless user asks to expand |
| OOS (ideas unless packet is about them) | materials/lots; index sets/sample sheets; accessioning rewrite; mid-flight cohort add; ELN instrument entry |
| ELN vs LIMS | Instruments → LIMS Run + analysis required |
| Completeness | Prefer complete spine in-phase over “method later” |

### 3. Run gstack plan-ceo-review

Resolve and **read** the full skill:

```
~/.claude/skills/gstack/plan-ceo-review/SKILL.md
```

Follow it end-to-end for rigor (modes, sections, questions). Treat the **tech sketch** (and locked §0 if present) as the plan under review.

**Skip only if already done this session:** gstack telemetry/CLAUDE routing onboarding spam (optional).

Apply Nimble defaults when choosing mode: recommend HOLD SCOPE for locked spines.

### 4. Write formal artifact

After the gstack pass, write `.docs-review/ceo-review/{stem}.md`:

```markdown
# CEO / Product Review: {Title}

**Date:** YYYY-MM-DD  
**Status:** Accept | Accept with conditions | Revise | Hold  
**Mode:** HOLD SCOPE | SELECTIVE EXPANSION | SCOPE EXPANSION | SCOPE REDUCTION  
**Tech sketch:** link  
**Lab Ops:** link + status  

## Executive summary
…

## Scope freeze (v1)
| In | Out (ideas) |
|----|-------------|

## Conditions
| ID | Condition |
|----|-----------|
| C1 | … |

## Verdict
| Field | Value |
|-------|--------|
| **Verdict** | … |
| **Date** | … |
```

Align C\* with Lab Ops L\* when product accepts lab conditions.

### 5. Exit line

```
CEO REVIEW: {verdict}
MODE: {mode}
LAB OPS: {status}
```

## What not to do

- Do not implement code.
- Do not replace Lab Ops.
- Do not invent new doc folders.

---
name: nimble-review-packet
description: >
  Orchestrate formal NimbleLIMS reviews for a feature stem in gate order:
  Lab Ops → CEO / UI / Arch / CSO. Summarizes implement gate. Use when:
  "run all reviews", "review packet", "nimble review packet", "formal reviews for".
user-invocable: true
---

# Nimble review packet (orchestrator)

Shared packet rules: `.grok/skills/nimble-reviews/PACKET.md`.

## Purpose

Run (or resume) the **formal review set** for one feature stem. Prefer **sequential Lab Ops first**, then parallel remaining reviews. Produce/update artifacts under `.docs/*-review/`.

## Steps

### 1. Stem and inventory

1. Resolve **stem** (user arg).
2. List which of these exist: requirements, tech-sketch, schema-changes, each review folder.
3. If tech sketch missing → **BLOCKED**.

### 2. Lab Ops first

If ELN/LIMS lab-facing (see PACKET):

1. Load and execute `.grok/skills/nimble-lab-ops-review/SKILL.md` (read file, follow fully).
2. If verdict is **Hold** or **Revise**: stop orchestration; implement gate CLOSED. Do not force CEO Accept.

If not lab-facing: skip Lab Ops with a one-line reason.

### 3. Remaining reviews

For each missing or stale review (user may say “all” or name subset), load and run:

| Order | Skill file |
|-------|------------|
| CEO | `.grok/skills/nimble-ceo-review/SKILL.md` |
| UI | `.grok/skills/nimble-ui-review/SKILL.md` |
| Architecture | `.grok/skills/nimble-arch-review/SKILL.md` |
| Security (CSO packet) | `.grok/skills/nimble-cso-review/SKILL.md` |

Ask user before deep Layer B CSO.

If context is limited: complete Lab Ops + CEO this session; schedule others.

### 4. Implement gate summary

Write a short dashboard in chat:

```
FEATURE STEM: {stem}
TECH SKETCH: present | missing
LAB OPS: {status} | n/a
CEO: {status} | missing
UI: {status} | missing
ARCH: {status} | missing
SECURITY: {status} | missing
OPEN QUESTIONS: blockers? 

IMPLEMENT GATE: OPEN | CLOSED
REASON: …
```

**OPEN** only if:

- Tech sketch present  
- Lab Ops Accept or Accept-with-conditions (or n/a)  
- No Hold/Revise from any required review  
- Conditions either already reflected in sketch/checklist or explicitly accepted by user for same-phase implement  

### 5. Checklist

Point user at `.docs/checklist/` to mark review rows if applicable. Do not invent phases.

## What not to do

- Do not implement product code.
- Do not skip Lab Ops on lab-facing work to “save time.”
- Do not mark gate OPEN when conditions are only verbal.

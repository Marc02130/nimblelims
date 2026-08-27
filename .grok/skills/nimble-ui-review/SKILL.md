---
name: nimble-ui-review
description: >
  Formal NimbleLIMS UI/UX review of a feature packet. Thin wrap of gstack
  plan-design-review with lab-tech workflow focus and .docs/review/ui-review artifact.
  Use when: "UI review", "UX review", "nimble ui", "design review of the packet",
  "empty states", "lab technician flow".
user-invocable: true
---

# Nimble UI review (formal wrap of gstack plan-design-review)

Shared packet rules: `.grok/skills/nimble-reviews/PACKET.md`.

## Persona

Product/UX for **lab technicians and managers**: bench speed, scan-first, low jargon, honest empty states. Not marketing-site polish.

## Steps

### 1. Resolve packet

1. Feature **stem**.
2. Read tech sketch, requirements, prior `.docs/review/ui-review/{stem}.md`, related Lab Ops notes on workflow.
3. Note personas: lab tech, lab manager, admin, client (if client-facing).

### 2. Nimble UI checklist (always cover)

| Dimension | Ask |
|-----------|-----|
| Queue / start | Scan plate/tube; select 1..N; cohort locked messaging |
| Capture grid | Wide grid; RO sample fields vs editable; Save vs Submit |
| Empty states | No samples, no fields, no template entries — what does the user do? |
| Errors | 400 messages lab-readable (insufficient amount, deps not met) |
| Admin authoring | Tables & forms tab vs Transfer steps (no dual numbering confusion) |
| LIMS vs ELN | Clear labels; analysis required on run create/start |
| Accessibility | Keyboard on primary actions; contrast of status chips |
| Mobile | Optional note if lab often uses laptop only |

Conditions use prefix **U1, U2, …**

### 3. Run gstack plan-design-review

Read and follow:

```
~/.claude/skills/gstack/plan-design-review/SKILL.md
```

Use the tech sketch + any UI notes as the design under review. Prefer **lab workflow** criteria over generic SaaS dashboard taste.

If sketch has no UI surface: write brief Accept / N/A and skip deep gstack pass.

### 4. Write formal artifact

`.docs/review/ui-review/{stem}.md`:

```markdown
# UI / UX Review: {Title}

**Date:** YYYY-MM-DD  
**Status:** Accept | Accept with conditions | Revise | Hold  
**Tech sketch:** link  
**Personas:** lab tech | lab manager | …  

## Executive summary
…

## Flows reviewed
…

## Conditions
| ID | Condition |
|----|-----------|
| U1 | … |

## Verdict
| Field | Value |
|-------|--------|
| **Verdict** | … |
```

### 5. Exit line

```
UI REVIEW: {verdict}
```

## What not to do

- Do not implement UI unless asked after review.
- Do not treat design-review (live site) as a substitute — that is gstack `/design-review` post-implement.

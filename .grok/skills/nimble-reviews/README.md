# Nimble formal review skills

Slash-friendly skills for the NimbleLIMS development process. Each skill produces a **versioned review artifact** under `.docs/` using shared packet rules in [PACKET.md](./PACKET.md).

## Skills

| Slash / name | Persona | Artifact | gstack template |
|--------------|---------|----------|-----------------|
| `/nimble-lab-ops-review` | SVP Lab Ops | `.docs/lab-ops-review/{stem}.md` | Custom (no gstack analog) |
| `/nimble-ceo-review` | Founder / product | `.docs/ceo-review/{stem}.md` | `plan-ceo-review` |
| `/nimble-ui-review` | UX / lab workflow UI | `.docs/ui-review/{stem}.md` | `plan-design-review` |
| `/nimble-arch-review` | Systems architecture | `.docs/architecture-review/{stem}.md` | `plan-eng-review` |
| `/nimble-cso-review` | Feature security + optional deep CSO | `.docs/security-review/{stem}.md` | `cso` (feature-scoped + optional full) |
| `/nimble-review-packet` | Orchestrator | Runs gate order, points at all artifacts | — |

## Recommended order (ELN / LIMS)

1. **Lab Ops** (required gate)  
2. **CEO** + **UI** + **Arch** + **CSO** (parallel after Lab Ops has spoken)  
3. Resolve **open questions**  
4. Implement only when implement gate is open  

## Invocation examples

```
/nimble-lab-ops-review experiment-template-entries
/nimble-ceo-review experiment-template-entries
/nimble-review-packet experiment-template-entries
```

Or: “Run Lab Ops review on the experiment template entries tech sketch.”

## Relationship to gstack

- **Wraps** do not fork gstack skill bodies. They load gstack SKILL.md at runtime and add Nimble defaults + artifact paths.  
- Upgrade gstack separately; these skills stay thin.  
- Diff-level **code review** remains gstack `/review` (not a formal packet review).  
- Full infra **CSO** remains available via gstack `/cso`; `/nimble-cso-review` is the **packet** security review with optional deep pass.

## Process docs

- Pipeline: `.docs/development-process/README.md`  
- Lab Ops role: `.docs/lab-ops-review/README.md`  
- Doc index: `.docs/README.md`

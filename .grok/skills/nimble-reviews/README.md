# Nimble formal review skills

Slash-friendly skills for the NimbleLIMS development process. Each skill produces a **versioned review artifact** under `.docs/` using shared packet rules in [PACKET.md](./PACKET.md).

## Skills

| Slash / name | Persona | Artifact | Type |
|--------------|---------|----------|------|
| `/nimble-lab-ops-review` | SVP Lab Ops | `.docs/lab-ops-review/{stem}.md` | Formal gate (required) |
| `/nimble-ceo-review` | Founder / product | `.docs/ceo-review/{stem}.md` | Formal parallel |
| `/nimble-ui-review` | UX / lab workflow UI | `.docs/ui-review/{stem}.md` | Formal parallel |
| `/nimble-arch-review` | Systems architecture | `.docs/architecture-review/{stem}.md` | Formal parallel |
| `/nimble-cso-review` | Feature security + optional deep CSO | `.docs/security-review/{stem}.md` | Formal parallel (Security) |
| `/nimble-scientific-cso-review` | Chief Scientific Officer (assays, results, QC, data integrity) | `.docs/scientific-cso-review/{stem}.md` | Formal parallel |
| `/nimble-ba-review` | Business Analyst | `.docs/ba-review/{stem}.md` | Formal parallel |
| `/nimble-qa-review` | Testing / QA Lead | `.docs/qa-review/{stem}.md` | Formal parallel |
| `/nimble-developer-review` | Skilled Developer (Cursor implementability) | `.docs/developer-review/{stem}.md` | Formal parallel |
| `/nimble-documentarian` | Documentarian (docs quality & Cursor hand-off) | `.docs/docs-review/{stem}.md` | Formal parallel |
| `/nimble-test-data` | Test Data Developer | `.docs/test-data/{stem}.md` | Supporting / generative |
| `/nimble-sop-researcher` | SOP Researcher | `.docs/sop-research/{stem-or-topic}.md` | Supporting / generative |
| `/nimble-review-packet` | Orchestrator | Runs gate order, points at all artifacts | Orchestrator |

## Recommended order (ELN / LIMS)

1. **Lab Ops** (required gate)  
2. **CEO** + **UI** + **Arch** + **Security CSO** + **Scientific CSO** + **BA** + **QA** + **Developer** + **Documentarian** (parallel after Lab Ops has spoken)  
3. Supporting skills as needed: **Test Data** and **SOP Researcher**  
4. Resolve **open questions**  
5. Implement only when implement gate is open  

## Invocation examples

```
/nimble-lab-ops-review experiment-template-entries
/nimble-ceo-review experiment-template-entries
/nimble-scientific-cso-review experiment-template-entries
/nimble-ba-review experiment-template-entries
/nimble-qa-review experiment-template-entries
/nimble-developer-review experiment-template-entries
/nimble-documentarian experiment-template-entries
/nimble-test-data experiment-template-entries
/nimble-sop-researcher aliquoting plasma samples
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

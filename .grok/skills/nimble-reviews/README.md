# Nimble formal review skills

Slash-friendly skills for the NimbleLIMS development process. Each skill produces a **versioned review artifact** under `.docs/review/` using shared packet rules in [PACKET.md](./PACKET.md).

**Teams:** [`.grok/teams/`](../../teams/) — Leadership · BA · Dev · QA · Docs.  
**Docs root:** [`.docs/README.md`](../../../.docs/README.md).

## Skills

| Slash / name | Persona | Artifact | Type | Team |
|--------------|---------|----------|------|------|
| `/nimble-lab-ops-review` | SVP Lab Ops | `.docs/review/lab-ops-review/{stem}.md` | Formal gate | Leadership |
| `/nimble-ceo-review` | Founder / product | `.docs/review/ceo-review/{stem}.md` | Formal | Leadership |
| `/nimble-cso-review` | Security CSO | `.docs/review/security-review/{stem}.md` | Formal | Leadership |
| `/nimble-scientific-cso-review` | Scientific CSO | `.docs/review/scientific-cso-review/{stem}.md` | Formal | Leadership |
| `/nimble-ba-review` | Business Analyst | `.docs/review/ba-review/{stem}.md` | Formal | **BA** |
| `/nimble-arch-review` | Architecture | `.docs/review/architecture-review/{stem}.md` | Formal | Dev |
| `/nimble-developer-review` | Developer | `.docs/review/developer-review/{stem}.md` | Formal | Dev |
| `/nimble-ui-review` | UI / UX | `.docs/review/ui-review/{stem}.md` | Formal | Dev |
| `/nimble-qa-review` | QA / Testing | `.docs/review/qa-review/{stem}.md` | Formal | QA |
| `/nimble-test-data` | Test Data | `.docs/review/test-data/{stem}.md` | Supporting | QA |
| `/nimble-documentarian` | Documentarian | `.docs/review/docs-review/{stem}.md` | Formal | Docs |
| `/nimble-sop-researcher` | SOP Researcher | `.docs/review/sop-research/{stem-or-topic}.md` | Supporting | Docs |
| `/nimble-review-packet` | Orchestrator | Gate order | Orchestrator | Leadership |

## Recommended order (ELN / LIMS)

1. **Leadership:** Lab Ops → CEO + CSOs  
2. **BA:** requirements / AC / stories  
3. **Dev:** Arch + Developer (+ UI)  
4. **QA:** QA + Test Data  
5. **Docs:** Documentarian  
6. Open questions cleared → implement when gate open  

Or: `/nimble-review-packet {stem}`.

## Process docs

- Pipeline: `.docs/review/development-process/README.md`  
- Doc index: `.docs/README.md`  
- Teams: `.grok/teams/README.md`  

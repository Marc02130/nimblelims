# NimbleLIMS product development process

**Status:** Active  
**Date:** 2026-07-12  
**Audience:** Humans and coding agents working on product features

This is the standard path from idea to **production**. It is **proportional**: tiny work skips ceremony; everything non-trivial uses the full pipeline. Implementation is **phased**, with feedback loops—not a one-way waterfall.

**Production gate:** code reaches production via **merge to `main`** (then deploy). Dogfood and UAT happen **before** that merge (on a feature branch / preview env), unless an emergency hotfix (document why).

---

## 1. Pipeline (full path)

```
Ideation
    ↓
Requirements
    ↓
Tech sketch                          ← how (lightweight)
    ↓
Reviews (parallel when possible)
    ├── CEO / product
    ├── Security
    ├── UI design
    └── Architecture design
    ↓
Developer reviews review docs
    ├── Agree → proceed
    ├── Resolve disagreement → update reqs / sketch / open questions
    ├── Defer (if possible) → log; continue non-blocked work
    └── Hold idea → stop implementation
    ↓
Open questions resolution            ← blockers for next phase clear
    ↓
Implementation (by phase)
    ├── Build phase N
    ├── Automated / developer test
    └── (loop) new blockers → open questions / requirements / sketch
    ↓
Docs sync                            ← manuals + dogfood/UAT docs so others can exercise the feature
    ↓
Dogfood                              ← internal use on branch / staging
    ↓
UAT                                  ← scripted acceptance (pass required for merge)
    ↓
Merge to main → production           ← production gate
    ↓
Monitor (production signals)
    ↓
Requirements update                  ← learnings, gaps, next phase
```

**Not a single pass.** Reviews and open questions can send work **back** to requirements or tech sketch. Dogfood/UAT failures send work **back** to implementation. Production monitoring sends work **forward** into the next requirements slice.

---

## 2. Proportional process

| Size | Examples | Path |
|------|----------|------|
| **Tiny** | Typo, copy, one-line bug, config flag already decided | Skip formal pipeline → implement → **merge** (smoke only) |
| **Small** | Localized fix, minor UX polish, no new product surface | Idea optional → implement → light docs if user-facing → **merge** |
| **Everything else** | New feature, schema change, AI, auth, multi-page UX | **Full pipeline** including dogfood + UAT **before merge** |

When in doubt, use the **full** pipeline.  
Tiny/small must **not** skip security or product decisions on sensitive changes (auth, RLS, AI, money, client data)—treat those as full.  
**Merge to `main` is still required for production** for all sizes.

---

## 3. Stages and folders (keep docs organized)

| Stage | Purpose | Where artifacts live |
|-------|---------|----------------------|
| **Ideation** | Problem, one-liner, non-goals, rough success metric | [`.docs/ideas/`](../ideas/) |
| **Requirements** | FR/NFR, phases, acceptance criteria, review packet links | [`.docs/requirements/`](../requirements/) |
| **Tech sketch** | Lightweight *how*: data model, APIs, engine contracts | [`.docs/tech-sketch/`](../tech-sketch/) |
| **CEO review** | Scope, MVP cut, priority | [`.docs/ceo-review/`](../ceo-review/) |
| **Security review** | Trust boundaries, STRIDE, authZ, AI/data | [`.docs/security-review/`](../security-review/) |
| **UI design review** | Personas, flows, empty states | [`.docs/ui-review/`](../ui-review/) |
| **Architecture design review** | Schema, APIs, migration | [`.docs/architecture-review/`](../architecture-review/) |
| **Open questions** | Decision log; phase gate | [`.docs/open-questions/`](../open-questions/) |
| **Implementation tracking** | Phase checklists / tasks | [`.docs/checklist/`](../checklist/) |
| **Long-form design** (optional) | Deeper tech design | [`.docs/design/`](../design/) |
| **Docs sync** | User/operator manuals + API notes for the feature | [`.docs/manuals/`](../manuals/), root `README.md` |
| **Dogfood notes** | Internal exercise log / known issues | [`.docs/development-process/dogfood/`](./dogfood/) or checklist |
| **UAT scripts & results** | Scripted acceptance | [`UAT_Scripts/`](../../UAT_Scripts/) (repo root); optional feature notes under [`.docs/development-process/uat/`](./uat/) |
| **This process** | How we work | [`.docs/development-process/`](./) |

**Naming:** same feature stem across docs when possible, e.g. `data-parsers-lims-runs.md`, `uat-data-parsers-lims-runs.md`.

**Do not** leave feature docs at `.docs/` root. Do not invent parallel process trees.

### Tech sketch vs design vs architecture review

| Artifact | Role |
|----------|------|
| **Tech sketch** | Early *how*—enough for architecture/UI review |
| **Architecture review** | Verdict on the sketch/requirements |
| **design/** | Optional longer design once the approach is stable |

---

## 4. Exit criteria (tracking)

| Stage | Exit when |
|-------|-----------|
| **Ideation** | Problem, non-goals, rough success metric written |
| **Requirements** | FR/NFR, phases, acceptance criteria, review links; ready for review |
| **Tech sketch** | Model/APIs/contracts sketched; risks listed; linked from requirements |
| **Each review** | Verdict: **Accept** / **Accept with conditions** / **Reject** |
| **Developer review of reviews** | Disagreements **resolved**, **deferred**, or idea **on hold**—§5 |
| **Open questions (phase N)** | No **Open** items that **block phase N** |
| **Implementation phase N** | Phase acceptance met; automated tests green for touched paths |
| **Docs sync** | Manuals/README updated enough that a non-author can run dogfood/UAT; UAT script exists for full-pipeline features |
| **Dogfood** | Feature exercised internally; blockers logged (fix or accept risk) |
| **UAT** | Scripted cases executed; **pass** (or waived in writing with owner) |
| **Merge → production** | Merged to **`main`**; deploy per environment practice |
| **Monitor** | Post-deploy signals noted (errors, confusion, support) |
| **Requirements update** | Learnings / next phase / deferrals written back |

---

## 5. Who does what

| Role | Responsibility |
|------|----------------|
| **Author** | Idea → requirements → tech sketch; review stubs |
| **CEO / Security / UI / Architecture** | Verdicts on packet |
| **Developer** | Reads reviews; implement; docs for dogfood/UAT; fix UAT fails |
| **Dogfood participants** | Internal users; file issues quickly |
| **UAT executor** | Run script; record pass/fail |
| **Merger** | Merge to `main` only after UAT gate (full pipeline) |

### Developer handling of review outcomes

| Situation | Action |
|-----------|--------|
| Agree | Proceed to open-questions gate for the phase |
| Disagreement | Resolve via reqs/sketch/open questions; re-review if material |
| Defer | Log; implement only non-blocked slices |
| Hold | Stop implementation |

---

## 6. Open questions gate

See [`.docs/open-questions/`](../open-questions/) and root [`AGENTS.md`](../../AGENTS.md).

1. Blocking questions for **phase N** must not remain **Open**.  
2. Checklists = tasks; open questions = decisions.  
3. New questions during coding → log; **pause** if blocking.  
4. Labels: **Open** · **Decided (provisional)** · **Decided** · **Deferred**.

---

## 7. Phased implementation

```
For each phase N:
  1. Open questions that block N are Decided / provisional
  2. Implement N + automated tests
  3. Docs sync for that slice (enough for dogfood/UAT)
  4. Dogfood
  5. UAT (phase or cumulative script)
  6. Merge to main → production   ← required to be “live”
  7. Monitor production
  8. Requirements update
  9. Next phase or stop
```

| Loop | Direction |
|------|-----------|
| Review → requirements / tech sketch | Before code |
| Implementation → open questions | New unknowns |
| Dogfood/UAT fail → implementation | Fix before merge |
| **Monitor → requirements** | Next phase / backlog |
| Phase N done → phase N+1 | Re-run open-questions gate for N+1 |

Multi-phase epics: each phase can merge independently when UAT for that phase passes (prefer small production increments).

---

## 8. Docs sync (after implementation, before dogfood/UAT)

**Why here:** dogfood and UAT need accurate instructions. Docs are not only a post-production cleanup.

| Update | When |
|--------|------|
| Manuals / API / README | User-visible behavior changed |
| **UAT script** | Full-pipeline feature: create or update `UAT_Scripts/uat-<feature>.md` |
| **Dogfood guide** (optional) | Short “how to try this on staging” in `development-process/dogfood/` or checklist |

Docs may still get a final polish after UAT findings; that is a small loop, not a substitute for pre-UAT docs.

---

## 9. Dogfood

**What:** Internal use of the feature on a **feature branch or staging** environment—not yet production `main`.

**Goals**

- Catch UX confusion and broken paths before formal UAT  
- Exercise real workflows (e.g. import → publish) with realistic data  

**Exit**

- At least one non-author path exercised when possible  
- Issues filed; **blockers fixed** or explicitly accepted before UAT  

**Artifacts:** short log under [`.docs/development-process/dogfood/`](./dogfood/) or notes on the checklist (date, who, what broke).

See [dogfood/README.md](./dogfood/README.md).

---

## 10. UAT

**What:** **Scripted** acceptance against requirements for this phase/feature.

**Location**

- Primary: [`UAT_Scripts/`](../../UAT_Scripts/) (existing repo convention: `uat-*.md`, runners, results)  
- Process notes / templates: [`.docs/development-process/uat/`](./uat/)

**Exit**

- Script run; results recorded (pass/fail)  
- **Pass required** to merge for full-pipeline work  
- Fail → fix on branch → re-dogfood if needed → re-UAT  

**Not the same as** automated unit/integration tests (those run during implementation). UAT is human-executable product acceptance.

See [uat/README.md](./uat/README.md).

---

## 11. Merge → production

| Rule | Detail |
|------|--------|
| **Production path** | Merge feature work to **`main`**, then deploy per environment practice |
| **Gate (full pipeline)** | Docs sync done · dogfood done · **UAT pass** (or written waiver) |
| **Gate (tiny/small)** | CI green; smoke; still merge to `main` for production |
| **Do not** | Treat “works on my machine / long-lived feature branch” as production |

After merge: **monitor** production, then **update requirements** with learnings.

---

## 12. Review packet template

| Doc | Role |
|-----|------|
| `ideas/<stem>.md` | Ideation |
| `requirements/<stem>.md` | Requirements |
| `tech-sketch/<stem>.md` | Tech sketch |
| `ceo-review/<stem>.md` | CEO verdict |
| `security-review/<stem>.md` | Security verdict |
| `ui-review/<stem>.md` | UI verdict |
| `architecture-review/<stem>.md` | Architecture verdict |
| `open-questions/<stem>.md` | Decision log |
| `checklist/<stem>.md` (optional) | Phase tasks |
| `UAT_Scripts/uat-<stem>.md` | UAT script |
| `development-process/dogfood/<stem>.md` (optional) | Dogfood log |

---

## 13. Examples

| Feature | Note |
|---------|------|
| **run-results** | Phased build → docs → UAT/dogfood as applicable → **merge to main** |
| **data-parsers-lims-runs** | In review; after implement: docs + dogfood + UAT **before** production merge |

---

## 14. Agent rules (summary)

1. Full pipeline for non-tiny work; never skip security on AI/auth/RLS.  
2. Correct folder; same feature stem.  
3. No phase implement while blocking open questions are **Open**.  
4. Read reviews; resolve / defer / hold.  
5. After implement: **docs → dogfood → UAT → merge to main** for production.  
6. After production: monitor → requirements update.  

---

## Related

- [`.docs/README.md`](../README.md)  
- [dogfood/README.md](./dogfood/README.md)  
- [uat/README.md](./uat/README.md)  
- [`.docs/open-questions/README.md`](../open-questions/README.md)  
- [`.docs/tech-sketch/README.md`](../tech-sketch/README.md)  
- [`UAT_Scripts/`](../../UAT_Scripts/)  
- Root [`AGENTS.md`](../../AGENTS.md)  

# NimbleLIMS product development process

**Status:** Active  
**Date:** 2026-07-12  
**Audience:** Humans and coding agents working on product features

This is the standard path from idea to shipped software. It is **proportional**: tiny work skips ceremony; everything non-trivial uses the full pipeline. Implementation is **phased**, with feedback loops—not a one-way waterfall.

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
Open questions resolution            ← only blockers for next phase must be clear
    ↓
Implementation (by phase)
    ├── Build phase N
    ├── Test
    └── (loop) new blockers → open questions / requirements / sketch
    ↓
Monitor (UAT / dogfood / production signals)
    ↓
Requirements update                  ← learnings, gaps, next phase
    ↓
Docs sync + merge
```

**Not a single pass.** Reviews and open questions can send work **back** to requirements or tech sketch. Monitoring sends work **forward** into the next requirements slice.

---

## 2. Proportional process

| Size | Examples | Path |
|------|----------|------|
| **Tiny** | Typo, copy, one-line bug, config flag already decided | **Skip** formal pipeline → implement → small PR |
| **Small** | Localized fix, minor UX polish, no new product surface | **Idea optional** → implement (tests as needed) → docs if user-facing |
| **Everything else** | New feature, schema change, AI, auth, multi-page UX, cross-service work | **Full pipeline** below |

When in doubt, use the **full** pipeline.  
Tiny/small must **not** be used to skip security or product decisions on sensitive changes (auth, RLS, AI, money, client data)—treat those as full.

---

## 3. Stages and folders (keep docs organized)

| Stage | Purpose | Where artifacts live |
|-------|---------|----------------------|
| **Ideation** | Problem, one-liner, non-goals, rough success metric | [`.docs/ideas/`](../ideas/) |
| **Requirements** | FR/NFR, phases, acceptance criteria, review packet links | [`.docs/requirements/`](../requirements/) |
| **Tech sketch** | Lightweight *how*: data model, APIs, engine contracts, sequence diagrams | [`.docs/tech-sketch/`](../tech-sketch/) |
| **CEO review** | Scope, MVP cut, priority, market fit | [`.docs/ceo-review/`](../ceo-review/) |
| **Security review** | Trust boundaries, STRIDE, authZ, AI/data handling | [`.docs/security-review/`](../security-review/) |
| **UI design review** | Personas, flows, empty states, dangerous defaults | [`.docs/ui-review/`](../ui-review/) |
| **Architecture design review** | Schema, APIs, migration, system fit | [`.docs/architecture-review/`](../architecture-review/) |
| **Open questions** | Decision log; gate for blocked work | [`.docs/open-questions/`](../open-questions/) |
| **Implementation tracking** | Phase checklists / tasks | [`.docs/checklist/`](../checklist/) |
| **Long-form design** (optional) | Deeper tech design after sketch solidifies | [`.docs/design/`](../design/) |
| **Manuals / root README** | User- and operator-facing truth after ship | [`.docs/manuals/`](../manuals/), root `README.md` |
| **This process** | How we work | [`.docs/development-process/`](./) |

**Naming:** One feature uses the **same stem** across folders when possible, e.g. `data-parsers-lims-runs.md`.

**Do not** leave feature docs at `.docs/` root. Do not invent parallel process trees.

### Tech sketch vs design vs architecture review

| Artifact | Role |
|----------|------|
| **Tech sketch** | Early *how*—enough for architecture/UI review; may be incomplete |
| **Architecture review** | Verdict on the sketch/requirements (Accept / conditions / Reject) |
| **design/** | Optional longer design once the approach is stable (or historical) |

---

## 4. Exit criteria (tracking)

| Stage | Exit when |
|-------|-----------|
| **Ideation** | Problem, non-goals, rough success metric written; status not “commitment to build” |
| **Requirements** | FR/NFR, delivery phases, acceptance criteria, links to review stubs; status “ready for review” |
| **Tech sketch** | Proposed model/APIs/engine contracts; open risks listed; linked from requirements |
| **Each review** | Verdict recorded: **Accept** / **Accept with conditions** / **Reject**; conditions listed |
| **Developer review of reviews** | Disagreements **resolved**, **deferred** (with log), or idea **on hold**—see §5 |
| **Open questions (for phase N)** | No **Open** items that **block phase N** (provisional OK if labeled) |
| **Implementation phase N** | Acceptance for that phase met; tests green for changed paths; new questions logged if found |
| **Monitor** | Notes from UAT/dogfood/prod (even informal) captured |
| **Requirements update** | Learnings / next phase / deferrals written back into requirements or open questions |
| **Docs + merge** | Manuals/README updated if user-facing; merge to main (or PR) |

---

## 5. Who does what (including developer on reviews)

| Role | Responsibility |
|------|----------------|
| **Author (PM / tech lead / agent)** | Writes idea → requirements → tech sketch; opens review stubs |
| **CEO review** | Scope, priority, MVP cut |
| **Security** | Trust boundary; blocks unsafe AI/auth/data paths |
| **UI design** | Flows and clarity; blocks confusing/dangerous UX |
| **Architecture design** | Technical approach; blocks unsound schema/contracts |
| **Developer (implementer)** | **Reads all completed review docs** before coding the gated phase |

### Developer handling of review outcomes

| Situation | Action |
|-----------|--------|
| Agree with reviews | Proceed to open-questions gate for the phase |
| Disagreement | Discuss; **resolve** by updating requirements, tech sketch, and/or open questions; re-review only what changed if material |
| Can ship without deciding | **Defer**—log in open questions as Deferred or Decided provisional; implement non-blocked slices only |
| Fundamental conflict | **Hold idea**—do not implement; status on idea/requirements = on hold |

Developers do **not** silently ignore review conditions.

---

## 6. Open questions gate

Owned by [`.docs/open-questions/`](../open-questions/) and root [`AGENTS.md`](../../AGENTS.md).

1. Blocking questions for the **next phase** must not remain **Open**.  
2. Checklists track *tasks*; open questions track *decisions*.  
3. If coding surfaces a product/architecture question, **add it** to the open-questions doc and **pause** if it blocks the current slice.  
4. Labels: **Open** · **Decided (provisional)** · **Decided** · **Deferred**.

---

## 7. Phased implementation + feedback loops

Full-pipeline features are delivered in **phases** (P0, P1, …), not one big bang.

```
For each phase N:
  1. Confirm open questions that block N are Decided / provisional
  2. Implement N
  3. Test (automated + manual UAT for that slice)
  4. Monitor (dogfood, logs, support signals)
  5. Feed learnings → requirements (and open questions if new decisions)
  6. Start phase N+1 or stop
```

| Loop | Direction |
|------|-----------|
| Review → requirements / tech sketch | Fix scope or design before code |
| Implementation → open questions | New unknowns pause or slice |
| **Test → monitor → requirements** | Production learning drives the next requirement delta |
| Phase N done → phase N+1 | Re-run open-questions gate for N+1 only |

---

## 8. After a phase or epic ships

1. **Test** — automated suite for touched paths; UAT script if user-facing.  
2. **Monitor** — short note (checklist or requirements “learnings”): what broke, what users confused.  
3. **Requirements update** — close acceptance items; add follow-on FR or defer explicitly.  
4. **Docs sync** — manuals / API / README if behavior is user-visible.  
5. **Merge** — land on `main` (or open PR); avoid long-lived doc-only drift on side branches when process docs should apply globally.

---

## 9. Review packet template (full pipeline)

For feature stem `my-feature`:

| Doc | Status progression |
|-----|-------------------|
| `ideas/my-feature.md` | Exploratory → linked to requirements |
| `requirements/my-feature.md` | Draft → ready for review → approved / conditions |
| `tech-sketch/my-feature.md` | Draft → ready for architecture/UI review |
| `ceo-review/my-feature.md` | Awaiting → verdict |
| `security-review/my-feature.md` | Awaiting → verdict |
| `ui-review/my-feature.md` | Awaiting → verdict |
| `architecture-review/my-feature.md` | Awaiting → verdict |
| `open-questions/my-feature.md` | Living log |
| `checklist/my-feature.md` (optional) | Phase tasks |

Reviews may run **in parallel** once requirements + tech sketch are ready enough.

---

## 10. Examples

| Feature | Process note |
|---------|----------------|
| **run-results** (shipped) | Idea → reviews → open questions decided → phased P0–P4 → docs → merge |
| **data-parsers-lims-runs** (in flight) | Idea → requirements → reviews open → open questions (schema, testing) → tech sketch next → implement only after phase gates |

---

## 11. Agent rules (summary)

1. Prefer **full pipeline** for non-tiny work; never skip security on AI/auth/RLS.  
2. Put artifacts in the **correct folder**; same feature stem.  
3. **Do not implement** a phase while its open questions are **Open**.  
4. Read review verdicts; resolve / defer / hold—do not ignore.  
5. After shipping a slice: test, note monitor signals, update requirements/docs.  

---

## Related

- [`.docs/README.md`](../README.md) — documentation map  
- [`.docs/open-questions/README.md`](../open-questions/README.md) — gate rule  
- [`.docs/tech-sketch/README.md`](../tech-sketch/README.md) — tech sketch purpose  
- Root [`AGENTS.md`](../../AGENTS.md) — open questions gate for agents  

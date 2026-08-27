# Discussion: Framework-driven NimbleLIMS (and accessioning flexibility)

**Date:** 2026-08-25  
**Status:** Discussion — Leadership comments captured; not an implement gate  
**Author framing:** Marc  
**Inputs:** [`.docs/internal/prd/nimblelims-prd.md`](../prd/nimblelims-prd.md) · [`.docs/internal/prd/sample-accessioning/PRD.md`](../prd/sample-accessioning/PRD.md) · accessioning ISSUES · atomic-receive locks · idea `accessioning-and-workflows-revisit`  
**Personas:** CEO · Security CSO · Scientific CSO · VP Lab Ops  

---

## 1. Thesis (Marc)

Labs share one spine:

```text
Sample → Tests → Results → Reports
```

They all do it **slightly differently**: how intake works (scan stream, dual entry, manifest+verify, bulk), when tests are ordered, whether work is driven by a **process** or a **test backlog**, what fields are sticky, what review gates apply.

**Therefore NimbleLIMS must be a framework:** behavior driven by **configuration stored in the DB**, not by hard-coded “the one accessioning path.”

Out of the box we still ship **opinionated defaults** (e.g. atomic scan-receive as the seeded intake profile) so a startup can run without configuring everything. Defaults ≠ hard-coding forever.

### What “framework” means here

| Layer | Configurable in DB (examples already or needed) |
|-------|--------------------------------------------------|
| **Fields** | FieldDefinitions, lists, name templates |
| **Intake** | Intake **profiles/modes** (steps, required fields, sticky set, whether sample-ID shown, whether tests optional, continuous vs verify) |
| **Work** | Process definitions vs test-order backlog; how they relate (open — A-15 / X-5) |
| **Assay** | Analyses, batteries, parsers, METHOD_CATALOG |
| **Gates** | Review/second-person, status transitions (system-managed vs pickable) |
| **AuthZ** | Roles/permissions; never replace RLS with “config says allow” |

### What’s wrong today (accessioning)

1. **PRD goals** for accessioning read as a **single hard path** (scan only, no sample-ID, one txn) — correct as a **default profile**, incomplete as **product goals**.  
2. The **wizard** was intended as multi-mode flexibility but was never a real config framework — it became one awkward UI.  
3. Adjacent shipped pieces (Field Management, process definitions, workflow templates, parsers) are already framework-shaped; **intake is the inconsistent holdout**.  
4. **Tests at receive** vs **process-owned work** (A-15) is the same class of problem: hard-coding “order tests at intake” without a configurable work model.

### Tension with recent P0

Leadership P0 (2026-08-24) locked **atomic receive only** for the first implement slice and **deferred** unfinished wizard modes. That remains a valid **sequencing** choice: ship one coherent default path first.

This discussion asks to **reframe product goals**: AR = OOB default configuration of an intake framework — not “flexibility is out of product forever.”

---

## 2. Author recommendation

| # | Recommendation |
|---|----------------|
| R1 | Update umbrella PRD: **framework-first** product principle; OOB defaults for BioTech/Pharma startups |
| R2 | Update accessioning PRD goals: flexibility via **DB-backed intake profiles**; AR goals become **Default profile (OOB)** |
| R3 | Keep P0 sequencing: implement AR as first seeded profile; do not revive unfinished wizard as the framework |
| R4 | New work (later): intake-profile schema + admin; map dual-entry / manifest-verify as **profiles**, not one-off UIs |
| R5 | Park solving A-15 inside intake; but track it as a **work-model framework** question (tests backlog vs process claim) |

---

## 3. CEO / Product (Founder)

**Verdict on thesis:** **Agree — this is the right product identity.**

A LIMS that hard-codes one lab’s intake is a consulting project forever. A LIMS that sells “sample → test → result → report” with **tenant configuration** is a product. BioTech/Pharma startups still need a **fast OOB path**; that’s seed data + default profile, not an excuse to skip the framework.

**Scope caution:** Do not expand implement scope mid–atomic-receive. Reframe docs **now**; build intake-profile engine **after** AR default works. Wizard revival without DB config = same failure mode.

**Conditions**

| ID | Comment |
|----|---------|
| **C-CEO-1** | Umbrella PRD must state: **same spine, configurable how**. |
| **C-CEO-2** | OOB = opinionated BioTech/Pharma defaults (AR-shaped intake), not “empty framework.” |
| **C-CEO-3** | Framework ≠ infinite modes at once. Ship profiles when a second real lab mode is needed — not speculative. |
| **C-CEO-4** | Freeze: no new accessioning UI modes until AR default is real **or** Leadership explicitly opens an intake-framework packet. |

**Mode:** HOLD SCOPE on code; SELECTIVE EXPANSION on **product narrative** in PRDs.

```
CEO: Agree with framework thesis; hold code scope; update PRDs now
```

---

## 4. VP Lab Ops (Deiter)

**Verdict on thesis:** **Agree with hard bench conditions.**

Every lab does receive differently — continuous scan, cooler+manifest, dual ID entry for legacy barcodes. Ops will reject a product that only does one of those **if** they’re stuck. They will also reject a product that makes the tech configure YAML at the bench.

**Conditions**

| ID | Comment |
|----|---------|
| **L-OPS-1** | **One fast OOB path** must exist day one: scan → commit → next tube. No “configure first, then receive.” |
| **L-OPS-2** | Mode/profile changes are **admin / lab-manager** work, not mid-rack. |
| **L-OPS-3** | Sticky fields, barcode-as-vessel, system sample ID remain correct for the **default** high-throughput profile. |
| **L-OPS-4** | Dual-entry / manifest-verify are real lab modes — schedule as **profiles after AR**, not as half-wizard. |
| **L-OPS-5** | A-15 (tests vs process): on the bench, “what’s next?” must be unambiguous. Prefer process journey for SOP labs; tests-as-backlog for simple R&D. Configurable later — don’t ship ambiguous queues. |

```
LAB OPS: Agree; OOB speed non-negotiable; profiles admin-owned; no unfinished wizard
```

---

## 5. Security CSO (Heidi / Günter)

**Verdict on thesis:** **Agree — with elevation controls.**

Configurable intake is an **AuthZ surface**. If “profile” can weaken project checks, invent parallel receive permissions, or let Client edit intake rules, we re-open the receive AuthZ spine (PR 68).

**Conditions**

| ID | Comment |
|----|---------|
| **S-CSO-1** | Intake profiles stored in DB; **mutate = `config:edit` only** (or stricter). Not Client. |
| **S-CSO-2** | Every profile’s commit path still = **sample create AuthZ + project RLS**. No profile flag bypasses RLS. |
| **S-CSO-3** | Prefer **one receive service** parameterized by profile over many endpoints. |
| **S-CSO-4** | Audit profile id on receive events (who received under which config). |
| **S-CSO-5** | Do not ship profile engine in the same slice as AR unless AuthZ matrix is restamped — docs OK now; code later. |

Atomic-receive AuthZ docs gate remains **satisfied**; product code still waits on Marc for P0.

```
SECURITY CSO: Agree; config:edit; no RLS bypass; one service + profile param
```

---

## 6. Scientific CSO

**Verdict on thesis:** **Agree — protect scientific SoT.**

Flexibility must not blur **identity**, **lineage**, or **result integrity**. Different intake modes can change UX; they must not change what a Sample ID means, what a Result is bound to, or whether daughters are the assay target after extract.

**Conditions**

| ID | Comment |
|----|---------|
| **Sci-1** | Sample lab ID vs container barcode remains two identities across all profiles. |
| **Sci-2** | Framework fields for intake must not silently write scientific SoT that belongs on results / process entries. |
| **Sci-3** | Ordering tests at receive is scientifically optional; for process-driven SOPs, “work to do” should follow **process membership**, not a dangling Test list (ties to A-15 / X-5). |
| **Sci-4** | Status after receive for default profile stays **Available for Testing** so Decision #24 eligibility stays coherent. |
| **Sci-5** | Profile-driven QC/review gates later — default R&D vs GxP already sketched in umbrella PRD; keep tenant-configurable. |

```
SCIENTIFIC CSO: Agree; identity/lineage/results SoT fixed; work-queue model separate from intake UX
```

---

## 7. Synthesis

| Question | Answer from this discussion |
|----------|------------------------------|
| Is framework the right product shape? | **Yes** (all personas) |
| Are current accessioning PRD goals wrong? | **Incomplete** — they describe the **OOB default**, not the framework |
| Kill atomic receive? | **No** — keep as default seeded profile / P0 path |
| Revive wizard as-is? | **No** — unfinished UI ≠ framework |
| When to build intake-profile engine? | **After** AR default is coherent (or explicit Leadership packet) |
| Where is config stored? | **DB** — admin-editable; not code constants |

### Proposed PRD wording direction

- Umbrella: add **Platform principle: framework + OOB defaults**.  
- Accessioning: split **Goals (framework)** vs **Default profile (atomic receive OOB)**.  
- ISSUES: keep A-1–A-4 deferred for P0 code; reopen as **intake-profile** packet when ready — not as wizard revival.

---

## 8. Open follow-ups (not stamped)

1. Intake-profile schema sketch (steps, field set, sticky, txn rules).  
2. How profiles relate to Workflow Templates (compose vs replace).  
3. Work-model framework: Test backlog ↔ Process claim (A-15 / X-5).  
4. Whether “modes” are named profiles selectable at session start or lab-global default only.

---

## 9. Sign-off table (discussion only)

| Persona | Stance |
|---------|--------|
| CEO | Agree — narrative now; hold code expansion |
| VP Lab Ops | Agree — OOB speed; admin-owned profiles |
| Security CSO | Agree — config:edit; no AuthZ bypass |
| Scientific CSO | Agree — protect SoT; separate work-queue problem |

**Next:** Update `nimblelims-prd.md` + `sample-accessioning/PRD.md` to reflect framework + OOB default. No implement gate change.

---

## Addendum (same day) — work orders complete the thesis

See **[what-is-a-good-framework.md](2026-08-25-what-is-a-good-framework.md)** and **[work-orders-assay-params-compounds.md](2026-08-25-work-orders-assay-params-compounds.md)**.

Intake flexibility alone is insufficient. The missing middle is **order/params → routing map → work orders → Process/Experiment/LimsRun**. Analysis-at-accession is not the work model. Execution framework already exists; configure how work *enters* it.

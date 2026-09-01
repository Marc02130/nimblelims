# Temporary issues — Experiments & entries

**Parent:** [ISSUES.md](ISSUES.md)  
**Status:** Synced 2026-08-26 (paths + framework; Leadership/BA/Dev)  
**Includes:** aliquot/pool + extract-hold (largest complexity knot)  
**Kick-back log:** [../../../decision-logs/extract-hold-dual-map-kickback.md](../../../decision-logs/extract-hold-dual-map-kickback.md)

---

## A. Entries framework

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| E-1 | Only two kinds (`experiment_sample_data` / `experiment_data`) vs desire for richer catalog (#17–21 Open) | Feature pressure without Phase 4 | Hold catalog expansion |
| E-2 | Save vs submit vs write-back allowlist narrow / evolving | Unclear when Sample updates | Align with extract-hold kick-back |
| E-3 | Accessioning identity fields RO on entries — but processing still needs dest type / qty story | Boundary blur with Sample columns | Keep RO for intake SoT; FDs for process data |
| E-4 | Header-pins-to-top parked | Template UX debt | Separate entries fold |
| E-5 | Ad hoc FieldDefinitions on instance vs template-authored write-back rules | Accidental write-back | Enforce “ad hoc never write-back” |

## B. Cohort / start

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| E-6 | Decision #24 (Available for Testing + process membership) vs accessioning still setting **Received** | Can’t start experiments on freshly accessioned samples | Fix intake status (AR) |
| E-7 | Template `accepted_sample_types` vs product stamp: gate on **experiment / LimsRun**, not entry | Spec/AC12 conflict | Rewrite AC; implement gate at right layer |
| E-8 | Cohort locked after start vs desire to add mid-flight | Support tickets | Hold lock; document |

## C. Aliquot / pool + extract-hold (critical)

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| E-9 | **Dual-map kick-back:** dest vol/amount/conc as entry FDs vs Sample/Contents update timing not restamped | Blocks clean implement | Heidi/Mathilda restamp ([decision-logs](../../../decision-logs/extract-hold-dual-map-kickback.md)). Dev: unblock before WO schema |
| E-10 | **Atomic pair** locked (one add → plan + dest entries) but UI still offers separate presets | Operators create half-pairs | Template + ad hoc UI fix |
| E-11 | METHOD_CATALOG / `METHOD_PROFILES` plan inputs shipped; **dest FieldDefinitions attach** lag | Qty story incomplete | After E-9 |
| E-12 | Template authoring: method often present; **default dest type** weak/missing | Dest type only at runtime | Template controls per lock |
| E-13 | Mid-flight method change = cancel experiment (no warn/wipe) — UX may still allow edit attempts | 409 surprise | Lock controls after lines exist |
| E-14 | S3 transition catalog: read API + seeds; **mutate API + admin UI** lag | Can’t configure without DB | config:edit CRUD + thin admin |
| E-15 | Matrix still copies parent on mint (intentional); eligibility keys off `sample_type` — easy to miss | Wrong assay on “blood-looking” DNA | C2 messaging + UAT |
| E-16 | Normalization requires prior Result conc — not free type-in; failure modes opaque | Bench friction | Clear errors + which analyte |

## D. Docs / UAT

| ID | Issue | Why it hurts | Suggested next |
|----|-------|--------------|----------------|
| E-17 | extract-hold reviews still say “no product UI” in places while AliquotPlanEditor exists | False gaps | Doc restamp |
| E-18 | Hold notes claim dest never joins process — partially outdated | Re-work fixed bugs | Sync Hold + UAT |
| E-19 | Testdata: no blood / DNA daughter / Qubit in 0058/0059 | Can’t close path | Testdata OQ |

## Priority sketch

1. **E-9** restamp (blocker)  
2. **E-10 + E-14 + E-12** (pair, catalog admin, template dest)  
3. **E-7 + E-6** (gates + intake status)  
4. Docs **E-17–E-19**  

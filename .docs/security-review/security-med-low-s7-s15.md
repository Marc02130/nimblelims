# Security Review: Med/Low remediation packet (S7–S15)

**Date:** 2026-08-21  
**Status:** **Accept with conditions**  
**Packet:** Remediation of [codebase.md](codebase.md) S7–S15  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)  
**Tech sketch:** [`.docs/tech-sketch/security-med-low-s7-s15.md`](../tech-sketch/security-med-low-s7-s15.md)

## Relationship to codebase audit

| Doc | Role |
|-----|------|
| [codebase.md](codebase.md) | Finding list (S1–S6 Met; S7–S15 Open) |
| **This packet** | How Med/Low closes |

## STRIDE (this packet)

| Threat | Control |
|--------|---------|
| Spoofing | S15 lockout; S13 verify-email hygiene |
| Tampering | S7 start access; S14 write-back allowlist |
| Repudiation | Unchanged |
| Info disclosure | S9 auth; S13 catalog GET; S10 honesty |
| DoS | S8 upload caps; S15 lockout |
| Elevation | S11 FORCE RLS; S12 no published DB in prod |

## Conditions

| ID | Severity | Condition |
|----|----------|-----------|
| **Sec1** | Med | S9: unauthenticated validate must be impossible after P1. |
| **Sec2** | Med | S8: caps server-side; nginx alone insufficient. |
| **Sec3** | Med | S7: no cross-client sample start via raw UUID. |
| **Sec4** | Med | S12: prod profile must not ship `5432:5432` + `lims_password`. |
| **Sec5** | Low | S15: never store plaintext passwords in throttle state. |
| **Sec6** | Med | S11: FORCE must not be claimed until tested as `lims_app`. |
| **Sec7** | Low | S10: no marketing claim that browser RBAC is security. |

## Phasing gate

| Phase | Security gate |
|-------|----------------|
| P1 | Sec1, Sec2, S13, S14 |
| P2 | Sec3, Sec5 |
| P3 | Sec4, Sec6 |
| P4 | Sec7 |

## Verdict

| Field | Value |
|-------|--------|
| **Verdict** | **Accept with conditions** Sec1–Sec7 |
| **Deep `/cso`** | Still optional; not a substitute for this packet |
| **Hold High S1–S6?** | No — separate track |

## Implement gate

**Cleared for P1** after CEO/Arch/QA also Accept (provisional OQ leans OK).  
**P3** needs OQ-S11a/b.

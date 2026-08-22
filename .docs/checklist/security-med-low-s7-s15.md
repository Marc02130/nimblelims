# Checklist: security-med-low-s7-s15

**Branch:** `security/med-low-s7-s15`  
**Last updated:** 2026-08-21  
**Requirements:** [`.docs/requirements/security-med-low-s7-s15.md`](../requirements/security-med-low-s7-s15.md)

## Packet gate

- [x] Idea  
- [x] Requirements  
- [x] Tech sketch  
- [x] Schema-changes  
- [x] Open questions  
- [x] CEO / Arch / Security / QA reviews drafted  
- [ ] Reviews Accept (re-confirm P4 cookie scope with CEO if needed)  
- [x] OQs decided (2026-08-21) — S9 enter\|review; S10 cookies; S11a atomic+INSERT-only created_by; S11b contents RLS; S12 prod overlay; S14 drop write-back; S15 Postgres table  

## P1 — Quick harden (S8, S9, S13, S14)

- [x] Upload 10 MB caps (import-file + SOP) + nginx `client_max_body_size 10m`  
- [x] AuthN + `result:enter`|`review` on `/results/validate`  
- [x] Tighten GET `/roles` `/permissions`; verify-email no existence leak  
- [x] Drop biotype/temperature from write-back allowlist (S14)  
- [x] Tests (`test_security_p1_s8_s9_s13_s14.py`)  

## P2 — Access & abuse (S7, S15)

- [x] Start/link/run cohort sample access via `require_accessible_sample` (RLS + has_project_access)  
- [x] `login_throttle` table (0063) + lockout service  
- [x] Tests (`test_security_p2_s7_s15.py`)  

## P3 — Platform (S11, S12)

- [x] FORCE RLS migration `0064`  
- [x] Containers policies split (INSERT `created_by`; UPDATE/DELETE via contents/project)  
- [x] `contents` RLS + FORCE + policy  
- [x] `docker-compose.prod.yml` (ports: [] on db)  
- [x] Tests (`test_security_p3_s11_s12.py`)  

## P4 — Cookie AuthN (S10 expanded)

- [ ] httpOnly Secure SameSite cookie (or BFF) design in tech sketch detail  
- [ ] Login/logout/me + frontend credentials  
- [ ] CSRF strategy  
- [ ] Remove localStorage token reliance  
- [ ] manuals/backend-auth + README honesty  

## Docs / UAT / merge

- [ ] `UAT_Scripts/uat-security-med-low-s7-s15.md`  
- [ ] Update codebase.md S7–S15 statuses  
- [ ] UAT pass per phase  
- [ ] Merge to `main` (after High branch merge strategy decided)  

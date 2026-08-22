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

- [ ] Upload 10 MB caps (import-file + SOP) + nginx align  
- [ ] AuthN + permission on `/results/validate`  
- [ ] Tighten GET `/roles` `/permissions`; verify-email hygiene  
- [ ] Write-back allowlist vs system fields (S14)  
- [ ] Tests  

## P2 — Access & abuse (S7, S15)

- [ ] Start/link sample access via RLS/session  
- [ ] `login_throttle` table + lockout service  
- [ ] Tests  

## P3 — Platform (S11, S12)

- [ ] FORCE RLS migration(s)  
- [ ] Containers policy: INSERT-only `created_by`; no committed empty containers  
- [ ] `contents` RLS + policy  
- [ ] Prod compose overlay (no published 5432)  
- [ ] RLS regression tests  

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

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
- [ ] Reviews Accept  
- [ ] OQ-S9 / OQ-S14 decided (or provisional lean accepted)  
- [ ] OQ-S11a/b decided before P3  

## P1 — Quick harden (S8, S9, S13, S14)

- [ ] Upload 10 MB caps (import-file + SOP) + nginx align  
- [ ] AuthN + permission on `/results/validate`  
- [ ] Tighten GET `/roles` `/permissions`; verify-email hygiene  
- [ ] Write-back allowlist vs system fields (S14)  
- [ ] Tests  

## P2 — Access & abuse (S7, S15)

- [ ] Start/link sample access via RLS/session  
- [ ] Login throttle / lockout  
- [ ] Tests  

## P3 — Platform (S11, S12)

- [ ] FORCE RLS migration(s)  
- [ ] Containers created_by residual decision implemented  
- [ ] Prod compose overlay (no published 5432)  
- [ ] RLS regression tests  

## P4 — Honesty (S10)

- [ ] manuals/backend-auth + README + frontend comments  

## Docs / UAT / merge

- [ ] `UAT_Scripts/uat-security-med-low-s7-s15.md`  
- [ ] Update codebase.md S7–S15 statuses  
- [ ] UAT pass per phase  
- [ ] Merge to `main` (after High branch merge strategy decided)  

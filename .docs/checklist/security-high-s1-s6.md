# Checklist: security-high-s1-s6

**Branch:** `security/high-s1-s6`  
**Last updated:** 2026-08-20  
**Requirements:** [`.docs/requirements/security-high-s1-s6.md`](../requirements/security-high-s1-s6.md)

## Packet gate

- [x] Idea  
- [x] Requirements  
- [x] Tech sketch  
- [x] Schema-changes doc  
- [x] Open questions  
- [x] CEO / Arch / Security / QA reviews drafted (Accept with conditions)  
- [x] Q2 / Q7 decided (vendor seeds + must-change + complexity)  
- [ ] Q1 decided before P0d  

## P0a — S3 JWT + S4 logging

- [x] Resolve SECRET_KEY / JWT_SECRET_KEY; refuse defaults  
- [x] Align docker-compose + env examples  
- [x] Remove body logging from middleware  
- [x] Tests (`tests/test_security_config_s3_s4.py`)

## P0b — S2 passwords (+ Q2/Q7)

- [ ] bcrypt hash/verify + SHA256 upgrade path  
- [ ] Gate persona seeds behind ALLOW_DEV_SEED_USERS; prod bootstrap path  
- [ ] `users.must_change_password` migration + login gate + change-password API  
- [ ] Complexity rules (12+ / upper / lower / digit / symbol / ≠ username / ≠ current)  
- [ ] Frontend change-password gate  
- [ ] Tests (`test_auth` bcrypt + must-change + complexity)  

## P0c — S5 aliquot + S6 cohort write

- [ ] Entry cohort check on upsert / write-back  
- [ ] Aliquot execute single transaction  
- [ ] Source ∈ cohort; refuse null amount  
- [ ] Tests  

## P0d — S1 app role

- [ ] Q1 decided  
- [ ] Create `lims_app` + grants migration  
- [ ] SET LOCAL / set_config GUCs on request  
- [ ] Dual DATABASE_URL in compose/entrypoint  
- [ ] RLS tests as app role  

## Docs / UAT / merge

- [ ] manuals/backend-auth + README security claims  
- [ ] Update codebase.md S1–S6 status after ship  
- [ ] `UAT_Scripts/uat-security-high-s1-s6.md`  
- [ ] Dogfood local compose  
- [ ] UAT pass  
- [ ] Merge to `main`  

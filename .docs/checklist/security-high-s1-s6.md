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
- [ ] CEO review Accept  
- [ ] Architecture review Accept  
- [ ] Security review Accept  
- [ ] QA review Accept  
- [ ] Q1–Q2 decided before P0d  

## P0a — S3 JWT + S4 logging

- [x] Resolve SECRET_KEY / JWT_SECRET_KEY; refuse defaults  
- [x] Align docker-compose + env examples  
- [x] Remove body logging from middleware  
- [x] Tests (`tests/test_security_config_s3_s4.py`)

## P0b — S2 passwords

- [ ] bcrypt hash/verify + SHA256 upgrade path  
- [ ] Gate seed users behind ALLOW_DEV_SEED_USERS  
- [ ] Tests (`test_auth` bcrypt expectations)  

## P0c — S5 aliquot + S6 cohort write

- [ ] Entry cohort check on upsert / write-back  
- [ ] Aliquot execute single transaction  
- [ ] Source ∈ cohort; refuse null amount  
- [ ] Tests  

## P0d — S1 app role

- [ ] Q1/Q2 decided  
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

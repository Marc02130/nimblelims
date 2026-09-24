# UAT: UI-driven schema DDL (`ui-schema-ddl`)

**Stem:** `ui-schema-ddl`  
**Brief:** `.docs/review/requirements/ui-schema-ddl-brief.md`  
**Status:** Tobias **Fail** on product `8c14a84` (evidence `/workspace/uat-ui-schema-ddl-8c14a84/`). Blockers A+B fixed this tip — **re-UAT** §§2/3/6/7. No invent Pass.  
**Not IC50.**

## Fail bars (Tobias, locked)

1. No-privilege write → **403/422**, not silent drop; not-on-layout ≠ API allow.  
2. Privilege-denied read → **refuse**, not empty-as-layout.  
3. **`schema:edit`** only for CREATE/ALTER; lab role without it cannot DDL.  
4. CREATE/ALTER proves real Postgres (`information_schema`), not JSONB-as-config.  
5. Config path writing JSONB instead of DDL/catalog rows → **Fail**.

## Logins

- Admin: `admin` / `admin123` (has `schema:edit` + `layout:edit`)
- Lab tech: `lab-tech` / `labtech123` (no `schema:edit`)

## 1. Surfaces

1. Admin → Schema: **Tables**, **Columns**, **Layouts**, **Privileges** are four distinct tabs.  
2. Asked-for and Routing map are **unchanged** (not schema-config screens).  
**Pass / Fail:**

## 2. CREATE TABLE (AC2 / Fail bar 4)

1. As Admin, Tables → Add table → display name `Lot Notes` → Create real table.  
2. Physical name starts with `x_`. Platform columns shown as fixed.  
3. Prove in DB: table exists, `client_id` column, FORCE RLS.  
**Pass / Fail:**

## 3. ADD COLUMN on Samples (AC1)

1. Columns → table Samples → Add field `Lab note`, type Text.  
2. Preview copy says real field, not custom-attribute JSON.  
3. Prove `information_schema` has `lab_note` on `samples`.  
**Pass / Fail:**

## 4. schema:edit gate (S-UI-1 / Fail bar 3)

1. As lab-tech, open `/admin/schema/tables` (or call POST `/v1/schema/tables`).  
2. CREATE is **403**. `config:edit` alone is not enough.  
**Pass / Fail:**

## 5. Layout membership (OQ-2)

1. Layouts → pick Lab Technician + Samples list.  
2. Add/remove fields by membership. **No hide toggle.**  
3. Save does **not** CREATE/ALTER.  
**Pass / Fail:**

## 6. Privileges default-deny (S-UI-3 / Fail bar 1)

1. Privileges → a role with access **none** on Samples extra field.  
2. API write of that extra field → **403** with readable copy, not silent drop.  
3. Saving privileges does **not** grant `schema:edit`.  
**Pass / Fail:**

## 7. Deprecate vs DROP (OQ-9 / S-UI-6)

1. Deprecate the extra field — data retained.  
2. DROP without confirm → refused. DROP with confirm → audited.  
**Pass / Fail:**

## 8. JSONB-as-config (OQ-16 / Fail bar 5)

1. Type picker has no “JSONB config field”. List/Text/Number/etc. only.  
**Pass / Fail:**

## Sign-off

| Role | Result | SHA |
|------|--------|-----|
| Tobias | | |

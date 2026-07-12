# Schema changes: \<feature-stem\>

**Feature / cycle:**  
**Phases covered:** P0 / P1 / …  
**Status:** Draft | Ready for architecture review | Approved | Implemented  
**Alembic revisions:** _(fill when implemented)_  
**Requirements:**  
**Tech sketch:**  
**Architecture review:**  

## 1. Summary

One paragraph: what the DB must gain or change this cycle.

## 2. Delta (authoritative list)

### 2.1 New tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| | | |

### 2.2 Altered tables

| Table | Change | Notes |
|-------|--------|-------|
| | ADD column / ALTER nullability / DROP | |

### 2.3 Constraints & indexes

| Name | Definition | Why |
|------|------------|-----|
| | | |

### 2.4 Enums / types

| Type | Change |
|------|--------|
| | |

## 3. RLS

| Object | Policy change | Notes |
|--------|---------------|-------|
| | None / new / modified | |

## 4. Data migration / backfill

- [ ] None  
- [ ] Backfill: …  
- [ ] Dual-write period: …  

## 5. Rollback

How to reverse, or “forward-only” with reason.

## 6. Explicitly out of scope (this cycle)

List tables/columns **not** changing so reviewers do not hunt elsewhere.

## 7. Open schema blockers

Link to open-questions items that block migration.

## 8. Implementation checklist

- [ ] Migration(s) match this doc  
- [ ] Models match migration  
- [ ] RLS tested if changed  
- [ ] This file updated with revision id(s)  

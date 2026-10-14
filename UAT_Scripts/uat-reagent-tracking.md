# UAT: Reagent tracking (vendors, reagents, lots, uses)

**Stem:** `reagent-tracking`
**Bars:** RT-1..RT-10, Tobias provisional bars (2026-10-14). Promote to final when Tobias signs off.
**UI:** Admin → **Reagents** (`/admin/reagents`) · LIMS run detail → **Reagents used** panel
**API:** `/v1/vendors`, `/v1/reagents`, `/v1/reagent-vendors`, `/v1/reagent-lots`, `/v1/reagent-uses` (see `manuals/api-endpoints.md`)
**Actors:** `config-editor` (config:edit), `lab-tech` (experiment:manage), `client` (client user), `admin`
**Env:** local docker compose (`lims-*`), http://localhost:3000 + :8000
**Last run:** main `0a90f6f` (2026-10-14): RT-1..RT-6 and RT-8..RT-10 Pass. **RT-7 Fail (blocker):** at 12 parallel requests the API hung and `/health` timed out. Zero-quantity use was accepted (RT-6 finding). Both are fixed on branch `reagent-use-concurrency`; rerun RT-6 and RT-7 there.

Record per row: Pass / Fail / Incomplete, commit SHA, evidence path (API JSON, `pg_stat_activity` dump for RT-7).

---

## Setup

Run as `config-editor`: vendor **Thermo Fisher**, reagent **Qubit dsDNA HS Assay Kit** (unit mL, storage RT, stability after opening 30 days), reagent-vendor (catalog Q32851, reorder point 50, preferred). Create one LIMS run (`RUN`) for the uses.

Lots on that reagent (quantity 100 mL unless stated otherwise; use dates as of the run date T):

| Lot | Setup |
|-----|-------|
| L1-OPEN | label expiry T+60, opened T-13 → effective T+17; released |
| L2-LABELEXP | label expiry T-13 |
| L3-STABEXP | label expiry T+365, opened T-44 → effective T-14 |
| L4-REJ | qc_status rejected |
| L5-HOLD | qc_status pending, released false |
| L6-INACT | active false |
| L7-HOLD2 | released false |
| LC | 100 mL, released: used by RT-7 only |

---

## Bars

| ID | Bar | Steps | Expected |
|----|-----|-------|----------|
| RT-1 | Catalog create | Run the setup via the API and the Admin → Reagents UI | 201 for vendor, reagent, reagent-vendor, lot; lot quantity_remaining = quantity_received (100) |
| RT-2 | Effective expiry | GET L1, L2, L3 | `effective_expiration_date` = earlier of the label expiry and opened + stability; L1 not expired, L2 and L3 expired |
| RT-3 | QC status + released gate | L4 rejected; L5 pending + released false; PATCH L5 `{"qc_status":"released"}`; GET `/v1/reagent-lots?usable=true` | L5 becomes released true (QC release releases the lot unless the request says released false); the usable list holds only active, released, unexpired, non-rejected lots (L1, L5) |
| RT-4 | Use decrements, void restores | `lab-tech` POST use of 12.5 mL on L1; PATCH `{"active":false}`; PATCH `{"active":true}`; void again | 201 and L1 87.5; void → 100 exactly; un-void → 422; double void changes nothing; the use copies lot_number, effective expiry, unit |
| RT-5 | Refusals at use | POST use of 1 on L2, L3, L4, L6, L7 | Each 422 with a reason (expired / opened past stability / QC-rejected / inactive / not released); no quantity change |
| RT-6 | Bad quantities | On L1: use 100.01 (over-draw), unit `uL` (wrong unit), -5, **0**, 0.000 | All 422; L1 unchanged. *(0a90f6f: zero was accepted with 201, a finding, now fixed.)* |
| RT-7 | Concurrency (blocker) | On LC (100 mL): fire **12 and then 20** parallel POST uses of 30 mL as `lab-tech`. While they run, poll `GET /health` every 0.5 s. Then dump `pg_stat_activity` | All requests return within 15 s; exactly 3 × 201, the rest 422; LC remaining = 10, never < 0; sum of active uses + remaining = 100; `/health` answers every poll in < 1 s; no session `idle in transaction`; no restart needed. Repeat with 4 parallel (regression) |
| RT-8 | No hard delete | DELETE on each of the 5 resources; retire then reactivate a vendor | DELETE → 405 (or 404), rows remain; retire/reactivate via `active` → 200 |
| RT-9 | Privileges | `lab-tech` POST vendor / GET reagents; `client` GET reagents, lots, uses, POST use, POST vendor; `config-editor` POST use | lab-tech: vendor 403, read 200. client: reads return 0 rows, writes 403. config-editor use 403 (needs experiment:manage) |
| RT-10 | Audit | SQL: `created_by`/`modified_by` usernames on the RT-4 use, L1 and the vendor | use = lab-tech, lab-tech; lot and vendor = config-editor, config-editor; created_at/modified_at set. *(0a90f6f: Pass by SQL. The script's own query had a bug; use a join on users.id.)* |

---

## RT-7 helper

```bash
# 20 parallel uses of 30 on lot $LC; /health polled alongside
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code}\n" -m 15 -X POST localhost:8000/v1/reagent-uses \
    -H "Authorization: Bearer $LABTECH" -H 'Content-Type: application/json' \
    -d "{\"reagent_lot_id\":\"$LC\",\"lims_run_id\":\"$RUN\",\"quantity_used\":30}" &
done
for i in $(seq 1 20); do curl -s -m 1 -o /dev/null -w "health %{http_code} %{time_total}\n" localhost:8000/health; sleep 0.5; done
wait
docker exec lims-db psql -U postgres -d lims_db -c "select pid,state,wait_event_type,now()-xact_start age from pg_stat_activity where datname='lims_db'"
```

Automated cover: `backend/tests/test_reagent_use_concurrency.py` (16 parallel against Postgres, pool 5+10).

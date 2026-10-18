# UAT: Reagent tracking (vendors, reagents, lots, uses)

**Stem:** `reagent-tracking`
**Bars:** RT-1..RT-10, Tobias provisional bars (2026-10-14). Promote to final when Tobias signs off.
**UI:** Admin → **Reagents** (`/admin/reagents`) · LIMS run detail → **Reagents used** panel · Experiment template **Type → Reagent** · experiment entry lot picker
**API:** `/v1/vendors`, `/v1/reagents`, `/v1/reagent-vendors`, `/v1/reagent-lots`, `/v1/reagent-uses` (see `manuals/api-endpoints.md`)
**Actors:** `config-editor` (config:edit), `lab-tech` (experiment:manage), `client` (client user), `admin`
**Env:** local docker compose (`lims-*`), http://localhost:3000 + :8000
**Last run:** main `0a90f6f` (2026-10-14): RT-1..RT-6 and RT-8..RT-10 Pass. **RT-7 Fail (blocker):** at 12 parallel requests the API hung and `/health` timed out. Zero-quantity use was accepted (RT-6 finding). Both are fixed on branch `reagent-use-concurrency`; rerun RT-6 and RT-7 there.
**Run 67481e9** (2026-10-14): RT-1..RT-10 Pass (RT-1 API only); RT-7 clean at 4/12/20/30 parallel and with a 3 s / 8 s held lock.

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
| RT-10 | Audit | SQL: `created_by`/`modified_by` usernames on the RT-4 use, L1 and the vendor | use = lab-tech, lab-tech. Vendor = config-editor, config-editor. Lot: created_by = config-editor, **modified_by = lab-tech** (recording or voiding a use draws down the lot and stamps the lab tech as its last modifier; correct, not a fail). created_at/modified_at set. *(0a90f6f: Pass by SQL. The script's own query had a bug; use a join on users.id.)* |
| RT-11 | Template defaults | As `config-editor`, create two active catalog reagents (A the default, B not on the template) and one inactive reagent. Give A and B a released lot, and give the inactive reagent a released lot too. Also give A an expired or rejected lot. On **Experiment templates**, add a **Reagent** entry and select A as a default. Create an experiment from that template. Reload the experiment. As `lab-tech`, open A's lot picker (B is not listed yet). Before adding B, POST a use of B's lot with the experiment id, then POST the inactive reagent's lot with the experiment id, then POST B's lot with only a LIMS run id. **Add reagent** B (`POST /v1/experiments/{id}/reagents`). Reload. Add B again. Add the inactive reagent. Record a usable lot of A and of B on the experiment. POST A's expired lot and A's rejected lot. Save a Reagent entry with an empty default list. | The experiment entry reloads with `allowed_reagent_ids` = [A]. A's picker lists only A's usable lots. Before the add, B's experiment use and the inactive reagent's experiment use are each **422** `reagent_not_on_experiment` (the saved list is checked before the active flag) and both lot quantities are unchanged. B's LIMS-run-only use is **201**. Add B is **201** and a reload shows [A, B]. B's picker lists only B's usable lots. Adding B again is **200** and the list still has one B. The inactive add is **422** `reagent_inactive` and the list is unchanged. After the add, the experiment uses of A's usable lot (the template default) and of B's usable lot are **201**. The expired and rejected lots are **422**. An empty, unknown, or inactive default list on the template is **422** `reagent_entry_invalid`. |
| RT-12 | Snapshot and inactive reagent | Create an experiment from a template whose default is A. Give B a released lot. PATCH the template so its Reagent entry defaults to only B. GET the experiment's reagent entry. POST a use of B's lot with the experiment id. POST a use of A's lot with the experiment id. POST add of active B. Reload. Set A inactive while A's lot stays released and unexpired. POST a use of A's lot with the experiment id. POST the same lot with only a LIMS run id. | The template now lists B. Before the add, the experiment entry is still [A]. B's experiment use is **422** `reagent_not_on_experiment` and B's quantity is unchanged. A's use is **201** because the snapshotted default counts as on the list. After adding B, a reload shows [A, B]. The experiment use of inactive A and the LIMS-run use are each **422** `reagent_inactive` (A is on the list, so the active-flag check runs after the list check), and A's lot quantity is unchanged after both of those refusals. An inactive lot is still refused by the lot rules (RT-5). |
| RT-13 | Ad hoc experiment | Create an experiment with no template. Confirm it has no reagent entry. POST a use of an active reagent's released lot with that experiment id. POST the same lot with only a LIMS run id. As `lab-tech`, **Add reagent** for that active catalog reagent. Reload. Add that reagent again. Add an inactive reagent. Record the released lot from that reagent's picker. Then set the reagent inactive and POST the same lot on the experiment again. | Before the add, the experiment use is **422** `reagent_not_on_experiment`, the lot quantity is unchanged, and there is still no reagent entry. The LIMS-run-only use is **201**. The first add is **201** and creates the reagent entry. A reload shows that reagent and a lot picker with only its usable lots. The duplicate add is **200** and the entry still lists the reagent once. The inactive add is **422** `reagent_inactive` and the list is unchanged. The experiment use after the add is **201**. The inactive use is **422** `reagent_inactive` and the quantity stays at the value after that experiment use. |

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

# TODOS

## Hamilton-specific worklist format

**What:** Add Hamilton .csv worklist format output as an alternative to the generic CSV.

**Why:** Hamilton is the most common liquid handling robot at Series A biotech. Generic CSV works and maps to any robot, but scientists running Hamilton robots will want a native format that loads directly without a field-mapping step.

**Pros:** Reduces friction for the most common robot type at NimbleLIMS's target customer. Unlocks a demo talking point: "it generates a Hamilton worklist directly."

**Cons:** Hamilton format is validated against a specific robot model/firmware version. Needs a real Hamilton worklist to test against before shipping. Minor maintenance burden if Hamilton changes their format.

**Context:** Phase 2 of the NimbleLIMS flexible experiment engine adds robot worklist export as generic CSV (source_well, dest_well, volume). Hamilton format was deliberately deferred until the generic CSV path is validated with a real experiment end-to-end. See design doc: `~/.gstack/projects/garrytan-gstack/marcbreneiser-main-design-20260324-214055.md`.

**Depends on / blocked by:** Generic CSV worklist export (Phase 2) validated with a real experiment run.

---

## Paginate GET /experiment-runs/{id}/data

**What:** Add `limit`/`offset` parameters to `ExperimentDataRepository.list_for_run()` and expose them on the `GET /experiment-runs/{id}/data` route.

**Why:** Currently returns all rows unbounded. A 384-well plate with multiple imports could produce thousands of rows loaded into memory at once, causing latency spikes and OOM risk under concurrent load.

**Pros:** Protects against memory spikes; standard REST pagination pattern already used on `list_runs`.

**Cons:** Minor breaking change to API consumers (need to handle paginated response); adds a page/size response envelope.

**Priority:** P2

**Context:** Surfaced during `/plan-eng-review` on `flexible-experiment-engine` branch. The worklist export (`export_worklist_csv`) reads all rows intentionally — that's fine since it's generating a full CSV. Only the list-data API endpoint needs pagination. The fix is ~10 lines: add limit/offset to the query, add page/size/total to the response schema.

**Depends on / blocked by:** Nothing — independent change.

---

## Background task connection pool: release DB before API call

**What:** In `SOPParseService.run_extraction_background()`, release the SQLAlchemy connection before calling the Anthropic API, then re-acquire after to write the result.

**Why:** The background task opens a `SessionLocal()` and holds it open for 90–120s while waiting for Claude. Under concurrent SOP parse jobs, this exhausts the connection pool. The DB is not needed during the Claude API call — it's a pure wait.

**Pros:** Eliminates connection pool pressure from long-running background tasks; more correct resource management.

**Cons:** Requires restructuring the background task to use two DB sessions (one to mark processing, one to write result), or to use `db.close()` + `db.bind.connect()` pattern.

**Priority:** P3

**Context:** Surfaced during `/plan-eng-review` on `flexible-experiment-engine` branch. Acceptable at current scale (few concurrent parse jobs). Revisit when SOP parse jobs become a high-throughput operation.

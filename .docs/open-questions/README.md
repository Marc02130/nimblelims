# Open questions

Decision logs for workstreams that must not proceed until product/architecture questions are resolved.

**MVP Release Bar:** The MVP release focuses on three pillars (sample tracking, test ordering, results entry). Open questions that block **those three pillars** must be resolved before release. Open questions for shipped-adjacent features (ELN, LimsRuns/parsers, dose-response, workflow templates) are tracked here but **do not block MVP release**—they block future expansion of those enhancements.

| Doc | Area | Blocks MVP Release? |
|-----|------|---------------------|
| [experiments.md](experiments.md) | ELN Processes, Entries; Q11–Q16 substrate; **Q17–Q22 open (Lab Ops Hold on Phase 4)** | **No** — ELN is shipped/in-tree but not the MVP release bar |
| [containers.md](containers.md) | Nested containers; solute mass / derived volume; type **rows×columns**; contents only on 1×1 — **Decided** (schema implement pending) | **Partially** — Basic tube/plate tracking is MVP; advanced pooling/aliquot calculations do not block release |
| [run-results.md](run-results.md) | LimsRun → structured Results on publish | **No** — LimsRuns/parsers are shipped but not the MVP release path; manual results entry is the release bar |
| [data-parsers-lims-runs.md](data-parsers-lims-runs.md) | Parsers (analysis×instrument/CRO), run lineage, AI setup schema | **No** — Data parsers are shipped but not required for release; instrument integration is a post-release enhancement |
| [sop-sample-identity-audit.md](sop-sample-identity-audit.md) | Sample identity, dispositions, audit trail, review/amendment (Issues #22–#26) — **Q1–Q5 open** | **Partially** — Implementation can proceed with provisional answers; Q1 (UAT cutover) and Q5 (Deiter gate) do not block MVP implementation but must resolve before UAT/production use |
| [security-high-s1-s6.md](security-high-s1-s6.md) | High security remediation — **Q1–Q7 decided** (C ensure role; vendor seeds; must-change + complexity; …); implement P0b–P0d | **Yes for production** — S1–S6 block production claim until shipped |

## Gate rule

1. Track open questions in this folder (not only in checklists).
2. **Do not start** a new phase or major feature until questions that block that scope are **Decided**.
3. For **MVP release**: only questions that block the three pillars (sample tracking, test ordering, results entry) must be resolved. Questions for shipped-adjacent features (ELN, parsers, dose-response) do not block release but block expansion of those enhancements.
4. Provisional answers used to ship earlier slices must be labeled **Decided (provisional)** and revisited before expanding scope.
5. Agents and humans: see root `AGENTS.md` → *Open questions gate*.

## Docs layout

Project documentation is organized under [`.docs/README.md`](../README.md). Checklists track *tasks*; this folder owns *decisions*.

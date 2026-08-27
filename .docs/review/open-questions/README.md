# Open questions

Cycle/feature **gates** for workstreams that must not proceed until product/architecture questions are **Decided**. This folder is **not** the Leadership stamp tree.

**MVP Release Bar:** The MVP release focuses on three pillars (sample tracking, test ordering, results entry). Open questions that block **those three pillars** must be resolved before release. Open questions for shipped-adjacent features (ELN, LimsRuns/parsers, dose-response, workflow templates) are tracked here but **do not block MVP release**—they block future expansion of those enhancements.

| Doc | Area | Blocks MVP Release? |
|-----|------|---------------------|
| [experiments.md](experiments.md) | ELN Processes, Entries; Q11–Q16 substrate; **Q17–Q22 open (Lab Ops Hold on Phase 4)** | **No** — ELN is shipped/in-tree but not the MVP release bar |
| [containers.md](containers.md) | Nested containers; solute mass / derived volume; type **rows×columns**; contents only on 1×1 — **Decided** (schema implement pending) | **Partially** — Basic tube/plate tracking is MVP; advanced pooling/aliquot calculations do not block release |
| [run-results.md](run-results.md) | LimsRun → structured Results on publish | **No** — LimsRuns/parsers are shipped but not the MVP release path; manual results entry is the release bar |
| [data-parsers-lims-runs.md](data-parsers-lims-runs.md) | Parsers (analysis×instrument/CRO), run lineage, AI setup schema | **No** — Data parsers are shipped but not required for release; instrument integration is a post-release enhancement |
| [sop-sample-identity-audit.md](sop-sample-identity-audit.md) | Sample identity, dispositions, audit trail, review/amendment (Issues #22–#26) — **Q1–Q5 open** | **Partially** — Implementation can proceed with provisional answers; Q1 (UAT cutover) and Q5 (Deiter gate) do not block MVP implementation but must resolve before UAT/production use |
| [security-high-s1-s6.md](security-high-s1-s6.md) | High security remediation — **Q1–Q7 decided**; S1–S6 **Met** | No longer blocks (High Met) |
| [security-med-low-s7-s15.md](security-med-low-s7-s15.md) | Med/Low S7–S15 — OQ-S9/S11/S14/S15 open; P1–P4 plan | **Partially** — whole-product “production ready” still needs P1+P2+S12 at minimum |
| [extract-then-qubit-testdata-gap.md](extract-then-qubit-testdata-gap.md) | Extract-then-Qubit Hold — 0058/0059 catalog map (findings only; not an SOP pack) | **No** — Hold; testdata will not invent blood/DNA/Qubit IDs until Hold ships; Compose stays down |
| [blood-dnatruseq-testdata-gap.md](blood-dnatruseq-testdata-gap.md) | Blood→DNA→TruSeq Nano UAT path — 0058/0059 catalog map (findings only; not an SOP pack; capture parked) | **No** — Hold; testdata will not invent blood/DNA/TruSeq IDs until dest DNA lands; Compose stays down |

## Gate rule

1. Track open questions in this folder (not only in checklists).
2. **Do not start** a new phase or major feature until questions that block that scope are **Decided**.
3. For **MVP release**: only questions that block the three pillars (sample tracking, test ordering, results entry) must be resolved. Questions for shipped-adjacent features (ELN, parsers, dose-response) do not block release but block expansion of those enhancements.
4. Provisional answers used to ship earlier slices must be labeled **Decided (provisional)** and revisited before expanding scope.
5. Agents and humans: see root `AGENTS.md` → *Open questions gate*.

## Decision-logs vs open-questions

Two different trees. Do not merge them.

| Tree | Role |
|------|------|
| [`.docs/decision-logs/`](../../decision-logs/) | **Leadership stamps** — short decided locks (FW/WO, reorg, framework). Already decided. Committed. |
| [`.docs/review/open-questions/`](./) | **Cycle/feature gates** — open questions that block a packet/phase until **Decided**. Formal review process. Committed. |

**Rule:** a new Leadership lock (FW/WO/reorg) goes in `decision-logs/`. A packet that cannot start until questions are answered goes in `review/open-questions/`. When an OQ is Decided, leave it there as Decided (do not move it to decision-logs unless it is a cross-cutting Leadership stamp). When saying "fold into docs," name the tree: `review` / `internal` / `decision-logs` / `discussions`.

## Docs layout

Project documentation is organized under [`.docs/review/README.md`](../README.md) (parent index: [`.docs/README.md`](../../README.md)). Checklists track *tasks*; this folder owns *cycle/feature questions*. Leadership stamps live in [`.docs/decision-logs/`](../../decision-logs/).

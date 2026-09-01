# `.docs/internal/user-stories` — domain split

Layout mirrors `prd/` and `specs/` (three hard domains) plus platform + schema-modification.

```
user-stories/
  README.md
  sample-accessioning/USER-STORIES.md
  containers/USER-STORIES.md
  sample-processing/USER-STORIES.md
  platform/USER-STORIES.md          ← auth, lists/config, audit (not a hard domain)
  schema-modification/USER-STORIES.md
```

| Folder | Owns (US ids) |
|--------|----------------|
| sample-accessioning | US-1, US-2, US-23, US-24, US-30, US-31, US-32 |
| containers | US-5, US-21, US-38 |
| sample-processing | US-3, US-4, US-6, US-7, US-8, US-9, US-10, US-11, US-26, US-27, US-28, US-29, US-35, US-36, US-37 |
| platform | US-12, US-13, US-14, US-15, US-16, US-17, US-18, US-19, US-20, US-22, US-25, US-33, US-34, CUSTOM-FIELDS |
| schema-modification | FieldDefinition / column add-deprecate MVP |

The old flat `nimblelims-user.md` and `schema-modification.md` were split into these folders and removed.

**P0:** accessioning atomic receive — see `sample-accessioning/USER-STORIES.md` (US-1) and `.docs/internal/prd/sample-accessioning/ISSUES.md`.

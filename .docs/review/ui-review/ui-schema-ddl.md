# UI review: UI-driven schema DDL (admin UX sketch)

**Date:** 2026-09-22 (Marc layout locks folded 2026-09-23 via Rolf)  
**Status:** **Sketch Accept** (Mathilda @ `e12b0c2`). [Brief](../requirements/ui-schema-ddl-brief.md) 2026-09-22 Decides OQ-4–13. **Marc layout locks folded** (via Rolf 2026-09-23). **Design Group UX Accept pending** (this sketch is not that stamp). Implement gate **CLOSED**.  
**Stem:** `ui-schema-ddl`  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**Open questions:** [`.docs/review/open-questions/ui-schema-ddl.md`](../open-questions/ui-schema-ddl.md)  
**Persona:** lab admin with `schema:edit` / `layout:edit` **permissions** (not new roles) — scientist vocabulary, not DBA.  
**Not IC50. No product code.**

## 1. Verdict shape

**UI Accept (sketch)** for three admin concerns, four nav surfaces under **Admin → Schema**:

| Surface | Owns | Mutate perm |
|---------|------|-------------|
| **Tables** | Table registry + CREATE TABLE | `schema:edit` |
| **Columns** | Column registry + ADD COLUMN on allow-listed / UI-created tables | `schema:edit` |
| **Layouts** | Role × screen × **displayed columns** / sections (OQ-2) | `layout:edit` |
| **Privileges** | Role × table/column read vs write (OQ-3) | `schema:edit` |

Layout hide ≠ privilege deny. Schema edit ≠ layout edit. No SQL console as default. Mutate rights are **permissions**, not new roles named “schema-admin” / “layout-admin”.

## Marc layout locks (2026-09-23)

Folded via Rolf 2026-09-23. These lock the sketch until Design Group UX Accept:

1. **Permissions:** `schema:edit` and `layout:edit` (permissions, **not** new roles).
2. **List pages:** role layout drives **default** columns; on-the-fly add/remove of columns on a list is **ephemeral** (session only — **not** written to the layout registry).
3. **Layout = displayed columns only;** read/write comes from role privileges (OQ-3). Layout editor toggles visibility / order / sections only — not privileges.
4. **Runtime presentation:** multi-row screens → **table**; single-record screens → **form**.
5. **Labels:** **Vessel = Container** in UI copy; use **sample type**, not matrix (SOP hint chip is sample type; bounce “matrix” as the field label).

## 2. Principles

1. **Lab words first.** Labels: Table, Field, Type, Required, List source, Screen, Role, Show, Read, Write. **Vessel = Container** in UI copy. Use **sample type**, not matrix. Never lead with CREATE TABLE / ALTER / GRANT.
2. **Preview before apply.** Every CREATE/ADD shows: physical name (auto-slugged), type, nullability, impact list (forms/search that will gain the field), confirm CTA.
3. **Registries behind the glass.** Admin never edits `information_schema`. They edit registry rows; apply hits real Postgres + registry in one controlled op (Heidi OQ-4).
4. **Three layers stay separate.** Schema (exists) · Layout (**displayed columns** only) · Privileges (may read/write — OQ-3). Never one mega-grid that confuses hide with deny. Layout chrome must not blur into privileges.
5. **SOP field-name hints** (Katinka) live on the column row as an optional “SOP name” chip/select (barcode, vessel/container, parent, **sample type**) — for later AI mapping. No house SOP paste box. Bounce **matrix** as the field label (and as the SOP hint chip text).
6. **Bounce DBA chrome** as default: raw SQL, unrestricted type picker, DROP as primary action, Indexes/FKs UI (parked). **OQ-16:** never offer JSONB as the way to configure schema/layout/privileges; JSONB type for payload/instrument **data** fields is OK when Heidi locks types.

## 3. Tables (OQ-1)

**List:** configurable tables only (registry). Columns: display name, physical name (read-only after create), status (active/deprecated), column count, tenant scope (when locked).

**Add table:**
- Display name (required)
- Physical name: auto from display (editable only before apply; slug rules Heidi)
- Platform columns: shown as a fixed checklist (**Brief OQ-7**: `id`, `client_id`, created/modified at/by, `active`) — not free-add
- Confirm → toast with table name; stay on Columns for that table

**Bounce:** CREATE without platform columns; creating core system tables outside allow-list (OQ-6); JSONB “document table” option.

## 4. Columns (OQ-1)

**Entry:** pick table → list columns (order, display name, type, required, SOP hint, status).

**Add field:**
- Display name
- Type from **P1 allow-list only** (**Brief OQ-8**: Text, Number, Whole number, Yes/No, Date, Date and time, List)
- Required toggle
- List source (when type = List) → existing `lists` / `list_entries`
- SOP field-name hint (optional select: barcode, vessel/container, parent, **sample type** — not matrix)
- Sort order (drag later; number now)
- Preview: “Adds a real field on {Table}. Not a custom-attribute JSON key.”
- Apply → column-registry row + real ADD COLUMN

**Deprecate:** hide from new layouts by default; data retained; destructive remove is a separate confirm with impact (OQ-9).

**Bounce:** free-text PG type; writing only `custom_attributes`; burying layout/privilege toggles on this form (use Layouts / Privileges screens).

## 5. Layouts — centerpiece (OQ-2 / OQ-15)

**Mental model:** Schema says what exists. Layout says which **columns this role displays** on this **screen**. Layout does **not** grant or revoke read/write — that is OQ-3 privileges.

### OQ-15 decisions (UI lock for sketch)

| Item | Decision |
|------|----------|
| Screen identity | Stable keys for known product screens first (e.g. `receive`, `asked-for`, `samples.detail`, `samples.list`). Free-text screen IDs wait. |
| Grain | **Section** (optional group) → **fields** (column-registry refs) ordered. Layout = **displayed columns only**. |
| Default when no layout row | Show all columns the role may **read** (privilege), in column-registry order. Never show write-denied as editable (privilege, not layout chrome). |
| List pages | Role layout drives **default** columns. On-the-fly add/remove of columns on a list is **ephemeral** (session only — **not** written to the layout registry). |
| Presentation | Multi-row screens → **table**. Single-record screens → **form**. |
| Bench vs review | Separate layout rows for Lab tech vs Review/Manager (Katinka) — do not overload one role layout. |
| Gloved use | Large targets on Apply/Confirm; Layout editor itself is desk/admin (mouse OK). Runtime screens that consume layout stay barcode/glove-friendly. |

**Editor UX:**
1. Pick Role + Screen
2. Left: available fields (privilege-filtered: only columns this role can read)
3. Right: visible stack (drag order); optional section headers
4. Per field: **Visible** (and order / section). Layout editor does **not** offer “Read-only display” or other privilege chrome — read vs write is Privileges (OQ-3) only.
5. Save layout — **no DDL**. Requires `layout:edit`. Session-only list column add/remove is **not** a Save-to-registry action.

**Empty state:** “No layout for this role/screen — using default (all readable fields).” CTA: Create layout.

**Bounce:** editing layout that silently ADD COLUMNs; layout as the only access control; per-user layouts (role only in P1); treating layout as read/write; persisting on-the-fly list column picks into the layout registry.

## 6. Privileges (OQ-3)

**Separate screen** from Layouts.

**Grid:** Role × Table: Read / Write / none. Drill-in: Role × Column overrides (Read / Write / inherit table).

**Rules (UX copy):**
- `schema:edit` is a **permission** (not a new role) for Tables/Columns Apply and privilege-registry mutate — not granted by Write on Samples.
- `layout:edit` is a **permission** (not a new role) for layout-registry mutate — not DDL and not privilege minting.
- Privilege refuse surfaces as **403/422** with lab-readable text (“You can’t change this field”), never a silent no-op and never “empty because hidden.”
- Layout-hidden + Write granted: field not shown; do not invent a back door in the layout editor.

**Bounce:** merging privilege toggles into the layout drag list; treating hide as deny; “Read-only display” as a layout control.

## 7. Runtime consumption (non-admin)

Receive, Asked-for, Samples, etc. load: column registry ∩ layout(role, screen) ∩ privileges(role).

- Missing layout → default (§5)
- No read privilege → omit field (and API refuse if forced)
- Read yes / Write no → field may display; control is **read-only because of privilege**, not because layout said “read-only”
- Multi-row screens render as a **table**; single-record screens render as a **form**
- List: start from role-layout **default** columns; user add/remove of columns on that list is **ephemeral** (session only)
- SOP hint is metadata for AI later — not shown to bench unless a later packet asks

## 8. Error / confirm copy (lab-readable)

| Event | Copy |
|-------|------|
| Apply ADD COLUMN | “Add field {name} to {table}? This creates a real database field.” |
| Privilege refuse write | “You don’t have permission to change {field}.” |
| Not allow-listed table | “This table can’t get new fields from the UI.” |
| Duplicate physical name | “A field with that database name already exists.” |
| JSONB-only path attempted | Never offer it. |

## 9. Bounce bars (UI)

- DBA SQL console as default path
- JSONB / `custom_attributes` as “add field” or any **config** store (**OQ-16** — JSONB OK only for instrument/payload **data**)
- Layout hide as sole access control
- Privileges buried on column row only
- Layout editor “Read-only display” (privileges own read/write)
- Persisting ephemeral list-column picks into the layout registry
- **Matrix** as a field label (use **sample type**); do not treat Vessel and Container as different UI labels
- Indexes / FKs UI this packet
- AI apply DDL / AI login-reporting-storage
- Per-user layouts
- Dropping data-bearing fields without impact confirm
- New roles named schema-admin / layout-admin (use `schema:edit` / `layout:edit` permissions)

## 10. Brief lock (do not invent in UX)

OQ-4–13 are **Decided** in the [Brief](../requirements/ui-schema-ddl-brief.md) (Hybrid apply, shared+FORCE RLS, allow-list, platform columns, P1 types, deprecate-first, privilege registry, `ui_schema` head, leave Entries, `custom_attributes` follow-on). Sketch chrome must follow those locks **and** the Marc layout locks (§ above). Remaining gate: **Design Group UX Accept** on Tables / Columns / Layouts / Privileges — this sketch is not that stamp.

## 11. Sign-off

| Review | Verdict |
|--------|---------|
| UI (Mathilda) | **Sketch Accept** — Tables / Columns / Layouts / Privileges; OQ-15 locked as above; Marc layout locks folded 2026-09-23 |
| Architecture (Heidi) | **Accept with conditions** (OQ-4–13 now Decided in Brief) — 2026-09-22 |
| Security (Günter) | **Accept with conditions** (S-UI-1…6) — restamp pending under Brief |
| Lab Ops (Deiter) | **Accept with conditions** — Brief written |
| Design Group | **UX Accept pending** (Mathilda Sketch Accept is not this stamp) |

**Implement gate:** **CLOSED** until Design Group UX Accept + Günter restamp.

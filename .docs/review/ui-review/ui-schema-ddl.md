# UI review: UI-driven schema DDL (admin UX sketch)

**Date:** 2026-09-22  
**Status:** **Sketch Accept** (Mathilda @ `e12b0c2`). [Brief](../requirements/ui-schema-ddl-brief.md) 2026-09-22 Decides OQ-4–13. **Design Group UX Accept pending** (this sketch is not that stamp). Implement gate **CLOSED**.  
**Stem:** `ui-schema-ddl`  
**Requirements:** [`.docs/review/requirements/ui-schema-ddl.md`](../requirements/ui-schema-ddl.md)  
**Open questions:** [`.docs/review/open-questions/ui-schema-ddl.md`](../open-questions/ui-schema-ddl.md)  
**Persona:** lab admin / `schema:edit` — scientist vocabulary, not DBA. **Günter follow-on:** Admin role defaults to `schema:edit` + privilege admin (small-startup) — **Admin only** (not lab manager / lab-tech / client); **Marc Confirm closed**; optional re-assign later; optional separate role later.  
**Not IC50. No product code.**

## 1. Verdict shape

**UI Accept (sketch)** for three admin concerns, four nav surfaces under **Admin → Schema**:

| Surface | Owns | Mutate perm |
|---------|------|-------------|
| **Tables** | Table registry + CREATE TABLE | `schema:edit` |
| **Columns** | Column registry + ADD COLUMN on allow-listed / UI-created tables | `schema:edit` |
| **Layouts** | Role × screen × visible fields/sections (OQ-2) | `schema:edit` or `layout:edit` (Heidi/Günter) |
| **Privileges** | Role × table/column read vs write (OQ-3) | `schema:edit` |

Not on layout ≠ privilege deny. Schema edit ≠ layout edit. No SQL console as default. **No layout hide toggle.**

## 2. Principles

1. **Lab words first.** Labels: Table, Field, Type, Required, List source, Screen, Role, Show, Read, Write. Never lead with CREATE TABLE / ALTER / GRANT.
2. **Preview before apply.** Every CREATE/ADD shows: physical name (auto-slugged), type, nullability, impact list (forms/search that will gain the field), confirm CTA.
3. **Registries behind the glass.** Admin never edits `information_schema`. They edit registry rows; apply hits real Postgres + registry in one controlled op (Heidi OQ-4).
4. **Three layers stay separate.** Schema (exists) · Layout (sees) · Privileges (may). Never one mega-grid that confuses layout membership with deny.
5. **SOP field-name hints** (Katinka) live on the column row as an optional “SOP name” chip/select (barcode, container (vessel), parent, sample type) — for later AI mapping. No house SOP paste box.
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
- SOP field-name hint (optional select)
- Sort order (drag later; number now)
- Preview: “Adds a real field on {Table}. Not a custom-attribute JSON key.”
- Apply → column-registry row + real ADD COLUMN

**Deprecate:** hide from new layouts by default; data retained; destructive remove is a separate confirm with impact (OQ-9).

**Bounce:** free-text PG type; writing only `custom_attributes`; burying layout/privilege toggles on this form (use Layouts / Privileges screens).

## 5. Layouts — centerpiece (OQ-2 / OQ-15)

**Mental model:** Schema says what exists. Layout says what this **role** sees on this **screen**.

### OQ-15 decisions (UI lock for sketch)

| Item | Decision |
|------|----------|
| Screen identity | Stable keys for known product screens first (e.g. `receive`, `asked-for`, `samples.detail`, `samples.list`). Free-text screen IDs wait. |
| Grain | **Section** (optional group) → **fields** (column-registry refs) ordered. |
| Default when no layout row | Show all columns the role may **read** (privilege), in column-registry order. Never show write-denied as editable. |
| Bench vs review | Separate layout rows for Lab tech vs Review/Manager (Katinka) — do not overload one role layout. |
| Gloved use | Large targets on Apply/Confirm; Layout editor itself is desk/admin (mouse OK). Runtime screens that consume layout stay barcode/glove-friendly. |

**Editor UX:**
1. Pick Role + Screen
2. Left: available fields (privilege-filtered: only columns this role can read)
3. Right: visible stack (drag order); optional section headers
4. Per field: **on layout or not** (membership only — **no hide / Visible toggle**). Read-only comes from privileges (Read yes / Write no), not layout hide. API write still OQ-3.
5. Save layout — **no DDL**

**Empty state:** “No layout for this role/screen — using default (all readable fields).” CTA: Create layout.

**Bounce:** editing layout that silently ADD COLUMNs; layout as the only access control; per-user layouts (role only in P1).

## 6. Privileges (OQ-3)

**Separate screen** from Layouts.

**Grid:** Role × Table: Read / Write / none. Drill-in: Role × Column overrides (Read / Write / inherit table).

**Rules (UX copy):**
- Schema-admin is a separate capability for Tables/Columns Apply — not granted by Write on Samples.
- Privilege refuse surfaces as **403/422** with lab-readable text (“You can’t change this field”), never a silent no-op and never “empty because hidden.”
- Layout-hidden + Write granted: field not shown; do not invent a back door in the layout editor.

**Bounce:** merging privilege toggles into the layout drag list; treating “not on layout” as deny; any Visible/hide toggle that keeps a field on the layout as hidden.

## 7. Runtime consumption (non-admin)

Receive, Asked-for, Samples, etc. load: column registry ∩ layout(role, screen) ∩ privileges(role).

- Missing layout → default (§5)
- No read privilege → omit field (and API refuse if forced)
- Read yes / Write no → visible read-only
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
- Layout hide / Visible-as-hidden toggle (visibility = membership only)
- Layout hide as sole access control
- Privileges buried on column row only
- Indexes / FKs UI this packet
- AI apply DDL / AI login-reporting-storage
- Per-user layouts
- Dropping data-bearing fields without impact confirm

## 10. Brief lock (do not invent in UX)

OQ-4–13 are **Decided** in the [Brief](../requirements/ui-schema-ddl-brief.md) (Hybrid apply, shared+FORCE RLS, allow-list, platform columns, P1 types, deprecate-first, privilege registry, `ui_schema` head, leave Entries, `custom_attributes` follow-on). Sketch chrome must follow those locks. Remaining gate: **Design Group UX Accept** on Tables / Columns / Layouts / Privileges — this sketch is not that stamp.

## 11. Sign-off

| Review | Verdict |
|--------|---------|
| UI (Mathilda) | **Sketch Accept** — Tables / Columns / Layouts / Privileges; OQ-15 locked as above |
| Architecture (Heidi) | **Accept with conditions** (OQ-4–13 now Decided in Brief) — 2026-09-22 |
| Security (Günter) | **Accept with conditions** (S-UI-1…6) — restamp pending under Brief |
| Lab Ops (Deiter) | **Accept with conditions** — Brief written |
| Design Group | **UX Accept pending** (Mathilda Sketch Accept is not this stamp) |

**Implement gate:** **CLOSED** until Design Group UX Accept + Günter restamp.

**Fold note 2026-09-23 (Marc Leadership overwrite; Rolf Confirm):** mutate Schema with permission `schema:edit` (not a new role); Layouts with `layout:edit` (no DDL). List ephemeral columns; layout = display; privileges = R/W; multi-row table / single-record form; receive/asked-for = select then enter.

**Fold note 2026-09-23 (Confirms; Rolf):** Günter + Hans + Deiter Confirmed Marc overwrite. Deiter Confirm retracts three-mode Hide/Read-only/Deny copy — layout = display; privileges = R/W. Implement CLOSED.

**Marc Confirm (2026-09-23; Rolf):** Default **`schema:edit`** + privilege admin = **Admin only** (not lab manager). **Closed.** Optional re-assign later. Implement CLOSED.

## Marc Leadership overwrite — layout visibility (2026-09-23; Rolf Confirm)

**No “hidden” on layout.** Visibility = **membership** on the layout only. Do **not** add a hide / Visible toggle that keeps the field on the layout as hidden.

| Case | Rule |
|------|------|
| **Show** | Field is on the role × screen layout. |
| **Not shown** | Field is **not added** to the layout (absent = not shown — Deiter stands). |
| Neither read nor write | Not displayed; layout editor **must not offer** that field. |
| Read yes / Write no | May appear on layout as **read-only** — from **privileges**, not a layout hide. |

Retract any remaining copy that implies a hide mode or three-mode Hide / Read-only / Deny. Implement still **CLOSED** pending Design Group UX Accept (Günter Brief restamp **Met**).


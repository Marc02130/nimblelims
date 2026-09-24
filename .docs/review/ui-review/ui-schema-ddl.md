# UI review: UI-driven schema DDL (admin UX sketch)

**Date:** 2026-09-22  
**Status:** **Sketch Accept** (Mathilda @ `e12b0c2`; **re-stamped** on Spec tip `f79e2a0` 2026-09-23). [Brief](../requirements/ui-schema-ddl-brief.md) 2026-09-22 Decides OQ-4–13. **Design Group UX Accept Met** on tip `f79e2a0` (Heidi/Hans/Deiter). Günter Brief restamp **Met**. Implement gate **OPEN**. Tobias **re-UAT Pass** on `b6d1920`. Rolf Confirm **Met**. Merge = Marc’s call.  
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
| **Layouts** | Role × screen × **membership** (OQ-2) | `schema:edit` or `layout:edit` (Heidi/Günter) |
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

**Deprecate:** omit from new layouts by default; data retained; destructive remove is a separate confirm with impact (OQ-9).

**Bounce:** free-text PG type; writing only `custom_attributes`; burying layout/privilege toggles on this form (use Layouts / Privileges screens).

## 5. Layouts — centerpiece (OQ-2 / OQ-15)

**Mental model:** Schema says what exists. Layout says what this **role** sees on this **screen**. Visibility = **membership** only (**no hide / Visible toggle**).

### OQ-15 decisions (UI lock for sketch)

| Item | Decision |
|------|----------|
| Screen identity | Stable keys for known product screens first (e.g. `receive`, `samples.detail`, `samples.list`). Free-text screen IDs wait. **Asked-for and routing leave as is** — not OQ-2 layout/schema-config surfaces this packet (**Marc overwrite**). |
| Grain | **Section** (optional group) → **fields** (column-registry refs) ordered. |
| Default when no layout row | Show all columns the role may **read** (privilege), in column-registry order. Never show write-denied as editable. |
| Bench vs review | Separate layout rows for Lab tech vs Review/Manager (Katinka) — do not overload one role layout. |
| Gloved use | Large targets on Apply/Confirm; Layout editor itself is desk/admin (mouse OK). Runtime screens that consume layout stay barcode/glove-friendly. |
| **List pages** | Show **role layout** columns. On-the-fly add/remove columns is **ephemeral** (session only — **not** stored in the layout registry). |
| **Receive (Lab Ops note)** | Select samples, then enter (simple) where receive already applies. **Asked-for / routing:** leave as is — not redesigned for layouts this packet. |

**Editor UX:**
1. Pick Role + Screen
2. Left: available fields (privilege-filtered: only columns this role can read — neither read nor write → **do not offer**)
3. Right: on-layout stack (drag order); optional section headers — **membership only**
4. Per field: **on layout or not**. Read-only comes from privileges (Read yes / Write no), not layout hide. API write still OQ-3.
5. Save layout — **no DDL**

**Empty state:** “No layout for this role/screen — using default (all readable fields).” CTA: Create layout.

**Bounce:** editing layout that silently ADD COLUMNs; layout as the only access control; per-user layouts (role only in P1); hide/Visible toggle that keeps a field on the layout as hidden.

## 6. Privileges (OQ-3)

**Separate screen** from Layouts.

**Grid:** Role × Table: Read / Write / none. Drill-in: Role × Column overrides (Read / Write / inherit table).

**Rules (UX copy):**
- Permission **`schema:edit`** (Admin-only default) is a separate capability for Tables/Columns Apply — **not** granted by Write on Samples. Not a new role.
- Privilege refuse surfaces as **403/422** with lab-readable text (“You can’t change this field”), never a silent no-op and never “empty because not on layout.”
- Field **not on layout** + Write granted: field not shown; do not invent a back door in the layout editor.

**Bounce:** merging privilege toggles into the layout drag list; treating “not on layout” as deny; any Visible/hide toggle that keeps a field on the layout as hidden.

## 7. Runtime consumption (non-admin)

Receive and Samples (and other layout-consuming screens) load: column registry ∩ layout(role, screen) ∩ privileges(role). **Asked-for and routing leave as is** — not layout consumers this packet.

- Missing layout → default (§5)
- No read privilege → omit field (and API refuse if forced); layout editor must not offer that field
- Read yes / Write no → visible read-only (from privileges)
- Field not on layout → not shown (membership only)
- **Receive:** select samples, then enter (simple) where it already applies — Lab Ops runtime note only
- **Asked-for / routing:** **leave as is** — not layout or schema-config surfaces this packet (**Marc overwrite**)
- **List pages:** role layout columns; on-the-fly add/remove is **ephemeral** (not stored)
- **Multi-row** screens → **table** with role data-type layout; **single record** → **form**
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
- Not on layout as sole access control
- Privileges buried on column row only
- Indexes / FKs UI this packet
- AI apply DDL / AI login-reporting-storage
- Per-user layouts
- Asked-for or routing as OQ-2 layout / schema-config surfaces this packet
- Inventing a Schema-admin role (use permission `schema:edit` on Admin only)
- Dropping data-bearing fields without impact confirm

## 10. Brief lock (do not invent in UX)

OQ-4–13 are **Decided** in the [Brief](../requirements/ui-schema-ddl-brief.md) (Hybrid apply, shared+FORCE RLS, allow-list, platform columns, P1 types, deprecate-first, privilege registry, `ui_schema` head, leave Entries, `custom_attributes` follow-on). Sketch chrome must follow those locks. Design Group UX Accept **Met** @ `f79e2a0`. Günter Brief restamp **Met**. Implement **OPEN**. Tobias **re-UAT Pass** on `b6d1920`.

## 11. Sign-off

| Review | Verdict |
|--------|---------|
| UI (Mathilda) | **Sketch Accept** — Tables / Columns / Layouts / Privileges; OQ-15 locked; **re-stamped** @ `f79e2a0` |
| Architecture (Heidi) | **Accept with conditions** (OQ-4–13 now Decided in Brief) — 2026-09-22; punches 1 and 4 **Met** (Design Group 2026-09-23) |
| Security (Günter) | **Accept with conditions** (S-UI-1…6) — Brief restamp **Met** |
| Lab Ops (Deiter) | **Accept with conditions** — Brief written; punches 1 and 4 **Met** |
| Science (Hans) | **Accept with conditions** — punches 1 and 4 **Met** |
| Design Group | **UX Accept Met** on tip `f79e2a0` (Heidi / Hans / Deiter) |
| QA (Tobias) | **re-UAT Pass** on `b6d1920` (0081). Rolf Confirm **Met**. Merge = Marc’s call. |

**Implement gate:** **OPEN**. Design UX Accept **Met**. Günter Brief restamp **Met**. Tobias **re-UAT Pass** on `b6d1920`. Rolf Confirm **Met**. Merge = Marc’s call.

**Fold note 2026-09-23 (Marc Leadership overwrite; Rolf Confirm):** mutate Schema with permission `schema:edit` (not a new role); Layouts with `layout:edit` (no DDL). List ephemeral columns; layout = membership; privileges = R/W; multi-row table / single-record form; receive/asked-for = select then enter.

**Fold note 2026-09-23 (Confirms; Rolf):** Günter + Hans + Deiter Confirmed Marc overwrite. Deiter Confirm retracts three-mode Hide/Read-only/Deny copy. Implement CLOSED (at the time; now OPEN).

**Marc Confirm (2026-09-23; Rolf):** Default **`schema:edit`** + privilege admin = **Admin only** (not lab manager). **Closed.** Optional re-assign later. Implement CLOSED (at the time; now OPEN).

**Design Group punch fold 2026-09-23 (Rolf):** (1) §6 uses permission `schema:edit` (Admin-only default) — not a separate schema-admin role label. (2) §5 / §7 body: list ephemeral columns; receive/asked-for select-then-enter; multi-row table / single form. (3) §6 says “not on layout” (never “layout-hidden”). Heidi/Hans/Deiter: punches 1 and 4 already Met. Awaiting Design Group re-stamp (at the time; now OPEN).

## Marc Leadership overwrite — layout visibility (2026-09-23; Rolf Confirm)

**No “hidden” on layout.** Visibility = **membership** on the layout only. Do **not** add a hide / Visible toggle that keeps the field on the layout as hidden.

| Case | Rule |
|------|------|
| **Show** | Field is on the role × screen layout. |
| **Not shown** | Field is **not added** to the layout (absent = not shown — Deiter stands). |
| Neither read nor write | Not displayed; layout editor **must not offer** that field. |
| Read yes / Write no | May appear on layout as **read-only** — from **privileges**, not a layout hide. |

Retract any remaining copy that implies a hide mode or three-mode Hide / Read-only / Deny. Implement still **CLOSED** pending Design Group UX Accept (Günter Brief restamp **Met**) (at the time; now OPEN).

## Marc Leadership overwrite — no Schema-admin role; asked-for/routing leave as is (2026-09-23; Rolf Confirm)

1. **No Schema-admin role.** Copy must say permission **`schema:edit`** on **Admin only** (small-startup; no large IT). Never invent a Schema-admin role. (Design punch 2 / Marc.)
2. **Asked-for and routing leave as is** — not designed for configuration. Do **not** make asked-for or routing layout/schema-config surfaces this packet. Deiter “select then enter” for **receive** may stay as a Lab Ops runtime note where it already applies; do **not** redesign asked-for/routing for OQ-2 layouts.
3. Still required: ephemeral list columns; multi-row = table / single = form; “not on layout” (never layout-hidden); `schema:edit` Admin-only.

Implement **CLOSED** (at the time; now OPEN). Design Group re-stamps after tip (at the time; now OPEN).
**UI Sketch Accept re-stamp (Mathilda; 2026-09-23):** Verified on tip `f79e2a0` — `schema:edit` Admin-only (no Schema-admin role); asked-for/routing leave as is; ephemeral list cols; multi-row table / single form; not on layout (membership only). Design Group UX Accept still pending on that tip (at the time; now OPEN). Implement CLOSED (at the time; now OPEN).

## Implement gate OPEN (2026-09-23; Rolf)

| Gate | Status |
|------|--------|
| Design Group UX Accept | **Met** on tip `f79e2a0` (Heidi / Hans / Deiter) |
| Günter Brief restamp | **Met** |
| Implement gate | **OPEN** |
| Tobias re-UAT | **Pass** on `b6d1920` (0081) |

Tobias **re-UAT Pass** on `b6d1920`. Rolf Confirm **Met**. Merge = Marc’s call — no merge until Marc says.


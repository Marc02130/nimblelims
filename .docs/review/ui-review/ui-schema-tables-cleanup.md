# UI review: Schema Tables cleanup + kill Custom Fields (admin UX sketch)

**Current truth (after the table-browser PR):** This sketch is history (pending Accept). Shipped behavior: Custom Fields chrome is gone; Schema is a table browser; system columns are locked; side links are 1:N / 1:1 real FKs in `schema_relations`; many-to-many is deferred; there is no universal join table. **Lists and list items are not schema tables.** `projects` stays on the Lab list. Do not read the sketch’s “Tables = Samples + Project + UI-created” or its M:N rows as the current display list.

**Date:** 2026-10-01  
**Status:** **Sketch pending Accept** (draft). Written against Spec/OQ tip `07ccd59` on `docs/ui-schema-tables-cleanup`. Not Accept.  
**Stem:** `ui-schema-tables-cleanup`  
**Requirements:** [`.docs/review/requirements/ui-schema-tables-cleanup.md`](../requirements/ui-schema-tables-cleanup.md)  
**Open questions:** [`.docs/review/open-questions/ui-schema-tables-cleanup.md`](../open-questions/ui-schema-tables-cleanup.md)  
**Prior sketch (standing):** [`.docs/review/ui-review/ui-schema-ddl.md`](ui-schema-ddl.md) — CREATE TABLE / ADD COLUMN / layout membership / privileges. Do not reopen.  
**Persona:** lab admin with **`schema:edit`** for Schema Tables and relation definition; lab tech / lab manager for Related lists (link / unlink only). Scientist vocabulary, not DBA.  
**Not IC50. No product code.**

## 1. Verdict shape

**UI sketch (pending Accept)** for three follow-on concerns. Schema chrome from `ui-schema-ddl` stays: **Tables**, **Columns**, **Layouts**, **Privileges**. This packet adds a **Relations** tab and removes Custom Fields.

| Surface | Owns | Who |
|---------|------|-----|
| **Tables** | Allow-listed real tables: **Samples**, **Project**, UI-created tables, plus link-table metadata | `schema:edit` (link rows: `schema:edit` only) |
| **Columns / Layouts / Privileges** | Unchanged from `ui-schema-ddl` once a table is on the list | `schema:edit` / `layout:edit` as already locked |
| **Relations** | Admin defines 1:N, 1:1, M:N | `schema:edit` |
| **Related list** | Operator link / unlink on a record | Write on that record (existing privileges) |
| **Custom Fields** | Nothing. Nav, page, deep link, and create/edit are gone | — |

Standing, not redesigned here: Hybrid apply, platform columns, P1 scalar types, layout = membership (no hide toggle), privileges ≠ layout, `schema:edit` on **Admin only**, no SQL console, JSONB-as-config forbidden (JSONB payload/instrument **data** still allowed). Asked-for and routing stay as they are.

## 2. Principles

1. **Real fields, or no field.** A new fact about a sample or a project is a real column (Schema → Columns) or a real link (Schema → Relations). Never a Custom Field, never a JSON key.
2. **Lab words first.** Table, Field, Project, Samples, Link, Unlink, Related. Never lead with FK, junction, JSONB, EAV, or `custom_attributes`.
3. **Allow-list is the list.** Schema → Tables shows Samples, Project, and tables an admin already created. Do not fill the grid with every Postgres table. **OQ-1 is open** — do not add containers, tests, clients, or any other system table until Marc names them.
4. **Links are records, not spreadsheets.** 1:N is a link on the many side. 1:1 is one link on the dependent, unique. M:N is a link table the product keeps **behind the scenes**. Operators link and unlink. They never open the link table.
5. **Three layers stay separate.** Schema (exists) · Layout (sees) · Privileges (may). A relation definition is schema. A Related list on a screen is layout membership of that relation’s display, not a new privilege model.
6. **Prior packet stays shut.** Do not reopen CREATE / ADD / layout / privilege locks to “fit” Custom Fields or relations.

## 3. Custom Fields chrome removal map (OQ-4)

Searched React under `frontend/src` for **Custom Fields**, **custom_attributes**, and **custom attribute** (2026-10-01, tip `07ccd59`). `/receive` (`AtomicReceive.tsx`) has **no** Custom Fields label and no `custom_attributes` use. Do not add one.

Admin create/edit lives on one route. Runtime forms repeat the same “Custom Attributes” block. Remove the route **and** every block. Renaming the page to “Field Management” is not removal — that heading is already on the page next to **Create Custom Field**.

| # | Screen | Route | What is on screen today | Sketch |
|---|--------|-------|-------------------------|--------|
| 1 | Admin nav item **Custom Fields** | Sidebar via `MainNav` `adminNavItems` → `/admin/custom-fields` | Nav label “Custom Fields” | **Remove** the item. Schema stays. |
| 2 | Custom Fields page | `/admin/custom-fields` (`App.tsx` → `CustomFieldsManagement.tsx`, `config:edit`) | Title **Field Management**, caption **(EAV)**, **Create Custom Field**, search, entity-type filter, row edit/delete. Entity types offered: samples, tests, results, projects, client_projects, batches, units, clients, experiments, analyses, containers | **Remove** the page and `CustomFieldDialog` (**Create New Custom Field** / **Edit Custom Field** / **Edit Built-in (OOB) Field**). OOB edits do not survive here. Built-in fields are Schema → Columns. |
| 3 | Deep link + window title | `/admin/custom-fields`; `MainLayout` title “Custom Fields Management” | Bookmark opens the editor | **Redirect** to `/admin/schema/tables`. No dialog, no query that opens create/edit. Copy on arrival: “Custom Fields are removed. Add a real field under Schema → Columns.” |
| 4 | Help tip | `/help` when the viewer is an admin and the help section is **EAV Configuration** (`AdminHelpSection.tsx`) | “Use Field Management (Custom Fields)… Custom Fields Management page… EAV attributes.” | **Remove** that tip. If the section remains, point at Schema → Columns. Do not teach EAV. |
| 5 | Sample form | `/samples`, `/samples/:id` (`SampleForm.tsx`) | Heading **Custom Attributes**; loads configs `entity_type: samples`; writes `custom_attributes` | **Remove** the section and the widget. |
| 6 | Test form | `/tests`, `/tests/:id` (`TestForm.tsx`) | Same heading; `entity_type: tests` | **Remove** the section. |
| 7 | Project form | `/projects` (`ProjectForm.tsx`) | Same heading; `entity_type: projects` | **Remove** the section. |
| 8 | Client project form | `/client-projects` (`ClientProjectForm.tsx`) | Same heading; `entity_type: client_projects` | **Remove** the section. |
| 9 | Batch form | `/batches` (`BatchForm.tsx`) | Same heading; `entity_type: batches` | **Remove** the section. |
| 10 | Analyses form | `/analyses` (`AnalysesManagement.tsx`) | Same heading; `entity_type: analyses` | **Remove** the section. Admin `/admin/analyses` has no such block. |
| 11 | Analytes form | `/analytes` (`AnalytesManagement.tsx`) | Same heading; `entity_type: analytes` | **Remove** the section. Admin `/admin/analytes` has no such block. |
| 12 | Results entry | `/results` (`ResultsEntryTable.tsx`, opened from batch results) | Extra columns from custom-attribute configs (`entity_type: tests`), values from `test.custom_attributes`. No “Custom Attributes” heading — the columns are the chrome | **Remove** those columns. Analyte result entry stays. |
| 13 | Experiment detail | `/experiments/:id` (selected experiment on `/experiments` too) | Row **Custom attributes** plus a JSON dump | **Remove** the row. Do not show the JSON blob. |
| 14 | Samples list deep link | `/samples` (`SamplesManagement.tsx`) | No filter control labeled custom. The list **does** pass `custom.*` query params through for JSONB filtering | **Drop** `custom.*` passthrough so a link cannot filter on JSON keys. |
| 15 | Shared widget + client call | `CustomAttributeField.tsx`; `apiService.getCustomAttributeConfigs` → `GET /admin/custom-attributes` | Renderer and loader for rows 5–12 | **Stop rendering and stop calling** from these screens. API refuse (403/422) is Spec AC2, not a second UI. |

**Rename, do not delete the editor:** `/experiments/templates` (`ExperimentTemplatesManagement.tsx`) says “Not Custom Fields on Sample/Test” and “not a Custom Field on Sample/Test database tables.” Those entry columns are template fields, not Custom Fields. **Rename** the disclaimer so it does not name the killed page. Leave entry-column authoring alone.

**Not found:** a Custom Fields item on Admin Dashboard (`/admin` cards), a second sidebar list, or a receive label. `ProjectsManagement.tsx` carries `custom_attributes` on its types; the visible block is the project form (row 7).

Cutover of existing JSON data is **OQ-2** (park / migrate / refuse). This sketch only hides the chrome. No migrate wizard, no “review your custom keys” screen, until Brief Decides.

## 4. Tables list expansion

Same screen: **Admin → Schema → Tables** (`/admin/schema/tables`). Add table stays the standing CREATE TABLE dialog. This packet changes **who appears in the grid**.

**P1 rows (minimum, locked):**

| Display name | Database name (secondary, read-only) | Kind |
|--------------|--------------------------------------|------|
| **Samples** | `samples` | Core |
| **Project** | `project` | Core |
| *(UI-created display name, e.g. Lot Notes)* | physical name from CREATE | Created |

Lead with the display name. **Project**, never `project`, as the name the admin reads. Database name stays a second column.

**Do not invent more system tables.** Containers, tests, clients, batches, analyses are not rows until OQ-1 option B and Marc names the set.

**Link tables (OQ-5e A, default):** after a relation exists, its link table is a row on this grid for **`schema:edit` only**. Kind = **Link**. Display name is the relation name. Read-only metadata: the two tables, cardinality, database name. No Add field, no layout membership, no Deprecate-as-if-it-were-a-lab-table. `layout:edit` does not see Link rows. Operators never see them. If Marc overwrites OQ-5e to **B** (hidden even here), the row goes away and the Relations list still names the relation. Until that overwrite, show the row.

**Selecting Project or Samples** opens the standing Columns, Layouts, and Privileges screens for that table. Those screens are not redrawn here.

**Missing row:** if Project is in Postgres and absent from the grid, that is Tobias Fail (3) — not a cue to CREATE TABLE `project` again. Same for a UI-created table absent from the grid (Fail 4). How registry rows are seeded is **OQ-3** (Alembic / lazy / Register). This sketch does **not** add a Register button.

**Empty state** (no UI-created tables yet): grid still shows Samples and Project. Helper: “Tables you add appear here with Samples and Project.”

## 5. Relations admin UX (OQ-5a)

**Preferred sketch: a Relations tab** on the existing Schema chrome (`/admin/schema/relations`), `schema:edit` only — same gate as Privileges. Not a new Admin nav item. **Not** a new type on Add field.

A “Reference” type on Columns would reopen the P1 type allow-list (Text, Number, Whole number, Yes/No, Date, Date and time, List) and cannot express M:N without a fake list of ids. One tab covers all three cardinalities. **Brief must Decide** that this tab is the answer to OQ-5a (versus a Reference column type).

**Add relation**

1. **From** and **To** — display names, allow-listed tables only. Which pairs are legal in P1 is **OQ-5d**, blocked on OQ-1. Do not invent pairs.
2. **How they relate** — One to many · One to one · Many to many.
3. **Related list name** — what operators will read (“Samples”, “Parent sample”).
4. **Preview, then confirm.** Lab sentence plus what is stored:

| Choice | Preview |
|--------|---------|
| One to many | “Each {child} points at one {parent}. {Parent} lists its {children}. Stored as a real link on {child}.” |
| One to one | “Each {dependent} points at one {other}, and only one dependent may point at that record.” |
| Many to many | “People link {A} and {B}. Nimble keeps the link table. People do not open it.” |

5. Apply is `schema:edit`. Toast names the relation. Stay on Relations.

Examples that match Katinka, **without** putting those tables on the allow-list early: vessel/container and parent → aliquot are one-to-many on the child **when** OQ-5d allows the pair. Until then they are not rows and not relation targets.

**On delete (OQ-5b — not frozen here).** The dialog shows “When a linked record is deleted” with lab words: **Block while linked** · **Clear the link** · **Also delete linked records**. Katinka’s lean — **Block while linked** (RESTRICT) on identity links (sample, barcode vessel); **Clear the link** (SET NULL) only where the link is optional — is **Spec lean, not a Mathilda freeze**. This sketch does not ship a default. CASCADE on an identity link is a bounce (Fail 7, provisional). **Brief must Decide** OQ-5b before the control is enabled. Until then the three words are visible and the confirm stays disabled.

**Junction row** appears under Tables as in §4. Admin does not edit its columns. Removing a relation is a separate confirm (“Remove this link definition?”) — not a spreadsheet delete. What happens to existing links is Brief (with OQ-2/OQ-5b), not a silent wipe.

## 6. Operator Related list / link-unlink (OQ-5c)

Operators never see Schema → Relations and never see a link table. On the **single record** (form) they see a **Related** section. On a **list** they do not edit links.

| Relation | On the record | Actions |
|----------|---------------|---------|
| One to many, many side | One picker, label = the one side (“Project”) | Choose a record, or clear when the link is optional |
| One to many, one side | Related list (table of the many side) | **Link**, **Unlink** |
| One to one | One picker, one slot | Choose, or “Already linked to another record” |
| Many to many | Related list on **both** records | **Link** opens a search picker. **Unlink** removes the link. Nimble writes the link row |

**Link** opens a picker: search by the related record’s name, pick one, confirm. It does not open a grid of link-table columns.

**Unlink** copy: “Unlink {name} from {record}? Both records stay. Only the link is removed.” Unlink is not delete. Unlink must not wipe the other record.

**Empty:** “No {related name} linked yet.” Primary action: **Link**.

**Columns in the Related list** are the role’s layout for that related table (membership, standing rule). Not link-table columns.

**Who may link:** Write on the record they are editing (privileges already locked). Defining the relation stays `schema:edit`. No new permission in this sketch.

**Brief must Decide** which side shows the list versus the single picker when both are plausible (OQ-5c). This sketch’s default is the table above. OQ-5e **A** stands until Marc overwrites: link tables never appear on operator layouts, including this Related list.

## 7. Bounce bars (UI)

Aligned to Tobias Fail (1)–(7). Open OQs stay open. Bars (3) and (7) stay provisional exactly as Spec wrote them.

| Fail | Bounce |
|------|--------|
| (1) | Custom Fields nav, `/admin/custom-fields` editor, Create/Edit Custom Field, or any “Custom Attributes” section still reachable |
| (2) | A screen that writes or shows `custom_attributes` / JSON-as-fields, including results columns from those configs, the experiment JSON dump, and `custom.*` list filters |
| (3) | Schema → Tables missing **Project** (or another P1 table once Marc names it) while that table is in Postgres. Provisional until OQ-1 freezes |
| (4) | A UI-created table in Postgres absent from Schema → Tables |
| (5) | A relation stored only as JSON / `custom_attributes` (no real link or link table) |
| (6) | Operator opens a link table as data entry, edits link rows as a spreadsheet, or a layout offers the link table to anyone without `schema:edit` |
| (7) | CASCADE or a silent wipe on identity links (sample, barcode vessel) where Spec says RESTRICT. Provisional until OQ-5b freezes |

Also bounce, from standing locks and this sketch:

- JSONB or Custom Fields as the way to add a field or a relation
- Listing every Postgres table (no allow-list)
- Inventing system tables beyond Samples, Project, and UI-created tables
- CREATE TABLE used to “add” Project or Samples
- Reference / FK type crammed into the standing Add field type list
- Hide toggle, SQL console, or a new Schema-admin role
- Unlink that deletes the other record
- A migrate wizard this sketch did not get from Brief (OQ-2)

## 8. Open for Brief

| Item | Sketch stance | Brief must Decide |
|------|----------------|-------------------|
| OQ-1 | Grid = Samples + Project + UI-created only | Any other P1 system tables (option B) |
| OQ-2 | Chrome gone either way; data untouched by UI | Park, migrate, or refuse |
| OQ-3 | No Register button | How Project / Samples get registry rows |
| OQ-4 | Map in §3 | Accept the removals and the template-copy rename |
| OQ-5a | **Relations tab** (preferred) | Confirm tab vs Reference-as-column-type |
| OQ-5b | Three lab words shown; confirm **disabled** | RESTRICT / SET NULL / CASCADE. Katinka lean is Spec lean, not this sketch’s freeze |
| OQ-5c | Related list + picker as in §6 | Which side shows list vs single picker |
| OQ-5d | No invented pairs | Which allow-listed pairs may relate (after OQ-1) |
| OQ-5e | **A** — link row on Tables for `schema:edit` only; never operator layouts | Marc overwrite to B or C, if any |
| Deep link | Redirect `/admin/custom-fields` → Schema Tables, no editor | 404 instead of redirect, if wanted |

## 9. Sign-off

| Review | Verdict |
|--------|---------|
| UI (Mathilda) | **Sketch pending Accept** — Custom Fields removal map, Tables list (Samples, Project, UI-created, link metadata), Relations tab, Related list link/unlink. Against Spec/OQ base **`07ccd59`**. |
| Spec (Wilhelmina) | Living. This sketch does not edit requirements or OQs. |
| QA (Tobias) | Fail (1)–(7) cited, not restamped. (3) and (7) stay provisional. |
| Architecture / Lab Ops / Security / Science | Not stamped here. |

**Implement gate:** **CLOSED.** No product code in this sketch. Accept of the sketch is still open. Prior `ui-schema-ddl` CREATE / ADD / layout / privilege locks stand.

**UI Sketch pending Accept** vs tip `07ccd59`.

# UAT: Experiment Templates & SOP (AI) Assist

**Prerequisites:** `uat-security-rbac` (roles and permissions). Users with `experiment:manage`: Administrator, Lab Manager, Lab Technician (default seed). Client user must **not** have this permission.

**Optional:** `ANTHROPIC_API_KEY` set on the backend for end-to-end SOP extraction. Without it, SOP jobs should fail with a clear error — still valid UAT for configuration and UX.

**Objective:** Verify experiment template CRUD, navigation, mandatory review sign-off, activation rules, RBAC, and (when configured) SOP upload → apply → pre-filled edit dialog.

---

## 1. Navigation & RBAC

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1.1 | Log in as **Administrator** | Sidebar **Experiments** accordion visible; expand shows **All Experiments** and **Experiment Templates**. |
| 1.2 | Click **Experiment Templates** | Navigates to `/experiments/templates`; AppBar title **Experiment Templates**; list/grid loads. |
| 1.3 | Log in as **Lab Manager** or **Lab Technician** | Same as admin: both experiment sub-items visible; templates page loads. |
| 1.4 | Log in as **Client** | **Experiments** accordion not visible. |
| 1.5 | As Client, open `/experiments/templates` directly | Redirect to `/dashboard` (or equivalent unauthorized handling). |

---

## 2. Manual template create & edit

| Step | Action | Expected Result |
|------|--------|-----------------|
| 2.1 | Click **New Template** | Dialog opens with tabs (e.g. Basic Info, Protocol Steps, Transfer Steps, Result Columns). |
| 2.2 | Leave outer **name** empty, try Save | Save disabled or validation prevents submit until required fields satisfied. |
| 2.3 | Fill **name** (outer), **experiment name** (in definition), add at least one protocol step, save | Template created; appears in grid; no raw JSON required in UI. |
| 2.4 | Click **Edit** on the row | Dialog opens with existing data; save updates template. |
| 2.5 | Add a transfer step with **Requires sign-off before activation** checked | Save; row shows pending sign-offs chip / non-zero mandatory review count. |
| 2.6 | **Active** toggle on row | Disabled (or blocked) while mandatory reviews pending; tooltip mentions sign-off if implemented. |

---

## 3. Sign-off & activation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 3.1 | Click pending sign-offs chip (or equivalent control) | Sign-off dialog opens listing mandatory transfer steps. |
| 3.2 | Confirm **one** step, try closing dialog | Warning about unconfirmed steps if closing without completing all. |
| 3.3 | Confirm **each** remaining step individually (no single “confirm all”) | After all confirmed, complete action saves template with reviews cleared / count zero. |
| 3.4 | **Active** toggle | Can be turned on when sign-offs complete. |

---

## 4. Delete

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.1 | Delete a template (with confirmation) | Template removed from list or soft-deleted per product rules; no server 500. |

---

## 5. Upload SOP (AI) — when `ANTHROPIC_API_KEY` is set

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5.1 | Open **Upload SOP** (or equivalent) | Dialog requires **two** files: SOP + instrument CSV. |
| 5.2 | Submit both files | Job starts; progress or polling UI; status moves toward complete or failed. |
| 5.3 | On **complete**, apply | Apply creates template (and related records); list refreshes; edit dialog can open with SOP-highlighted fields. |
| 5.4 | Apply again same job | 409 or idempotent handling — user not left with duplicate templates without warning. |

---

## 6. Upload SOP — without API key (negative / config)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 6.1 | With `ANTHROPIC_API_KEY` empty, run upload | Job fails with explicit configuration/error message; **Fill in manually** or similar path available. |

---

## Pass criteria

- All RBAC steps behave as expected for Admin / Lab Manager / Lab Tech vs Client.
- Manual CRUD and sign-off/activation rules work without console errors.
- SOP flow matches backend contract (two files, poll, apply) when key is set; degrades clearly when not.

---

## Summary

**Script file:** `UAT_Scripts/uat-experiment-templates.md`  
**Referenced from:** `UAT_Scripts/uat-testing-log.md` (dependency order and completion log).

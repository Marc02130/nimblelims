# UAT: Experiment Templates & SOP (AI) Assist

**Prerequisites:** `uat-security-rbac` (roles and permissions). Users with `experiment:manage`: Administrator, Lab Manager, Lab Technician (default seed). Client user must **not** have this permission.

**Optional:** `ANTHROPIC_API_KEY` set on the backend for end-to-end SOP extraction. Without it, SOP jobs should fail with a clear error — still valid UAT for configuration and UX.

**Objective:** Verify experiment template CRUD, **Tables & forms (entries)** authoring, activation, RBAC, and (when configured) SOP upload → apply → review dialog.

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

## 2. Manual template create & edit (entries)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 2.1 | Click **New Template** | Dialog opens with **two** tabs only: **Basic Info** and **Tables & forms**. No Protocol Steps, Transfer Steps, or Result Columns. |
| 2.2 | Open **Tables & forms** | Pre-seeded with **Experiment header** and **Samples** presets (or equivalent spine). |
| 2.3 | Leave outer **name** empty, try Save | Save disabled or validation prevents submit until required fields satisfied. |
| 2.4 | Fill **name** (outer), **experiment name** (Basic Info), ensure at least one entry with name + type, save | Template created; grid shows entry count under **Tables & forms** column; no raw JSON required. |
| 2.5 | Click **Edit** on the row | Dialog opens; Tables & forms shows existing entries; save updates template. |
| 2.6 | Add **Aliquot/pool plan** (and optionally Aliquots/pools results) via presets; save | Entries persisted; experiment created from this template later instantiates them. |
| 2.7 | Remove all entries and try Save | Validation error on Tables & forms: at least one entry required. |
| 2.8 | **Active** toggle on row | Can toggle on/off without sign-off dialog (no transfer mandatory-review gate). |

---

## 3. Delete

| Step | Action | Expected Result |
|------|--------|-----------------|
| 3.1 | Delete a template (with confirmation) | Template removed from list or soft-deleted per product rules; no server 500. |

---

## 4. Upload SOP (AI) — when `ANTHROPIC_API_KEY` is set

| Step | Action | Expected Result |
|------|--------|-----------------|
| 4.1 | Open **Upload SOP** (or equivalent) | Dialog requires **two** files: SOP + instrument CSV. |
| 4.2 | Submit both files | Job starts; progress or polling UI; status moves toward complete or failed. |
| 4.3 | On **complete**, apply | Apply creates template; edit dialog opens; review **Tables & forms** (entries may need manual authoring if extract only filled legacy keys). |
| 4.4 | Save template | Legacy protocol/transfer arrays cleared; `mandatory_review_count` 0; activation not blocked. |
| 4.5 | Apply again same job | 409 or idempotent handling — user not left with duplicate templates without warning. |

---

## 5. Upload SOP — without API key (negative / config)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 5.1 | With `ANTHROPIC_API_KEY` empty, run upload | Job fails with explicit configuration/error message; **Fill in Manually** or similar path available. |

---

## Pass criteria

- All RBAC steps behave as expected for Admin / Lab Manager / Lab Tech vs Client.
- Manual CRUD is **entries-only** (Basic Info + Tables & forms); activation works without transfer sign-off.
- SOP flow matches backend contract (two files, poll, apply) when key is set; degrades clearly when not.

---

## Summary

**Script file:** `UAT_Scripts/uat-experiment-templates.md`  
**Referenced from:** `UAT_Scripts/uat-testing-log.md` (dependency order and completion log).

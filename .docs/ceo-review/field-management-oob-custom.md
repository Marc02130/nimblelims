# CEO Review: Field Management for OOB + Custom Fields

**Date:** 2026-07-05
**Reviewer:** CEO of NimbleLIMS
**Topic:** Harmonizing Out-of-the-Box (OOB) fields and custom fields in a single "Field Management" admin experience. Decision around lists vs. validation_rules.options, requirement to pick entity type first, showing context of existing fields, making OOB fields visible + editable (for validation/options), while keeping legacy Custom Attributes and Name Templates UIs.

## Executive Summary

**Verdict: Do this narrowly and soon. It is high-leverage for our users and low-risk to the core product.**

Early-stage biotech teams (our buyers) live in a world of changing requirements. A scientist or lab manager frequently needs to track "just one more thing" on a sample, a batch, a result, or inside an experiment step. Today they either:

- Abuse the old custom_attributes JSONB (hard to query, no validation, invisible in good UIs).
- File support tickets or wait for us to add columns.
- Abuse lists or spreadsheets.

Making **both** the built-in OOB list-backed fields (sample_type, status, matrix, qc_type, specimen_biotype, project status, etc.) **and** true custom fields visible in one place per entity type, with a clean way to define/edit options via validation rules, and forcing context (what else exists on this entity) before adding something new, directly attacks a daily pain point.

**Key decisions we are endorsing:**
- Unified view in Field Management: OOB (denoted) + Custom.
- Require entity type before creating a custom field + show existing fields as helpful context.
- Harmonize "select" options via validation_rules (OOB fields get the same treatment for definition/validation). We are **not** forcing every admin to go through the Lists system just to define a field's allowed values.
- Lists system remains available (not removed).
- Legacy "Custom attributes" and "Name templates" pages stay as separate entries.
- Validation rules (including required + options) become first-class for OOB too.

This is scoped admin tooling. It does not require changing core data storage for existing OOB columns right now. It improves discoverability, consistency, and self-service.

**Business impact:** Faster time-to-usable-data for customers, fewer "can you add this field?" tickets, better data quality (enforced options + validation on more fields), stronger perception that NimbleLIMS understands real lab work.

## Why This Matters for Our Customers

Early-stage biotechs:
- Requirements evolve weekly (new assay, new CRO requirement, new internal QC metric for the next funding update).
- The person configuring the system is often the same person running experiments or managing the lab.
- They hate invisible or second-class data. If "specimen_biotype" or "matrix" feels like a black box compared to a custom field they just added, trust erodes.
- Clean, validated, reportable data is part of what they sell to investors and partners.

Giving them one screen where they can say "show me everything defined on Samples", instantly see which are our OOB fields vs their customs, see the allowed options, and add a new one (after being reminded what already exists) is exactly the low-friction experience that wins lab managers.

## Tradeoffs & Scope (Important for a Small Team)

**We are NOT:**
- Deprecating or removing the Lists feature.
- Doing a big migration to move all OOB list_entries data into validation rules.
- Letting users arbitrarily change the storage column type of core OOB fields today.
- Building full dynamic table creation (that was previously deprioritized by CEO feedback).

**We ARE:**
- Making the admin experience for "fields on entities" consistent and contextual.
- Allowing validation rules + options editing for OOB fields in the same UI.
- Using validation_rules.options as the harmonized way to express allowed values for "select" fields in the definition layer (while OOB columns can continue using their existing list-backed storage).
- Improving the add flow with required entity + context.

This is classic "make the 80% painful thing delightful" work.

## Alignment with Broader Schema Evolution

This fits the ongoing hard-cutover / FieldDefinition work:
- FieldDefinition already contemplates validation_rules and data_type.
- We are using the field management UI as the practical place where admins interact with both OOB extensions and new custom extensions.
- It supports the goal of reducing reliance on unstructured custom_attributes JSONB.
- Later we can make the rendering components (CustomAttributeField, form generators, Entry columns) consume these definitions uniformly.

## Risks

1. **Admin confusion between Lists and field options**
   Mitigation: Clear labels in UI ("Options defined for this field" vs "Reusable lists"). Docs update. Lists remain useful for other things.

2. **Data drift between options shown in field mgmt and actual list_entries for OOB columns**
   Mitigation: For MVP, treat the field definition options as the "declared / validated set" shown in admin and forms. The underlying list can be the runtime source for existing data. We can add "sync from list" or "update list from options" later if customers need it. Document the current reality.

3. **Over-building**
   Mitigation: This change is mostly in two frontend files + some seed data for OOB. No new heavy backend schema admin engine yet. We stay narrow.

4. **Legacy Custom Attributes page**
   Per request: leave it alone and available. Field Management becomes the recommended modern view.

## Recommendation

**Approve and ship the UI harmonization.**

- Prioritize the described changes to CustomFieldsManagement + CustomFieldDialog.
- Use validation_rules (with options) as the harmonized mechanism for select field definitions in this UI.
- Make OOB fields first-class (visible + editable for validation/options).
- Enforce entity selection + context display.
- Expand entity coverage.
- Keep legacy pages.

This is the kind of polish that makes an admin feel the product "gets" their world and saves them time every week. It strengthens our position vs generic tools or "we'll add it in the next ticket."

After this lands, watch support tickets and customer feedback around "adding fields" and "where do I manage specimen_biotype / status options?". Use that signal to decide if/when to deepen the backend integration with FieldDefinition or add list-sync features.

Resources: small — 1-2 eng days for solid implementation + tests + review docs.

This is a good use of time.
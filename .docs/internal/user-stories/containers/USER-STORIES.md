# User stories — Containers

User stories in Agile form: "As a [role], I want [feature] so that [benefit]."

**MVP Release Bar:** Stories labeled **[MVP]** are required for basic LIMS (sample tracking, test ordering, results entry). **[Shipped, Not MVP]** / **[Post-MVP]** are enhancements.

**Formal review SoT** stays under `.docs/review/`. These files are local working notes (`.docs/internal/`).

**Domain PRD:** [`../../prd/containers/PRD.md`](../../prd/containers/PRD.md) · **Spec:** [`../../specs/containers/SPEC.md`](../../specs/containers/SPEC.md)

---

- **US-5: Container Management** **[MVP]**  
  As a Lab Technician, I want to assign and manage hierarchical containers for samples so that physical storage is tracked.  
  *Acceptance Criteria*:  
  - Types: tube, plate, well, rack (from container_types table with capacity, material, dimensions, preservative).  
  - Self-referential (parent_container_id for plates/wells).  
  - Contents link: Multiple samples per container (pooling) with concentration/amount/units.  
  - Units table: id, name, description, active, audit fields, multiplier, type (list: concentration, mass, volume, molar).  
  - API: POST /containers; link via /contents; RBAC: sample:update.  
  *Priority*: High | *Estimate*: 8 points

- **US-21: Container Types Management** **[MVP]**  
  As an Administrator, I want to manage container types so that they are standardized before use.  
  *Acceptance Criteria*:  
  - CRUD operations for container types (name, capacity, material, dimensions, preservative).  
  - Types must exist before container instances can be created.  
  - API: CRUD /containers/types; RBAC: config:edit.  
  *Priority*: Medium | *Estimate*: 3 points

- **US-38: Aliquot Remaining Quantity Tracking** **[MVP]**  
  As a Lab Technician, I want to track remaining quantity when creating aliquots so that depletion is visible and over-aliquoting is prevented.  
  *Acceptance Criteria*:  
  - Parent sample has quantity and remaining_quantity fields.  
  - Creating aliquot decreases parent remaining_quantity by aliquot volume/amount.  
  - Cannot aliquot more than remaining quantity (validation error).  
  - Aliquot (later): new container barcode on the **same** sample ID. Derivative (later): new system sample ID. Not in atomic-receive P0.  
  - Parent history survives deleting a child aliquot.  
  - Remaining quantity = 0 signals depletion (optional link to Discarded disposition).  
  - API: POST /samples/aliquot validates remaining quantity; updates parent.  
  - UI: Aliquot form shows parent remaining quantity; validates against available amount.  
  - Parked: Numeric freeze-thaw limits (no public SOP found); robotic worklist integration.  
  *Priority*: Medium | *Estimate*: 5 points  
  *Related*: Issue #24 (aliquot identity)


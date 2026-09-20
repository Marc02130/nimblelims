# UAT: E-6 intake Available for Testing

**Stem:** `e6-intake-available`  
**Branch:** `feat/e6-intake-available-for-testing`  
**Scope:** Leftover accession / bulk-accession write **Available for Testing**, matching CORE receive (AR-ST-01). Decision #24 start gate can then see freshly accessioned samples.

**Unsigned.** Do not invent Pass. Do not restamp atomic-receive AR-ST-01. Process assign still does **not** change Sample.status.

## Prerequisites

1. Local compose on this branch.  
2. Log in as Admin (`admin` / `admin123`) with `sample:create` and `experiment:manage`.  
3. Sample status list includes **Received** and **Available for Testing**.

## 1. CORE receive (already Pass — smoke only)

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 1.1 | `/receive` one Blood sample. | Status **Available for Testing**. No Received hop. | Unsigned this packet (AR-ST-01 already Pass) |

## 2. Legacy accession

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 2.1 | `POST /samples/accession` for a Blood sample. | **201**. `status` is Available for Testing, not Received. | Unsigned |
| 2.2 | Start an ad hoc experiment with that sample. | Sample is eligible (Available for Testing). Start succeeds. | Unsigned |

## 3. Bulk accession

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 3.1 | `POST /samples/bulk-accession` two samples. | Both **Available for Testing**. | Unsigned |

## 4. Process assign does not promote

| Step | Action | Expected result | Result |
|------|--------|-----------------|--------|
| 4.1 | Create a sample whose status is **Received** (manager edit). Assign to a process. | Sample.status stays **Received**. Start dialog shows ineligible. | Unsigned |

**Fail:** accession or bulk still writes Received; assign-to-process silently flips status; CORE receive regresses off AFT.

## Pass criteria

- Steps **2.1–2.2**, **3.1**, **4.1**. **Unsigned** until Tobias.  
- CORE receive AR-ST-01 stays the `uat-atomic-receive` stamp. Do not restamp it here.

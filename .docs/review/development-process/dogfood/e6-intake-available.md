# Dogfood: E-6 intake Available for Testing

**Stem:** `e6-intake-available`  
**Branch:** `feat/e6-intake-available-for-testing`  
**When:** After this branch is up, **before** Tobias UAT.  
**Not a UAT Result.** Do not invent Pass. Not E-7 restamp. Not dest-follow.

CORE receive already writes Available for Testing (AR-ST-01). This packet is leftover **accession** and **bulk-accession**.

## Env

Local compose. `admin` / `admin123`. `sample:create`, `experiment:manage`.

## Paths

1. `POST /samples/accession` → sample status **Available for Testing**. Start an ad hoc experiment with it → eligible.
2. `POST /samples/bulk-accession` → each row Available for Testing.
3. `/receive` smoke: still Available for Testing (no Received hop).
4. Manager sets a sample to **Received**, assign to a process → status stays Received (Decision #24). Start dialog ineligible.

## Ready for UAT?

Unsigned until Tobias. Do not invent Ready=Yes.

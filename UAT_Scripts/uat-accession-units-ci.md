# UAT: accession conflict, concentration scales, zero values

## Duplicate accession name

1. Accession a sample with a name that already exists.
2. The response is HTTP 409.
3. The message says a sample with this name already exists.

## Concentration units

1. Open Units. Mass concentration uses g/L as multiplier 1.
2. ng/µL, µg/mL, and mg/L are 0.001. 1 g/L is 1000 ng/µL. mg/mL is 1 (the same quantity as g/L).
3. EU/mL is unit type activity. copies/µL is copy_concentration. cfu is count.
4. Pool two vessels, one in ng/µL and one in µg/mL. The pool succeeds and reports g/L.
5. Pool a mass concentration with EU/mL. The pool is refused and neither vessel is debited.

## Zero is a value

1. Edit an analysis whose turnaround time is 0 and whose cost is 0. Save. Both stay 0.
2. Edit an analyte rule with significant figures 0. The rule list shows 0, not blank.
3. On a container grid, row 0 and column 0 stay visible in the editor.

## Pool concurrency

1. Two pools that each need more than the source holds: one succeeds, the source is never negative.
2. A draw against a vessel another transaction has locked returns a busy error instead of hanging.

# UAT: zero values, clearable fields, batch grid, pool concentration

Run against a database that includes the #178 unit rescale (nM is 1e-9 mol/L and µM is 1e-6 mol/L).

## Turnaround time and significant figures

1. Edit an analysis. Set turnaround time to 0 and save. The list shows 0.
2. Clear turnaround time and save. The list no longer shows the previous number.
3. Edit an analyte rule. Set significant figures to 0 and save. The rule list shows 0.
4. Clear significant figures and save. The rule list no longer shows the previous number.
5. A negative turnaround time or negative significant figures is refused in the form.

## Asked-for turnaround time

1. Record asked-for with TAT (days) set to 0. The row is stored with tat_days 0.
2. TAT of -1 is refused. The form checks `value < 0`, and the API returns 422.

## Grid positions stay 1-based

1. Open a batch container grid and edit a container.
2. Row 0 or column 0 is refused in the form, and the API returns 422.
3. Row 1, column 1 saves.

## Batch grid edit

1. Open a batch that already has a container.
2. Edit that container and save.
3. The request is PATCH /containers/{container id}, and the id is not the word undefined.
4. The saved row and column are the values entered.

## Remove content

1. Open a container that holds a sample.
2. Use the remove-content button.
3. The contents amount becomes 0. The request is PATCH /containers/{container id}/contents/{sample id} with amount 0. The contents row is still there.
4. DELETE /containers/{container id}/contents/{sample id} returns 405. DELETE /contents/{id} is not a route.

## Pool concentration

1. Pool two sources in the same concentration unit, 10 and 20, with amounts 5 and 10.
2. Each destination contents row stores concentration 15 in that shared unit.
3. Pool 1000 ng/µL with 1000 µg/mL. Each destination contents row stores 1 g/L.
4. The source vessels are still debited by the transferred quantity.

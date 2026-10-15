# Frontend test suite: known failures and open issues

Last triaged: 2026-10-15 (off main b096eb1).

## Status

| Check | Before | After |
|---|---|---|
| `CI=true npm test -- --watchAll=false` | 47 failed / 167 run (29 of 42 suites failed; many suites did not load) | **462 passed / 462**, 41 of 41 suites |
| `npx tsc --noEmit` | 14 errors (all in `node_modules/@mui/x-internals`) | **0** |

**No tests are currently known to fail.** No tests were deleted or skipped to get there.

## What was wrong (root causes)

1. **TypeScript 4.9 could not parse MUI X v8 typings.** `@mui/x-internals` and `@mui/x-data-grid` v8 use
   `const` type parameters, a TypeScript 5.0 feature. `skipLibCheck` was already `true`, and it does not
   help with parse errors. Fix: align TypeScript to `~5.4.5` (MUI X v8 needs TS 5+). `react-scripts@5`
   declares a peer range of TS 3/4, so `package.json` pins it with `"overrides": {"typescript": "$typescript"}`.
   CRA's build, its type checker and Jest all run fine on 5.4. `skipLibCheck` is unchanged.
2. **Jest 27 (CRA 5) vs ESM-only and modern dependencies.**
   - `axios` and `date-fns` v4 ship ESM, which Jest 27 cannot load untransformed. `transformIgnorePatterns`
     now transforms them.
   - MUI X v8 imports `.css`, so a `moduleNameMapper` points CSS at `src/__mocks__/styleMock.js`.
   - jsdom has no `TextEncoder`, which `@mui/x-internals/hash` needs. `setupTests.ts` polyfills it from `util`.
3. **CRA's `resetMocks: true`** wipes every `jest.fn(impl)` before each test. Module-level mocks such as
   `hasPermission: jest.fn(...)`, `matchMedia` and `ResizeObserver` returned `undefined` in every test.
   They are now plain functions. `src/__tests__/setup.ts` moved to `src/testSetup.ts`, because Jest had
   been collecting it as an empty test suite.
4. **UserProvider now probes the cookie session** (`apiService.getCurrentUser()`, `/auth/me`, P4/S10)
   instead of reading a localStorage token. Every factory mock of `apiService` now provides `getCurrentUser`.
5. **Tests written for older UI.** Fixed against the current UI:
   - Required labels now end with `*`.
   - Sidebar and AdminDashboard render their drawer twice.
   - Batch creation is now a 4-step wizard.
   - Container types use rows×columns instead of dimensions.
   - Users now have a required Name.
   - Grid row actions are menuitems.
   - Eligible samples load only after a test is picked.
   - Some routes need `:analysisId`.

## Real bugs fixed while triaging

- **Dashboard:** the Type and Matrix columns always showed "Unknown", because names were looked up in
  an empty list. Status and Project filter labels were not associated with their selects.
- **AnalysisFormDialog:** a cost of 0 was dropped (`|| undefined` changed to `?? undefined`).
- **AnalyteRuleForm:** editing a rule with a 0 limit (for example pH low 0) dropped the limit (`||` changed to `??`).
  The "low ≤ high" error was never shown, because it was an object-level Yup error; it is now attached to Low Value.
- **ContainerTypeForm (Capacity) and UnitFormDialog (Multiplier):** `field.onChange({target:{value}})` had no
  `name`, so Formik ignored the change and edits to these fields were silently dropped. They now use `setFieldValue`.
- **ContainerTypeForm:** clearing Rows or Columns showed a type error instead of "required".
- **UserFormDialog:** the Role "required" error was never displayed.
- **AnalysisAnalytesConfig:** load failures were masked as "Analysis not found".
- **BatchResultsEntryTable:** `editable: true` on cells that render their own inputs made the grid start its own
  edit mode and swallow keystrokes. Grid keyboard navigation is now kept out of the inputs.
- **ResultsEntryTable** (single-test results entry):
  - Results were initialised before analytes loaded, so typed values were dropped.
  - Rows were duplicated per sample, and all duplicates were submitted.
  - The save body did not match `POST /results/batch` (US-28 `{batch_id, results:[{test_id, analyte_results}]}`).
  - The save response (not a list) replaced the table state.
  - Analytes were fetched with the test id instead of the test's analysis id.
- **Accessibility:**
  - Several MUI Selects had an `InputLabel` with no `labelId`, so screen readers got no label:
    BatchForm, AliquotForm, HelpManagement, HelpEntryDialog, ClientProjects, AnalyteRuleForm,
    UserFormDialog and ResultsEntryTable.
  - The search "clear" icon buttons had no accessible name; they now say "Clear search" on 15 pages.
  - The ClientHelpSection spinner had no label.
- **EligibleSample type:** its nullable API fields are now typed `| null`, matching the Pydantic schema.

## Open issues (not fixed here, and why)

- **ESLint errors in `npm run build`.** Unless `DISABLE_ESLINT_PLUGIN=true` is set, the build fails on existing
  `no-explicit-any` and `no-unused-vars` errors across many files. The production Dockerfile already sets
  `DISABLE_ESLINT_PLUGIN=true`, and `DISABLE_ESLINT_PLUGIN=true npm run build` compiles. Cleaning the lint debt
  is a separate, mechanical task outside this triage.
- **ResultsEntryTable layout.** For one selected test it still renders a row for every batch sample, and all
  rows edit the same per-analyte result. A test belongs to one sample, so the table should show that sample
  only. That is a UX change, left for a follow-up. Data sent to the API is now correct (one result per analyte).
- **Console noise.** Tests print React `act()` warnings, React Router v7 future-flag warnings and a deprecated
  `ReactDOMTestUtils.act` warning from the RTL and React versions in use. None of them fail tests.
- **Slow wizard tests.** BatchManagement drives the 4-step wizard with MUI Selects and Autocompletes. Each test
  takes 2–6 s under jsdom, so that file sets `jest.setTimeout(30000)`.
- **CRA 5 / Jest 27 are end-of-life.** Moving to Vite + Vitest, or Jest 29 with native ESM, would remove the
  `transformIgnorePatterns` and TypeScript `overrides` workarounds. That is out of scope here.

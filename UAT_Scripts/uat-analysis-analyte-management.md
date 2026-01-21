# UAT Script: Analysis and Analyte Management

## Overview
This UAT script validates the Analyses and Analytes management functionality, including CRUD operations, expandable grid for linked analytes, and permission-based access control.

## Prerequisites
- NimbleLIMS application running (backend + frontend + database)
- Test users with different roles:
  - Admin user with `analysis:manage` permission
  - Lab Manager user with `analysis:manage` permission
  - Lab Technician user without `analysis:manage` permission

---

## Test Cases

### TC-1: Navigation Access - Admin/Lab Manager

**Objective:** Verify users with `analysis:manage` permission can access the Analyses and Analytes pages from the Lab Mgmt accordion.

**Steps:**
1. Log in as Admin or Lab Manager user
2. Locate the sidebar navigation
3. Click on the "Lab Mgmt" accordion to expand it
4. Verify "Analyses" and "Analytes" menu items are visible
5. Click on "Analyses"
6. Verify the Analyses page loads at `/analyses`
7. Click on "Analytes"
8. Verify the Analytes page loads at `/analytes`

**Expected Results:**
- [ ] Lab Mgmt accordion expands when clicked
- [ ] "Analyses" menu item is visible with Biotech icon
- [ ] "Analytes" menu item is visible with Science icon
- [ ] Clicking "Analyses" navigates to `/analyses`
- [ ] Clicking "Analytes" navigates to `/analytes`
- [ ] Lab Mgmt accordion auto-expands when navigating directly to `/analyses` or `/analytes`

---

### TC-2: Navigation Access - Restricted User

**Objective:** Verify users without `analysis:manage` permission cannot access the Analyses and Analytes pages.

**Steps:**
1. Log in as Lab Technician user (without `analysis:manage` permission)
2. Locate the sidebar navigation
3. Click on the "Lab Mgmt" accordion (if visible)
4. Verify "Analyses" and "Analytes" menu items are NOT visible
5. Try navigating directly to `/analyses` in the browser
6. Try navigating directly to `/analytes` in the browser

**Expected Results:**
- [ ] "Analyses" and "Analytes" menu items are not visible in Lab Mgmt accordion
- [ ] Direct navigation to `/analyses` redirects to dashboard
- [ ] Direct navigation to `/analytes` redirects to dashboard

---

### TC-3: Analyses List View

**Objective:** Verify the Analyses management page displays a grid with all expected columns and functionality.

**Steps:**
1. Log in as Admin user
2. Navigate to `/analyses`
3. Verify the DataGrid displays with columns:
   - Expand icon (first column)
   - Name
   - Method
   - Turnaround (days)
   - Cost
   - Status (Active/Inactive chip)
   - Created
   - Actions (Edit icon)
4. Verify pagination controls are present
5. Use the search field to search by name
6. Use the search field to search by method

**Expected Results:**
- [ ] DataGrid displays all analyses with correct columns
- [ ] Expand icon is visible in the first column of each row
- [ ] Pagination shows correct page numbers and total count
- [ ] Search by name filters results correctly
- [ ] Search by method filters results correctly
- [ ] Status column shows colored chips (green for Active, gray for Inactive)

---

### TC-4: Create New Analysis

**Objective:** Verify a new analysis can be created successfully.

**Steps:**
1. Navigate to `/analyses`
2. Click the FAB (floating action button) with the "+" icon
3. Verify the Create Analysis dialog opens
4. Enter the following data:
   - Name: "UAT Test Analysis"
   - Method: "UAT Method 001"
   - Turnaround Time: 5
   - Cost: 99.99
   - Description: "Created for UAT testing"
   - Active: checked
5. Click "Create" button
6. Verify success snackbar message appears
7. Verify the new analysis appears in the grid

**Expected Results:**
- [ ] FAB button is visible and clickable
- [ ] Create dialog opens with empty form
- [ ] All fields accept input correctly
- [ ] "Create" button submits the form
- [ ] Success message: "Analysis created successfully"
- [ ] New analysis appears in the grid with correct values

---

### TC-5: Edit Existing Analysis

**Objective:** Verify an existing analysis can be edited.

**Steps:**
1. Navigate to `/analyses`
2. Find an analysis in the grid
3. Click the Edit icon in the Actions column
4. Verify the Edit dialog opens with pre-populated data
5. Modify the following fields:
   - Method: "Updated Method"
   - Cost: 150.00
6. Click "Update" button
7. Verify success snackbar message appears
8. Verify the analysis in the grid shows updated values

**Expected Results:**
- [ ] Edit icon is visible and clickable
- [ ] Edit dialog opens with existing data pre-populated
- [ ] Fields can be modified
- [ ] "Update" button submits the form
- [ ] Success message: "Analysis updated successfully"
- [ ] Grid reflects the updated values

---

### TC-6: Expand Analysis to View Linked Analytes

**Objective:** Verify the expandable row functionality shows linked analytes.

**Steps:**
1. Navigate to `/analyses`
2. Click the expand icon (chevron) on a row that has linked analytes
3. Verify the detail panel expands below the grid
4. Verify the "Linked Analytes" section displays:
   - Header with "Linked Analytes" and count chip
   - DataGrid with columns: Analyte Name, CAS Number, Data Type, Remove action
   - "Add Analytes" button

**Expected Results:**
- [ ] Clicking expand icon expands the detail panel
- [ ] Detail panel shows "Linked Analytes" header with count
- [ ] Linked analytes are displayed in a nested DataGrid
- [ ] Each analyte row shows name, CAS number, and data type chip
- [ ] "Add Analytes" button is visible
- [ ] Clicking expand icon again collapses the panel

---

### TC-7: Link New Analytes to Analysis

**Objective:** Verify analytes can be linked to an analysis from the expandable detail panel.

**Steps:**
1. Navigate to `/analyses`
2. Expand a row by clicking the expand icon
3. Click "Add Analytes" button
4. Verify an Autocomplete search field appears
5. Type a partial analyte name to search
6. Select one or more analytes from the dropdown
7. Click "Add (#)" button
8. Verify success snackbar message appears
9. Verify the newly linked analytes appear in the Linked Analytes grid

**Expected Results:**
- [ ] "Add Analytes" button expands the linking UI
- [ ] Autocomplete field searches analytes by name
- [ ] Multiple analytes can be selected
- [ ] "Add" button shows count of selected analytes
- [ ] Success message: "X analyte(s) linked successfully"
- [ ] Newly linked analytes appear in the grid
- [ ] Cancel button dismisses the add UI without changes

---

### TC-8: Unlink Analyte from Analysis

**Objective:** Verify an analyte can be unlinked from an analysis.

**Steps:**
1. Navigate to `/analyses`
2. Expand a row that has linked analytes
3. Click the Remove (trash) icon on a linked analyte row
4. Verify success snackbar message appears
5. Verify the analyte is removed from the Linked Analytes grid

**Expected Results:**
- [ ] Remove icon is visible on each analyte row
- [ ] Clicking Remove unlinks the analyte
- [ ] Success message: "Analyte unlinked successfully"
- [ ] Analyte is removed from the grid
- [ ] Linked analyte count updates correctly

---

### TC-9: Analytes List View

**Objective:** Verify the Analytes management page displays correctly.

**Steps:**
1. Navigate to `/analytes`
2. Verify the DataGrid displays with columns:
   - Name
   - CAS Number
   - Default Unit
   - Data Type (chip)
   - Status (Active/Inactive chip)
   - Created
   - Actions (Edit icon)
3. Verify pagination controls are present
4. Use the search field to search by name
5. Use the search field to search by CAS number

**Expected Results:**
- [ ] DataGrid displays all analytes with correct columns
- [ ] Data Type column shows colored chips (numeric=blue, text=purple, etc.)
- [ ] Status column shows colored chips
- [ ] Pagination works correctly
- [ ] Search by name filters results
- [ ] Search by CAS number filters results

---

### TC-10: Create New Analyte

**Objective:** Verify a new analyte can be created successfully.

**Steps:**
1. Navigate to `/analytes`
2. Click the FAB with the "+" icon
3. Enter the following data:
   - Name: "UAT Test Analyte"
   - CAS Number: "12345-67-8"
   - Data Type: "numeric"
   - Description: "Created for UAT testing"
   - Active: checked
4. Click "Create" button
5. Verify success snackbar message appears
6. Verify the new analyte appears in the grid

**Expected Results:**
- [ ] FAB button is visible and clickable
- [ ] Create dialog opens with empty form
- [ ] Data Type dropdown shows all options (numeric, text, date, boolean)
- [ ] Default Unit autocomplete loads available units
- [ ] "Create" button submits the form
- [ ] Success message: "Analyte created successfully"
- [ ] New analyte appears in the grid

---

### TC-11: Edit Existing Analyte

**Objective:** Verify an existing analyte can be edited.

**Steps:**
1. Navigate to `/analytes`
2. Click the Edit icon on an analyte row
3. Verify the Edit dialog opens with pre-populated data
4. Modify the CAS Number field
5. Change the Data Type
6. Click "Update" button
7. Verify success snackbar message appears
8. Verify the grid shows updated values

**Expected Results:**
- [ ] Edit dialog opens with existing data
- [ ] Fields can be modified
- [ ] "Update" button submits changes
- [ ] Success message: "Analyte updated successfully"
- [ ] Grid reflects updated values

---

### TC-12: Unique Name Validation

**Objective:** Verify duplicate analysis and analyte names are rejected.

**Steps:**
1. Navigate to `/analyses`
2. Click FAB to create new analysis
3. Enter a name that already exists
4. Enter required fields (method)
5. Click "Create"
6. Verify error message about duplicate name

7. Navigate to `/analytes`
8. Click FAB to create new analyte
9. Enter a name that already exists
10. Click "Create"
11. Verify error message about duplicate name

**Expected Results:**
- [ ] Analysis creation fails with "Analysis name already exists" error
- [ ] Analyte creation fails with "Analyte name already exists" error
- [ ] Error is displayed in snackbar or inline
- [ ] Form remains open for correction

---

### TC-13: API Error Handling - 500 Error

**Objective:** Verify the application handles server errors gracefully.

**Steps:**
1. Navigate to `/analyses`
2. Expand a row to view linked analytes
3. (Simulate a 500 error if possible, or use browser dev tools to block the API)
4. Verify error message is displayed
5. Verify the application remains functional

**Expected Results:**
- [ ] Error message is displayed in snackbar or alert
- [ ] Application does not crash
- [ ] User can retry the operation

---

## Test Summary

| Test Case | Description | Pass/Fail | Notes |
|-----------|-------------|-----------|-------|
| TC-1 | Navigation Access - Admin/Lab Manager | | |
| TC-2 | Navigation Access - Restricted User | | |
| TC-3 | Analyses List View | | |
| TC-4 | Create New Analysis | | |
| TC-5 | Edit Existing Analysis | | |
| TC-6 | Expand Analysis to View Linked Analytes | | |
| TC-7 | Link New Analytes to Analysis | | |
| TC-8 | Unlink Analyte from Analysis | | |
| TC-9 | Analytes List View | | |
| TC-10 | Create New Analyte | | |
| TC-11 | Edit Existing Analyte | | |
| TC-12 | Unique Name Validation | | |
| TC-13 | API Error Handling | | |

---

## Related Documentation
- [API Endpoints](../.docs/api_endpoints.md) - Analyses and Analytes API documentation
- [Navigation](../.docs/navigation.md) - Sidebar navigation structure
- [Batches](../.docs/batches.md) - Batch management documentation

# UAT Scripts: Navigation and UI Responsiveness

## Overview

This document contains User Acceptance Testing (UAT) scripts for navigation and UI responsiveness in NimbleLIMS. These scripts validate the unified sidebar navigation, responsive design, and accessibility features as defined in:

- **Navigation Document**: `navigation.md` (unified sidebar, accordions, permission gating, auto-expand)
- **UI Document**: `ui-accessioning-to-reporting.md` (responsive adaptations, breakpoints)
- **PRD**: Section 6.3 Usability (WCAG 2.1 compliance, accessibility)

## Test Environment Setup

### Prerequisites
- NimbleLIMS application running (backend and frontend)
- Browser with developer tools (for responsive testing)
- Test user accounts:
  - Administrator with `config:edit` permission (for Admin accordion test)
  - Lab Manager with `project:manage` permission (for Client accordion test)
  - Lab Technician with `sample:create` permission (for permission gating test)
- Browser window resizable (for responsive testing)

---

## Test Case 1: Sidebar Navigation - Permission Gating and Auto-Expand

### Test Case ID
TC-NAV-SIDEBAR-001

### Description
Verify that sidebar navigation correctly gates menu items by permissions, auto-expands accordions on route navigation, and maintains proper visual states.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Administrator (with `config:edit` permission) |
| **User Logged In** | User successfully authenticated |
| **Browser** | Desktop viewport (≥600px width) |
| **Sidebar State** | Expanded (240px width) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Administrator | User authenticated, dashboard loads |
| 2 | **Verify Sidebar Structure** | |
| 2.1 | Verify sidebar visible | Sidebar visible on left side (240px width) |
| 2.2 | Verify Core Features section | Core Features section visible with items: Dashboard, Accessioning, Samples, Tests, Containers, Batches, Results, Help |
| 2.3 | Verify Admin accordion visible | Admin accordion visible (requires `config:edit` permission) |
| 2.4 | Verify Client accordion visible (if user has `project:manage`) | Client accordion visible if user has `project:manage` permission |
| 3 | **Test Permission Gating** | |
| 3.1 | Verify all core items visible | All core items visible (Administrator sees all items) |
| 3.2 | Verify Admin accordion visible | Admin accordion visible (user has `config:edit`) |
| 3.3 | Log out and log in as Lab Technician (no `config:edit`) | User authenticated |
| 3.4 | Verify Admin accordion NOT visible | Admin accordion NOT visible (user lacks `config:edit`) |
| 3.5 | Verify Client accordion NOT visible (if no `project:manage`) | Client accordion NOT visible if user lacks `project:manage` |
| 4 | **Test Auto-Expand Accordion** | |
| 4.1 | Log in as Administrator | User authenticated |
| 4.2 | Navigate to `/dashboard` | Dashboard loads, Admin accordion collapsed (not on admin route) |
| 4.3 | Navigate to `/admin` | Admin Dashboard loads |
| 4.4 | Verify Admin accordion auto-expanded | Admin accordion expanded automatically (shows sub-items) |
| 4.5 | Verify "Overview" item highlighted | "Overview" item shows active state (primary color icon) |
| 4.6 | Navigate to `/admin/lists` | Lists Management page loads |
| 4.7 | Verify Admin accordion still expanded | Admin accordion remains expanded |
| 4.8 | Verify "Lists Management" item highlighted | "Lists Management" item shows active state |
| 4.9 | Navigate to `/dashboard` | Dashboard loads |
| 4.10 | Verify Admin accordion collapsed | Admin accordion collapsed (not on admin route) |
| 5 | **Test Client Accordion Auto-Expand** | |
| 5.1 | Log in as user with `project:manage` permission | User authenticated |
| 5.2 | Navigate to `/clients` | Clients page loads |
| 5.3 | Verify Client accordion auto-expanded | Client accordion expanded automatically |
| 5.4 | Navigate to `/client-projects` | Client Projects page loads |
| 5.5 | Verify Client accordion still expanded | Client accordion remains expanded |
| 6 | **Test Manual Accordion Toggle** | |
| 6.1 | Navigate to `/admin` | Admin Dashboard loads, Admin accordion expanded |
| 6.2 | Click Admin accordion header | Accordion collapses |
| 6.3 | Click Admin accordion header again | Accordion expands |
| 7 | **Test Active State** | |
| 7.1 | Navigate to `/admin/lists` | Lists Management page loads |
| 7.2 | Verify "Lists Management" item highlighted | Item shows primary color icon and selected state |
| 7.3 | Verify other admin items not highlighted | Other admin items show default styling |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Sidebar Structure** | - Sidebar visible on left (240px width expanded)<br>- Core Features section with navigation items<br>- Admin accordion visible (if `config:edit` permission)<br>- Client accordion visible (if `project:manage` permission) |
| **Permission Gating** | - Menu items visible only if user has required permission<br>- Admin accordion hidden if no `config:edit` permission<br>- Client accordion hidden if no `project:manage` permission<br>- Core items filtered by permissions |
| **Auto-Expand Accordion** | - Admin accordion auto-expands when navigating to `/admin/*` routes<br>- Client accordion auto-expands when navigating to `/clients` or `/client-projects` routes<br>- Accordions remain expanded while on related routes<br>- Accordions collapse when navigating away |
| **Manual Toggle** | - Accordions can be manually collapsed/expanded by clicking header<br>- Toggle state persists during navigation within section |
| **Active State** | - Current page item highlighted with primary color icon<br>- Selected state applied to active item<br>- Other items show default styling |

### Test Steps - Sidebar Collapse (Desktop)

| Step | Action | Expected Result |
|------|--------|-----------------|
| 8 | **Test Sidebar Collapse** | |
| 8.1 | Verify sidebar toggle button in AppBar | ChevronLeft icon visible in AppBar (sidebar expanded) |
| 8.2 | Click sidebar toggle button | Sidebar collapses to icon-only mode (56px width) |
| 8.3 | Verify icons only visible | Only icons visible, text labels hidden |
| 8.4 | Verify tooltips on hover | Tooltips appear on hover for each icon |
| 8.5 | Verify accordions collapsed | Admin and Client accordions auto-collapsed |
| 8.6 | Click sidebar toggle button again | Sidebar expands to full width (240px) |
| 8.7 | Verify text labels visible | Text labels visible again |
| 8.8 | Refresh page | Sidebar state persists (from localStorage) |

### Expected Results - Sidebar Collapse

| Category | Expected Outcome |
|----------|------------------|
| **Collapse Functionality** | - Sidebar collapses to 56px width (icon-only mode)<br>- Text labels hidden when collapsed<br>- Tooltips appear on hover for icons<br>- Accordions auto-collapse when sidebar collapses<br>- State persists to localStorage |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Sidebar visible and properly structured | ✓ | ✗ |
| Permission gating works correctly | ✓ | ✗ |
| Admin accordion auto-expands on admin routes | ✓ | ✗ |
| Client accordion auto-expands on client routes | ✓ | ✗ |
| Manual accordion toggle works | ✓ | ✗ |
| Active state highlighting works | ✓ | ✗ |
| Sidebar collapse/expand works | ✓ | ✗ |
| Tooltips appear on collapsed sidebar | ✓ | ✗ |
| State persists across page refresh | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 2: Mobile Drawer

### Test Case ID
TC-NAV-MOBILE-002

### Description
Verify that sidebar converts to temporary drawer on mobile devices (<600px), with proper toggle behavior and auto-close on navigation.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Lab Technician (or any authenticated user) |
| **User Logged In** | User successfully authenticated |
| **Browser** | Mobile viewport (<600px width) or browser DevTools mobile emulation |
| **Viewport Width** | <600px (sm breakpoint) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Lab Technician | User authenticated, dashboard loads |
| 2 | **Resize Browser to Mobile** | |
| 2.1 | Resize browser window to <600px width | Viewport width <600px |
| 2.2 | Verify sidebar hidden by default | Sidebar drawer NOT visible (closed) |
| 2.3 | Verify hamburger icon in AppBar | Hamburger menu icon (☰) visible in AppBar |
| 2.4 | Verify user info text hidden | User info text hidden (only logout icon visible) |
| 3 | **Test Drawer Open/Close** | |
| 3.1 | Click hamburger icon | Sidebar drawer opens as overlay |
| 3.2 | Verify drawer full-screen width | Drawer takes full screen width |
| 3.3 | Verify overlay backdrop | Dark overlay appears behind drawer |
| 3.4 | Verify navigation items visible | All navigation items visible in drawer |
| 3.5 | Click overlay backdrop | Drawer closes |
| 3.6 | Click hamburger icon again | Drawer opens |
| 3.7 | Click hamburger icon again | Drawer closes |
| 4 | **Test Auto-Close on Navigation** | |
| 4.1 | Open drawer (click hamburger) | Drawer opens |
| 4.2 | Click "Accessioning" navigation item | Route changes to `/accessioning` |
| 4.3 | Verify drawer auto-closes | Drawer closes automatically after navigation |
| 4.4 | Verify page content loads | Accessioning page loads correctly |
| 4.5 | Open drawer again | Drawer opens |
| 4.6 | Click "Dashboard" navigation item | Route changes to `/dashboard` |
| 4.7 | Verify drawer auto-closes | Drawer closes automatically |
| 5 | **Test Accordion in Mobile Drawer** | |
| 5.1 | Log in as Administrator | User authenticated |
| 5.2 | Resize to mobile viewport | Viewport <600px |
| 5.3 | Open drawer | Drawer opens |
| 5.4 | Verify Admin accordion visible | Admin accordion visible in drawer |
| 5.5 | Click Admin accordion header | Accordion expands |
| 5.6 | Verify sub-items visible | Admin sub-items visible (Overview, Lists, etc.) |
| 5.7 | Click "Lists Management" | Route changes to `/admin/lists` |
| 5.8 | Verify drawer auto-closes | Drawer closes automatically |
| 6 | **Test Responsive Breakpoint** | |
| 6.1 | Resize browser from mobile (<600px) to desktop (≥600px) | Viewport width ≥600px |
| 6.2 | Verify sidebar converts to permanent drawer | Sidebar becomes permanent drawer (always visible) |
| 6.3 | Verify hamburger icon hidden | Hamburger icon NOT visible (desktop toggle visible instead) |
| 6.4 | Resize browser from desktop (≥600px) to mobile (<600px) | Viewport width <600px |
| 6.5 | Verify sidebar converts to temporary drawer | Sidebar becomes temporary drawer (hidden by default) |
| 6.6 | Verify hamburger icon visible | Hamburger icon visible in AppBar |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Mobile Drawer** | - Sidebar hidden by default on mobile (<600px)<br>- Hamburger icon visible in AppBar<br>- Drawer opens as overlay when hamburger clicked<br>- Drawer takes full screen width<br>- Dark backdrop overlay appears |
| **Toggle Behavior** | - Drawer opens/closes on hamburger click<br>- Drawer closes on backdrop click<br>- Drawer auto-closes after navigation |
| **Navigation** | - Navigation items clickable in drawer<br>- Route changes correctly<br>- Drawer closes automatically after navigation<br>- Page content loads correctly |
| **Accordion in Drawer** | - Accordions work in mobile drawer<br>- Expand/collapse functionality works<br>- Sub-items accessible |
| **Responsive Breakpoint** | - Sidebar converts between permanent (desktop) and temporary (mobile) at 600px breakpoint<br>- UI elements show/hide based on breakpoint |

### Test Steps - Layout Integrity

| Step | Action | Expected Result |
|------|--------|-----------------|
| 7 | **Test Layout Integrity** | |
| 7.1 | Resize browser window gradually | Viewport width changes |
| 7.2 | Verify no layout breaks | No horizontal scrolling, no content overflow |
| 7.3 | Verify content adapts | Content adapts to viewport width |
| 7.4 | Verify AppBar responsive | AppBar adapts to viewport (hamburger on mobile, toggle on desktop) |

### Expected Results - Layout Integrity

| Category | Expected Outcome |
|----------|------------------|
| **Layout** | - No layout breaks during resize<br>- No horizontal scrolling<br>- Content adapts smoothly<br>- AppBar responsive elements show/hide correctly |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Sidebar hidden by default on mobile | ✓ | ✗ |
| Hamburger icon visible on mobile | ✓ | ✗ |
| Drawer opens as overlay | ✓ | ✗ |
| Drawer auto-closes on navigation | ✓ | ✗ |
| Accordion works in mobile drawer | ✓ | ✗ |
| Responsive breakpoint works (600px) | ✓ | ✗ |
| No layout breaks during resize | ✓ | ✗ |
| Content adapts to viewport | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Test Case 3: Accessibility - Keyboard Navigation and ARIA

### Test Case ID
TC-NAV-ACCESSIBILITY-003

### Description
Verify that navigation is accessible via keyboard navigation, has proper ARIA labels, and supports screen readers.

### Preconditions

| Item | Value |
|------|-------|
| **User Role** | Administrator (or any authenticated user) |
| **User Logged In** | User successfully authenticated |
| **Browser** | Desktop viewport (≥600px width) |
| **Keyboard** | Physical keyboard available (for keyboard navigation test) |
| **Screen Reader** | Optional (for ARIA verification) |

### Test Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Log in as Administrator | User authenticated, dashboard loads |
| 2 | **Test Keyboard Navigation** | |
| 2.1 | Press Tab key | Focus moves to first interactive element (Logo or Dashboard link) |
| 2.2 | Continue pressing Tab | Focus moves through navigation items in order |
| 2.3 | Verify focus visible | Focus indicator visible (outline or highlight) |
| 2.4 | Press Enter on focused navigation item | Route changes to selected page |
| 2.5 | Press Tab to navigate to Admin accordion | Focus moves to Admin accordion header |
| 2.6 | Press Enter on Admin accordion | Accordion expands/collapses |
| 2.7 | Press Tab after accordion expands | Focus moves to first sub-item in accordion |
| 2.8 | Press Escape key | Accordion collapses (if supported) |
| 3 | **Test ARIA Labels** | |
| 3.1 | Inspect navigation elements (browser DevTools) | ARIA attributes present |
| 3.2 | Verify main navigation ARIA label | `aria-label="main navigation"` on sidebar container |
| 3.3 | Verify navigation item ARIA labels | Each navigation item has `aria-label` (e.g., "Navigate to Dashboard") |
| 3.4 | Verify active item ARIA current | Active item has `aria-current="page"` |
| 3.5 | Verify accordion ARIA attributes | Accordion has:<br>- `aria-label="Admin section"` or `aria-label="Client section"`<br>- `aria-controls` pointing to content<br>- `aria-expanded` (true/false) |
| 3.6 | Verify admin sub-navigation ARIA label | Admin sub-items have `aria-label="admin navigation"` |
| 4 | **Test Sidebar Toggle ARIA** | |
| 4.1 | Locate sidebar toggle button in AppBar | Toggle button visible |
| 4.2 | Verify ARIA label | Toggle button has `aria-label="Collapse sidebar"` or `aria-label="Expand sidebar"` |
| 4.3 | Press Tab to focus toggle button | Focus moves to toggle button |
| 4.4 | Press Enter | Sidebar collapses/expands |
| 5 | **Test Mobile Menu Toggle ARIA** | |
| 5.1 | Resize browser to mobile (<600px) | Viewport <600px |
| 5.2 | Locate hamburger menu button | Hamburger icon visible |
| 5.3 | Verify ARIA label | Hamburger button has `aria-label="open drawer"` |
| 5.4 | Press Tab to focus hamburger | Focus moves to hamburger button |
| 5.5 | Press Enter | Drawer opens |
| 6 | **Test Logo ARIA** | |
| 6.1 | Locate Logo component in sidebar | Logo visible |
| 6.2 | Verify ARIA label | Logo has `aria-label="Navigate to dashboard"` |
| 6.3 | Press Tab to focus Logo | Focus moves to Logo |
| 6.4 | Press Enter | Navigates to `/dashboard` |
| 7 | **Test Focus Management** | |
| 7.1 | Navigate to `/admin/lists` | Lists Management page loads |
| 7.2 | Verify focus management | Focus moves to page content (not stuck in navigation) |
| 7.3 | Press Tab | Focus moves through page content elements |
| 8 | **Test Screen Reader Announcements** (if screen reader available) | |
| 8.1 | Enable screen reader | Screen reader active |
| 8.2 | Navigate with Tab key | Screen reader announces navigation items |
| 8.3 | Navigate to accordion | Screen reader announces accordion state (expanded/collapsed) |
| 8.4 | Navigate to active item | Screen reader announces "current page" or similar |

### Expected Results

| Category | Expected Outcome |
|----------|------------------|
| **Keyboard Navigation** | - Tab key moves focus through navigation items<br>- Enter key activates focused item<br>- Focus indicator visible<br>- Focus order follows visual flow<br>- Escape key closes accordions (if supported) |
| **ARIA Labels** | - Main navigation: `aria-label="main navigation"`<br>- Navigation items: `aria-label="Navigate to [page]"`<br>- Active items: `aria-current="page"`<br>- Accordions: `aria-label="[Section] section"`, `aria-controls`, `aria-expanded`<br>- Sub-navigation: `aria-label="admin navigation"` or `aria-label="client navigation"` |
| **Toggle Buttons** | - Sidebar toggle: `aria-label="Collapse sidebar"` / `aria-label="Expand sidebar"`<br>- Mobile menu toggle: `aria-label="open drawer"` |
| **Logo** | - Logo: `aria-label="Navigate to dashboard"` |
| **Focus Management** | - Focus moves correctly through navigation<br>- Focus moves to page content after navigation<br>- No focus traps |
| **Screen Reader Support** | - Screen reader announces navigation items<br>- Screen reader announces accordion state<br>- Screen reader announces active page |

### Test Steps - Tab Order

| Step | Action | Expected Result |
|------|--------|-----------------|
| 9 | **Test Tab Order** | |
| 9.1 | Press Tab from page start | Focus moves to Logo |
| 9.2 | Continue pressing Tab | Focus moves through: Logo → Dashboard → Accessioning → Samples → ... → Help → Admin accordion → (if expanded) Admin items → Sidebar toggle → Page content |
| 9.3 | Verify logical order | Tab order follows visual flow (top to bottom, left to right) |

### Expected Results - Tab Order

| Category | Expected Outcome |
|----------|------------------|
| **Tab Order** | - Tab order follows visual flow<br>- Logo first, then navigation items, then accordions, then page content<br>- Logical and predictable order |

### Pass/Fail Criteria

| Criteria | Pass | Fail |
|----------|------|------|
| Keyboard navigation works (Tab, Enter) | ✓ | ✗ |
| Focus indicator visible | ✓ | ✗ |
| ARIA labels present and correct | ✓ | ✗ |
| Active item has aria-current | ✓ | ✗ |
| Accordion ARIA attributes correct | ✓ | ✗ |
| Toggle buttons have ARIA labels | ✓ | ✗ |
| Logo has ARIA label | ✓ | ✗ |
| Focus management works correctly | ✓ | ✗ |
| Tab order follows visual flow | ✓ | ✗ |
| Screen reader support (if tested) | ✓ | ✗ |

### Test Result
- [ ] **PASS** - All criteria met
- [ ] **FAIL** - One or more criteria not met

**Notes**: _________________________________________________________

---

## Reference Documentation

### Navigation Document (navigation.md)
- **Unified Sidebar Navigation**: Persistent left sidebar (240px expanded, 56px collapsed)
- **Layout**: Permanent drawer on desktop (≥600px), temporary drawer on mobile (<600px)
- **Permission Gating**: Menu items shown/hidden based on user permissions
- **Accordion Behavior**: Auto-expands on route navigation, manual toggle available
- **Responsive Breakpoints**: Mobile <600px, Desktop ≥600px
- **ARIA Labels**: Navigation items, accordions, toggle buttons have proper ARIA attributes

### UI Document (ui-accessioning-to-reporting.md)
- **Responsive Design**: Material-UI Grid System breakpoints (xs: <600px, sm: 600-960px, md: 960-1280px, lg: >1280px)
- **Layout Adaptations**: Forms adapt to viewport (2-column desktop, 1-column mobile)
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support
- **Keyboard Navigation**: Tab order follows visual flow, Enter submits, Escape closes dialogs

### PRD Section 6.3 Usability
- **Accessibility**: WCAG 2.1 compliant
- **React UI**: Intuitive forms with real-time validation
- **User Experience**: Focus on usability and accessibility

### Component Architecture
- **Sidebar Component** (`frontend/src/components/Sidebar.tsx`):
  - Permission-based item filtering
  - Active state detection (exact and prefix matching)
  - Responsive drawer variants (permanent/temporary)
  - Collapsible on desktop (icon-only mode with tooltips)
  - Accordions for Client and Admin sections
  - Auto-expand accordions on navigation
- **MainLayout Component** (`frontend/src/layouts/MainLayout.tsx`):
  - Unified layout wrapper for all routes
  - Top AppBar with dynamic title
  - Mobile drawer toggle
  - Desktop sidebar collapse toggle (with localStorage persistence)
  - Back button for nested routes
  - Responsive content area offset

### Breakpoints
- **Mobile**: <600px (sm breakpoint)
  - Temporary drawer with overlay
  - Hamburger menu toggle
  - User info text hidden
- **Desktop**: ≥600px
  - Permanent drawer always visible
  - Sidebar collapse toggle
  - Full user info displayed

### ARIA Accessibility
- **Navigation**: `aria-label="main navigation"` on sidebar container
- **Navigation Items**: `aria-label="Navigate to [page]"` on each item
- **Active Items**: `aria-current="page"` on current page item
- **Accordions**: `aria-label="[Section] section"`, `aria-controls`, `aria-expanded`
- **Toggle Buttons**: `aria-label="Collapse sidebar"` / `aria-label="Expand sidebar"`, `aria-label="open drawer"`
- **Logo**: `aria-label="Navigate to dashboard"`

### Permission-Based Navigation
- **Core Features**: Permission-gated (e.g., `sample:create` for Accessioning)
- **Admin Section**: Requires `config:edit` permission
- **Client Section**: Requires `project:manage` permission
- **Help**: Always visible (no permission required)

### Auto-Expand Behavior
- **Admin Accordion**: Auto-expands when navigating to `/admin/*` routes
- **Client Accordion**: Auto-expands when navigating to `/clients` or `/client-projects` routes
- **Auto-Collapse**: Accordions collapse when navigating away from related routes

### Sidebar Collapse (Desktop)
- **Collapsed State**: 56px width, icons only, tooltips on hover
- **Expanded State**: 240px width, full text labels
- **Persistence**: State saved to localStorage
- **Accordion Behavior**: Accordions auto-collapse when sidebar collapses

### Mobile Drawer
- **Temporary Drawer**: Overlay with backdrop
- **Full-Screen Width**: Drawer takes full screen width on mobile
- **Auto-Close**: Drawer closes automatically after navigation
- **Toggle**: Hamburger icon in AppBar

---

## Test Execution Log

| Test Case | Tester | Date | Result | Notes |
|-----------|--------|------|--------|-------|
| TC-NAV-SIDEBAR-001 | | | | |
| TC-NAV-MOBILE-002 | | | | |
| TC-NAV-ACCESSIBILITY-003 | | | | |

---

## Appendix: Browser Testing

### Recommended Browsers
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

### Viewport Sizes for Testing
- **Mobile**: 375px, 414px, 480px
- **Tablet**: 768px, 1024px
- **Desktop**: 1280px, 1920px

### Keyboard Navigation Keys
- **Tab**: Move focus forward
- **Shift+Tab**: Move focus backward
- **Enter**: Activate focused element
- **Escape**: Close dialogs/accordions
- **Arrow Keys**: Navigate dropdowns/selects

### Screen Reader Testing
- **Windows**: NVDA (free), JAWS (commercial)
- **macOS**: VoiceOver (built-in)
- **Browser Extensions**: Screen reader simulation tools


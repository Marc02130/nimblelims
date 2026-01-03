# Site Navigation Documentation

## Overview

NimbleLIMS uses a unified sidebar navigation system that provides consistent navigation across all application routes. The sidebar is a persistent left-side drawer that contains all navigation items, organized into sections with collapsible accordions for submenus (e.g., Admin section).

Navigation is permission-based, with menu items and routes dynamically shown/hidden based on user roles and permissions.

## 1. Unified Sidebar Navigation

### Location
- Component: `frontend/src/components/Sidebar.tsx`
- Layout Component: `frontend/src/layouts/MainLayout.tsx`
- Display: Persistent left sidebar (240px width expanded, 56px collapsed) on all authenticated routes
- Layout: Permanent drawer on desktop (≥600px), temporary drawer on mobile (<600px)
- Collapsible: Desktop sidebar can be collapsed to icon-only mode (56px width) with tooltips

### Structure

```
┌─────────────┐
│ [Logo]      │ ← Clickable, navigates to /dashboard
│ NimbleLIMS  │
├─────────────┤
│ Core        │
│ Features    │
├─────────────┤
│ Dashboard   │
│ Accessioning│
│ Containers  │
│ Batches     │
│ Results     │
│ Help        │
├─────────────┤
│ ▼ Client    │ ← Accordion (collapsible, requires project:manage)
│   Clients   │
│   Client    │
│   Projects  │
├─────────────┤
│ ▼ Admin     │ ← Accordion (collapsible)
│   Overview  │
│   Lists     │
│   Container │
│     Types   │
│   Users     │
│   Roles     │
│   Analyses  │
│   Analytes  │
│   Batteries │
│   Help      │
│     Management│
├─────────────┤
│ testuser    │
│ (Lab Tech)  │
└─────────────┘
```

### Navigation Sections

#### Core Features Section
All items are permission-gated and only visible to users with the required permissions:

| Menu Item | Route | Icon | Permission Required | Description |
|-----------|-------|------|---------------------|-------------|
| **Dashboard** | `/dashboard` | Dashboard | Always visible | Main dashboard with sample overview and statistics |
| **Accessioning** | `/accessioning` | Science | `sample:create` | Sample accessioning form for receiving new samples |
| **Containers** | `/containers` | Inventory | `sample:update` | Container management interface |
| **Batches** | `/batches` | ViewList | `batch:manage` | Batch creation and management |
| **Results** | `/results` | Assessment | `result:enter` | Results entry interface |
| **Help** | `/help` | Help | Always visible | Role-filtered help content and documentation |

#### Client Section (Accordion)
The Client section uses a Material-UI Accordion component for collapsible submenu functionality. It is only visible to users with `project:manage` permission.

**Accordion Behavior:**
- Auto-expands when user navigates to any `/clients` or `/client-projects` route
- Can be manually collapsed/expanded by clicking the accordion header
- Shows active state (primary color icon) when on any client route
- Contains client-related sub-items in a nested list structure

| Menu Item | Route | Icon | Description |
|-----------|-------|------|-------------|
| **Clients** | `/clients` | People | Client (organization) management (CRUD) |
| **Client Projects** | `/client-projects` | ViewList | Client project management (CRUD) |

#### Admin Section (Accordion)
The Admin section uses a Material-UI Accordion component for collapsible submenu functionality. It is only visible to users with `config:edit` permission.

**Accordion Behavior:**
- Auto-expands when user navigates to any `/admin/*` route
- Can be manually collapsed/expanded by clicking the accordion header
- Shows active state (primary color icon) when on any admin route
- Contains all admin sub-items in a nested list structure

| Menu Item | Route | Icon | Description |
|-----------|-------|------|-------------|
| **Overview** | `/admin` | DashboardIcon | Admin dashboard with statistics |
| **Lists Management** | `/admin/lists` | ViewList | Manage configurable lists and entries |
| **Container Types** | `/admin/container-types` | Inventory | Manage container type definitions |
| **Users Management** | `/admin/users` | People | User CRUD operations |
| **Roles & Permissions** | `/admin/roles` | Security | Role and permission management |
| **Analyses Management** | `/admin/analyses` | Science | Test analysis configuration |
| **Analytes Management** | `/admin/analytes` | Biotech | Analyte definitions |
| **Test Batteries** | `/admin/test-batteries` | BatteryChargingFull | Test battery configuration |
| **Custom Fields** | `/admin/custom-fields` | Tune | Manage custom attribute configurations (Post-MVP) |
| **Help Management** | `/admin/help` | Help | Manage help entries (CRUD) - requires `config:edit` permission |

### Visual States

- **Active State**: Current page highlighted with Material-UI `selected` prop and primary color icon
- **Inactive State**: Default styling
- **Hidden**: Menu items not shown if user lacks required permission
- **Accordion Expanded**: Admin section expands automatically when on admin routes
- **Accordion Collapsed**: Admin section can be manually collapsed when not needed

### User Info Section

Located at the bottom of the sidebar:
- **Display**: `{username} ({role})` (read-only, non-clickable)
- **Styling**: Secondary text color, medium font weight
- **Note**: Logout functionality is handled in the top AppBar

## 2. Top AppBar

### Location
- Component: `frontend/src/layouts/MainLayout.tsx`
- Display: Fixed at top of all authenticated pages
- Layout: Horizontal toolbar with title, navigation controls, and user actions

### Structure

```
┌─────────────────────────────────────────────────────────────┐
│ [☰] [←] Dashboard                    testuser (Lab Tech) [🚪]│
└─────────────────────────────────────────────────────────────┘
```

### AppBar Components

- **Mobile Menu Toggle** (hamburger icon): Visible only on mobile (<600px), toggles sidebar drawer
- **Desktop Sidebar Toggle** (ChevronLeft/ChevronRight): Visible only on desktop (≥600px), toggles sidebar collapsed state
  - ChevronLeft icon when expanded (collapses sidebar to icon-only mode)
  - ChevronRight icon when collapsed (expands sidebar to full width)
  - ARIA labels: "Collapse sidebar" / "Expand sidebar"
  - State persists to localStorage
- **Back Button** (arrow icon): Visible only for nested routes (e.g., `/admin/analyses/:id/analytes`), navigates to parent route
- **Page Title**: Dynamically set based on current route (e.g., "Dashboard", "Admin Dashboard", "Lists Management", "Clients")
- **User Info**: `{username} ({role})` - visible on desktop, hidden on mobile
- **Logout Button**: Logout icon button, calls logout function and navigates to `/login`

### Dynamic Title Mapping

The AppBar title is automatically determined from the current route:

| Route | Title |
|-------|-------|
| `/dashboard` | Dashboard |
| `/accessioning` | Accessioning |
| `/containers` | Containers |
| `/batches` | Batches |
| `/results` | Results |
| `/clients` | Clients |
| `/client-projects` | Client Projects |
| `/help` | Help |
| `/admin` | Admin Dashboard |
| `/admin/lists` | Lists Management |
| `/admin/container-types` | Container Types |
| `/admin/users` | Users Management |
| `/admin/roles` | Roles & Permissions |
| `/admin/analyses` | Analyses Management |
| `/admin/analyses/:id/analytes` | Analysis Analytes Configuration |
| `/admin/analytes` | Analytes Management |
| `/admin/test-batteries` | Test Batteries |
| `/admin/help` | Help Management |
| Unknown routes | NimbleLIMS (default) |

## 3. Route Structure

### All Routes Use Unified Layout

All authenticated routes use the `MainLayout` component, which provides the unified sidebar and top AppBar:

| Route | Component | Layout |
|-------|-----------|--------|
| `/` | Redirect to `/dashboard` | MainLayout |
| `/dashboard` | Dashboard | MainLayout |
| `/accessioning` | AccessioningForm | MainLayout |
| `/containers` | ContainerManagement | MainLayout |
| `/batches` | BatchManagement | MainLayout |
| `/results` | ResultsManagement | MainLayout |
| `/clients` | ClientsManagement | MainLayout |
| `/client-projects` | ClientProjects | MainLayout |
| `/help` | HelpPage | MainLayout |
| `/admin` | AdminOverview | MainLayout |
| `/admin/lists` | ListsManagement | MainLayout |
| `/admin/container-types` | ContainerTypesManagement | MainLayout |
| `/admin/users` | UsersManagement | MainLayout |
| `/admin/roles` | RolesManagement | MainLayout |
| `/admin/analyses` | AnalysesManagement | MainLayout |
| `/admin/analyses/:analysisId/analytes` | AnalysisAnalytesConfig | MainLayout |
| `/admin/analytes` | AnalytesManagement | MainLayout |
| `/admin/test-batteries` | TestBatteriesManagement | MainLayout |
| `/admin/help` | HelpManagement | MainLayout |

### Route Protection

- **Authentication**: All routes require user authentication (redirects to `/login` if not authenticated)
- **Permission-Based Routes**: Routes check permissions and redirect to `/dashboard` if unauthorized
  - Admin routes require `config:edit` or specific permissions (e.g., `user:manage` for users/roles)
  - Core feature routes require respective permissions (e.g., `sample:create` for accessioning)
- **Permission-Based Visibility**: Sidebar items hidden if user lacks required permission

## 4. Permission-Based Navigation

### Permission Checks

Navigation visibility is controlled by the `hasPermission()` function from `UserContext`:

```typescript
hasPermission('sample:create')  // Accessioning menu
hasPermission('sample:update')  // Containers menu
hasPermission('batch:manage')   // Batches menu
hasPermission('result:enter')   // Results menu
hasPermission('project:manage') // Client section (accordion) - includes Clients and Client Projects
hasPermission('config:edit')    // Admin section (accordion)
// Help menu: No permission required - always visible to all users
```

### Role-Based Access

| Role | Visible Sidebar Items | Admin Access |
|------|---------------------|--------------|
| **Administrator** | All items (including Help) | Full access (accordion visible, including Help Management) |
| **Lab Manager** | Dashboard, Batches, Results, Help | No access (accordion hidden) |
| **Lab Technician** | Dashboard, Accessioning, Containers, Batches, Results, Help | No access (accordion hidden) |
| **Client** | Dashboard, Help (read-only) | No access (accordion hidden) |

### Edge Cases

- **No Permissions**: If user has no permissions for core items, Dashboard is still visible, and a "No items available" message may appear
- **Administrator Role**: Administrators see all items regardless of permissions array (role check takes precedence)
- **Missing User**: Layout handles missing user gracefully, showing basic structure

## 5. Navigation Patterns

### Programmatic Navigation

Uses React Router's `useNavigate()` hook:

```typescript
const navigate = useNavigate();
navigate('/dashboard');
navigate('/admin/lists');
```

### Active Route Detection

Uses `useLocation()` to detect current route with exact and prefix matching:

```typescript
const location = useLocation();
// Exact match for Dashboard and Admin Overview
const isActive = location.pathname === '/dashboard';
// Prefix match for other routes
const isActive = location.pathname.startsWith('/admin/lists');
```

### Navigation from Components

- **Logo click**: Navigates to `/dashboard`
- **Sidebar item clicks**: Navigate to respective routes
- **Accordion expansion**: Auto-expands when navigating to admin routes
- **Mobile drawer**: Auto-closes after navigation on mobile devices
- **Back button**: Navigates to parent route for nested routes

## 6. User Context Integration

Navigation relies on `UserContext` for:
- **User information**: Username, role, permissions
- **Permission checks**: `hasPermission(permission)`
- **Logout functionality**: `logout()` function (called from AppBar)
- **Loading state**: Prevents navigation during auth check

## 7. Responsive Design

### Breakpoints

- **Mobile**: < 600px (sm breakpoint)
- **Desktop**: ≥ 600px

### Mobile Adaptations

- **Sidebar**: Converts to temporary drawer with overlay
- **Drawer Toggle**: Hamburger icon appears in AppBar on mobile
- **User Info**: Text hidden on mobile (only logout icon visible)
- **Auto-Close**: Sidebar drawer closes automatically after navigation on mobile
- **Full-Screen**: Temporary drawer takes full screen width on mobile

### Desktop Adaptations

- **Sidebar**: Permanent drawer always visible (240px width expanded, 56px collapsed)
- **Collapsible Sidebar**: Toggle button in AppBar allows collapsing to icon-only mode
  - Collapsed state: 56px width, icons only with tooltips on hover
  - Expanded state: 240px width, full text labels
  - State persists to localStorage across sessions
  - Accordions auto-collapse when sidebar is collapsed
  - Accordions auto-expand on item click if sidebar is collapsed
- **Content Offset**: Main content area offset by sidebar width (adjusts dynamically)
- **User Info**: Full username and role displayed in AppBar
- **Toggle Button**: ChevronLeft/ChevronRight icon in AppBar for sidebar collapse/expand

## 8. Navigation Flow Examples

### Accessing Core Features

1. User clicks "Accessioning" in sidebar (requires `sample:create`)
2. Route changes to `/accessioning`
3. Sidebar highlights "Accessioning" as active
4. AppBar title updates to "Accessioning"
5. AccessioningForm component renders in main content area

### Accessing Admin Section

1. User clicks "Admin" accordion header in sidebar (requires `config:edit`)
2. Accordion expands (if collapsed) or remains expanded
3. User clicks "Overview" sub-item
4. Route changes to `/admin`
5. Sidebar highlights "Overview" as active
6. AppBar title updates to "Admin Dashboard"
7. AdminOverview component renders in main content area

### Accessing Nested Admin Routes

1. User in Admin section clicks "Analyses Management"
2. Route changes to `/admin/analyses`
3. Sidebar highlights "Analyses Management" as active (prefix match)
4. AppBar title updates to "Analyses Management"
5. AnalysesManagement component renders in main content area

### Accessing Deeply Nested Routes

1. User clicks "Analyses Management" in admin accordion
2. Route changes to `/admin/analyses`
3. User clicks "Configure Analytes" action on an analysis
4. Route changes to `/admin/analyses/:id/analytes`
5. AppBar shows back button (←) for nested route
6. AppBar title updates to "Analysis Analytes Configuration"
7. Sidebar still highlights "Analyses Management" (parent route)
8. AnalysisAnalytesConfig component renders in main content area
9. User clicks back button to return to `/admin/analyses`

### Mobile Navigation

1. User on mobile device sees hamburger icon in AppBar
2. User clicks hamburger icon
3. Sidebar drawer opens as overlay
4. User clicks navigation item
5. Route changes and drawer auto-closes
6. Content updates in main area

## 9. Logo Component

- **Location**: `frontend/src/components/Logo.tsx`
- **Usage**: Displayed in sidebar header (clickable, navigates to `/dashboard`)
- **Styling**: Customizable via `sx` prop (fontSize, margin, etc.)
- **Accessibility**: Has `aria-label="Navigate to dashboard"`

## 10. Refinements: Unified Sidebar Architecture

### Shift from Dual Navigation

The navigation system was refactored from a dual approach (top Navbar + separate Admin Sidebar) to a unified sidebar architecture. This change provides:

**Benefits:**
- **Consistency**: Single navigation pattern across all routes eliminates layout switching
- **Space Efficiency**: Sidebar uses vertical space more effectively than horizontal navbar
- **Scalability**: Easy to add new sections or submenus without cluttering the interface
- **Mobile-Friendly**: Drawer pattern works better on mobile devices than horizontal navigation
- **Visual Hierarchy**: Clear organization with sections and collapsible accordions

**Implementation Details:**
- All routes now use `MainLayout` component
- Sidebar is always present (hidden on mobile until toggled)
- Top AppBar provides context (page title, back button, user actions)
- No layout switching between admin and non-admin sections

### Accordion Usage for Admin Section

The Admin section uses Material-UI's Accordion component to provide collapsible submenu functionality:

**Features:**
- **Auto-Expansion**: Accordion automatically expands when user navigates to any `/admin/*` route
- **Manual Toggle**: Users can collapse/expand the accordion by clicking the header
- **Active State**: Admin icon shows primary color when on any admin route
- **Nested Structure**: Admin sub-items are indented (pl: 4) to show hierarchy
- **Accessibility**: Proper ARIA labels for screen readers

**Technical Implementation:**
```typescript
<Accordion
  expanded={adminExpanded}
  onChange={(_, expanded) => setAdminExpanded(expanded)}
>
  <AccordionSummary expandIcon={<ExpandMore />}>
    <SettingsIcon color={isAdminRoute ? 'primary' : 'inherit'} />
    <Typography>Admin</Typography>
  </AccordionSummary>
  <AccordionDetails>
    <List>
      {/* Admin sub-items */}
    </List>
  </AccordionDetails>
</Accordion>
```

### Future Enhancements

Potential navigation improvements for future iterations:

- **Breadcrumb Navigation**: Show breadcrumb trail for deep nested routes (e.g., Admin > Analyses > Analysis Details > Analytes)
- **Quick Search/Command Palette**: Keyboard shortcut (Cmd/Ctrl+K) to open command palette for quick navigation
- **Recent Pages History**: Show recently visited pages in sidebar or quick access menu
- **Keyboard Shortcuts**: Navigate using keyboard shortcuts (e.g., `g d` for dashboard, `g a` for admin)
- **Collapsible Core Sections**: Allow collapsing core features section for users who primarily use one feature (partially implemented via sidebar collapse)
- **Customizable Sidebar**: Allow users to pin/favorite frequently used items
- **Contextual Navigation**: Show related items based on current page context
- **Search Within Navigation**: Filter navigation items by search term

## 11. Component Architecture

### Sidebar Component (`frontend/src/components/Sidebar.tsx`)

**Props:**
- `mobileOpen: boolean` - Controls mobile drawer visibility
- `onMobileClose: () => void` - Callback to close mobile drawer
- `collapsed?: boolean` - Controls desktop sidebar collapsed state (default: false)

**Features:**
- Permission-based item filtering
- Active state detection (exact and prefix matching)
- Responsive drawer variants (permanent/temporary)
- Collapsible on desktop (icon-only mode with tooltips)
- Accordions for Client and Admin sections
- Auto-expand accordions on navigation when collapsed
- User info display at bottom (hidden when collapsed)

### MainLayout Component (`frontend/src/layouts/MainLayout.tsx`)

**Props:**
- `children: React.ReactNode` - Page content to render

**Features:**
- Unified layout wrapper for all routes
- Top AppBar with dynamic title
- Mobile drawer toggle
- Desktop sidebar collapse toggle (with localStorage persistence)
- Back button for nested routes
- Logout functionality
- Responsive content area offset (adjusts for collapsed sidebar)

### Integration

Both components work together:
- `MainLayout` manages sidebar state and provides layout structure
- `Sidebar` handles navigation rendering and permission checks
- Both use `UserContext` for user information and permissions
- Both use React Router hooks for navigation and location

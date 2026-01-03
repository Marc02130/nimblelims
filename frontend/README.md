# NimbleLIMS Frontend

React frontend for the NimbleLIMS Laboratory Information Management System (LIMS) MVP.

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

Copyright (c) 2025 Marc Breneiser

## Features

### Sample Accessioning (US-1, US-24)
- Multi-step wizard for sample entry
- **Bulk Mode**: Toggle for bulk accessioning with common fields and unique per-sample data
- Required fields: due_date, received_date, sample_type, status, matrix, temperature
- Container specification: Select pre-setup container type, create instance dynamically
- Optional double-entry validation for key fields
- Test assignment during accessioning (individual analyses or test batteries)
- Container assignment with concentration/amount tracking
- Client project selection for grouping multiple projects

### Container Management (US-5)
- Create and manage hierarchical containers
- Container types pre-setup by administrators
- Dynamic container instance creation during workflows
- Support for different container types (tube, plate, well, rack)
- Contents linking with concentration/amount/units
- Pooled samples support with calculations

### Admin Configuration (US-15, US-16)
- **Container Types Management**: CRUD operations for container types
- **Lists Management**: Full CRUD for lists and list entries
- **Analyses Management**: CRUD operations for analyses (methods, turnaround times, costs)
- **Analytes Management**: CRUD operations for analytes
- **Analysis-Analyte Configuration**: Configure validation rules (data types, ranges, significant figures)
- **Test Batteries Management**: Create and manage test batteries (grouped analyses with sequence and optional flags)
- **Custom Fields Management** (Post-MVP): Define and manage custom attributes for samples, tests, results, projects, client_projects, and batches
- **Users Management**: CRUD operations for users
- **Roles & Permissions Management**: CRUD operations for roles and permission assignments
- Restricted to users with `config:edit`, `test:configure`, or `user:manage` permissions
- Enables system customization without code changes

### Test Assignment (US-7)
- Assign individual analyses or test batteries to samples during accessioning
- Test batteries automatically create sequenced tests for all analyses in the battery
- Test instances with status tracking
- Integration with sample lifecycle

### Batch Management (US-11, US-26, US-27)
- Create batches with container tracking
- **Cross-Project Batching**: Select containers from multiple projects with compatibility validation
- **QC at Batch Creation**: Automatically generate QC samples when creating batches
- Batch status management (Created → In Process → Completed)
- Batch validation endpoint for pre-checking compatibility

### Results Entry (US-9, US-28)
- **Batch Results Entry**: Tabular interface for entering results for multiple tests/samples
- Real-time validation (data type, range, required fields)
- QC sample indicators and validation
- Auto-update test and batch statuses on completion
- Configurable QC blocking behavior

### Dashboard
- Role-based views (client sees own projects)
- Sample listing with filtering by status/project
- Summary statistics
- Real-time status updates

## Technical Implementation

### Architecture
- **React 18** with TypeScript
- **Material-UI** for components and theming
- **Formik + Yup** for form management and validation
- **React Router** for navigation
- **Axios** for API communication
- **Jest + Testing Library** for testing
- **Unified Sidebar Navigation**: Persistent sidebar with permission-based menu items and collapsible admin section

### State Management
- Context API for user authentication and permissions
- Local state for component-specific data
- API service layer for backend communication

### Security
- JWT token-based authentication
- Role-based access control (RBAC)
- Permission-based UI rendering
- Secure API communication

### Accessibility
- ARIA labels and semantic HTML
- Keyboard navigation support
- Screen reader compatibility
- WCAG 2.1 compliance

## Components

### Pages
- `Dashboard` - Main overview with sample listing and filtering
- `AccessioningForm` - Multi-step sample accessioning wizard
- `ContainerManagement` - Container instance creation and management
- `BatchManagement` - Batch creation and management
- `ResultsManagement` - Results entry and review
- `ClientProjects` - Client project management
- `Login` - User authentication
- `AdminOverview` - Admin dashboard with statistics (admin-only)

### Accessioning Components
- `SampleDetailsStep` - Sample information entry with double-entry validation
- `TestAssignmentStep` - Analysis selection and assignment
- `ReviewStep` - Final review before submission

### Container Components
- `ContainerForm` - Container instance creation/editing form
- `ContainerDetails` - Container information and contents management
- `ContainerGrid` - Batch container grid display

### Admin Components
- `AdminOverview` - Main admin dashboard with statistics (admin-only)
- `ContainerTypesManagement` - Manage container types (admin-only)
- `ListsManagement` - Manage lists and list entries (admin-only)
- `AnalysesManagement` - Manage analyses (CRUD operations, admin-only)
- `AnalysisAnalytesConfig` - Configure analyte rules and validation for analyses (admin-only)
- `AnalytesManagement` - Manage analytes (CRUD operations, admin-only)
- `TestBatteriesManagement` - Manage test batteries with analyses grouping (admin-only)
- `BatteryFormDialog` - Create/edit battery dialog with analysis selector
- `AnalysisSelector` - Multi-select component for adding analyses to batteries with sequence/optional controls
- `CustomFieldsManagement` - Manage custom attribute configurations (Post-MVP, admin-only)
- `CustomFieldDialog` - Create/edit custom attribute configuration dialog
- `UsersManagement` - Manage users (CRUD operations, admin-only)
- `RolesManagement` - Manage roles and permissions (admin-only)

### Layout Components
- `MainLayout` - Unified layout wrapper with sidebar and top AppBar for all authenticated routes
- `Sidebar` - Persistent sidebar navigation with permission-based menu items and collapsible admin accordion
- `Logo` - Application logo component (clickable, navigates to dashboard)

### Shared Components
- `UserContext` - Authentication and permission management
- `CustomAttributeField` - Reusable component for rendering custom attribute fields dynamically (text, number, date, boolean, select)

## API Integration

### Endpoints Used
- `POST /auth/login` - User authentication
- `GET /auth/me` - Current user information
- `GET /samples` - List samples with filtering
- `POST /samples` - Create new sample
- `PATCH /samples/{id}` - Update sample
- `GET /tests` - List tests
- `POST /tests` - Create test assignment
- `GET /containers` - List containers
- `POST /containers` - Create container instance
- `GET /containers/types` - Get container types (public lookup)
- `POST /containers/types` - Create container type (admin)
- `PATCH /containers/types/{id}` - Update container type (admin)
- `POST /contents` - Link sample to container
- `GET /analyses` - List available analyses
- `GET /test-batteries` - List test batteries
- `GET /lists` - Get all lists with entries
- `GET /lists/{name}/entries` - Get lookup data
- `POST /lists` - Create list (admin)
- `POST /lists/{name}/entries` - Add entry to list (admin)
- `GET /units` - Get measurement units
- `GET /projects` - Get user projects
- `GET /batches` - List batches
- `POST /batches` - Create batch (with cross-project and QC support)
- `POST /batches/validate-compatibility` - Validate container compatibility
- `POST /results/batch` - Enter batch results
- `GET /test-batteries` - List test batteries
- `GET /client-projects` - List client projects
- `GET /admin/custom-attributes` - List custom attribute configs (admin)
- `POST /admin/custom-attributes` - Create custom attribute config (admin)
- `PATCH /admin/custom-attributes/{id}` - Update custom attribute config (admin)
- `DELETE /admin/custom-attributes/{id}` - Delete custom attribute config (admin)

### Error Handling
- Global error handling with user-friendly messages
- Form validation with real-time feedback
- Network error recovery
- Authentication error handling

## Testing

### Test Coverage
- Component rendering tests
- Form submission tests
- User interaction tests
- API integration tests
- Error handling tests

### Running Tests
```bash
npm test
```

### Test Structure
- Unit tests for individual components
- Integration tests for user workflows
- Mock API responses for consistent testing
- Accessibility testing with screen readers

## Development

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running on localhost:8000

### Setup
```bash
npm install
npm start
```

### Environment Variables
```env
REACT_APP_API_URL=http://localhost:8000
```

### Code Quality
- ESLint for code linting
- TypeScript for type safety
- Prettier for code formatting
- Husky for pre-commit hooks

## Deployment

### Build
```bash
npm run build
```

### Docker
The frontend is containerized with Nginx for production serving.

### Environment Configuration
- Development: `npm start`
- Production: Built files served via Nginx
- API URL configurable via environment variables

## Navigation

NimbleLIMS uses a unified sidebar navigation system:

- **Sidebar**: Persistent left sidebar (240px) with all navigation items
- **Permission-Based**: Menu items shown/hidden based on user permissions
- **Admin Accordion**: Collapsible admin section with submenu items
- **Top AppBar**: Dynamic page titles, back button for nested routes, user info, logout
- **Responsive**: Permanent drawer on desktop, temporary drawer on mobile

See [`.docs/navigation.md`](../.docs/navigation.md) for complete navigation documentation.

## User Workflows

### Sample Accessioning Workflow
1. Click "Accessioning" in sidebar (requires `sample:create` permission)
2. Toggle bulk mode if needed (for multiple samples)
3. Fill sample details (name, type, dates, etc.)
   - In bulk mode: Fill common fields and unique per-sample data in table
4. Enable double-entry validation if needed
5. Select analyses or test battery for testing
6. Review all information
7. Submit to create sample(s), container(s), and tests
   - Bulk mode: Creates all samples atomically in single transaction

### Container Management Workflow
1. Click "Containers" in sidebar (requires `sample:update` permission)
2. Create new container with type and specifications
3. Add samples to container with concentration/amount
4. Manage container contents
5. Track container hierarchy

### Dashboard Workflow
1. View sample summary statistics
2. Filter samples by status/project
3. Track sample progress
4. Monitor test assignments

### Admin Configuration Workflow
1. Click "Admin" accordion in sidebar (requires `config:edit` permission)
2. Accordion expands to show admin submenu items
3. Select admin section (e.g., "Lists Management", "Analyses Management")
4. Manage configuration items via CRUD operations
5. Use back button in AppBar for nested routes (e.g., Analysis Analytes Configuration)

## Security Considerations

### Authentication
- JWT tokens stored in localStorage
- Automatic token refresh
- Secure logout with token cleanup

### Authorization
- Role-based component rendering
- Permission-based feature access
- Client data isolation

### Data Protection
- Input validation and sanitization
- XSS protection
- CSRF token handling
- Secure API communication

## Performance

### Optimization
- Code splitting for route-based loading
- Lazy loading for heavy components
- Memoization for expensive calculations
- Efficient re-rendering with React.memo

### Monitoring
- Error boundary implementation
- Performance metrics tracking
- User interaction analytics
- API response time monitoring
